import base64
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from sipo.models_portal import SipoCandidatoAcceso
from sipo.services.candidato_portal import (
    _acceso_por_token,
    emitir_acceso,
    guardar_publico,
    qr_svg_base64,
)


class QrYTokenTests(TestCase):
    def test_qr_base64_svg(self):
        value = qr_svg_base64('http://localhost:5173/portal-candidato/abc')
        self.assertTrue(value.startswith('data:image/svg+xml;base64,'))
        raw = base64.b64decode(value.split(',', 1)[1])
        self.assertIn(b'<svg', raw)

    @patch('sipo.services.candidato_portal.SipoObra.objects')
    @patch('sipo.services.candidato_portal._candidato')
    def test_tokens_unicos_y_reutiliza_vigente(self, mock_cand, mock_obra):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_candidato_nomcar = 'Maestro'
        mock_cand.return_value = candidato
        mock_obra.using.return_value.filter.return_value.first.return_value = None

        a = emitir_acceso(sip_id=10, candidato_id='cand-1', front_origin='http://localhost:5173')
        b = emitir_acceso(sip_id=10, candidato_id='cand-1', front_origin='http://localhost:5173')
        self.assertEqual(a['token'], b['token'])
        self.assertEqual(SipoCandidatoAcceso.objects.count(), 1)
        self.assertIn('/portal-candidato/', a['url'])

    def test_bloquea_expirado_y_completado(self):
        acceso = SipoCandidatoAcceso.objects.create(
            candidato_id='cand-2',
            sip_id=10,
            token=uuid.uuid4(),
            expira_at=timezone.now() - timedelta(hours=1),
            estado=SipoCandidatoAcceso.PENDIENTE,
        )
        with self.assertRaises(PermissionDenied):
            _acceso_por_token(str(acceso.token))

        acceso.expira_at = timezone.now() + timedelta(days=1)
        acceso.estado = SipoCandidatoAcceso.COMPLETADO
        acceso.save()
        with self.assertRaises(PermissionDenied):
            _acceso_por_token(str(acceso.token))

    @patch('sipo.services.candidato_portal._candidato')
    def test_guardar_publico_marca_completado(self, mock_cand):
        acceso = SipoCandidatoAcceso.objects.create(
            candidato_id='cand-3',
            sip_id=11,
            token=uuid.uuid4(),
            expira_at=timezone.now() + timedelta(days=2),
            estado=SipoCandidatoAcceso.PENDIENTE,
        )
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_candidato_rut = ''
        candidato.cf_rrhh_sip_obra_candidato_nombre = ''
        candidato.cf_rrhh_sip_obra_candidato_ap = ''
        candidato.cf_rrhh_sip_obra_candidato_am = ''
        mock_cand.return_value = candidato

        result = guardar_publico(
            token=str(acceso.token),
            data={
                'enviar': 'true',
                'cf_rrhh_sip_obra_candidato_nombre': 'Ana',
                'cf_rrhh_sip_obra_candidato_ap': 'Perez',
                'cf_rrhh_sip_obra_candidato_am': 'Soto',
                'cf_rrhh_sip_obra_candidato_rut': '11.111.111-1',
            },
            files={},
        )
        self.assertEqual(result['estado'], SipoCandidatoAcceso.COMPLETADO)
        candidato.save.assert_called()
        acceso.refresh_from_db()
        self.assertEqual(acceso.estado, SipoCandidatoAcceso.COMPLETADO)
        with self.assertRaises(PermissionDenied):
            _acceso_por_token(str(acceso.token))
