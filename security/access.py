import logging
import os
from dataclasses import dataclass

from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)

SIPO_OBRA_DB = 'sip_db'
SIPO_ROL_ADMIN = 1
SIPO_ROL_OBRA = 0
SIPO_ROL_OBRA_NAME = 'Usuario obra'


@dataclass
class SipoAccess:
    rol_id: int
    rol_name: str


def _normalized_email(email: str | None) -> str:
    return (email or '').strip().lower()


def _allowed_email_domains() -> set[str]:
    raw = (os.getenv('SIPO_ALLOWED_EMAIL_DOMAINS') or 'flesan.cl').lower()
    return {item.strip().lstrip('@') for item in raw.split(',') if item.strip()}


def _email_domain_allowed(email: str) -> bool:
    if '@' not in email:
        return False
    domain = email.rsplit('@', 1)[-1]
    return domain in _allowed_email_domains()


def _fetch_rol(email: str | None) -> SipoAccess | None:
    normalized = _normalized_email(email)
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
    """
    1) Perfil explícito en cf_rrhh_sip_perfil.
    2) DEV_AUTH_ALLOWED_EMAILS → Admin (solo desarrollo).
    3) Dominio permitido (default @flesan.cl) → rol 0 Usuario obra (sin fila en perfil).
    """
    access = _fetch_rol(email)
    if access is not None:
        return access

    normalized = _normalized_email(email)
    if not normalized:
        return None

    allowed = (os.getenv('DEV_AUTH_ALLOWED_EMAILS') or '').lower()
    if normalized in {item.strip() for item in allowed.split(',') if item.strip()}:
        return _rol_from_catalog(int(os.getenv('ROL_PERFIL01') or SIPO_ROL_ADMIN))

    if _email_domain_allowed(normalized):
        return SipoAccess(rol_id=SIPO_ROL_OBRA, rol_name=SIPO_ROL_OBRA_NAME)

    return None
