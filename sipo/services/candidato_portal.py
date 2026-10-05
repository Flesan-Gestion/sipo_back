"""Portal público del candidato (enlace / QR)."""

from __future__ import annotations

import base64
import io
import uuid
from datetime import timedelta

import segno
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from ..models import SipoCandidatoObra, SipoObra
from ..models_portal import SipoCandidatoAcceso

TOKEN_DIAS = 7

PORTAL_FIELDS = (
    'cf_rrhh_sip_obra_candidato_nombre',
    'cf_rrhh_sip_obra_candidato_segundo_nombre',
    'cf_rrhh_sip_obra_candidato_ap',
    'cf_rrhh_sip_obra_candidato_am',
    'cf_rrhh_sip_obra_candidato_genero',
    'cf_rrhh_sip_obra_candidato_rut',
    'cf_rrhh_sip_obra_candidato_fecha_nacimiento',
    'cf_rrhh_sip_obra_candidato_estado_civil',
    'cf_rrhh_sip_obra_candidato_telefono',
    'cf_rrhh_sip_obra_candidato_correo',
    'cf_rrhh_sip_obra_candidato_pais_nacimiento',
    'cf_rrhh_sip_obra_candidato_region_nacimiento',
    'cf_rrhh_sip_obra_candidato_nacionalidad',
    'cf_rrhh_sip_obra_candidato_nacionalidad_ext',
    'cf_rrhh_sip_obra_candidato_direccion',
    'cf_rrhh_sip_obra_candidato_numero_dire',
    'cf_rrhh_sip_obra_candidato_num_depto',
    'cf_rrhh_sip_obra_candidato_villa',
    'cf_rrhh_sip_obra_candidato_region',
    'cf_rrhh_sip_obra_candidato_ciudad',
    'cf_rrhh_sip_obra_candidato_comuna',
    'cf_rrhh_sip_obra_candidato_banco',
    'cf_rrhh_sip_obra_candidato_metodo_pago',
    'cf_rrhh_sip_obra_candidato_numcta',
    'cf_rrhh_sip_obra_candidato_nom_afp',
    'cf_rrhh_sip_obra_candidato_nom_salud',
    'cf_rrhh_sip_obra_candidato_valor_plan',
    'cf_rrhh_sip_obra_candidato_valor_uf',
    'cf_rrhh_sip_obra_candidato_jubilado',
    'cf_rrhh_sip_obra_candidato_tratamiento',
)


def qr_svg_base64(url: str) -> str:
    buffer = io.BytesIO()
    segno.make(url, error='m').save(buffer, kind='svg', scale=4, border=2)
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/svg+xml;base64,{encoded}'


def _candidato(sip_id: int, candidato_id: str) -> SipoCandidatoObra:
    row = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_id=candidato_id,
            cf_rrhh_sip_obra_candidato_estado=1,
        )
        .first()
    )
    if not row:
        raise NotFound('Candidato no encontrado.')
    return row


def emitir_acceso(*, sip_id: int, candidato_id: str, front_origin: str) -> dict:
    candidato = _candidato(sip_id, candidato_id)
    acceso = SipoCandidatoAcceso.objects.filter(candidato_id=candidato_id).first()
    renovar = (
        acceso is None
        or acceso.expirado
        or acceso.estado == SipoCandidatoAcceso.COMPLETADO
    )
    if acceso is None:
        acceso = SipoCandidatoAcceso(candidato_id=candidato_id, sip_id=sip_id)
    if renovar:
        acceso.token = uuid.uuid4()
        acceso.sip_id = sip_id
        acceso.estado = SipoCandidatoAcceso.PENDIENTE
        acceso.expira_at = timezone.now() + timedelta(days=TOKEN_DIAS)
        acceso.save()
    url = f"{front_origin.rstrip('/')}/portal-candidato/{acceso.token}"
    obra = SipoObra.objects.using('sip_db').filter(cf_rrhh_sip_id=sip_id).first()
    return {
        'token': str(acceso.token),
        'url': url,
        'qr_base64': qr_svg_base64(url),
        'expira_at': acceso.expira_at.isoformat(),
        'estado': acceso.estado,
        'cargo': candidato.cf_rrhh_sip_obra_candidato_nomcar,
        'empresa': getattr(obra, 'cf_rrhh_sip_razonsocial', None) if obra else None,
        'obra': getattr(obra, 'cf_rrhh_sip_nombre_cc', None) if obra else None,
    }


