"""CRUD perfiles SIP Obra (paridad legado cf_rrhh_sip_perfil)."""

from __future__ import annotations

from django.db import connections
from rest_framework.exceptions import NotFound, ValidationError

from security.models import SipoRol

from sipo.constants import SIPO_ROL_ADMIN, SIPO_ROL_SUPERVISOR

from .usuario_scope import (
    delete_assignments_for_perfil,
    get_assignments_for_perfil,
    set_assignments_for_perfil,
)

SIP_DB = 'sip_db'


def _normalize_email(email: str | None) -> str:
    return (email or '').strip().lower()


def _next_perfil_id() -> int:
    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(
            'SELECT COALESCE(MAX(cf_rrhh_sip_perfil_id), 0) + 1 FROM cf_rrhh_sip_perfil'
        )
        row = cursor.fetchone()
    return int(row[0]) if row else 1


def _fetch_rol_names() -> dict[int, str]:
    roles = SipoRol.objects.using(SIP_DB).all().values('cf_rol_id', 'cf_rol_name')
    return {int(r['cf_rol_id']): (r['cf_rol_name'] or '').strip() for r in roles}


def _resolve_rol_id(*, rol_id: int | None = None, rol_nombre: str | None = None) -> int:
    if rol_id is not None:
        if not SipoRol.objects.using(SIP_DB).filter(cf_rol_id=rol_id).exists():
            raise ValidationError({'rol_id': ['Rol no válido.']})
        return int(rol_id)

    nombre = (rol_nombre or '').strip()
    if not nombre:
        raise ValidationError({'rol_id': ['El rol es obligatorio.']})

    roles = _fetch_rol_names()
    for rid, label in roles.items():
        if label.lower() == nombre.lower():
            return rid

    raise ValidationError({'rol_id': ['Rol no válido.']})


def _serialize_row(row: dict, rol_names: dict[int, str]) -> dict:
    rol_id = int(row['cf_rol_id'])
    perfil_id = int(row['cf_rrhh_sip_perfil_id'])
    scope = get_assignments_for_perfil(perfil_id)
    return {
        'id': perfil_id,
        'correo': _normalize_email(row['usuario_email']),
        'rol_id': rol_id,
        'rol': rol_names.get(rol_id, ''),
        'empresas_ids': scope['empresas_ids'],
        'centros_costo_ids': scope['centros_costo_ids'],
        'empresas': scope['empresas'],
        'centros_costo': scope['centros_costo'],
    }


