"""Integración creación trabajadores iBuilder (paridad class_sip_obra.php)."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from requests.exceptions import RequestException, Timeout

from ..constants import (
    SIPO_CANDIDATO_ACTIVO,
    SIPO_CANDIDATO_SELECCIONADO,
)
from ..models import SipoCandidatoObra, SipoObra
from .rut_validation import _ibuilder_session_cookie

logger = logging.getLogger(__name__)

SIP_DB = 'sip_db'

BUILDER_WORKER_CONTEXT_SQL = """
SELECT
    CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN b.id IS NOT NULL THEN b.id
    END AS id_builder,
    builder_empresas.id AS empresa_id,
    z.id AS cargo_id,
    t.id AS turno_id,
    builder_tipo_contrato.id AS tipo_contrato,
    builder_centro_gestion.id AS centro_gestion_id
FROM cf_rrhh_sip_candidato_obra co
INNER JOIN cf_rrhh_sip_obra o ON co.cf_rrhh_sip_obra_id = o.cf_rrhh_sip_id
LEFT JOIN builder_proyectos ON (
    CASE
        WHEN SUBSTRING(o.cf_rrhh_sip_cc, -2, 2) IN ('PU', 'NS', 'GG')
        THEN SUBSTRING(o.cf_rrhh_sip_cc, 1, LENGTH(o.cf_rrhh_sip_cc) - 2)
        ELSE o.cf_rrhh_sip_cc
    END = builder_proyectos.costcenterintegration
)
LEFT JOIN builder_proyectos a ON o.cf_rrhh_sip_uni = a.costcenterintegration
LEFT JOIN builder_proyectos b ON o.cf_rrhh_sip_rut = b.costcenterintegration
LEFT JOIN builder_proyectos c ON o.cf_rrhh_sip_dep = c.costcenterintegration
LEFT JOIN builder_empresas ON (
    builder_empresas.id_proyecto = CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN b.id IS NOT NULL THEN b.id
    END
    AND (builder_empresas.subcontrato = '' OR builder_empresas.subcontrato IS NULL)
)
LEFT JOIN (
    SELECT MAX(id) AS id, nombre, id_proyecto
    FROM builder_cargos
    GROUP BY id_proyecto, nombre
) AS z ON (
    z.id_proyecto = CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN b.id IS NOT NULL THEN b.id
    END
    AND co.cf_rrhh_sip_obra_candidato_nomcar = UPPER(z.nombre)
)
LEFT JOIN (
    SELECT MAX(id) AS id, nombre, id_proyecto
    FROM builder_turnos
    GROUP BY id_proyecto, nombre
) AS t ON (
    t.id_proyecto = CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN b.id IS NOT NULL THEN b.id
    END
    AND t.nombre = co.cf_rrhh_sip_obra_candidato_horario_trabajo
)
LEFT JOIN builder_tipo_contrato ON (
    builder_tipo_contrato.id_proyecto = CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN b.id IS NOT NULL THEN b.id
    END
    AND TRIM(UPPER(builder_tipo_contrato.nombre)) =
        UPPER(co.cf_rrhh_sip_obra_candidato_tipo_contrato)
)
LEFT JOIN builder_centro_gestion ON (
    builder_centro_gestion.id_proyecto = CASE
        WHEN builder_proyectos.id IS NOT NULL THEN builder_proyectos.id
        WHEN a.id IS NOT NULL THEN a.id
        WHEN c.id IS NOT NULL THEN c.id
        WHEN b.id IS NOT NULL THEN b.id
    END
    AND o.cf_rrhh_sip_cc = builder_centro_gestion.nombre
)
WHERE co.cf_rrhh_sip_obra_id = %s
  AND co.cf_rrhh_sip_obra_candidato_id = %s
