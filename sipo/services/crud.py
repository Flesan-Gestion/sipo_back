from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from ..constants import (
    SIPO_ID_CUTOFF,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
    SIPO_STATUS_CANCELADA,
    SIPO_STATUS_EN_ESPERA,
)
from ..models import SipoObra
from .list import _actor_email, _user_rol_id


EDITABLE_FIELDS = (
    'cf_rrhh_sip_rut',
    'cf_rrhh_sip_razonsocial',
    'cf_rrhh_sip_uni',
    'cf_rrhh_sip_nombre_uni',
    'cf_rrhh_sip_dep',
    'cf_rrhh_sip_nombre_dep',
    'cf_rrhh_sip_cc',
    'cf_rrhh_sip_nombre_cc',
    'cf_rrhh_sip_adm',
    'cf_rrhh_sip_as',
    'cf_rrhh_sip_ubicacion',
)

REQUIRED_CREATE_FIELDS = (
    'cf_rrhh_sip_rut',
    'cf_rrhh_sip_razonsocial',
    'cf_rrhh_sip_uni',
    'cf_rrhh_sip_nombre_uni',
    'cf_rrhh_sip_dep',
    'cf_rrhh_sip_nombre_dep',
    'cf_rrhh_sip_cc',
    'cf_rrhh_sip_nombre_cc',
    'cf_rrhh_sip_adm',
    'cf_rrhh_sip_as',
    'cf_rrhh_sip_ubicacion',
)


def _normalize_email(value: str | None) -> str:
    return (value or '').strip().lower()


def _clean_payload(data: dict) -> dict:
    payload = {}
    for field in EDITABLE_FIELDS:
        if field not in data:
            continue
        value = data.get(field)
        if field in ('cf_rrhh_sip_adm', 'cf_rrhh_sip_as'):
            payload[field] = _normalize_email(value)
        elif isinstance(value, str):
            payload[field] = value.strip()
        else:
            payload[field] = value
    return payload


def _assert_rs_cc_pais(payload: dict, *, base: SipoObra | None = None) -> None:
    from .pais_segregation import validate_razon_social_centro_costo

    rs = payload.get('cf_rrhh_sip_rut')
    cc = payload.get('cf_rrhh_sip_cc')
    if rs is None and base is not None:
        rs = base.cf_rrhh_sip_rut
    if cc is None and base is not None:
        cc = base.cf_rrhh_sip_cc
    validate_razon_social_centro_costo(
        razon_social_id=rs,
        centro_costo_id=cc,
        external_code_pais=payload.get('external_code_pais')
        if 'external_code_pais' in payload
        else None,
    )


def _validate_required(payload: dict):
    missing = [field for field in REQUIRED_CREATE_FIELDS if not payload.get(field)]
    if missing:
        raise APIException(
            f"Campos requeridos: {', '.join(missing)}",
            status.HTTP_400_BAD_REQUEST,
        )


def user_can_access_obra(obra: SipoObra, user) -> bool:
    from .usuario_scope import get_scope_for_user

    rol_id = _user_rol_id(user)
    if rol_id == SIPO_ROL_ADMIN:
        return True

    scope = get_scope_for_user(user)
    empresas_ids = set(scope.get('empresas_ids') or [])
    centros_ids = set(scope.get('centros_costo_ids') or [])
    if empresas_ids or centros_ids:
        rut_ok = not empresas_ids or str(obra.cf_rrhh_sip_rut or '').strip() in empresas_ids
        cc_ok = not centros_ids or str(obra.cf_rrhh_sip_cc or '').strip() in centros_ids
        if rut_ok and cc_ok:
            return True
        return False

    if rol_id == SIPO_ROL_RRHH:
        return True

    email = _actor_email(user)
    actors = {
        _normalize_email(obra.cf_rrhh_sip_create_user),
        _normalize_email(obra.cf_rrhh_sip_adm),
        _normalize_email(obra.cf_rrhh_sip_as),
    }
    return bool(email) and email in actors


