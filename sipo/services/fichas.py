"""Servicios CRUD + aprobación Ficha de Ingreso Personal (flujo 2 niveles)."""

from __future__ import annotations

from datetime import datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from sipo.constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH, SIPO_ROL_SUPERVISOR
from sipo.models_ficha import SipoFichaIngreso
from sipo.services.ficha_labels import resolve_ficha_catalog_fields
from sipo.services.usuario_scope import get_scope_for_user

ESTADO_FLOW = {
    SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR: SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
    SipoFichaIngreso.ESTADO_PENDIENTE_RRHH: SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
    SipoFichaIngreso.ESTADO_PENDIENTE_ADMIN: SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
    SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO: SipoFichaIngreso.ESTADO_APROBADA,
    'PENDIENTE_JEFE': SipoFichaIngreso.ESTADO_APROBADA,
}

ESTADOS_EDITABLES = frozenset(
    {
        SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR,
        SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
        SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
        'PENDIENTE_JEFE',
        SipoFichaIngreso.ESTADO_PENDIENTE_RRHH,
        SipoFichaIngreso.ESTADO_RECHAZADA,
        'PENDIENTE',
        'EN_REVISION',
    }
)

ESTADOS_BLOQUEADOS_EDICION = frozenset(
    {
        SipoFichaIngreso.ESTADO_APROBADA,
        'FINALIZADA',
    }
)


def normalize_ficha_estado(estado: str | None) -> str:
    raw = (estado or SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO).strip().upper()
    if raw in ('PENDIENTE_JEFE', SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO):
        return SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO
    if raw == SipoFichaIngreso.ESTADO_PENDIENTE_ADMIN:
        return SipoFichaIngreso.ESTADO_PENDIENTE_RRHH
    return raw


def accion_aprobar_label(estado: str | None) -> str:
    est = normalize_ficha_estado(estado)
    if est == SipoFichaIngreso.ESTADO_PENDIENTE_RRHH:
        return 'Enviar a Jefe de Terreno'
    if est == SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO:
        return 'Aprobar (Jefe de Terreno)'
    return 'Aprobar'


def _actor_email(user) -> str:
    return (
        getattr(user, 'email', None) or getattr(user, 'username', None) or ''
    ).strip().lower()


def _rol_id(user) -> int | None:
    rol_id = getattr(user, 'sip_rol_id', None)
    try:
        return int(rol_id) if rol_id is not None else None
    except (TypeError, ValueError):
        return None


def _is_admin(user) -> bool:
    return _rol_id(user) == SIPO_ROL_ADMIN


def _is_rrhh(user) -> bool:
    return _rol_id(user) == SIPO_ROL_RRHH


def _is_supervisor(user) -> bool:
    return _rol_id(user) == SIPO_ROL_SUPERVISOR


def _parse_date(value):
    if value in (None, ''):
        return None
    if hasattr(value, 'year'):
        return value
    text = str(value).strip()[:10]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or '').strip().lower()
    return text in ('1', 'true', 't', 'yes', 'y', 'si', 'sí', 's')


def apply_ficha_scope(queryset, user):
    """
    Admin: todas.
    Supervisor: fichas que creó o cuyo RS/CC está en su alcance asignado.
    Resto: fichas donde el correo es jefe directo, admin obra o creador;
    RRHH además ve su alcance territorial.
    """
    if _is_admin(user):
        return queryset

    if _is_supervisor(user):
        email = _actor_email(user)
        own = Q(creado_por__iexact=email) if email else Q()
        scope = get_scope_for_user(user)
        empresas = scope.get('empresas_ids') or []
        centros = scope.get('centros_costo_ids') or []
        territorial = Q()
        if empresas:
            territorial &= Q(razon_social_id__in=empresas)
        if centros:
            territorial &= Q(centro_costo_id__in=centros)
        if territorial:
            return queryset.filter(own | territorial)
        if email:
            return queryset.filter(own)
        return queryset.none()

    email = _actor_email(user)
    participation = Q()
    if email:
        participation = (
            Q(correo_jefe_directo__iexact=email)
            | Q(correo_admin_obra__iexact=email)
            | Q(creado_por__iexact=email)
        )

    if _is_rrhh(user):
        scope = get_scope_for_user(user)
        empresas = scope.get('empresas_ids') or []
        centros = scope.get('centros_costo_ids') or []
        territorial = Q()
        if empresas:
            territorial &= Q(razon_social_id__in=empresas)
        if centros:
            territorial &= Q(centro_costo_id__in=centros)
        if territorial:
            return queryset.filter(participation | territorial)
        if email:
            return queryset.filter(participation)
        return queryset.none()

    if email:
        return queryset.filter(participation)
    return queryset.none()