def list_sipo_usuarios(*, search: str | None = None, cf_rol_id: int | None = None) -> list[dict]:
    conditions: list[str] = []
    params: list = []

    if search:
        conditions.append('LOWER(TRIM(usuario_email)) LIKE %s')
        params.append(f'%{_normalize_email(search)}%')

    if cf_rol_id is not None:
        conditions.append('cf_rol_id = %s')
        params.append(cf_rol_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    sql = f"""
        SELECT cf_rrhh_sip_perfil_id, usuario_email, cf_rol_id
        FROM cf_rrhh_sip_perfil
        {where_clause}
        ORDER BY usuario_email
    """

    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    rol_names = _fetch_rol_names()
    return [_serialize_row(row, rol_names) for row in rows]


def get_sipo_usuario_by_id(perfil_id: int) -> dict | None:
    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(
            """
            SELECT cf_rrhh_sip_perfil_id, usuario_email, cf_rol_id
            FROM cf_rrhh_sip_perfil
            WHERE cf_rrhh_sip_perfil_id = %s
            LIMIT 1
            """,
            [perfil_id],
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [col[0] for col in cursor.description]
        data = dict(zip(columns, row))

    return _serialize_row(data, _fetch_rol_names())


def _perfil_exists(email: str, rol_id: int, *, exclude_perfil_id: int | None = None) -> bool:
    sql = """
        SELECT 1 FROM cf_rrhh_sip_perfil
        WHERE LOWER(TRIM(usuario_email)) = %s AND cf_rol_id = %s
    """
    params: list = [_normalize_email(email), rol_id]
    if exclude_perfil_id is not None:
        sql += ' AND cf_rrhh_sip_perfil_id <> %s'
        params.append(exclude_perfil_id)

    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() is not None


def create_sipo_usuario(
    *,
    correo: str,
    rol_id: int | None = None,
    rol_nombre: str | None = None,
    empresas_ids: list | None = None,
    centros_costo_ids: list | None = None,
    empresas_meta: dict | None = None,
    centros_meta: dict | None = None,
) -> dict:
    email = _normalize_email(correo)
    if not email:
        raise ValidationError({'correo': ['El correo es obligatorio.']})

    resolved_rol_id = _resolve_rol_id(rol_id=rol_id, rol_nombre=rol_nombre)

    if _perfil_exists(email, resolved_rol_id):
        raise ValidationError({'correo': ['Este usuario ya tiene asignado el rol seleccionado.']})

    perfil_id = _next_perfil_id()
    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO cf_rrhh_sip_perfil (cf_rrhh_sip_perfil_id, usuario_email, cf_rol_id)
            VALUES (%s, %s, %s)
            """,
            [perfil_id, email, resolved_rol_id],
        )

    set_assignments_for_perfil(
        perfil_id,
        empresas_ids=[] if resolved_rol_id == SIPO_ROL_ADMIN else (empresas_ids or []),
        centros_costo_ids=[] if resolved_rol_id == SIPO_ROL_ADMIN else (centros_costo_ids or []),
        empresas_meta=empresas_meta,
        centros_meta=centros_meta,
        require_non_empty=False,
    )

    created = get_sipo_usuario_by_id(perfil_id)
    if created is None:
        raise ValidationError({'non_field_errors': ['No fue posible crear el usuario.']})
    return created


def update_sipo_usuario(
    perfil_id: int,
    *,
    rol_id: int | None = None,
    rol_nombre: str | None = None,
    cf_rol_id: int | None = None,
    empresas_ids: list | None = None,
    centros_costo_ids: list | None = None,
    empresas_meta: dict | None = None,
    centros_meta: dict | None = None,
) -> dict:
    current = get_sipo_usuario_by_id(perfil_id)
    if current is None:
        raise NotFound('Usuario no encontrado.')

    has_rol = any(v is not None for v in (rol_id, cf_rol_id, rol_nombre))
    resolved_rol_id = int(current['rol_id'])
    if has_rol:
        resolved_rol_id = _resolve_rol_id(
            rol_id=rol_id if rol_id is not None else cf_rol_id,
            rol_nombre=rol_nombre,
        )
        email = current['correo']
        if int(current['rol_id']) != resolved_rol_id and _perfil_exists(
            email, resolved_rol_id, exclude_perfil_id=perfil_id
        ):
            raise ValidationError({'rol_id': ['Este usuario ya tiene asignado el rol seleccionado.']})

        with connections[SIP_DB].cursor() as cursor:
            cursor.execute(
                """
                UPDATE cf_rrhh_sip_perfil
                SET cf_rol_id = %s
                WHERE cf_rrhh_sip_perfil_id = %s
                """,
                [resolved_rol_id, perfil_id],
            )

    if resolved_rol_id == SIPO_ROL_ADMIN:
        set_assignments_for_perfil(
            perfil_id,
            empresas_ids=[],
            centros_costo_ids=[],
            require_non_empty=False,
        )
    elif empresas_ids is not None or centros_costo_ids is not None:
        set_assignments_for_perfil(
            perfil_id,
            empresas_ids=empresas_ids if empresas_ids is not None else current.get('empresas_ids'),
            centros_costo_ids=(
                centros_costo_ids
                if centros_costo_ids is not None
                else current.get('centros_costo_ids')
            ),
            empresas_meta=empresas_meta,
            centros_meta=centros_meta,
            require_non_empty=True,
        )

    updated = get_sipo_usuario_by_id(perfil_id)
    if updated is None:
        raise NotFound('Usuario no encontrado.')
    return updated


def delete_sipo_usuario(perfil_id: int) -> None:
    current = get_sipo_usuario_by_id(perfil_id)
    if current is None:
        raise NotFound('Usuario no encontrado.')

    delete_assignments_for_perfil(perfil_id)
    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(
            'DELETE FROM cf_rrhh_sip_perfil WHERE cf_rrhh_sip_perfil_id = %s',
            [perfil_id],
        )
        if cursor.rowcount == 0:
            raise NotFound('Usuario no encontrado.')


def ensure_supervisor_rol() -> None:
    with connections[SIP_DB].cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
            VALUES (%s, 'Supervisor')
            ON DUPLICATE KEY UPDATE cf_rol_name = 'Supervisor'
            """,
            [SIPO_ROL_SUPERVISOR],
        )


def list_sipo_perfiles_roles() -> list[dict]:
    ensure_supervisor_rol()
    roles = SipoRol.objects.using(SIP_DB).all().order_by('cf_rol_id')
    items = [
        {'cf_rol_id': int(r.cf_rol_id), 'cf_rol_name': (r.cf_rol_name or '').strip()}
        for r in roles
    ]
    ids = {item['cf_rol_id'] for item in items}
    if SIPO_ROL_SUPERVISOR not in ids:
        items.append({'cf_rol_id': SIPO_ROL_SUPERVISOR, 'cf_rol_name': 'Supervisor'})
        items.sort(key=lambda row: row['cf_rol_id'])
    return items
