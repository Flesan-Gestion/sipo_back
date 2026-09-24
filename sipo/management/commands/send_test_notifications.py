from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand

from sipo.services.notifications import (
    send_email_builder_ok,
    send_email_contrato_disponible,
    send_email_error_builder,
    send_email_obra_finalizada,
    send_email_paso_revision,
    send_email_rechazo_documentos,
)


def _demo_obra(sip_id: int = 99999) -> SimpleNamespace:
    return SimpleNamespace(
        cf_rrhh_sip_id=sip_id,
        cf_rrhh_sip_rut='CFM',
        cf_rrhh_sip_razonsocial='Constructora Demo SIPO V2',
        cf_rrhh_sip_uni='UN01',
        cf_rrhh_sip_nombre_uni='Unidad Norte',
        cf_rrhh_sip_cc='CC01',
        cf_rrhh_sip_nombre_cc='Centro Demo',
        cf_rrhh_sip_ubicacion='NORTE',
        cf_rrhh_sip_adm='adm.obra@flesan.cl',
        cf_rrhh_sip_as='as.obra@flesan.cl',
        cf_rrhh_sip_create_user='creator@flesan.cl',
    )


def _demo_candidato() -> SimpleNamespace:
    return SimpleNamespace(
        cf_rrhh_sip_obra_candidato_nombre='Juan',
        cf_rrhh_sip_obra_candidato_segundo_nombre='Carlos',
        cf_rrhh_sip_obra_candidato_ap='Perez',
        cf_rrhh_sip_obra_candidato_am='Gomez',
        cf_rrhh_sip_obra_candidato_rut='12.345.678-9',
        cf_rrhh_sip_obra_candidato_nomcar='OPERADOR',
    )


class Command(BaseCommand):
    help = (
        'Envía los 6 correos activos de SIPO Obra (datos demo) '
        'para revisión visual. Respeta SIP_EMAIL_FORCE_OVERRIDE.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sip-id',
            type=int,
            default=99999,
            help='ID demo en asunto/cuerpo (default 99999)',
        )
        parser.add_argument(
            '--only',
            type=str,
            default='',
            help=(
                'Clave(s) separadas por coma: revision,error_builder,finalizada,'
                'contrato,builder_ok,rechazo_docs'
            ),
        )

    def handle(self, *args, **options):
        obra = _demo_obra(options['sip_id'])
        candidato = _demo_candidato()
        only = {
            p.strip().lower()
            for p in (options['only'] or '').split(',')
            if p.strip()
        }

        catalog = [
            (
                'revision',
                'Paso a revisión / Selección',
                lambda: send_email_paso_revision(obra, [candidato]),
            ),
            (
                'error_builder',
                'Error creación Builder',
                lambda: send_email_error_builder(
                    obra,
                    mensaje_error=(
                        'WORKER_STILL_HIRED para el colaborador '
                        'JUAN CARLOS PEREZ GOMEZ '
                        f'sip N° {obra.cf_rrhh_sip_id}'
                    ),
                ),
            ),
            (
                'finalizada',
                'Obra finalizada',
                lambda: send_email_obra_finalizada(obra, total_contratos=2),
            ),
            (
                'contrato',
                'Contrato disponible',
                lambda: send_email_contrato_disponible(obra, candidato),
            ),
            (
                'builder_ok',
                'Control de asistencia (Builder OK)',
                lambda: send_email_builder_ok(obra, candidato),
            ),
            (
                'rechazo_docs',
                'Rechazo de documentos',
                lambda: send_email_rechazo_documentos(
                    obra,
                    candidato,
                    razones='Cédula ilegible / contrato incompleto (DEMO)',
                ),
            ),
        ]

        override = bool(getattr(settings, 'SIP_EMAIL_FORCE_OVERRIDE', False))
        dest = getattr(settings, 'SIP_EMAIL_TEST_OVERRIDE', '')
        self.stdout.write(
            self.style.NOTICE(
                f'FORCE_OVERRIDE={override} | TEST_OVERRIDE={dest} | '
                f'BACKEND={settings.EMAIL_BACKEND}'
            )
        )

        sent = 0
        for key, label, fn in catalog:
            if only and key not in only:
                continue
            result = fn()
            ok = bool(result.get('sent'))
            status = self.style.SUCCESS('OK') if ok else self.style.ERROR('FAIL')
            detail = result.get('subject') or result.get('reason') or result.get('error') or ''
            self.stdout.write(f'[{status}] {key} — {label}')
            if detail:
                self.stdout.write(f'         {detail}')
            if ok:
                sent += 1

        self.stdout.write(self.style.SUCCESS(f'Enviados: {sent}'))
