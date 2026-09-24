from datetime import date, datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from ..constants import (
    ESTADO_FILTROS,
    SIPO_ID_CUTOFF,
    SIPO_LIST_ONLY_FIELDS,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
    SIPO_STATUS_CANCELADA,
)
from ..models import SipoObra


def _actor_email(user) -> str:
    return (
        getattr(user, 'email', None)
        or getattr(user, 'username', None)
        or ''
    ).strip().lower()


def _user_rol_id(user) -> int | None:
    rol = getattr(user, 'sip_rol_id', None)
    if rol is None:
        return None
    return int(rol)


def apply_estado_filter(queryset, estado: str | None):
    if estado is None or estado == 'Todas':
        return queryset

    if estado in ESTADO_FILTROS:
        value = ESTADO_FILTROS[estado]
        if isinstance(value, list):
            return queryset.filter(cf_rrhh_sip_status__in=value)
        return queryset.filter(cf_rrhh_sip_status=value)

    if str(estado).isdigit():
        return queryset.filter(cf_rrhh_sip_status=int(estado))

    return queryset


def apply_scope_filter(queryset, user):
    from .usuario_scope import get_scope_for_user

    rol_id = _user_rol_id(user)
    if rol_id == SIPO_ROL_ADMIN:
        return queryset

    scope = get_scope_for_user(user)
    empresas_ids = scope.get('empresas_ids') or []
    centros_ids = scope.get('centros_costo_ids') or []

    if empresas_ids or centros_ids:
        territorial = Q()
        if empresas_ids:
            territorial &= Q(cf_rrhh_sip_rut__in=empresas_ids)
        if centros_ids:
            territorial &= Q(cf_rrhh_sip_cc__in=centros_ids)
        return queryset.filter(territorial)

    if rol_id == SIPO_ROL_RRHH:
        return queryset

    email = _actor_email(user)
    if not email:
        return queryset.none()

    return queryset.filter(
        Q(cf_rrhh_sip_create_user__iexact=email)
        | Q(cf_rrhh_sip_adm__iexact=email)
        | Q(cf_rrhh_sip_as__iexact=email)
    )


def apply_search_filter(queryset, filter_text: str | None):
    text = (filter_text or '').strip()
    if not text:
        return queryset

    filters = (
        Q(cf_rrhh_sip_razonsocial__icontains=text)
        | Q(cf_rrhh_sip_nombre_cc__icontains=text)
        | Q(cf_rrhh_sip_cc__icontains=text)
        | Q(cf_rrhh_sip_nombre_uni__icontains=text)
        | Q(cf_rrhh_sip_adm__icontains=text)
        | Q(cf_rrhh_sip_as__icontains=text)
        | Q(cf_rrhh_sip_create_user__icontains=text)
    )
    if text.isdigit():
        filters |= Q(cf_rrhh_sip_id=int(text))
    return queryset.filter(filters)


def _parse_date_param(value) -> date | None:
    raw = (value or '').strip()[:10]
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return None


def apply_export_extra_filters(
    queryset,
    *,
    centro_costo: str | None = None,
    empresa_rut: str | None = None,
    cargo: str | None = None,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
):
    cc = (centro_costo or '').strip()
    if cc:
        queryset = queryset.filter(cf_rrhh_sip_cc=cc)

    rut = (empresa_rut or '').strip()
    if rut:
        queryset = queryset.filter(cf_rrhh_sip_rut=rut)

    cargo_text = (cargo or '').strip()
    if cargo_text:
        queryset = queryset.filter(
            Q(cf_rrhh_sip_nombre_cc__icontains=cargo_text)
            | Q(cf_rrhh_sip_nombre_cc=cargo_text)
        )

    if fecha_inicio:
        queryset = queryset.filter(cf_rrhh_sip_create_date__date__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(cf_rrhh_sip_create_date__date__lte=fecha_fin)
    return queryset


def get_sipo_list_queryset(estado: str | None = None, user=None, filter_text: str | None = None):
    queryset = SipoObra.objects.using('sip_db').only(*SIPO_LIST_ONLY_FIELDS)
    queryset = queryset.filter(cf_rrhh_sip_id__gt=SIPO_ID_CUTOFF)
    queryset = apply_estado_filter(queryset, estado)
    if user is not None and getattr(user, 'is_authenticated', False):
        queryset = apply_scope_filter(queryset, user)
    queryset = apply_search_filter(queryset, filter_text)
    return queryset.order_by('-cf_rrhh_sip_id')


def get_sipo_export_queryset(user, filtros: dict | None = None):
    filtros = filtros or {}
    estado = (
        filtros.get('estado')
        or filtros.get('status')
        or 'Activas'
    )
    filter_text = (
        filtros.get('search')
        or filtros.get('filterText')
        or filtros.get('q')
    )
    queryset = get_sipo_list_queryset(estado=estado, user=user, filter_text=filter_text)
    return apply_export_extra_filters(
        queryset,
        centro_costo=filtros.get('centro_costo'),
        empresa_rut=filtros.get('empresa') or filtros.get('filterEmpresa'),
        cargo=filtros.get('cargo') or filtros.get('filterCargo'),
        fecha_inicio=_parse_date_param(filtros.get('fecha_inicio')),
        fecha_fin=_parse_date_param(filtros.get('fecha_fin')),
    )


def get_sipo_list_page(
    *,
    estado: str | None,
    user,
    page: int = 1,
    per_page: int = 10,
    filter_text: str | None = None,
):
    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or 10), 100))

    queryset = get_sipo_list_queryset(estado=estado, user=user, filter_text=filter_text)
    total_records = queryset.count()
    start = per_page * (page - 1)
    end = start + per_page
    records = list(queryset[start:end])
    return records, total_records, page, per_page


def cancel_sipo_obra(*, sip_id: int, user, comentario: str | None = None) -> SipoObra:
    rol_id = _user_rol_id(user)
    if rol_id != SIPO_ROL_ADMIN:
        raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)

    obra = (
        SipoObra.objects.using('sip_db')
        .filter(cf_rrhh_sip_id=sip_id, cf_rrhh_sip_id__gt=SIPO_ID_CUTOFF)
        .first()
    )
    if obra is None:
        raise APIException('Solicitud no encontrada', status.HTTP_400_BAD_REQUEST)

    current = int(obra.cf_rrhh_sip_status)
    if current >= SIPO_STATUS_CANCELADA:
        raise APIException(
            'La solicitud no se puede cancelar en su estado actual',
            status.HTTP_400_BAD_REQUEST,
        )

    email = _actor_email(user)
    now = timezone.now()
    SipoObra.objects.using('sip_db').filter(cf_rrhh_sip_id=sip_id).update(
        cf_rrhh_sip_status=SIPO_STATUS_CANCELADA,
        cf_rrhh_sip_status_date=now.date() if hasattr(now, 'date') else now,
        cf_rrhh_sip_status_user=email,
        cf_rrhh_sip_update_user=email,
        cf_rrhh_sip_update_date=now if isinstance(now, datetime) else timezone.now(),
    )
    obra.refresh_from_db()

    from .estados import registrar_historial_estado

    registrar_historial_estado(
        sip_id=sip_id,
        estado_anterior=current,
        estado_nuevo=SIPO_STATUS_CANCELADA,
        user=user,
        comentario=comentario,
    )
    return obra
