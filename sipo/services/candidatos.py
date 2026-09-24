import uuid

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from ..constants import (
    SIPO_CANDIDATO_ACTIVO,
    SIPO_CANDIDATO_ELIMINADO,
    SIPO_MAX_CANDIDATOS,
    SIPO_STATUS_CANCELADA,
)
from ..models import SipoCandidatoObra
from .candidato_docs import normalize_candidato_doc_value, CANDIDATO_DOC_DB_FIELDS
from .candidato_fields import CREATE_FIELDS, REQUIRED_FIELDS, UPPER_FIELDS, is_blank_value
from .candidato_validaciones import sanitize_address_data, validate_candidato_negocio
from .crud import get_obra_for_user, user_can_edit_obra
from .list import _actor_email


def _upper(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().upper()
    return value


def _next_user_id() -> str:
    from django.db import connections

    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            'SELECT MAX(CAST(cf_rrhh_sip_obra_user_id AS UNSIGNED)) '
            'FROM cf_rrhh_sip_candidato_obra '
            "WHERE cf_rrhh_sip_obra_user_id REGEXP '^[0-9]+$'"
        )
        row = cursor.fetchone()
    current = int(row[0] or 0) if row else 0
    if current < 200000:
        return '200000'
    return str(current + 1)


def list_candidatos(sip_id: int, user) -> list[SipoCandidatoObra]:
    get_obra_for_user(sip_id, user)
    return list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .order_by('cf_rrhh_sip_obra_candidato_ap', 'cf_rrhh_sip_obra_candidato_am')
    )


def _normalize_genero(value) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    key = raw.upper()
    if key in ('M', 'MASCULINO', 'H', 'HOMBRE', 'MALE'):
        return 'M'
    if key in ('F', 'FEMENINO', 'MUJER', 'FEMALE'):
        return 'F'
    return raw


def _normalize_candidato_payload(data: dict) -> dict:
    payload = {}
    for field in CREATE_FIELDS:
        if field not in data:
            continue
        value = data.get(field)
        if field == 'cf_rrhh_sip_obra_candidato_genero':
            payload[field] = _normalize_genero(value)
        elif field in UPPER_FIELDS:
            payload[field] = _upper(value)
        elif field == 'cf_rrhh_sip_obra_candidato_correo' and isinstance(value, str):
            payload[field] = value.strip().lower()
        elif isinstance(value, str):
            payload[field] = value.strip()
        else:
            payload[field] = value
    for field in CANDIDATO_DOC_DB_FIELDS:
        if field in payload:
            payload[field] = normalize_candidato_doc_value(payload.get(field))
    return sanitize_address_data(payload)


def create_candidato(*, sip_id: int, data: dict, user) -> SipoCandidatoObra:
    obra = get_obra_for_user(sip_id, user)
    if not user_can_edit_obra(obra, user):
        raise APIException(
            'No se pueden agregar candidatos en el estado actual',
            status.HTTP_400_BAD_REQUEST,
        )
    if int(obra.cf_rrhh_sip_status) >= SIPO_STATUS_CANCELADA:
        raise APIException('La solicitud está cerrada', status.HTTP_400_BAD_REQUEST)

    activos = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .count()
    )
    if activos >= SIPO_MAX_CANDIDATOS:
        raise APIException(
            f'Máximo {SIPO_MAX_CANDIDATOS} candidatos por solicitud',
            status.HTTP_400_BAD_REQUEST,
        )

    payload = _normalize_candidato_payload(data)
    missing = [f for f in REQUIRED_FIELDS if is_blank_value(payload.get(f))]
    if missing:
        raise ValidationError({f: ['Este campo es obligatorio.'] for f in missing})

    docs_oblig = (
        'cf_rrhh_sip_obra_candidato_ci',
        'cf_rrhh_sip_obra_candidato_afp',
        'cf_rrhh_sip_obra_candidato_salud',
        'cf_rrhh_sip_obra_candidato_domi',
    )
    docs_missing = [f for f in docs_oblig if is_blank_value(payload.get(f))]
    if docs_missing:
        raise ValidationError({f: ['Documento obligatorio.'] for f in docs_missing})

    payload = validate_candidato_negocio(
        payload,
        ubicacion=getattr(obra, 'cf_rrhh_sip_ubicacion', None),
    )

    email = _actor_email(user)
    candidato = SipoCandidatoObra(
        cf_rrhh_sip_obra_id=sip_id,
        cf_rrhh_sip_obra_candidato_id=uuid.uuid4().hex[:13],
        cf_rrhh_sip_obra_user_id=_next_user_id(),
        cf_rrhh_sip_obra_candidato_create_user=email,
        cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        cf_rrhh_sip_obra_candidato_seleccionado=0,
        cf_rrhh_sip_obra_create_date=timezone.now(),
        **payload,
    )
    candidato.save(using='sip_db')
    return candidato


def soft_delete_candidato(*, sip_id: int, candidato_id: str, user) -> None:
    obra = get_obra_for_user(sip_id, user)
    if not user_can_edit_obra(obra, user):
        raise APIException(
            'No se pueden eliminar candidatos en el estado actual',
            status.HTTP_400_BAD_REQUEST,
        )

    updated = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_id=candidato_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .update(
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ELIMINADO,
            cf_rrhh_sip_obra_candidato_user_eliminador=_actor_email(user),
            cf_rrhh_sip_obra_candidato_date_eliminador=timezone.now(),
        )
    )
    if not updated:
        raise APIException('Candidato no encontrado', status.HTTP_400_BAD_REQUEST)


def update_candidato(*, sip_id: int, candidato_id: str, data: dict, user) -> SipoCandidatoObra:
    obra = get_obra_for_user(sip_id, user)
    if not user_can_edit_obra(obra, user):
        raise APIException(
            'No se pueden editar candidatos en el estado actual',
            status.HTTP_400_BAD_REQUEST,
        )

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

    payload = _normalize_candidato_payload(data)
    missing = [f for f in REQUIRED_FIELDS if is_blank_value(payload.get(f))]
    if missing:
        raise ValidationError({f: ['Este campo es obligatorio.'] for f in missing})
    payload = validate_candidato_negocio(
        payload,
        ubicacion=getattr(obra, 'cf_rrhh_sip_ubicacion', None),
    )

    for field, value in payload.items():
        setattr(candidato, field, value)
    candidato.save(using='sip_db')
    return candidato