def user_can_aprobar_ficha(ficha: SipoFichaIngreso, user) -> bool:
    estado = normalize_ficha_estado(ficha.estado)
    if estado in (SipoFichaIngreso.ESTADO_APROBADA, SipoFichaIngreso.ESTADO_RECHAZADA):
        return False
    if _is_admin(user):
        return estado in (
            SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
            SipoFichaIngreso.ESTADO_PENDIENTE_RRHH,
        )

    email = _actor_email(user)
    if estado == SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO:
        return bool(email) and email == (ficha.correo_jefe_directo or '').strip().lower()
    if estado == SipoFichaIngreso.ESTADO_PENDIENTE_RRHH:
        return _is_rrhh(user)
    return False


def user_can_rechazar_ficha(ficha: SipoFichaIngreso, user) -> bool:
    return user_can_aprobar_ficha(ficha, user)


def user_can_retroceder_ficha(ficha: SipoFichaIngreso, user) -> bool:
    """Admin o RRHH pueden devolver una ficha APROBADA al flujo de aprobación."""
    estado = normalize_ficha_estado(ficha.estado)
    if estado != SipoFichaIngreso.ESTADO_APROBADA:
        return False
    return _is_admin(user) or _is_rrhh(user)


def user_can_eliminar_ficha(ficha: SipoFichaIngreso, user) -> bool:
    """Admin o RRHH pueden eliminar cualquier ficha de su alcance."""
    return _is_admin(user) or _is_rrhh(user)


def ficha_es_editable(ficha: SipoFichaIngreso) -> bool:
    estado = normalize_ficha_estado(ficha.estado)
    if estado in ESTADOS_BLOQUEADOS_EDICION:
        return False
    return estado in {normalize_ficha_estado(e) for e in ESTADOS_EDITABLES} or estado.startswith(
        'PENDIENTE'
    )

def user_can_editar_ficha(ficha: SipoFichaIngreso, user) -> bool:
    if not ficha_es_editable(ficha):
        return False
    if user is not None and _is_supervisor(user):
        estado = normalize_ficha_estado(ficha.estado)
        if estado not in (
            SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR,
            SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
        ):
            return False
        email = _actor_email(user)
        return bool(email) and email == (ficha.creado_por or '').strip().lower()
    return True


def list_fichas(
    *,
    user,
    search: str | None = None,
    solo_aprobadas: bool = False,
    razon_social_id: str | None = None,
) -> list[SipoFichaIngreso]:
    qs = apply_ficha_scope(SipoFichaIngreso.objects.all(), user)
    if solo_aprobadas:
        qs = qs.filter(estado=SipoFichaIngreso.ESTADO_APROBADA)
    rs = (razon_social_id or '').strip()
    if rs:
        rs_clean = rs.replace('.', '').replace(' ', '').upper()
        qs = qs.filter(
            Q(razon_social_id=rs)
            | Q(razon_social_id=rs_clean)
            | Q(razon_social_id__iexact=rs)
            | Q(razon_social_id__iexact=rs_clean)
        )
    text = (search or '').strip()
    if text:
        qs = qs.filter(
            Q(rut__icontains=text)
            | Q(nombres__icontains=text)
            | Q(apellido_paterno__icontains=text)
            | Q(apellido_materno__icontains=text)
            | Q(razon_social_nombre__icontains=text)
            | Q(centro_costo_id__icontains=text)
            | Q(centro_costo_nombre__icontains=text)
            | Q(creado_por__icontains=text)
            | Q(cargo__icontains=text)
            | Q(correo_colaborador__icontains=text)
        )
    return list(qs.order_by('-id'))


def get_ficha_for_user(ficha_id: int, user) -> SipoFichaIngreso:
    ficha = SipoFichaIngreso.objects.filter(pk=ficha_id).first()
    if not ficha:
        raise NotFound('Ficha no encontrada.')
    scoped = apply_ficha_scope(SipoFichaIngreso.objects.filter(pk=ficha_id), user)
    if not scoped.exists():
        raise PermissionDenied("Don't have access to this resource")
    return ficha


