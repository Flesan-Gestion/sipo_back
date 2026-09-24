"""
Alcance territorial de usuarios SIP (razones sociales y centros de costo).

Tablas en sip_db (no managed por migraciones Django estándar):
- cf_rrhh_sip_perfil_empresa
- cf_rrhh_sip_perfil_cc
"""

from __future__ import annotations

import logging

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.exceptions import ValidationError

from sipo.constants import SIPO_ROL_ADMIN

logger = logging.getLogger(__name__)

SIP_DB = 'sip_db'
_TABLES_READY = False


def ensure_scope_tables() -> None:
    global _TABLES_READY
    if _TABLES_READY:
        return
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_rrhh_sip_perfil_empresa (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cf_rrhh_sip_perfil_id INT NOT NULL,
                    empresa_rut VARCHAR(32) NOT NULL,
                    empresa_nombre VARCHAR(200) NULL,
                    UNIQUE KEY uq_perfil_empresa (cf_rrhh_sip_perfil_id, empresa_rut),
                    KEY idx_perfil_empresa_perfil (cf_rrhh_sip_perfil_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_rrhh_sip_perfil_cc (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cf_rrhh_sip_perfil_id INT NOT NULL,
                    empresa_rut VARCHAR(32) NOT NULL,
                    centro_costo_id VARCHAR(100) NOT NULL,
                    centro_costo_nombre VARCHAR(200) NULL,
                    UNIQUE KEY uq_perfil_cc (cf_rrhh_sip_perfil_id, centro_costo_id),
                    KEY idx_perfil_cc_perfil (cf_rrhh_sip_perfil_id)
                )
                """
            )
        _TABLES_READY = True
    except (OperationalError, ProgrammingError):
        logger.exception('No se pudieron crear tablas de alcance territorial')


def _normalize_codes(values) -> list[str]:
    if not values:
        return []
    seen = set()
    result = []
    for raw in values:
        code = str(raw or '').strip()
        if not code or code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def get_assignments_for_perfil(perfil_id: int) -> dict:
    ensure_scope_tables()
    empresas: list[dict] = []
    centros: list[dict] = []
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT empresa_rut, COALESCE(empresa_nombre, '')
                FROM cf_rrhh_sip_perfil_empresa
                WHERE cf_rrhh_sip_perfil_id = %s
                ORDER BY empresa_nombre, empresa_rut
                """,
                [perfil_id],
            )
            for rut, nombre in cursor.fetchall():
                empresas.append(
                    {
                        'id': str(rut).strip(),
                        'external_code': str(rut).strip(),
                        'nombre': (nombre or '').strip() or str(rut).strip(),
                    }
                )

            cursor.execute(
                """
                SELECT centro_costo_id, COALESCE(centro_costo_nombre, ''), empresa_rut
                FROM cf_rrhh_sip_perfil_cc
                WHERE cf_rrhh_sip_perfil_id = %s
                ORDER BY centro_costo_nombre, centro_costo_id
                """,
                [perfil_id],
            )
            for cc_id, nombre, empresa_rut in cursor.fetchall():
                centros.append(
                    {
                        'id': str(cc_id).strip(),
                        'external_code': str(cc_id).strip(),
                        'nombre': (nombre or '').strip() or str(cc_id).strip(),
                        'empresa_rut': str(empresa_rut or '').strip(),
                    }
                )
    except (OperationalError, ProgrammingError):
        logger.exception('No se pudo leer alcance del perfil %s', perfil_id)

    return {
        'empresas': empresas,
        'centros_costo': centros,
        'empresas_ids': [e['id'] for e in empresas],
        'centros_costo_ids': [c['id'] for c in centros],
    }


def set_assignments_for_perfil(
    perfil_id: int,
    *,
    empresas_ids: list | None,
    centros_costo_ids: list | None,
    empresas_meta: dict[str, str] | None = None,
    centros_meta: dict[str, dict] | None = None,
    require_non_empty: bool = True,
) -> dict:
    ensure_scope_tables()
    empresas_ids = _normalize_codes(empresas_ids)
    centros_costo_ids = _normalize_codes(centros_costo_ids)
    empresas_meta = empresas_meta or {}
    centros_meta = centros_meta or {}

    if require_non_empty:
        if not empresas_ids:
            raise ValidationError({'empresas_ids': ['Debe asignar al menos una razón social.']})
        if not centros_costo_ids:
            raise ValidationError({'centros_costo_ids': ['Debe asignar al menos un centro de costo.']})

    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                'DELETE FROM cf_rrhh_sip_perfil_empresa WHERE cf_rrhh_sip_perfil_id = %s',
                [perfil_id],
            )
            cursor.execute(
                'DELETE FROM cf_rrhh_sip_perfil_cc WHERE cf_rrhh_sip_perfil_id = %s',
                [perfil_id],
            )
            for rut in empresas_ids:
                cursor.execute(
                    """
                    INSERT INTO cf_rrhh_sip_perfil_empresa
                        (cf_rrhh_sip_perfil_id, empresa_rut, empresa_nombre)
                    VALUES (%s, %s, %s)
                    """,
                    [perfil_id, rut, (empresas_meta.get(rut) or '')[:200]],
                )
            for cc_id in centros_costo_ids:
                meta = centros_meta.get(cc_id) or {}
                cursor.execute(
                    """
                    INSERT INTO cf_rrhh_sip_perfil_cc
                        (cf_rrhh_sip_perfil_id, empresa_rut, centro_costo_id, centro_costo_nombre)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [
                        perfil_id,
                        str(meta.get('empresa_rut') or '')[:32],
                        cc_id,
                        str(meta.get('nombre') or '')[:200],
                    ],
                )
    except (OperationalError, ProgrammingError) as exc:
        logger.exception('No se pudo guardar alcance del perfil %s', perfil_id)
        raise ValidationError(
            {'non_field_errors': ['No fue posible guardar razones sociales / centros de costo.']}
        ) from exc

    return get_assignments_for_perfil(perfil_id)


def delete_assignments_for_perfil(perfil_id: int) -> None:
    ensure_scope_tables()
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                'DELETE FROM cf_rrhh_sip_perfil_empresa WHERE cf_rrhh_sip_perfil_id = %s',
                [perfil_id],
            )
            cursor.execute(
                'DELETE FROM cf_rrhh_sip_perfil_cc WHERE cf_rrhh_sip_perfil_id = %s',
                [perfil_id],
            )
    except (OperationalError, ProgrammingError):
        logger.exception('No se pudo eliminar alcance del perfil %s', perfil_id)


def get_perfil_id_by_email(email: str | None) -> int | None:
    normalized = (email or '').strip().lower()
    if not normalized:
        return None
    try:
        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT cf_rrhh_sip_perfil_id
                FROM cf_rrhh_sip_perfil
                WHERE LOWER(TRIM(usuario_email)) = %s
                ORDER BY cf_rol_id ASC
                LIMIT 1
                """,
                [normalized],
            )
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError):
        return None
    return int(row[0]) if row else None