LIMIT 1
"""


def _gateway_url() -> str:
    return (
        getattr(settings, 'IBUILDER_GATEWAY_URL', None)
        or getattr(settings, 'IBUILDER_API_URL', None)
        or 'https://gateway.builder.cl'
    ).rstrip('/')


def _api_token() -> str:
    return (getattr(settings, 'IBUILDER_API_TOKEN', None) or '').strip()


def _timeout() -> int:
    try:
        return max(3, int(getattr(settings, 'IBUILDER_API_TIMEOUT', 15)))
    except (TypeError, ValueError):
        return 15


def _sync_enabled() -> bool:
    return bool(getattr(settings, 'IBUILDER_SYNC_ENABLED', False))


def _rut_ibuilder_worker(value: str | None) -> str:
    """
    Paridad legado POST /workers:
    REPLACE(rut,'.',''); si primer char='0' → últimos 9 chars.
    """
    rut = str(value or '').replace('.', '').strip()
    if rut[:1] == '0':
        return rut[-9:] if len(rut) >= 9 else rut
    return rut


def _parse_ibuilder_create_error(
    *,
    status_code: int,
    body: Any,
    sip_id: int,
    nombre: str,
) -> str | None:
    """
    Paridad legado: errors[0].message | statusCode 404 | validation.body.message.
    Retorna None si la respuesta se considera éxito.
    """
    data = body if isinstance(body, dict) else {}
    api_status = data.get('statusCode')
    errors = data.get('errors')
    err0 = None
    if isinstance(errors, list) and errors:
        err0 = errors[0] if isinstance(errors[0], dict) else None
    elif isinstance(errors, dict):
        err0 = errors.get('0') or errors.get(0)
        if not isinstance(err0, dict):
            err0 = None

    err_msg = ''
    if isinstance(err0, dict):
        err_msg = str(err0.get('message') or '').strip()

    if api_status == 404 or status_code == 404:
        return f'La obra no esta asociada a un ID en builder sip N° {sip_id}'
    if err_msg:
        return f'{err_msg} para el colaborador {nombre} sip N° {sip_id}'
    if api_status:
        validation = data.get('validation') or {}
        if isinstance(validation, dict):
            vbody = validation.get('body') or {}
            if isinstance(vbody, dict) and vbody.get('message'):
                return (
                    f"{vbody['message']} para el colaborador {nombre} sip N° {sip_id}"
                )
        return f'iBuilder statusCode={api_status} para el colaborador {nombre} sip N° {sip_id}'
    if status_code not in (200, 201):
        return (
            f'iBuilder HTTP {status_code} para el colaborador {nombre} sip N° {sip_id}'
        )
    return None


def _fmt_date(value: Any) -> str:
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    return str(value).strip()[:10]


def _gender_code(value: str | None) -> str:
    gen = (value or '').strip().upper()
    if gen == 'F':
        return 'GENDER_FEMALE'
    if gen == 'M':
        return 'GENDER_MALE'
    return ''


def _full_name(candidato: SipoCandidatoObra) -> str:
    parts = [
        candidato.cf_rrhh_sip_obra_candidato_ap,
        candidato.cf_rrhh_sip_obra_candidato_am,
        candidato.cf_rrhh_sip_obra_candidato_nombre,
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip()).upper()


def _first_names(candidato: SipoCandidatoObra) -> str:
    parts = [
        candidato.cf_rrhh_sip_obra_candidato_nombre,
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip()).upper()


def _last_names(candidato: SipoCandidatoObra) -> str:
    parts = [
        candidato.cf_rrhh_sip_obra_candidato_ap,
        candidato.cf_rrhh_sip_obra_candidato_am,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip()).upper()


def _load_builder_context(*, sip_id: int, candidato_id: str) -> dict[str, Any] | None:
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(BUILDER_WORKER_CONTEXT_SQL, [sip_id, candidato_id])
            row = cursor.fetchone()
            if not row:
                return None
            columns = [col[0] for col in cursor.description]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning(
            'builder_sync context lookup failed sip_id=%s candidato=%s: %s',
            sip_id,
            candidato_id,
            exc,
        )
        return None
    return dict(zip(columns, row))


def _build_worker_payload(
    candidato: SipoCandidatoObra,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    return {
        'className': 'Worker',
        'name': _full_name(candidato),
        'firstName': _first_names(candidato),
        'lastName': _last_names(candidato),
        'rut': _rut_ibuilder_worker(candidato.cf_rrhh_sip_obra_candidato_rut),
        'subCompany': str(ctx.get('empresa_id') or '').strip(),
        'projectPosition': str(ctx.get('cargo_id') or '').strip(),
        'fileNumber': (candidato.cf_rrhh_sip_obra_user_id or '').strip(),
        'start': _fmt_date(candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso),
        'blocked': False,
        'terminated': False,
        'shift': str(ctx.get('turno_id') or '').strip(),
        'shiftsHistory': [],
        'months': [],
        'processesAllowed': [],
        'correlative': 1,
        'color': '#cfd3d7',
        'chief': None,
        'phone': None,
        'end': None,
        'role': None,
        'email': (candidato.cf_rrhh_sip_obra_candidato_correo or '').strip().lower(),
        'contractType': str(ctx.get('tipo_contrato') or '').strip(),
        'documentType': None,
        'imageUrl': None,
        'birthDate': _fmt_date(candidato.cf_rrhh_sip_obra_candidato_fecha_nacimiento),
        'gender': _gender_code(candidato.cf_rrhh_sip_obra_candidato_genero),
    }


def _mark_builder_ok(candidato: SipoCandidatoObra) -> None:
    SipoCandidatoObra.objects.using(SIP_DB).filter(
        cf_rrhh_sip_obra_candidato_id=candidato.cf_rrhh_sip_obra_candidato_id,
    ).update(cf_rrhh_sip_obra_candidato_estado_builder=1)
    candidato.cf_rrhh_sip_obra_candidato_estado_builder = 1


def crear_trabajador_ibuilder(candidato: SipoCandidatoObra, obra_context: SipoObra) -> dict[str, Any]:
    """
    Crea trabajador en iBuilder.
    Retorna {builder_ok, error, candidato_id}.
    """
    candidato_id = candidato.cf_rrhh_sip_obra_candidato_id
    sip_id = int(obra_context.cf_rrhh_sip_id)
    nombre = _full_name(candidato) or str(candidato_id)

    def _fail(msg: str) -> dict[str, Any]:
        logger.warning(
            'builder_sync FAIL candidato=%s sip_id=%s: %s',
            candidato_id,
            sip_id,
            msg,
        )
        return {
            'builder_ok': False,
            'error': msg,
            'candidato_id': candidato_id,
        }

    if not _sync_enabled():
        return _fail('IBUILDER_SYNC_ENABLED=False')

    api_key = _api_token()
    if not api_key:
        return _fail('Falta IBUILDER_API_TOKEN')

    ctx = _load_builder_context(sip_id=sip_id, candidato_id=candidato_id)
    if not ctx or not ctx.get('id_builder'):
        return _fail(f'La obra no esta asociada a un ID en builder sip N° {sip_id}')

    project_id = str(ctx['id_builder'])
    payload = _build_worker_payload(candidato, ctx)
    cookie = _ibuilder_session_cookie()
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
    }
    if cookie:
        headers['Cookie'] = cookie

    url = f'{_gateway_url()}/worker/v1.1/{project_id}/workers'
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=_timeout(),
        )
    except (RequestException, Timeout) as exc:
        return _fail(
            f'Error de conexión iBuilder para el colaborador {nombre} sip N° {sip_id}: {exc}'
        )

    try:
        body = response.json()
    except ValueError:
        body = {'raw': (response.text or '')[:500]}

    err = _parse_ibuilder_create_error(
        status_code=response.status_code,
        body=body,
        sip_id=sip_id,
        nombre=nombre,
    )
    if err:
        return _fail(err)

    _mark_builder_ok(candidato)
    logger.info('builder_sync OK candidato=%s sip_id=%s project=%s', candidato_id, sip_id, project_id)
    try:
        from .notifications import send_email_builder_ok

        send_email_builder_ok(obra_context, candidato)
    except Exception:
        logger.warning(
            'builder_sync: fallo mail builder_ok candidato=%s',
            candidato_id,
            exc_info=True,
        )
    return {
        'builder_ok': True,
        'error': '',
        'candidato_id': candidato_id,
    }


def sync_trabajadores_ibuilder_obra(
    *,
    sip_id: int,
    obra: SipoObra,
    solo_activos: bool = False,
) -> dict:
    """
    Sincroniza candidatos hacia iBuilder.
    - solo_activos=True (6→7): todos los candidatos activos.
    - solo_activos=False: candidatos activos seleccionados.
    """
    if not _sync_enabled():
        return {
            'sip_id': sip_id,
            'candidatos_procesados': 0,
            'builder_ok': 0,
            'skipped': True,
            'message': 'IBUILDER_SYNC_ENABLED=False — sin escritura en iBuilder',
            'resultados': [],
        }

    qs = SipoCandidatoObra.objects.using(SIP_DB).filter(
        cf_rrhh_sip_obra_id=sip_id,
        cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
    )
    if not solo_activos:
        qs = qs.filter(cf_rrhh_sip_obra_candidato_seleccionado=SIPO_CANDIDATO_SELECCIONADO)

    candidatos = list(qs)
    resultados = []
    ok_count = 0
    for candidato in candidatos:
        result = crear_trabajador_ibuilder(candidato, obra)
        if result.get('builder_ok'):
            ok_count += 1
        resultados.append({
            'candidato_id': candidato.cf_rrhh_sip_obra_candidato_id,
            'builder_ok': bool(result.get('builder_ok')),
            'error': result.get('error') or '',
            'estado_builder': candidato.cf_rrhh_sip_obra_candidato_estado_builder,
        })

    return {
        'sip_id': sip_id,
        'candidatos_procesados': len(candidatos),
        'builder_ok': ok_count,
        'skipped': False,
        'resultados': resultados,
    }