def aprobar_ficha(*, ficha_id: int, user) -> SipoFichaIngreso:
    ficha = get_ficha_for_user(ficha_id, user)
    if not user_can_aprobar_ficha(ficha, user):
        raise PermissionDenied('No tiene permiso para aprobar esta ficha en el estado actual.')

    email = _actor_email(user)
    now = timezone.now()
    estado = normalize_ficha_estado(ficha.estado)
    next_estado = ESTADO_FLOW.get(estado)
    if not next_estado:
        raise ValidationError({'estado': ['La ficha ya está completamente aprobada.']})

    if estado == SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO:
        ficha.aprobado_jefe_por = email
        ficha.aprobado_jefe_at = now
    elif estado == SipoFichaIngreso.ESTADO_PENDIENTE_RRHH:
        ficha.aprobado_rrhh_por = email
        ficha.aprobado_rrhh_at = now

    ficha.estado = next_estado
    ficha.rechazo_comentario = None
    ficha.rechazo_por = None
    ficha.rechazo_at = None
    ficha.save()
    return ficha


def rechazar_ficha(*, ficha_id: int, user, comentario: str | None = None) -> SipoFichaIngreso:
    ficha = get_ficha_for_user(ficha_id, user)
    if not user_can_rechazar_ficha(ficha, user):
        raise PermissionDenied('No tiene permiso para rechazar esta ficha en el estado actual.')

    comentario_clean = (comentario or '').strip()
    if not comentario_clean:
        raise ValidationError({'comentario': ['El comentario de rechazo es obligatorio.']})

    email = _actor_email(user)
    now = timezone.now()
    ficha.estado = SipoFichaIngreso.ESTADO_RECHAZADA
    ficha.rechazo_comentario = comentario_clean
    ficha.rechazo_por = email
    ficha.rechazo_at = now
    ficha.save()
    return ficha


def retroceder_ficha(*, ficha_id: int, user) -> SipoFichaIngreso:
    """Devuelve una ficha APROBADA a Pendiente Jefe de Terreno para reaprobar."""
    ficha = get_ficha_for_user(ficha_id, user)
    if not user_can_retroceder_ficha(ficha, user):
        raise PermissionDenied(
            'No tiene permiso para retroceder el estado de esta ficha.'
        )

    estado = normalize_ficha_estado(ficha.estado)
    if estado != SipoFichaIngreso.ESTADO_APROBADA:
        raise ValidationError(
            {'estado': ['Solo se puede retroceder una ficha completamente aprobada.']}
        )

    ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO
    ficha.aprobado_jefe_por = None
    ficha.aprobado_jefe_at = None
    ficha.aprobado_admin_por = None
    ficha.aprobado_admin_at = None
    ficha.aprobado_rrhh_por = None
    ficha.aprobado_rrhh_at = None
    ficha.rechazo_comentario = None
    ficha.rechazo_por = None
    ficha.rechazo_at = None
    ficha.save()
    return ficha


_FICHA_DOC_FIELDS = (
    'doc_domicilio',
    'doc_titulo',
    'doc_afp',
    'doc_salud',
    'doc_cedula',
)


def eliminar_ficha(*, ficha_id: int, user) -> dict:
    ficha = get_ficha_for_user(ficha_id, user)
    if not user_can_eliminar_ficha(ficha, user):
        raise PermissionDenied('No tiene permiso para eliminar esta ficha.')

    for field_name in _FICHA_DOC_FIELDS:
        field = getattr(ficha, field_name, None)
        if field:
            try:
                field.delete(save=False)
            except Exception:
                pass

    deleted_id = ficha.id
    ficha.delete()
    return {'id': deleted_id, 'deleted': True}


def _es_solo_rrhh(data: dict) -> bool:
    return str(data.get('solo_rrhh') or '').lower() in ('1', 'true', 'si', 'sí')


def _es_solo_supervisor(data: dict) -> bool:
    return str(data.get('solo_supervisor') or '').lower() in ('1', 'true', 'si', 'sí')


_CAMPOS_PERSONALES = {
    'nombres', 'apellido_paterno', 'apellido_materno', 'rut', 'genero',
    'tratamiento', 'fecha_nacimiento', 'edad', 'nacionalidad',
    'pais_nacimiento', 'region_nacimiento', 'afp', 'isapre_fonasa',
    'estado_civil', 'telefono', 'domicilio', 'numero_direccion',
    'region', 'ciudad', 'comuna', 'email_personal', 'metodo_pago',
    'banco', 'numero_cuenta',
}