def _acceso_por_token(token: str) -> SipoCandidatoAcceso:
    try:
        uuid.UUID(str(token))
    except ValueError as exc:
        raise NotFound('Enlace inválido.') from exc
    acceso = SipoCandidatoAcceso.objects.filter(token=token).first()
    if not acceso:
        raise NotFound('Enlace inválido.')
    if acceso.expirado:
        raise PermissionDenied('El enlace expiró.')
    if acceso.estado == SipoCandidatoAcceso.COMPLETADO:
        raise PermissionDenied('El registro ya fue enviado.')
    return acceso


def resumen_publico(token: str) -> dict:
    acceso = SipoCandidatoAcceso.objects.filter(token=token).first()
    if not acceso:
        raise NotFound('Enlace inválido.')
    bloqueado = acceso.expirado or acceso.estado == SipoCandidatoAcceso.COMPLETADO
    candidato = _candidato(acceso.sip_id, acceso.candidato_id)
    obra = SipoObra.objects.using('sip_db').filter(cf_rrhh_sip_id=acceso.sip_id).first()
    datos = {field: getattr(candidato, field, None) for field in PORTAL_FIELDS}
    return {
        'estado': 'EXPIRADO' if acceso.expirado else acceso.estado,
        'bloqueado': bloqueado,
        'expira_at': acceso.expira_at.isoformat(),
        'cargo': candidato.cf_rrhh_sip_obra_candidato_nomcar,
        'sueldo': candidato.cf_rrhh_sip_obra_candidato_sueldo,
        'empresa': getattr(obra, 'cf_rrhh_sip_razonsocial', None) if obra else None,
        'obra': getattr(obra, 'cf_rrhh_sip_nombre_cc', None) if obra else None,
        'datos': datos,
    }


def guardar_publico(*, token: str, data: dict, files) -> dict:
    acceso = _acceso_por_token(token)
    candidato = _candidato(acceso.sip_id, acceso.candidato_id)
    enviar = str(data.get('enviar') or '').lower() in ('1', 'true', 'si', 'sí')

    from .candidato_docs import save_candidato_document

    for key, uploaded in (files or {}).items():
        if not uploaded:
            continue
        saved = save_candidato_document(
            uploaded_file=uploaded,
            doc_type=key,
            sip_id=acceso.sip_id,
            rut=str(data.get('cf_rrhh_sip_obra_candidato_rut') or candidato.cf_rrhh_sip_obra_candidato_rut or ''),
        )
        setattr(candidato, saved['field'], saved['path'])

    for field in PORTAL_FIELDS:
        if field in data and data.get(field) not in (None, ''):
            setattr(candidato, field, data.get(field))

    if enviar:
        faltan = [
            name for name in (
                'cf_rrhh_sip_obra_candidato_nombre',
                'cf_rrhh_sip_obra_candidato_ap',
                'cf_rrhh_sip_obra_candidato_am',
                'cf_rrhh_sip_obra_candidato_rut',
            )
            if not str(getattr(candidato, name) or '').strip()
        ]
        if faltan:
            raise ValidationError({name: 'Obligatorio para enviar.' for name in faltan})
        acceso.estado = SipoCandidatoAcceso.COMPLETADO
    else:
        acceso.estado = SipoCandidatoAcceso.EN_PROGRESO

    candidato.save(using='sip_db')
    acceso.save(update_fields=['estado', 'updated_at'])
    return {'estado': acceso.estado}
