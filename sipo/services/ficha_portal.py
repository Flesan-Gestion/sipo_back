"""Enlace público para que el colaborador complete la sección 2 de la ficha."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from ..models_ficha import SipoFichaIngreso
from ..models_ficha_acceso import SipoFichaAcceso
from .candidato_portal import qr_svg_base64

TOKEN_DIAS = 7

CAMPOS = (
    'nombres',
    'apellido_paterno',
    'apellido_materno',
    'rut',
    'genero',
    'tratamiento',
    'fecha_nacimiento',
    'edad',
    'nacionalidad',
    'nacionalidad_ext',
    'pais_nacimiento',
    'region_nacimiento',
    'afp',
    'isapre_fonasa',
    'jubilado',
    'estado_civil',
    'telefono',
    'domicilio',
    'numero_direccion',
    'villa',
    'num_depto',
    'region',
    'ciudad',
    'comuna',
    'email_personal',
    'banco',
    'metodo_pago',
    'numero_cuenta',
)


def _ficha(ficha_id: int) -> SipoFichaIngreso:
    ficha = SipoFichaIngreso.objects.filter(pk=ficha_id).first()
    if not ficha:
        raise NotFound('Ficha no encontrada.')
    return ficha


def emitir_acceso_ficha(*, ficha_id: int, front_origin: str) -> dict:
    ficha = _ficha(ficha_id)
    acceso = SipoFichaAcceso.objects.filter(ficha_id=ficha_id).first()
    renovar = acceso is None or acceso.expirado or acceso.estado == SipoFichaAcceso.COMPLETADO
    if acceso is None:
        acceso = SipoFichaAcceso(ficha_id=ficha_id)
    if renovar:
        acceso.token = uuid.uuid4()
        acceso.estado = SipoFichaAcceso.PENDIENTE
        acceso.expira_at = timezone.now() + timedelta(days=TOKEN_DIAS)
        acceso.save()
    url = f"{front_origin.rstrip('/')}/portal-candidato/{acceso.token}"
    return {
        'token': str(acceso.token),
        'url': url,
        'qr_base64': qr_svg_base64(url),
        'expira_at': acceso.expira_at.isoformat(),
        'estado': acceso.estado,
        'cargo': ficha.cargo,
        'empresa': ficha.razon_social_nombre,
        'obra': ficha.obra,
    }


def _acceso(token: str) -> SipoFichaAcceso:
    try:
        uuid.UUID(str(token))
    except ValueError as exc:
        raise NotFound('Enlace inválido.') from exc
    acceso = SipoFichaAcceso.objects.filter(token=token).first()
    if not acceso:
        raise NotFound('Enlace inválido.')
    if acceso.expirado:
        raise PermissionDenied('El enlace expiró.')
    if acceso.estado == SipoFichaAcceso.COMPLETADO:
        raise PermissionDenied('El registro ya fue enviado.')
    return acceso


def resumen_ficha(token: str) -> dict:
    acceso = SipoFichaAcceso.objects.filter(token=token).first()
    if not acceso:
        raise NotFound('Enlace inválido.')
    ficha = _ficha(acceso.ficha_id)
    bloqueado = acceso.expirado or acceso.estado == SipoFichaAcceso.COMPLETADO
    datos = {campo: getattr(ficha, campo, None) for campo in CAMPOS}
    if not str(datos.get('email_personal') or '').strip():
        datos['email_personal'] = ficha.correo_colaborador or ''
    if hasattr(datos.get('fecha_nacimiento'), 'isoformat'):
        datos['fecha_nacimiento'] = datos['fecha_nacimiento'].isoformat()
    from .candidato_maestros import get_candidato_maestros
    return {
        'estado': 'EXPIRADO' if acceso.expirado else acceso.estado,
        'bloqueado': bloqueado,
        'cargo': ficha.cargo,
        'empresa': ficha.razon_social_nombre,
        'obra': ficha.obra,
        'datos': datos,
        'documentos': {
            'doc_domicilio': bool(ficha.doc_domicilio),
            'doc_titulo': bool(ficha.doc_titulo),
            'doc_afp': bool(ficha.doc_afp),
            'doc_salud': bool(ficha.doc_salud),
            'doc_cedula': bool(ficha.doc_cedula),
        },
        'catalogos': get_candidato_maestros(),
    }


def guardar_ficha_publica(*, token: str, data: dict, files) -> dict:
    acceso = _acceso(token)
    ficha = _ficha(acceso.ficha_id)
    enviar = str(data.get('enviar') or '').lower() in ('1', 'true', 'si', 'sí')
    for campo in CAMPOS:
        if campo not in data:
            continue
        valor = data.get(campo)
        if campo == 'jubilado':
            ficha.jubilado = str(valor).lower() in ('1', 'true', 'si', 'sí')
        elif campo == 'edad':
            try:
                ficha.edad = int(valor) if str(valor).strip() else None
            except (TypeError, ValueError):
                ficha.edad = None
        elif campo == 'fecha_nacimiento':
            from .fichas import _parse_date
            ficha.fecha_nacimiento = _parse_date(valor)
        else:
            ficha.__setattr__(campo, (str(valor).strip() or None) if valor is not None else None)
    from .fichas import _assign_ficha_files
    _assign_ficha_files(ficha, files or {})
    if enviar:
        obligatorios = (
            'nombres', 'apellido_paterno', 'apellido_materno', 'rut', 'genero',
            'tratamiento', 'fecha_nacimiento', 'edad', 'nacionalidad',
            'pais_nacimiento', 'region_nacimiento', 'afp', 'isapre_fonasa',
            'estado_civil', 'telefono', 'domicilio', 'numero_direccion',
            'region', 'ciudad', 'comuna', 'email_personal', 'metodo_pago',
            'banco', 'numero_cuenta',
        )
        faltan = {
            campo: ['Este campo es obligatorio.']
            for campo in obligatorios
            if not str(getattr(ficha, campo) or '').strip()
        }
        if str(data.get('jubilado') or '').strip() == '':
            faltan['jubilado'] = ['Este campo es obligatorio.']
        from .rut_validation import validar_rut_activo

        activo = validar_rut_activo(str(getattr(ficha, 'rut') or ''))
        if activo.get('activo'):
            faltan['rut'] = [activo.get('motivo') or 'El trabajador aún está activo en SAP.']
        nac = (ficha.nacionalidad or '').strip()
        if nac in ('Extranjero', 'Extranjero-Definitiva') and not (ficha.nacionalidad_ext or '').strip():
            faltan['nacionalidad_ext'] = ['Debe indicar la nacionalidad extranjera.']
        docs = {
            'doc_domicilio': 'Comprobante de domicilio',
            'doc_afp': 'Certificado AFP',
            'doc_salud': 'Certificado salud',
            'doc_cedula': 'Cédula de identidad',
        }
        for campo, etiqueta in docs.items():
            if not getattr(ficha, campo, None):
                faltan[campo] = [f'{etiqueta} es obligatorio.']
        if faltan:
            raise ValidationError(faltan)
        acceso.estado = SipoFichaAcceso.COMPLETADO
        if ficha.estado in (
            SipoFichaIngreso.ESTADO_BORRADOR_SUPERVISOR,
            SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
            '',
            None,
        ):
            ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_RRHH
    else:
        acceso.estado = SipoFichaAcceso.EN_PROGRESO
    ficha.save()
    acceso.save(update_fields=['estado', 'updated_at'])
    return {'estado': acceso.estado}