_CAMPOS_RRHH = {
    'razon_social_id', 'obra', 'centro_costo_id', 'centro_costo_nombre',
    'correo_jefe_directo', 'correo_admin_obra', 'jefe_user_id', 'jefe_nombre',
    'cuenta_gasto',
}


def create_ficha(*, data: dict, files: dict, user) -> SipoFichaIngreso:
    email = _actor_email(user)
    if not email:
        raise ValidationError({'creado_por': ['Usuario sin correo en sesión.']})

    from sipo.serializers_ficha import FICHA_REQUIRED_TEXT_FIELDS

    if _is_supervisor(user) and not _es_solo_supervisor(data):
        raise PermissionDenied('El supervisor solo puede registrar la parte inicial de la ficha.')

    solo = _es_solo_rrhh(data)
    solo_supervisor = _es_solo_supervisor(data)
    omitir = set()
    if solo_supervisor:
        omitir = set(_CAMPOS_PERSONALES) | set(_CAMPOS_RRHH)
    elif solo:
        omitir = set(_CAMPOS_PERSONALES)
    errors = {}
    for key in FICHA_REQUIRED_TEXT_FIELDS:
        if key in omitir:
            continue
        val = data.get(key)
        if val is None or (isinstance(val, str) and str(val).strip() == ''):
            errors[key] = ['Este campo es obligatorio.']
    if not solo and not solo_supervisor:
        jub = data.get('jubilado')
        if jub is None or (isinstance(jub, str) and str(jub).strip() == ''):
            errors['jubilado'] = ['Este campo es obligatorio.']
        for field, alt in (
            ('doc_domicilio', 'comprobanteDomicilio'),
            ('doc_afp', 'certificadoAfp'),
            ('doc_salud', 'certificadoSalud'),
            ('doc_cedula', 'copiaCedula'),
        ):
            if not (files.get(field) or files.get(alt)):
                errors[field] = ['Documento obligatorio.']
    if errors:
        raise ValidationError(errors)

    _assert_scope_for_data(user, data)
    _assert_rs_cc_pais_ficha(data, is_create=True)
    labels = resolve_ficha_catalog_fields(data)

    ficha = SipoFichaIngreso(
        estado=(
            SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR
            if solo_supervisor
            else SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO
        ),
        creado_por=email,
        creado_por_id=getattr(user, 'id', None) or getattr(user, 'pk', None),
    )
    _assign_ficha_fields(ficha, data, labels)
    _assign_ficha_files(ficha, files)
    ficha.save()
    if solo_supervisor and not ficha.email_personal and ficha.correo_colaborador:
        ficha.email_personal = ficha.correo_colaborador
        ficha.save(update_fields=['email_personal'])
    if solo_supervisor:
        from sipo.services.notifications import send_email_invitacion_colaborador

        send_email_invitacion_colaborador(ficha.id)
        ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR
        ficha.save(update_fields=['estado'])
    return ficha


def update_ficha(*, ficha_id: int, data: dict, files: dict, user) -> SipoFichaIngreso:
    ficha = get_ficha_for_user(ficha_id, user)
    if not ficha_es_editable(ficha):
        raise APIException(
            'La ficha no puede modificarse porque ya fue aprobada o finalizada.',
            status.HTTP_400_BAD_REQUEST,
        )

    if _is_supervisor(user):
        estado = normalize_ficha_estado(ficha.estado)
        if estado not in (
            SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR,
            SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
        ):
            raise PermissionDenied('No puede modificar la ficha en este estado.')
        email = _actor_email(user)
        if not email or email != (ficha.creado_por or '').strip().lower():
            raise PermissionDenied('Solo puede editar fichas creadas por usted.')
        data = dict(data)
        data['solo_supervisor'] = '1'
        files = {}
        for key in _CAMPOS_PERSONALES | _CAMPOS_RRHH:
            data.pop(key, None)

    was_rechazada = normalize_ficha_estado(ficha.estado) == SipoFichaIngreso.ESTADO_RECHAZADA

    if ('rut' in data or 'nombres' in data) and not _es_solo_rrhh(data) and not _es_solo_supervisor(data):
        from sipo.serializers_ficha import FICHA_REQUIRED_TEXT_FIELDS

        errors = {}
        for key in FICHA_REQUIRED_TEXT_FIELDS:
            val = data.get(key)
            if val is None or (isinstance(val, str) and str(val).strip() == ''):
                errors[key] = ['Este campo es obligatorio.']
        jub = data.get('jubilado')
        if jub is None or (isinstance(jub, str) and str(jub).strip() == ''):
            errors['jubilado'] = ['Este campo es obligatorio.']
        if errors:
            raise ValidationError(errors)

    merged = {
        'razon_social_id': ficha.razon_social_id,
        'centro_costo_id': ficha.centro_costo_id,
        **{k: v for k, v in data.items()},
    }
    _assert_scope_for_data(user, merged)
    if any(k in data for k in ('razon_social_id', 'centro_costo_id', 'external_code_pais')):
        _assert_rs_cc_pais_ficha(merged)
    labels = resolve_ficha_catalog_fields(data if data else {})
    _assign_ficha_fields(ficha, data, labels, partial=True)
    _assign_ficha_files(ficha, files)
    if was_rechazada:
        ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO
        ficha.rechazo_comentario = None
        ficha.rechazo_por = None
        ficha.rechazo_at = None
    ficha.save()
    return ficha


