"""Tests de notificaciones SIPO Obra (correos vivos + override)."""

from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings

from sipo.services.notifications import (
    EVENTO_REVISION,
    collect_integration_errors,
    enviar_notificacion_email,
    send_email_builder_ok,
    send_email_contrato_disponible,
    send_email_error_builder,
    send_email_obra_finalizada,
    send_email_paso_revision,
    send_email_rechazo_documentos,
)


def _obra(**kwargs):
    obra = MagicMock()
    obra.cf_rrhh_sip_id = kwargs.get('sip_id', 1001)
    obra.cf_rrhh_sip_rut = 'CFM'
    obra.cf_rrhh_sip_razonsocial = kwargs.get('empresa', 'Constructora Demo')
    obra.cf_rrhh_sip_uni = 'UN01'
    obra.cf_rrhh_sip_nombre_uni = 'Unidad Norte'
    obra.cf_rrhh_sip_cc = 'CC01'
    obra.cf_rrhh_sip_nombre_cc = 'Centro Demo'
    obra.cf_rrhh_sip_ubicacion = 'NORTE'
    obra.cf_rrhh_sip_adm = kwargs.get('adm', 'adm@flesan.cl')
    obra.cf_rrhh_sip_as = kwargs.get('asistente', 'as@flesan.cl')
    obra.cf_rrhh_sip_create_user = 'creator@flesan.cl'
    return obra


def _candidato(**kwargs):
    c = MagicMock()
    c.cf_rrhh_sip_obra_candidato_nombre = kwargs.get('nombre', 'Juan')
    c.cf_rrhh_sip_obra_candidato_segundo_nombre = kwargs.get('segundo', '')
    c.cf_rrhh_sip_obra_candidato_ap = kwargs.get('ap', 'Perez')
    c.cf_rrhh_sip_obra_candidato_am = kwargs.get('am', 'Gomez')
    c.cf_rrhh_sip_obra_candidato_rut = '12.345.678-9'
    c.cf_rrhh_sip_obra_candidato_nomcar = 'OPERADOR'
    return c


@override_settings(
    SIP_EMAIL_ENABLED=True,
    SIP_EMAIL_FORCE_OVERRIDE=False,
    SIP_EMAIL_FROM='equipo_desarrollo@flesan.cl',
    SIP_EMAIL_FROM_NAME='Sip Obra',
    SIP_EMAIL_TEST_OVERRIDE='martin.norambuena@flesan.cl',
    SIP_EMAIL_ERROR_BUILDER='jorge.barrozo@flesan.cl,alejandro.jara@flesan.cl',
    SIP_EMAIL_RECHAZO_DOCS_BCC='jorge.barrozo@flesan.cl,sofia.figueroa@flesan.cl',
    SIP_EMAIL_IMG_BASE='https://www.flesanmvi.com/controlflujo/system/view/sip/img',
    SIPO_PORTAL_BASE_URL='http://localhost:5173/panel/sipo',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class NotificationsOutboxTests(SimpleTestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_paso_revision_to_adm(self):
        obra = _obra()
        result = send_email_paso_revision(obra, [_candidato()])
        self.assertTrue(result['sent'])
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['adm@flesan.cl'])
        self.assertIn('Notificación de Selección', msg.subject)
        self.assertIn('Administrador de Obra', msg.alternatives[0][0])

    def test_error_builder_lista_fija(self):
        obra = _obra()
        result = send_email_error_builder(
            obra,
            mensaje_error='WORKER_STILL_HIRED para el colaborador JUAN sip N° 1001',
        )
        self.assertTrue(result['sent'])
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(
            sorted(msg.to),
            ['alejandro.jara@flesan.cl', 'jorge.barrozo@flesan.cl'],
        )
        self.assertIn('NO creados en Builder', msg.subject)
        self.assertEqual(msg.from_email, 'Creacion trabajadores Builder <equipo_desarrollo@flesan.cl>')

    def test_obra_finalizada_adm_as(self):
        result = send_email_obra_finalizada(_obra(), total_contratos=3)
        self.assertTrue(result['sent'])
        msg = mail.outbox[0]
        self.assertEqual(sorted(msg.to), ['adm@flesan.cl', 'as@flesan.cl'])
        self.assertIn('a finalizado', msg.alternatives[0][0])

    def test_contrato_disponible(self):
        result = send_email_contrato_disponible(_obra(), _candidato())
        self.assertTrue(result['sent'])
        msg = mail.outbox[0]
        self.assertIn('Notificación de Contrato', msg.subject)
        self.assertIn('JUAN PEREZ GOMEZ', msg.alternatives[0][0])

    def test_builder_ok(self):
        result = send_email_builder_ok(_obra(), _candidato(nombre='Ana', ap='Lopez', am=''))
        self.assertTrue(result['sent'])
        msg = mail.outbox[0]
        self.assertIn('Control de Asistencia', msg.subject)
        self.assertIn('ANA LOPEZ', msg.alternatives[0][0])

    def test_rechazo_documentos_con_bcc(self):
        result = send_email_rechazo_documentos(
            _obra(),
            _candidato(),
            razones='CI ilegible',
        )
        self.assertTrue(result['sent'])
        msg = mail.outbox[0]
        self.assertEqual(sorted(msg.to), ['adm@flesan.cl', 'as@flesan.cl'])
        self.assertEqual(
            sorted(msg.bcc),
            ['jorge.barrozo@flesan.cl', 'sofia.figueroa@flesan.cl'],
        )
        self.assertIn('CI ilegible', msg.alternatives[0][0])

    def test_compat_enviar_notificacion_revision(self):
        result = enviar_notificacion_email(EVENTO_REVISION, _obra(), [_candidato()])
        self.assertTrue(result['sent'])
        self.assertEqual(mail.outbox[0].to, ['adm@flesan.cl'])


@override_settings(
    SIP_EMAIL_ENABLED=True,
    SIP_EMAIL_FORCE_OVERRIDE=True,
    SIP_EMAIL_TEST_OVERRIDE='martin.norambuena@flesan.cl',
    SIP_EMAIL_FROM='equipo_desarrollo@flesan.cl',
    SIP_EMAIL_FROM_NAME='Sip Obra',
    SIP_EMAIL_ERROR_BUILDER='jorge.barrozo@flesan.cl',
    SIP_EMAIL_RECHAZO_DOCS_BCC='sofia.figueroa@flesan.cl',
    SIP_EMAIL_IMG_BASE='https://example.com/img',
    SIPO_PORTAL_BASE_URL='http://localhost:5173/panel/sipo',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class NotificationsOverrideTests(SimpleTestCase):
    def setUp(self):
        mail.outbox.clear()

    def test_override_redirige_y_anota_era(self):
        result = send_email_paso_revision(_obra(), [_candidato()])
        self.assertTrue(result['sent'])
        self.assertEqual(result['recipients'], ['martin.norambuena@flesan.cl'])
        self.assertEqual(result['intended_recipients'], ['adm@flesan.cl'])
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['martin.norambuena@flesan.cl'])
        self.assertIn('TEST -> martin.norambuena@flesan.cl', msg.subject)
        self.assertIn('era: TO: adm@flesan.cl', msg.subject)

    def test_override_incluye_cco_en_asunto(self):
        send_email_rechazo_documentos(_obra(), _candidato(), razones='Falta')
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['martin.norambuena@flesan.cl'])
        self.assertEqual(msg.bcc, [])
        self.assertIn('CCO: sofia.figueroa@flesan.cl', msg.subject)
        self.assertIn('TO: adm@flesan.cl', msg.subject)

    def test_override_flag_si(self):
        with override_settings(SIP_EMAIL_FORCE_OVERRIDE=True):
            send_email_obra_finalizada(_obra(), total_contratos=1)
        self.assertEqual(mail.outbox[0].to, ['martin.norambuena@flesan.cl'])


