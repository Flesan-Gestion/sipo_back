"""Validación RUT activo en iBuilder y SAP (paridad ValidacionRut legado)."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from requests.exceptions import RequestException, Timeout

from .candidato_validaciones import format_rut_sap_pad, is_valid_rut, normalize_rut, rut_key

logger = logging.getLogger(__name__)

SIP_DB = 'sip_db'

BUILDER_PROJECT_SQL = """
SELECT
    CASE
        WHEN bp_cc.id IS NOT NULL THEN bp_cc.id
        WHEN bp_pu.id IS NOT NULL THEN bp_pu.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN b.id IS NOT NULL THEN b.id
        WHEN bp_dep.id IS NOT NULL THEN bp_dep.id
    END AS id_builder
FROM cf_rrhh_sip_obra
LEFT JOIN builder_proyectos bp_cc ON (
    REGEXP_REPLACE(cf_rrhh_sip_obra.cf_rrhh_sip_cc, '[[:alpha:]]+$', '') =
    bp_cc.costcenterintegration
)
LEFT JOIN builder_proyectos bp_pu ON (
    CASE
        WHEN SUBSTRING(cf_rrhh_sip_obra.cf_rrhh_sip_cc, -2, 2) IN ('PU', 'NS', 'GG')
        THEN SUBSTRING(
            cf_rrhh_sip_obra.cf_rrhh_sip_cc,
            1,
            LENGTH(cf_rrhh_sip_obra.cf_rrhh_sip_cc) - 2
        )
        ELSE cf_rrhh_sip_obra.cf_rrhh_sip_cc
    END = bp_pu.costcenterintegration
)
LEFT JOIN builder_proyectos a
    ON cf_rrhh_sip_obra.cf_rrhh_sip_uni = a.costcenterintegration
LEFT JOIN builder_proyectos b
    ON cf_rrhh_sip_obra.cf_rrhh_sip_rut = b.costcenterintegration
LEFT JOIN builder_proyectos bp_dep
    ON cf_rrhh_sip_obra.cf_rrhh_sip_dep = bp_dep.costcenterintegration