def _assert_scope_for_data(user, data: dict) -> None:
    scope = get_scope_for_user(user)
    if scope.get('is_admin'):
        return
    empresas = set(scope.get('empresas_ids') or [])
    centros = set(scope.get('centros_costo_ids') or [])
    rs = str(data.get('razon_social_id') or '').strip()
    cc = str(data.get('centro_costo_id') or '').strip()
    if empresas and rs and rs not in empresas:
        raise PermissionDenied('No tiene permiso para la razón social seleccionada')
    if centros and cc and cc not in centros:
        raise PermissionDenied('No tiene permiso para el centro de costo seleccionado')


def _assert_rs_cc_pais_ficha(data: dict, *, is_create: bool = False) -> None:
    from .pais_segregation import assert_create_only_grupo2, validate_razon_social_centro_costo

    rs = str(data.get('razon_social_id') or '').strip()
    cc = str(data.get('centro_costo_id') or '').strip()
    if not rs or not cc:
        return
    pais = data.get('external_code_pais')
    if is_create:
        pais = assert_create_only_grupo2(pais)
    validate_razon_social_centro_costo(
        razon_social_id=rs,
        centro_costo_id=cc,
        external_code_pais=pais,
    )


def _assign_ficha_fields(
    ficha: SipoFichaIngreso,
    data: dict,
    labels: dict,
    *,
    partial: bool = False,
) -> None:
    def has(key: str) -> bool:
        return (not partial) or (key in data)

    if has('razon_social_id'):
        ficha.razon_social_id = (data.get('razon_social_id') or '').strip() or None
    if has('razon_social_nombre'):
        ficha.razon_social_nombre = (data.get('razon_social_nombre') or '').strip() or None
    if has('obra'):
        ficha.obra = (data.get('obra') or '').strip() or None
    if has('centro_costo_id'):
        ficha.centro_costo_id = (data.get('centro_costo_id') or '').strip() or None
    if has('centro_costo_nombre'):
        ficha.centro_costo_nombre = (data.get('centro_costo_nombre') or '').strip() or None
    if has('cargo'):
        ficha.cargo = (data.get('cargo') or '').strip() or None
    if has('fecha_ingreso'):
        ficha.fecha_ingreso = _parse_date(data.get('fecha_ingreso'))
    if has('correo_jefe_directo'):
        ficha.correo_jefe_directo = (
            (data.get('correo_jefe_directo') or '').strip().lower() or None
        )
    if has('correo_admin_obra'):
        ficha.correo_admin_obra = (data.get('correo_admin_obra') or '').strip().lower() or None
    if has('correo_colaborador'):
        ficha.correo_colaborador = (
            (data.get('correo_colaborador') or '').strip().lower() or None
        )
    if has('jefe_user_id'):
        ficha.jefe_user_id = (data.get('jefe_user_id') or '').strip() or None
    if has('jefe_nombre'):
        ficha.jefe_nombre = (data.get('jefe_nombre') or '').strip() or None
    if has('jefe_correo'):
        ficha.jefe_correo = (data.get('jefe_correo') or '').strip().lower() or None
    if has('nombres'):
        ficha.nombres = (data.get('nombres') or '').strip().upper() or None
    if has('apellido_paterno'):
        ap = (data.get('apellido_paterno') or '').strip() or None
        ficha.apellido_paterno = ap.upper() if ap else None
    if has('apellido_materno'):
        am = (data.get('apellido_materno') or '').strip() or None
        ficha.apellido_materno = am.upper() if am else None
    if has('rut'):
        ficha.rut = (data.get('rut') or '').strip() or None
    if has('tratamiento'):
        ficha.tratamiento = (data.get('tratamiento') or '').strip() or None
    if has('genero'):
        ficha.genero = (data.get('genero') or '').strip() or None
    if has('afp'):
        ficha.afp = labels.get('afp')
    if has('isapre_fonasa'):
        ficha.isapre_fonasa = labels.get('isapre_fonasa')
    if has('jubilado'):
        ficha.jubilado = _parse_bool(data.get('jubilado'))
    if has('estado_civil'):
        ficha.estado_civil = labels.get('estado_civil')
    if has('edad'):
        ficha.edad = int(data['edad']) if str(data.get('edad') or '').isdigit() else None
    if has('fecha_nacimiento'):
        ficha.fecha_nacimiento = _parse_date(data.get('fecha_nacimiento'))
    if has('pais_nacimiento'):
        ficha.pais_nacimiento = (data.get('pais_nacimiento') or '').strip() or None
    if has('region_nacimiento'):
        ficha.region_nacimiento = (data.get('region_nacimiento') or '').strip() or None
    if has('nacionalidad'):
        ficha.nacionalidad = (data.get('nacionalidad') or '').strip() or None
    if has('nacionalidad_ext'):
        ficha.nacionalidad_ext = (data.get('nacionalidad_ext') or '').strip() or None
    if has('telefono'):
        ficha.telefono = (data.get('telefono') or '').strip() or None
    if has('domicilio'):
        ficha.domicilio = (data.get('domicilio') or '').strip() or None
    if has('villa'):
        ficha.villa = (data.get('villa') or '').strip() or None
    if has('numero_direccion'):
        ficha.numero_direccion = (data.get('numero_direccion') or '').strip() or None
    if has('num_depto'):
        ficha.num_depto = (data.get('num_depto') or '').strip() or None
    if has('region'):
        ficha.region = (data.get('region') or '').strip() or None
    if has('ciudad'):
        ficha.ciudad = (data.get('ciudad') or '').strip() or None
    if has('comuna'):
        ficha.comuna = (data.get('comuna') or '').strip() or None
    if has('email_personal'):
        ficha.email_personal = (data.get('email_personal') or '').strip() or None
    if has('banco'):
        ficha.banco = labels.get('banco')
    if has('metodo_pago') or has('tipo_cuenta'):
        ficha.metodo_pago = (
            data.get('metodo_pago') or data.get('tipo_cuenta') or ''
        ).strip() or None
    if has('numero_cuenta'):
        ficha.numero_cuenta = (data.get('numero_cuenta') or '').strip() or None
    if has('sueldo_liquido'):
        ficha.sueldo_liquido = (
            int(data['sueldo_liquido'])
            if str(data.get('sueldo_liquido') or '').replace('.', '').isdigit()
            else None
        )
    if has('dias_contrato'):
        ficha.dias_contrato = (
            int(data['dias_contrato']) if str(data.get('dias_contrato') or '').isdigit() else None
        )
    if has('cuenta_gasto'):
        ficha.cuenta_gasto = (data.get('cuenta_gasto') or '').strip() or None
    if has('tipo_contrato'):
        ficha.tipo_contrato = (data.get('tipo_contrato') or '').strip() or None
    if has('termino_contrato'):
        ficha.termino_contrato = (data.get('termino_contrato') or '').strip() or None
    if has('fecha_termino_ito'):
        ficha.fecha_termino_ito = _parse_date(data.get('fecha_termino_ito'))
    if has('tipo_jornada'):
        ficha.tipo_jornada = (data.get('tipo_jornada') or '').strip() or None
    if has('horario'):
        ficha.horario = (data.get('horario') or '').strip() or None
    if has('observaciones'):
        ficha.observaciones = (data.get('observaciones') or '').strip() or None


def _assign_ficha_files(ficha: SipoFichaIngreso, files: dict) -> None:
    file_map = {
        'doc_domicilio': files.get('doc_domicilio') or files.get('comprobanteDomicilio'),
        'doc_titulo': files.get('doc_titulo') or files.get('certificadoTitulo'),
        'doc_afp': files.get('doc_afp') or files.get('certificadoAfp'),
        'doc_salud': files.get('doc_salud') or files.get('certificadoSalud'),
        'doc_cedula': files.get('doc_cedula') or files.get('copiaCedula'),
    }
    for field, uploaded in file_map.items():
        if not uploaded:
            continue
        nombre = getattr(uploaded, 'name', None) or f'{field}.bin'
        getattr(ficha, field).save(nombre, uploaded, save=False)
