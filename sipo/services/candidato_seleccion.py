from django.db import connections
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from ..constants import (
    SIPO_CANDIDATO_ACTIVO,
    SIPO_CANDIDATO_CONTRATADO_SAP,
    SIPO_CANDIDATO_SELECCIONADO,
    SIPO_CANDIDATO_SIN_SELECCION,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
)
from ..models import SipoCandidatoObra
from .crud import get_obra_for_user


def _require_admin_rrhh(user) -> None:
    rol_id = int(getattr(user, 'sip_rol_id', -1))
    if rol_id not in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        raise APIException(
            "Don't have access to this resource",
            status.HTTP_403_FORBIDDEN,
        )


def _get_candidato_activo(sip_id: int, candidato_id: str) -> SipoCandidatoObra:
    candidato = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_id=candidato_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .first()
    )
    if not candidato:
        raise APIException('Candidato no encontrado', status.HTTP_400_BAD_REQUEST)
    return candidato


def _obra_tiene_seleccionado_date(sip_id: int, *, candidato_id: str | None = None) -> bool:
    sql = (
        'SELECT 1 FROM cf_rrhh_sip_candidato_obra '
        'WHERE cf_rrhh_sip_obra_id = %s '
        'AND cf_rrhh_sip_obra_candidato_seleccionado_date IS NOT NULL'
    )
    params: list = [sip_id]
    if candidato_id:
        sql += ' AND cf_rrhh_sip_obra_candidato_id = %s'
        params.append(candidato_id)
    sql += ' LIMIT 1'
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() is not None


def _apply_seleccion_update(
    *,
    sip_id: int,
    seleccionado: int,
    candidato_id: str | None = None,
    set_date: bool,
) -> int:
    now = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    params: list = [seleccionado]
    sql = (
        'UPDATE cf_rrhh_sip_candidato_obra '
        'SET cf_rrhh_sip_obra_candidato_seleccionado = %s, '
        'cf_rrhh_sip_obra_candidato_estado_documentos = 0'
    )
    if set_date:
        sql += ', cf_rrhh_sip_obra_candidato_seleccionado_date = %s'
        params.append(now)
    sql += ' WHERE cf_rrhh_sip_obra_id = %s AND cf_rrhh_sip_obra_candidato_estado = %s'
    params.extend([sip_id, SIPO_CANDIDATO_ACTIVO])
    if candidato_id:
        sql += ' AND cf_rrhh_sip_obra_candidato_id = %s'
        params.append(candidato_id)
    else:
        sql += ' AND (cf_rrhh_sip_obra_candidato_seleccionado IS NULL OR cf_rrhh_sip_obra_candidato_seleccionado <> %s)'
        params.append(SIPO_CANDIDATO_CONTRATADO_SAP)
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount


def toggle_seleccion_candidato(*, sip_id: int, candidato_id: str, user) -> SipoCandidatoObra:
    _require_admin_rrhh(user)
    get_obra_for_user(sip_id, user)
    candidato = _get_candidato_activo(sip_id, candidato_id)

    current = int(candidato.cf_rrhh_sip_obra_candidato_seleccionado or 0)
    if current == SIPO_CANDIDATO_CONTRATADO_SAP:
        raise APIException(
            'El candidato ya fue contratado en SAP y no puede modificarse',
            status.HTTP_400_BAD_REQUEST,
        )

    nuevo = (
        SIPO_CANDIDATO_SIN_SELECCION
        if current == SIPO_CANDIDATO_SELECCIONADO
        else SIPO_CANDIDATO_SELECCIONADO
    )
    set_date = not _obra_tiene_seleccionado_date(sip_id, candidato_id=candidato_id)
    updated = _apply_seleccion_update(
        sip_id=sip_id,
        seleccionado=nuevo,
        candidato_id=candidato_id,
        set_date=set_date,
    )
    if not updated:
        raise APIException('No se pudo actualizar la selección', status.HTTP_400_BAD_REQUEST)

    return _get_candidato_activo(sip_id, candidato_id)


def seleccionar_todos_candidatos(*, sip_id: int, seleccionado: int, user) -> dict:
    _require_admin_rrhh(user)
    get_obra_for_user(sip_id, user)

    if seleccionado not in (SIPO_CANDIDATO_SIN_SELECCION, SIPO_CANDIDATO_SELECCIONADO):
        raise APIException(
            'seleccionado debe ser 0 o 1',
            status.HTTP_400_BAD_REQUEST,
        )

    set_date = seleccionado == SIPO_CANDIDATO_SELECCIONADO and not _obra_tiene_seleccionado_date(sip_id)
    updated = _apply_seleccion_update(
        sip_id=sip_id,
        seleccionado=seleccionado,
        candidato_id=None,
        set_date=set_date,
    )
    return {'updated': updated, 'seleccionado': seleccionado}