WHERE cf_rrhh_sip_obra.cf_rrhh_sip_id = %s
LIMIT 1
"""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = getattr(settings, name, None)
    if raw is None:
        raw = __import__('os').getenv(name, str(default))
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')


def _ibuilder_base_url() -> str:
    return (
        getattr(settings, 'IBUILDER_GATEWAY_URL', None)
        or getattr(settings, 'IBUILDER_API_URL', None)
        or 'https://gateway.builder.cl'
    ).rstrip('/')


def _ibuilder_api_key() -> str:
    return (getattr(settings, 'IBUILDER_API_TOKEN', None) or '').strip()


def _ibuilder_login_email() -> str:
    return (getattr(settings, 'IBUILDER_API_EMAIL', None) or '').strip()


def _ibuilder_login_password() -> str:
    return (getattr(settings, 'IBUILDER_API_PASSWORD', None) or '').strip()


def _ibuilder_timeout() -> int:
    try:
        return max(3, int(getattr(settings, 'IBUILDER_API_TIMEOUT', 15)))
    except (TypeError, ValueError):
        return 15


def _rut_ibuilder_payload(rut: str) -> str:
    """RUT para getStatus (paridad rut1 legado: sin puntos, guión opcional)."""
    rut1 = str(rut or '').replace('.', '').strip()
    if rut1.startswith('0'):
        rut1 = rut1[-9:] if len(rut1) >= 9 else rut1.lstrip('0')
    return rut1


def _rut_key(value: str) -> str:
    return str(value or '').replace('.', '').replace('-', '').upper()


def _get_builder_project_id(sip_id: int) -> str | None:
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(BUILDER_PROJECT_SQL, [sip_id])
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('builder_proyectos lookup failed sip_id=%s: %s', sip_id, exc)
        return None
    if not row or row[0] is None:
        return None
    return str(row[0])


def _ibuilder_session_cookie() -> str | None:
    base = _ibuilder_base_url()
    email = _ibuilder_login_email()
    password = _ibuilder_login_password()
    api_key = _ibuilder_api_key()
    if not email or not password or not api_key:
        logger.warning('iBuilder login omitido: faltan IBUILDER_API_EMAIL/PASSWORD/TOKEN')
        return None
    try:
        response = requests.post(
            f'{base}/session/v1/login',
            json={'email': email, 'password': password},
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': api_key,
            },
            timeout=_ibuilder_timeout(),
        )
        response.raise_for_status()
        set_cookie = response.headers.get('Set-Cookie') or ''
        match = re.search(r'([^;]+)', set_cookie)
        return match.group(1) if match else set_cookie or None
    except (RequestException, Timeout) as exc:
        logger.warning('iBuilder session login failed: %s', exc)
        return None


def _parse_ibuilder_active(payload: Any, rut1: str) -> bool:
    """Paridad legado: primer valor interno; activo si coincide con rut1."""
    if not isinstance(payload, dict):
        return False

    rut1_key = _rut_key(rut1)
    for outer in payload.values():
        if not isinstance(outer, dict):
            continue
        for inner in outer.values():
            if inner is False or inner is None:
                return False
            if inner is True:
                return True
            inner_key = _rut_key(str(inner))
            if inner_key and inner_key == rut1_key:
                return True
            return False
    return False


def _check_ibuilder_active(*, rut: str, sip_id: int) -> tuple[bool, str, str | None]:
    project_id = _get_builder_project_id(sip_id)
    if not project_id:
        logger.info('iBuilder getStatus omitido: sin proyecto Builder para sip_id=%s', sip_id)
        return False, '', None

    api_key = _ibuilder_api_key()
    if not api_key:
        logger.warning('iBuilder API token ausente; omitiendo getStatus')
        return False, '', project_id

    rut1 = _rut_ibuilder_payload(rut)
    cookie = _ibuilder_session_cookie()
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
    }
    if cookie:
        headers['Cookie'] = cookie

    url = f'{_ibuilder_base_url()}/worker/v1.1/{project_id}/workers/getStatus'
    try:
        response = requests.post(
            url,
            json={'ruts': [rut1]},
            headers=headers,
            timeout=_ibuilder_timeout(),
        )
        response.raise_for_status()
        payload = response.json()
    except (RequestException, Timeout, ValueError, TypeError) as exc:
        logger.warning('iBuilder getStatus failed rut=%s sip_id=%s: %s', rut, sip_id, exc)
        return False, '', project_id

    if _parse_ibuilder_active(payload, rut1):
        return True, 'ibuilder', project_id
    return False, '', project_id


def _check_sap_colaborador_activo(rut: str) -> tuple[bool, dict[str, Any] | None]:
    rut_digits = rut_key(format_rut_sap_pad(rut) or normalize_rut(rut) or rut)
    if not rut_digits:
        return False, None

    sql = """
        SELECT empresa, nombre_centro_costo, national_id, empl_status
        FROM colaboradores
        WHERE empl_status = '41111'
          AND REPLACE(colaboradores.national_id, '-', '') =
              REPLACE(REPLACE(%s, '.', ''), '-', '')
        LIMIT 1
    """
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(sql, [rut])
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('SAP colaboradores lookup failed rut=%s: %s', rut, exc)
        return False, None

    if not row:
        return False, None

    columns = ['empresa', 'nombre_centro_costo', 'national_id', 'empl_status']
    return True, dict(zip(columns, row))


def validar_rut_activo(rut: str, *, sip_id: int | None = None) -> dict:
    """
    Verifica contrato activo en iBuilder (getStatus) y SAP local (empl_status 41111).
    """
    if not _env_bool('CHECK_IBUILDER_SAP_ENABLED', False):
        return {
            'activo': False,
            'motivo': '',
            'bypass': True,
            'fuente': None,
            'builder_proyecto_id': None,
        }

    if not is_valid_rut(rut):
        return {
            'activo': False,
            'motivo': 'RUT inválido',
            'bypass': False,
            'fuente': None,
            'builder_proyecto_id': None,
        }

    builder_proyecto_id: str | None = None
    if sip_id:
        ib_active, fuente, builder_proyecto_id = _check_ibuilder_active(
            rut=rut,
            sip_id=int(sip_id),
        )
        if ib_active:
            return {
                'activo': True,
                'motivo': (
                    'El trabajador aún está activo en iBuilder; '
                    'favor agregar fecha de término según corresponda.'
                ),
                'bypass': False,
                'fuente': fuente or 'ibuilder',
                'builder_proyecto_id': builder_proyecto_id,
            }

    sap_active, detalle = _check_sap_colaborador_activo(rut)
    if sap_active and detalle:
        empresa = detalle.get('empresa') or ''
        obra = detalle.get('nombre_centro_costo') or ''
        return {
            'activo': True,
            'motivo': (
                f'El trabajador aún está activo en SAP en la Empresa: {empresa} '
                f'Obra: {obra}; favor consultar al administrativo de RRHH '
                'correspondiente antes de seguir con la contratación.'
            ),
            'bypass': False,
            'fuente': 'sap',
            'detalle': detalle,
            'builder_proyecto_id': builder_proyecto_id,
        }

    return {
        'activo': False,
        'motivo': '',
        'bypass': False,
        'fuente': None,
        'builder_proyecto_id': builder_proyecto_id,
    }