class CollectErrorsTests(SimpleTestCase):
    def test_collect_builder_errors(self):
        errores = collect_integration_errors(
            builder_result={
                'skipped': False,
                'resultados': [
                    {
                        'candidato_id': 'abc',
                        'builder_ok': False,
                        'error': 'WORKER_STILL_HIRED para el colaborador JUAN sip N° 100',
                    },
                ],
            },
        )
        self.assertEqual(len(errores), 1)
        self.assertIn('WORKER_STILL_HIRED', errores[0])


@override_settings(
    SIP_EMAIL_ENABLED=True,
    SIP_EMAIL_FORCE_OVERRIDE=False,
    SIP_EMAIL_FROM='equipo_desarrollo@flesan.cl',
    SIP_EMAIL_FROM_NAME='Sip Obra',
    SIPO_PUBLIC_ORIGIN='http://localhost:5173',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class InvitacionColaboradorTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.user = MagicMock()
        self.user.is_authenticated = True
        self.user.sip_rol_id = 4
        self.user.email = 'supervisor@flesan.cl'
        self.user.id = 40
        self.user.pk = 40

    def test_guardar_supervisor_incluye_link_y_qr(self):
        from sipo.models_ficha import SipoFichaIngreso
        from sipo.services.fichas import create_ficha

        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            with patch('sipo.services.fichas.resolve_ficha_catalog_fields', return_value={}):
                ficha = create_ficha(
                    data={
                        'solo_supervisor': '1',
                        'cargo': 'Maestro',
                        'fecha_ingreso': '2026-10-01',
                        'correo_colaborador': 'colaborador@flesan.cl',
                        'sueldo_liquido': '650000',
                        'tipo_contrato': 'Indefinido',
                        'horario': 'L-V 08-17',
                    },
                    files={},
                    user=self.user,
                )
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['colaborador@flesan.cl'])
        html = msg.alternatives[0][0]
        self.assertIn('/portal-candidato/', html)
        self.assertIn('cid:qr_colaborador', html)
        self.assertIn('data:image/png;base64,', html)
        self.assertTrue(msg.attachments)