def _assert_user_can_create_payload(payload: dict, user) -> None:
    from .usuario_scope import get_scope_for_user

    if _user_rol_id(user) == SIPO_ROL_ADMIN:
        return

    scope = get_scope_for_user(user)
    empresas_ids = set(scope.get('empresas_ids') or [])
    centros_ids = set(scope.get('centros_costo_ids') or [])
    if not empresas_ids and not centros_ids:
        return

    rut = str(payload.get('cf_rrhh_sip_rut') or '').strip()
    cc = str(payload.get('cf_rrhh_sip_cc') or '').strip()
    if empresas_ids and rut not in empresas_ids:
        raise APIException(
            'No tiene permiso para la razón social seleccionada',
            status.HTTP_403_FORBIDDEN,
        )
    if centros_ids and cc not in centros_ids:
        raise APIException(
            'No tiene permiso para el centro de costo seleccionado',
            status.HTTP_403_FORBIDDEN,
        )


def user_can_edit_obra(obra: SipoObra, user) -> bool:
    if int(obra.cf_rrhh_sip_status) >= SIPO_STATUS_CANCELADA:
        return False
    return user_can_access_obra(obra, user)


def get_obra_for_user(sip_id: int, user) -> SipoObra:
    obra = (
        SipoObra.objects.using('sip_db')
        .filter(cf_rrhh_sip_id=sip_id, cf_rrhh_sip_id__gt=SIPO_ID_CUTOFF)
        .first()
    )
    if obra is None:
        raise APIException('Solicitud no encontrada', status.HTTP_400_BAD_REQUEST)
    if not user_can_access_obra(obra, user):
        raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)
    return obra


def _next_obra_id() -> int:
    current = (
        SipoObra.objects.using('sip_db')
        .aggregate(max_id=Max('cf_rrhh_sip_id'))
        .get('max_id')
    )
    return int(current or 0) + 1


@transaction.atomic(using='sip_db')
def create_sipo_obra(*, data: dict, user) -> SipoObra:
    payload = _clean_payload(data)
    _validate_required(payload)
    _assert_rs_cc_pais({**payload, 'external_code_pais': data.get('external_code_pais')})
    _assert_user_can_create_payload(payload, user)

    email = _actor_email(user)
    if not email:
        raise APIException('Usuario sin correo en sesión', status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    obra = SipoObra(
        cf_rrhh_sip_id=_next_obra_id(),
        cf_rrhh_sip_status=SIPO_STATUS_EN_ESPERA,
        cf_rrhh_sip_create_date=now,
        cf_rrhh_sip_create_user=email,
        cf_rrhh_sip_apro_date=now,
        cf_rrhh_sip_apro_user=payload['cf_rrhh_sip_as'],
        cf_rrhh_sip_end_date=now.date(),
        **payload,
    )
    obra.save(using='sip_db')
    return obra


@transaction.atomic(using='sip_db')
def update_sipo_obra(*, sip_id: int, data: dict, user) -> SipoObra:
    obra = get_obra_for_user(sip_id, user)
    if not user_can_edit_obra(obra, user):
        raise APIException(
            'La solicitud no se puede editar en su estado actual',
            status.HTTP_400_BAD_REQUEST,
        )

    payload = _clean_payload(data)
    if not payload:
        raise APIException('No hay campos para actualizar', status.HTTP_400_BAD_REQUEST)

    if any(k in data for k in ('cf_rrhh_sip_rut', 'cf_rrhh_sip_cc', 'external_code_pais')):
        _assert_rs_cc_pais(
            {**payload, 'external_code_pais': data.get('external_code_pais')},
            base=obra,
        )

    for field, value in payload.items():
        setattr(obra, field, value)

    obra.cf_rrhh_sip_update_user = _actor_email(user)
    obra.cf_rrhh_sip_update_date = timezone.now()
    obra.save(using='sip_db', update_fields=[*payload.keys(), 'cf_rrhh_sip_update_user', 'cf_rrhh_sip_update_date'])
    return obra
