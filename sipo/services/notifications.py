"""Notificaciones SMTP SIPO Obra — solo correos vivos del legado."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from ..constants import SIPO_CANDIDATO_ACTIVO
from ..models import SipoCandidatoObra, SipoObra

logger = logging.getLogger(__name__)

EVENTO_REVISION = 'revision'
EVENTO_APROBAR_CONTRATACION = 'aprobar_contratacion'
EVENTO_ERROR_INTEGRACION = 'error_integracion'
EVENTO_CONTRATO = 'contrato'
EVENTO_BUILDER_OK = 'builder_ok'
EVENTO_RECHAZO_DOCS = 'rechazo_documentos'


@dataclass
class SipoEmailMessage:
    subject: str
    html_body: str
    intended_recipients: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    notification_key: str = ''
    from_name: str | None = None
    inline_images: list[tuple[str, bytes]] = field(default_factory=list)


def _email_enabled() -> bool:
    return bool(getattr(settings, 'SIP_EMAIL_ENABLED', True))


def _force_override() -> bool:
    return bool(getattr(settings, 'SIP_EMAIL_FORCE_OVERRIDE', True))


def _test_override() -> str:
    return _normalize_email(
        getattr(settings, 'SIP_EMAIL_TEST_OVERRIDE', 'martin.norambuena@flesan.cl')
    )


def _img_base() -> str:
    return (getattr(settings, 'SIP_EMAIL_IMG_BASE', '') or '').rstrip('/')


def _portal_obra_url(sip_id: int) -> str:
    base = (getattr(settings, 'SIPO_PORTAL_BASE_URL', '') or '').rstrip('/')
    if not base:
        return ''
    return f'{base}/{sip_id}'


def _normalize_email(value: str | None) -> str:
    return (value or '').strip().lower()


def _unique_emails(*addresses: str | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in addresses:
        email = _normalize_email(raw)
        if email and email not in seen:
            seen.add(email)
            result.append(email)
    return result


def _split_setting_emails(setting_name: str) -> list[str]:
    raw = getattr(settings, setting_name, '') or ''
    return _unique_emails(*(p.strip() for p in str(raw).split(',') if p.strip()))


def _subject_prefix() -> str:
    return timezone.localdate().strftime('%Y/%m/%d')


def _subject_prefix_dmy() -> str:
    return timezone.localdate().strftime('%d/%m/%Y')


def _candidato_nombre(c: SipoCandidatoObra) -> str:
    parts = [
        c.cf_rrhh_sip_obra_candidato_nombre,
        getattr(c, 'cf_rrhh_sip_obra_candidato_segundo_nombre', None),
        c.cf_rrhh_sip_obra_candidato_ap,
        c.cf_rrhh_sip_obra_candidato_am,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip()).upper()


def _obra_empresa_un_cg(obra: SipoObra) -> tuple[str, str, str]:
    empresa = (obra.cf_rrhh_sip_razonsocial or obra.cf_rrhh_sip_rut or '—').strip()
    un = (obra.cf_rrhh_sip_nombre_uni or obra.cf_rrhh_sip_uni or '—').strip()
    cg = (obra.cf_rrhh_sip_nombre_cc or obra.cf_rrhh_sip_cc or '—').strip()
    return empresa, un, cg


def _base_context(**extra: Any) -> dict[str, Any]:
    ctx = {'img_base': _img_base(), **extra}
    return ctx


def _render(template_name: str, context: dict[str, Any]) -> str:
    return render_to_string(template_name, context)


def _resolve_to(intended: Iterable[str]) -> list[str]:
    cleaned = _unique_emails(*list(intended))
    if _force_override():
        override = _test_override()
        return [override] if override else cleaned
    return cleaned


def send_sipo_email(message: SipoEmailMessage) -> dict[str, Any]:
    """
    Envío HTML centralizado.
    Con SIP_EMAIL_FORCE_OVERRIDE=si redirige TO/BCC a SIP_EMAIL_TEST_OVERRIDE
    y anota en el asunto los destinatarios originales.
    """
    if not _email_enabled():
        logger.warning('notifications skipped: SIP_EMAIL_ENABLED=False key=%s', message.notification_key)
        return {'sent': False, 'skipped': True, 'reason': 'SIP_EMAIL_ENABLED=False'}

    intended = _unique_emails(*message.intended_recipients)
    intended_bcc = _unique_emails(*message.bcc)
    override_on = _force_override()
    override_addr = _test_override()

    if not intended and not intended_bcc:
        if override_on and override_addr:
            intended = [override_addr]
            logger.warning(
                'notifications: sin destinatarios reales key=%s — envío solo a override %s',
                message.notification_key,
                override_addr,
            )
        else:
            logger.warning(
                'notifications: sin destinatarios key=%s',
                message.notification_key,
            )
            return {'sent': False, 'skipped': True, 'reason': 'sin_destinatarios'}

    recipients = _resolve_to(intended or intended_bcc)
    subject = message.subject
    if override_on:
        original_parts = []
        real_to = _unique_emails(*message.intended_recipients)
        real_bcc = intended_bcc
        if real_to:
            original_parts.append(f'TO: {", ".join(real_to)}')
        if real_bcc:
            original_parts.append(f'CCO: {", ".join(real_bcc)}')
        if not original_parts:
            original_parts.append('TO: (sin destinatarios en obra)')
        subject = f'{subject} [TEST -> {override_addr}; era: {" | ".join(original_parts)}]'

    from_name = message.from_name or getattr(settings, 'SIP_EMAIL_FROM_NAME', 'Sip Obra')
    from_email = getattr(settings, 'SIP_EMAIL_FROM', None) or getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'equipo_desarrollo@flesan.cl'
    )

    html_body = (message.html_body or '').strip()
    if not html_body:
        return {'sent': False, 'skipped': True, 'reason': 'html_vacio'}

    bcc: list[str] = []
    if not override_on:
        to_set = set(recipients)
        bcc = [e for e in intended_bcc if e not in to_set]

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body='Este mensaje requiere un cliente de correo con soporte HTML.',
            from_email=f'{from_name} <{from_email}>',
            to=recipients,
            bcc=bcc,
        )
        msg.attach_alternative(html_body, 'text/html')
        if message.inline_images:
            from email.mime.image import MIMEImage

            msg.mixed_subtype = 'related'
            for cid, payload in message.inline_images:
                img = MIMEImage(payload, _subtype='png')
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=f'{cid}.png')
                msg.attach(img)
        msg.send(fail_silently=False)
        logger.info(
            'notifications OK key=%s to=%s intended=%s subject=%s',
            message.notification_key,
            recipients,
            message.intended_recipients,
            subject,
        )
        return {
            'sent': True,
            'recipients': recipients,
            'intended_recipients': _unique_emails(*message.intended_recipients),
            'intended_bcc': intended_bcc,
            'evento': message.notification_key,
            'subject': subject,
        }
    except Exception as exc:
        logger.exception(
            'notifications FALLÓ key=%s to=%s: %s',
            message.notification_key,
            recipients,
            exc,
        )
        return {
            'sent': False,
            'error': str(exc),
            'recipients': recipients,
            'intended_recipients': _unique_emails(*message.intended_recipients),
        }


def send_email_paso_revision(
    obra: SipoObra,
    candidatos: list[SipoCandidatoObra] | None = None,
) -> dict[str, Any]:
    """§3.1 — TO: Adm de obra."""
    candidatos = candidatos or []
    empresa, un, cg = _obra_empresa_un_cg(obra)
    html = _render(
        'emails/obra_paso_revision.html',
        _base_context(
            header_img='NE_Colaborador_Seleccionado.jpg',
            total_candidatos=len(candidatos),
            empresa=empresa,
            un=un,
            cg=cg,
            portal_url=_portal_obra_url(obra.cf_rrhh_sip_id),
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Notificación de Selección',
            html_body=html,
            intended_recipients=_unique_emails(obra.cf_rrhh_sip_adm),
            notification_key=EVENTO_REVISION,
        )
    )


def send_email_error_builder(
    obra: SipoObra,
    *,
    mensaje_error: str,
) -> dict[str, Any]:
    """§3.2 — TO: lista fija RRHH/Admin."""
    html = _render(
        'emails/obra_error_builder.html',
        _base_context(header_img='NF_Proceso_de_Seleccion_SIP.jpg', mensaje_error=mensaje_error),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=(
                f'{_subject_prefix_dmy()} Colaboradores NO creados en Builder '
                f'SIP_OBRA: {obra.cf_rrhh_sip_id}'
            ),
            html_body=html,
            intended_recipients=_split_setting_emails('SIP_EMAIL_ERROR_BUILDER'),
            notification_key=EVENTO_ERROR_INTEGRACION,
            from_name='Creacion trabajadores Builder',
        )
    )


def send_email_obra_finalizada(
    obra: SipoObra,
    *,
    total_contratos: int,
) -> dict[str, Any]:
    """§3.3 — TO: Adm + As."""
    empresa, un, cg = _obra_empresa_un_cg(obra)
    html = _render(
        'emails/obra_finalizada.html',
        _base_context(
            header_img='NA_Solicitud_de_incoporacion.jpg',
            sip_id=obra.cf_rrhh_sip_id,
            total_contratos=total_contratos,
            empresa=empresa,
            un=un,
            cg=cg,
            portal_url=_portal_obra_url(obra.cf_rrhh_sip_id),
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Notificación de Selección',
            html_body=html,
            intended_recipients=_unique_emails(obra.cf_rrhh_sip_adm, obra.cf_rrhh_sip_as),
            notification_key=EVENTO_APROBAR_CONTRATACION,
        )
    )


def send_email_contrato_disponible(
    obra: SipoObra,
    candidato: SipoCandidatoObra,
) -> dict[str, Any]:
    """§3.4 — TO: Adm + As."""
    html = _render(
        'emails/obra_contrato.html',
        _base_context(
            header_img='NE_Proceso_de_envio_de_documento.jpg',
            nombre_candidato=_candidato_nombre(candidato),
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Notificación de Contrato',
            html_body=html,
            intended_recipients=_unique_emails(obra.cf_rrhh_sip_adm, obra.cf_rrhh_sip_as),
            notification_key=EVENTO_CONTRATO,
        )
    )


def send_email_builder_ok(
    obra: SipoObra,
    candidato: SipoCandidatoObra,
) -> dict[str, Any]:
    """§3.5 — TO: Adm + As."""
    html = _render(
        'emails/obra_builder_ok.html',
        _base_context(
            header_img='NF_Proceso_de_Seleccion_SIP.jpg',
            nombre_candidato=_candidato_nombre(candidato),
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Notificación de Control de Asistencia',
            html_body=html,
            intended_recipients=_unique_emails(obra.cf_rrhh_sip_adm, obra.cf_rrhh_sip_as),
            notification_key=EVENTO_BUILDER_OK,
        )
    )


def send_email_rechazo_documentos(
    obra: SipoObra,
    candidato: SipoCandidatoObra,
    *,
    razones: str,
) -> dict[str, Any]:
    """§3.6 — TO: Adm + As; CCO: lista RRHH."""
    html = _render(
        'emails/obra_rechazo_documentos.html',
        _base_context(
            header_img='Rechazo_Proc_seleccion.jpg',
            nombre_candidato=_candidato_nombre(candidato),
            razones=(razones or '').strip() or '—',
            portal_url=_portal_obra_url(obra.cf_rrhh_sip_id),
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Notificación de Aprobacion de Selección',
            html_body=html,
            intended_recipients=_unique_emails(obra.cf_rrhh_sip_adm, obra.cf_rrhh_sip_as),
            bcc=_split_setting_emails('SIP_EMAIL_RECHAZO_DOCS_BCC'),
            notification_key=EVENTO_RECHAZO_DOCS,
        )
    )


def enviar_notificacion_email(
    evento: str,
    obra: SipoObra,
    candidatos: list[SipoCandidatoObra] | None = None,
    *,
    errores: list[str] | None = None,
    origen_error: str = 'integración',
) -> dict[str, Any]:
    """Compatibilidad: despacha a funciones dedicadas de correos vivos."""
    candidatos = candidatos or []
    if evento == EVENTO_REVISION:
        return send_email_paso_revision(obra, candidatos)
    if evento == EVENTO_APROBAR_CONTRATACION:
        return send_email_obra_finalizada(obra, total_contratos=len(candidatos))
    if evento == EVENTO_ERROR_INTEGRACION:
        detalle = '; '.join(errores or []) or f'Error de {origen_error}'
        return send_email_error_builder(obra, mensaje_error=detalle)
    logger.warning('notifications: evento no operativo en legado vivo: %s', evento)
    return {'sent': False, 'skipped': True, 'reason': 'evento_no_operativo'}


def list_candidatos_activos_obra(sip_id: int) -> list[SipoCandidatoObra]:
    return list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
        )
        .order_by('cf_rrhh_sip_obra_candidato_ap')
    )


def collect_integration_errors(
    *,
    builder_result: dict | None = None,
    sap_result: dict | None = None,
) -> list[str]:
    errores: list[str] = []
    builder_result = builder_result or {}
    sap_result = sap_result or {}

    if not builder_result.get('skipped'):
        for row in builder_result.get('resultados', []):
            if not row.get('builder_ok'):
                detail = (row.get('error') or '').strip()
                if detail:
                    errores.append(detail)
                else:
                    errores.append(
                        f'candidato {row.get("candidato_id")} no sincronizado'
                    )

    if not sap_result.get('skipped'):
        for row in sap_result.get('resultados', []):
            for entity in row.get('entities', []):
                status = str(entity.get('status') or '').upper()
                if status not in ('OK', 'SUCCESS', 'SKIPPED') and not entity.get('dry_run'):
                    errores.append(
                        f'SAP {entity.get("entity")} user {row.get("user_id")}: '
                        f'{entity.get("message") or status}'
                    )
    return errores


def _qr_png(url: str) -> bytes:
    import io

    import segno

    buffer = io.BytesIO()
    segno.make(url, error='m').save(buffer, kind='png', scale=6, border=2)
    return buffer.getvalue()


def send_email_invitacion_colaborador(ficha_id: int) -> dict[str, Any]:
    """Enlace y QR al correo_colaborador al guardar la ficha del supervisor."""
    import base64

    from ..models_ficha import SipoFichaIngreso
    from .ficha_portal import emitir_acceso_ficha

    ficha = SipoFichaIngreso.objects.filter(pk=ficha_id).first()
    if not ficha:
        return {'sent': False, 'skipped': True, 'reason': 'ficha_no_encontrada'}

    origin = getattr(settings, 'SIPO_PUBLIC_ORIGIN', '') or 'http://localhost:5173'
    acceso = emitir_acceso_ficha(ficha_id=ficha.id, front_origin=origin)
    url = acceso['url']
    png = _qr_png(url)
    qr_b64 = base64.b64encode(png).decode('ascii')
    html = _render(
        'emails/invitacion_candidato_sip.html',
        _base_context(
            header_img='NE_Solicitud_de_incorporacion.jpg',
            portal_url=url,
            token=acceso['token'],
            qr_base64=qr_b64,
            cargo=ficha.cargo or '',
            empresa=ficha.razon_social_nombre or '',
            obra=ficha.obra or '',
        ),
    )
    return send_sipo_email(
        SipoEmailMessage(
            subject=f'{_subject_prefix()} [SIP OBRA] Completa tu ficha de ingreso',
            html_body=html,
            intended_recipients=_unique_emails(ficha.correo_colaborador),
            notification_key='invitacion_colaborador',
            inline_images=[('qr_colaborador', png)],
        )
    )
