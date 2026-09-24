import logging
import os
from dataclasses import dataclass

from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)

SIPO_OBRA_DB = 'sip_db'
SIPO_ROL_ADMIN = 1


@dataclass
class SipoAccess:
    rol_id: int
    rol_name: str


def _fetch_rol(email: str | None) -> SipoAccess | None:
    normalized = (email or '').strip().lower()
    if not normalized:
        return None

    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT p.cf_rol_id, r.cf_rol_name
                FROM cf_rrhh_sip_perfil p
                INNER JOIN cf_rrhh_sip_rol r ON r.cf_rol_id = p.cf_rol_id
                WHERE LOWER(TRIM(p.usuario_email)) = %s
                ORDER BY p.cf_rol_id DESC
                LIMIT 1
                """,
                [normalized],
            )
            row = cursor.fetchone()
    except OperationalError:
        logger.exception('No se pudo consultar cf_rrhh_sip_perfil / cf_rrhh_sip_rol')
        return None

    if not row:
        return None
    return SipoAccess(rol_id=int(row[0]), rol_name=(row[1] or '').strip())


def _rol_from_catalog(rol_id: int) -> SipoAccess | None:
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT cf_rol_id, cf_rol_name
                FROM cf_rrhh_sip_rol
                WHERE cf_rol_id = %s
                LIMIT 1
                """,
                [rol_id],
            )
            row = cursor.fetchone()
    except OperationalError:
        logger.exception('No se pudo consultar cf_rrhh_sip_rol')
        return None

    if not row:
        return None
    return SipoAccess(rol_id=int(row[0]), rol_name=(row[1] or '').strip())


def resolve_sipo_access_for_email(email: str | None) -> SipoAccess | None:
    access = _fetch_rol(email)
    if access is not None:
        return access

    allowed = (os.getenv('DEV_AUTH_ALLOWED_EMAILS') or '').lower()
    normalized = (email or '').strip().lower()
    if normalized and normalized in {item.strip() for item in allowed.split(',') if item.strip()}:
        return _rol_from_catalog(int(os.getenv('ROL_PERFIL01') or SIPO_ROL_ADMIN))

    return None