def get_scope_for_user(user) -> dict:
    """
    Retorna alcance territorial del usuario autenticado.
    Admin global: is_admin=True y listas vacías (sin restricción).
    """
    rol_id = getattr(user, 'sip_rol_id', None)
    try:
        rol_id = int(rol_id) if rol_id is not None else None
    except (TypeError, ValueError):
        rol_id = None

    if rol_id == SIPO_ROL_ADMIN:
        return {
            'is_admin': True,
            'empresas_ids': [],
            'centros_costo_ids': [],
            'empresas': [],
            'centros_costo': [],
        }

    email = (
        getattr(user, 'email', None) or getattr(user, 'username', None) or ''
    ).strip().lower()
    perfil_id = get_perfil_id_by_email(email)
    if not perfil_id:
        return {
            'is_admin': False,
            'empresas_ids': [],
            'centros_costo_ids': [],
            'empresas': [],
            'centros_costo': [],
        }

    data = get_assignments_for_perfil(perfil_id)
    data['is_admin'] = False
    return data


def user_has_unrestricted_scope(user) -> bool:
    return int(getattr(user, 'sip_rol_id', -1) or -1) == SIPO_ROL_ADMIN


def filter_empresas_by_scope(empresas: list[dict], scope: dict) -> list[dict]:
    if scope.get('is_admin'):
        return empresas
    allowed = set(scope.get('empresas_ids') or [])
    if not allowed:
        return []
    return [e for e in empresas if str(e.get('external_code') or '').strip() in allowed]


def filter_centros_in_empresa_tree(empresas: list[dict], allowed_cc: set[str]) -> list[dict]:
    """Recorta centros_costo dentro del árbol de maestros a los IDs permitidos."""
    if not allowed_cc:
        return empresas
    result = []
    for empresa in empresas:
        unidades = []
        for uni in empresa.get('unidades') or []:
            departamentos = []
            for dep in uni.get('departamentos') or []:
                ccs = [
                    cc
                    for cc in (dep.get('centros_costo') or [])
                    if str(cc.get('external_code') or '').strip() in allowed_cc
                ]
                if ccs:
                    departamentos.append({**dep, 'centros_costo': ccs})
            if departamentos:
                unidades.append({**uni, 'departamentos': departamentos})
        result.append({**empresa, 'unidades': unidades})
    return result
