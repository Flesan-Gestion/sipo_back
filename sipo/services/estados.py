from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from ..constants import (
    SIPO_ACCION_ESTADO,
    SIPO_CANDIDATO_ACTIVO,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
    SIPO_STATUS_CANCELADA,
    SIPO_STATUS_EN_ESPERA,
    SIPO_STATUS_EN_REVISION,
    SIPO_TRANSICIONES_APROBACION,
)
from ..models import SipoCandidatoObra, SipoObra, SipoSolicitudHistorial
from .builder_sync import sync_trabajadores_ibuilder_obra
from .crud import get_obra_for_user
from .list import _actor_email, _user_rol_id
from .notifications import (
    collect_integration_errors,
    list_candidatos_activos_obra,
    send_email_error_builder,
    send_email_paso_revision,
)


def registrar_historial_estado(
    *,
    sip_id: int,
    estado_anterior: int,
    estado_nuevo: int,
    user,
    comentario: str | None = None,
) -> SipoSolicitudHistorial:
    texto = (comentario or '').strip()
    return SipoSolicitudHistorial.objects.create(
        solicitud=sip_id,
        estado_anterior=int(estado_anterior),
        estado_nuevo=int(estado_nuevo),
        usuario=_actor_email(user) or 'sistema',
        comentario=texto,
    )


def list_historial_solicitud(sip_id: int) -> list[SipoSolicitudHistorial]:
    return list(
        SipoSolicitudHistorial.objects.filter(solicitud=int(sip_id)).order_by(
            '-fecha_creacion', '-id'
        )
    )

def _normalize_email(value: str | None) -> str:
    return (value or '').strip().lower()


def _can_pasar_revision(obra: SipoObra, user) -> bool:
    """Paridad legado view_rrhh_sip_obra_2: ADM (status<=7) o AS (status<=6)."""
    rol_id = _user_rol_id(user)
    if rol_id in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        return True
    email = _actor_email(user)
    if not email:
        return False
    current = int(obra.cf_rrhh_sip_status)
    adm = _normalize_email(obra.cf_rrhh_sip_adm)
    asistente = _normalize_email(obra.cf_rrhh_sip_as)
    if current <= SIPO_STATUS_EN_REVISION and email == adm:
        return True
    if current <= SIPO_STATUS_EN_ESPERA and email == asistente:
        return True
    return False


def _can_cambiar_estado_aprobacion(obra: SipoObra, user, target: int) -> bool:
    rol_id = _user_rol_id(user)
    if rol_id in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        return True
    if target == SIPO_STATUS_EN_REVISION:
        return _can_pasar_revision(obra, user)
    return False


def count_candidatos_activos(sip_id: int) -> int:
    return (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .count()
    )


def get_acciones_estado(obra: SipoObra, user) -> list[dict]:
    rol_id = _user_rol_id(user)
    current = int(obra.cf_rrhh_sip_status)
    acciones = []

    if rol_id in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        for target in SIPO_TRANSICIONES_APROBACION.get(current, set()):
            meta = SIPO_ACCION_ESTADO.get(target)
            if meta:
                acciones.append({**meta, 'nuevo_estado': target})
    elif current == SIPO_STATUS_EN_ESPERA and _can_pasar_revision(obra, user):
        meta = SIPO_ACCION_ESTADO.get(SIPO_STATUS_EN_REVISION)
        if meta:
            acciones.append({**meta, 'nuevo_estado': SIPO_STATUS_EN_REVISION})

    if rol_id == SIPO_ROL_ADMIN and current < SIPO_STATUS_CANCELADA:
        meta = SIPO_ACCION_ESTADO[SIPO_STATUS_CANCELADA]
        acciones.append({**meta, 'nuevo_estado': SIPO_STATUS_CANCELADA})

    return acciones


def cambiar_estado_obra(*, sip_id: int, nuevo_estado: int, user, comentario: str | None = None) -> SipoObra:
    obra = get_obra_for_user(sip_id, user)
    current = int(obra.cf_rrhh_sip_status)
    target = int(nuevo_estado)
    rol_id = _user_rol_id(user)

    if target == SIPO_STATUS_CANCELADA:
        if rol_id != SIPO_ROL_ADMIN:
            raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)
        if current >= SIPO_STATUS_CANCELADA:
            raise APIException(
                'La solicitud no se puede cancelar en su estado actual',
                status.HTTP_400_BAD_REQUEST,
            )
    else:
        if not _can_cambiar_estado_aprobacion(obra, user, target):
            raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)
        allowed = SIPO_TRANSICIONES_APROBACION.get(current, set())
        if target not in allowed:
            raise APIException(
                f'Transición no permitida: {current} → {target}',
                status.HTTP_400_BAD_REQUEST,
            )

    pasar_revision = current == SIPO_STATUS_EN_ESPERA and target == SIPO_STATUS_EN_REVISION
    if pasar_revision and count_candidatos_activos(sip_id) < 1:
        raise APIException(
            'Debe registrar al menos un candidato antes de pasar a revisión',
            status.HTTP_400_BAD_REQUEST,
        )

    builder_result = None
    email_revision = None
    email_builder_errors: list[dict] = []

    # Mail de revisión ANTES del sync iBuilder (evitar timeout sin correo).
    if pasar_revision:
        candidatos = list_candidatos_activos_obra(sip_id)
        email_revision = send_email_paso_revision(obra, candidatos)
        builder_result = sync_trabajadores_ibuilder_obra(
            sip_id=sip_id,
            obra=obra,
            solo_activos=True,
        )

    email = _actor_email(user)
    now = timezone.now()
    update_fields = {
        'cf_rrhh_sip_status': target,
        'cf_rrhh_sip_status_date': now.date(),
        'cf_rrhh_sip_status_user': email,
        'cf_rrhh_sip_update_user': email,
        'cf_rrhh_sip_update_date': now,
    }

    SipoObra.objects.using('sip_db').filter(cf_rrhh_sip_id=sip_id).update(**update_fields)
    obra.refresh_from_db()

    registrar_historial_estado(
        sip_id=sip_id,
        estado_anterior=current,
        estado_nuevo=target,
        user=user,
        comentario=comentario,
    )

    if pasar_revision:
        for msg in collect_integration_errors(builder_result=builder_result):
            email_builder_errors.append(send_email_error_builder(obra, mensaje_error=msg))
        obra._email_revision = email_revision  # type: ignore[attr-defined]
        obra._email_builder_errors = email_builder_errors  # type: ignore[attr-defined]

    return obra
