"""Tests integración API workflow SIPO Obra (mocks HTTP / servicios externos)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from sipo.constants import (
    SIPO_ROL_ADMIN,
    SIPO_STATUS_EN_ESPERA,
    SIPO_STATUS_EN_REVISION,
    SIPO_STATUS_FINALIZADA,
)
from sipo.services.aprobar_contratacion import aprobar_contratacion_obra
from sipo.services.estados import cambiar_estado_obra
from sipo.services.kiptor import KiptorService, calcular_sueldos_kiptor_obra
from sipo.services.sap_sync.client import clear_sap_auth_cache, upsert_entity
from sipo.views import SipoValidarCorreoView, SipoValidarRutView


def _response_payload(response):
    return json.loads(response.content.decode('utf-8'))['data']


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    user.email = 'rrhh@flesan.cl'
    return user


def _obra_mock(*, status: int = SIPO_STATUS_EN_ESPERA):
    obra = MagicMock()
    obra.cf_rrhh_sip_id = 100
    obra.cf_rrhh_sip_status = status
    obra.cf_rrhh_sip_adm = 'adm@flesan.cl'
    obra.cf_rrhh_sip_as = 'as@flesan.cl'
    return obra


class Transicion6a7Tests(SimpleTestCase):
    @patch('sipo.services.estados.send_email_paso_revision')
    @patch('sipo.services.estados.list_candidatos_activos_obra', return_value=[])
    @patch('sipo.services.estados.sync_trabajadores_ibuilder_obra')
    @patch('sipo.services.estados.registrar_historial_estado')
    @patch('sipo.services.estados.SipoObra')
    @patch('sipo.services.estados.count_candidatos_activos', return_value=2)
    @patch('sipo.services.estados.get_obra_for_user')
    def test_dispara_ibuilder_y_notificacion(
        self,
        mock_get_obra,
        mock_count,
        mock_sipo_obra,
        mock_historial,
        mock_builder,
        mock_list_cand,
        mock_email,
    ):
        obra = _obra_mock(status=SIPO_STATUS_EN_ESPERA)
        mock_get_obra.return_value = obra
        mock_builder.return_value = {
            'sip_id': 100,
            'procesados': 2,
            'ok': 2,
            'errores': [],
        }

        user = _admin_user()
        result = cambiar_estado_obra(
            sip_id=100,
            nuevo_estado=SIPO_STATUS_EN_REVISION,
            user=user,
        )

        mock_builder.assert_called_once_with(sip_id=100, obra=obra, solo_activos=True)
        mock_email.assert_called_once()
        mock_sipo_obra.objects.using.return_value.filter.return_value.update.assert_called_once()
        self.assertEqual(result, obra)


class AprobarContratacion7a10Tests(SimpleTestCase):
    @patch('sipo.services.aprobar_contratacion.send_email_contrato_disponible', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion.send_email_obra_finalizada', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion._candidatos_seleccionados_activos', return_value=[])
    @patch('sipo.services.aprobar_contratacion.SipoObra')
    @patch('sipo.services.aprobar_contratacion.transaction')
    @patch('sipo.services.aprobar_contratacion.sync_candidatos_to_sap')
    @patch('sipo.services.aprobar_contratacion.calcular_bonos_mineria_obra', return_value=[])
    @patch('sipo.services.aprobar_contratacion.calcular_sueldos_kiptor_obra')
    @patch('sipo.services.aprobar_contratacion._marcar_contratados_sap', return_value=1)
    @patch('sipo.services.aprobar_contratacion._auto_seleccionar_activos', return_value=1)
    @patch('sipo.services.aprobar_contratacion._count_seleccionados_explicitos', return_value=0)
    @patch('sipo.services.aprobar_contratacion.count_candidatos_activos', return_value=1)
    @patch('sipo.services.aprobar_contratacion.get_obra_for_user')
    def test_invoca_kiptor_sap_y_finaliza(
        self,
        mock_get_obra,
        mock_count,
        mock_count_sel,
        mock_auto_sel,
        mock_marcar,
        mock_kiptor,
        mock_bono,
        mock_sap,
        mock_transaction,
        mock_sipo_obra,
        mock_cand_sel,
        mock_email_fin,
        mock_email_contrato,
    ):
        obra = _obra_mock(status=SIPO_STATUS_EN_REVISION)
        mock_get_obra.return_value = obra
        mock_kiptor.return_value = [{'candidato_id': '1', 'kiptor_ok': True}]
        mock_sap.return_value = {
            'sip_id': 100,
            'candidatos_procesados': 1,
            'resultados': [
                {
                    'candidato_id': '1',
                    'entities': [{'entity': 'CompInfo-M020', 'status': 'OK'}],
                }
            ],
        }

        user = _admin_user()
        result = aprobar_contratacion_obra(sip_id=100, user=user)

        mock_auto_sel.assert_called_once_with(100)
        mock_kiptor.assert_called_once_with(sip_id=100)
        mock_sap.assert_called_once_with(sip_id=100, obra=obra)
        mock_bono.assert_called_once()
        mock_sipo_obra.objects.using.return_value.filter.return_value.update.assert_called_once()
        self.assertEqual(result['nuevo_estado'], SIPO_STATUS_FINALIZADA)
        self.assertEqual(result['modo_seleccion'], 'auto')
        self.assertIn('sap_sync', result)
        mock_email_fin.assert_called()


class SapOrchestratorLogTests(SimpleTestCase):
    _FAKE_BUILDERS = [
        (
            'CompInfo',
            lambda ctx: [{'payComponent': 'M020', 'amount': 850000}],
        ),
    ]

    @override_settings(
        SAP_SF_SYNC_ENABLED=True,
        SAP_SF_BASIC_USER='user',
        SAP_SF_BASIC_PASSWORD='pass',
        SAP_SF_UPSERT_URL='https://sap.test/upsert',
    )
    @patch('sipo.services.sap_sync.orchestrator.SAP_ENTITY_BUILDERS', _FAKE_BUILDERS)
    @patch('sipo.services.sap_sync.orchestrator.write_sap_log')
    @patch('sipo.services.sap_sync.orchestrator.upsert_entity')
    @patch('sipo.services.sap_sync.orchestrator._build_context')
    @patch('sipo.services.sap_sync.orchestrator.SipoCandidatoObra')
    def test_sync_genera_logs_m020(
        self,
        mock_candidato_model,
        mock_build_ctx,
        mock_upsert,
        mock_write_log,
    ):
        from sipo.services.sap_sync.orchestrator import sync_candidatos_to_sap

        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_candidato_id = 'c1'
        candidato.cf_rrhh_sip_obra_user_id = '200001'
        mock_candidato_model.objects.using.return_value.filter.return_value = [candidato]

        ctx = MagicMock()
        mock_build_ctx.return_value = ctx

        def fake_upsert(*, entity_type, payload):
            return {'status': 'OK', 'message': f'upsert {entity_type}', 'dry_run': False}

        mock_upsert.side_effect = fake_upsert

        obra = _obra_mock()
        result = sync_candidatos_to_sap(sip_id=100, obra=obra)

        self.assertEqual(result['candidatos_procesados'], 1)
        log_types = [call.kwargs['log_type'] for call in mock_write_log.call_args_list]
        self.assertTrue(any('M020' in lt for lt in log_types))


class ValidarCorreoRutApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _admin_user()

    @patch('sipo.views.validar_correo_smtp', return_value=True)
    def test_validar_correo_ok(self, mock_validar):
        request = self.factory.get('/api/sipo/candidatos/validar-correo/', {'email': 'test@flesan.cl'})
        force_authenticate(request, user=self.user)
        response = SipoValidarCorreoView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        mock_validar.assert_called_once_with('test@flesan.cl')
        self.assertTrue(_response_payload(response)['valido'])

    @patch('sipo.services.rut_validation.validar_rut_activo')
    @patch('sipo.services.candidato_validaciones.is_valid_rut', return_value=True)
    def test_validar_rut_ok(self, mock_is_valid, mock_activo):
        mock_activo.return_value = {
            'activo': False,
            'motivo': '',
            'bypass': False,
            'fuente': 'ibuilder',
            'builder_proyecto_id': '99',
        }
        request = self.factory.get(
            '/api/sipo/candidatos/validar-rut/',
            {'rut': '12.345.678-5', 'sip_id': '100'},
        )
        force_authenticate(request, user=self.user)
        with patch('sipo.views.get_obra_for_user'):
            response = SipoValidarRutView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        payload = _response_payload(response)
        self.assertTrue(payload['valido'])
        self.assertFalse(payload['activo_ibuilder_sap'])


class TokenCacheTests(SimpleTestCase):
    def setUp(self):
        clear_sap_auth_cache()

    def tearDown(self):
        clear_sap_auth_cache()

    @override_settings(
        KIPTOR_ENABLED=True,
        KIPTOR_USER='u',
        KIPTOR_PASSWORD='p',
    )
    @patch('sipo.services.kiptor.requests')
    def test_kiptor_reusa_token_en_batch(self, mock_requests):
        auth_resp = MagicMock()
        auth_resp.raise_for_status.return_value = None
        auth_resp.json.return_value = {'token': 'tok-batch'}
        mock_requests.post.return_value = auth_resp

        service = KiptorService()
        service.ensure_token()
        service.ensure_token()

        self.assertEqual(mock_requests.post.call_count, 1)

    @override_settings(
        SAP_SF_SYNC_ENABLED=True,
        SAP_SF_BASIC_USER='',
        SAP_SF_BASIC_PASSWORD='',
        SAP_SF_CLIENT_ID='cid',
        SAP_SF_CLIENT_SECRET='sec',
        SAP_SF_OAUTH_URL='https://sap.test/oauth',
        SAP_SF_UPSERT_URL='https://sap.test/upsert',
    )
    @patch('sipo.services.sap_sync.client.requests')
    def test_sap_reusa_oauth_en_batch(self, mock_requests):
        clear_sap_auth_cache()
        oauth_resp = MagicMock()
        oauth_resp.raise_for_status.return_value = None
        oauth_resp.json.return_value = {'access_token': 'oauth-tok'}
        upsert_resp = MagicMock()
        upsert_resp.text = '{"d":[{"status":"OK"}]}'
        upsert_resp.json.return_value = {'d': [{'status': 'OK', 'message': 'ok'}]}
        mock_requests.post.side_effect = [oauth_resp, upsert_resp, upsert_resp]

        upsert_entity(entity_type='CompInfo-M020', payload={'x': 1})
        upsert_entity(entity_type='CompInfo-M020', payload={'x': 2})

        self.assertEqual(mock_requests.post.call_count, 3)
        self.assertEqual(mock_requests.post.call_args_list[0][0][0], 'https://sap.test/oauth')

    @patch('sipo.services.kiptor.KiptorService.calcular_y_persistir_sueldo_base')
    @patch('sipo.services.kiptor.KiptorService._get_uf_utm_cached', return_value=(39000.0, 68000))
    @patch('sipo.services.kiptor.KiptorService.ensure_token')
    @patch('sipo.services.kiptor.SipoObra')
    @patch('sipo.services.kiptor.SipoCandidatoObra')
    def test_calcular_sueldos_kiptor_obra_preauth(
        self,
        mock_model,
        mock_obra_model,
        mock_ensure,
        mock_uf,
        mock_calc,
    ):
        c1, c2 = MagicMock(), MagicMock()
        mock_model.objects.using.return_value.filter.return_value = [c1, c2]
        obra = MagicMock()
        obra.cf_rrhh_sip_cc = 'OTROCC'
        mock_obra_model.objects.using.return_value.filter.return_value.first.return_value = obra
        mock_calc.side_effect = [{'kiptor_ok': True}, {'kiptor_ok': True}]

        with override_settings(KIPTOR_ENABLED=True):
            calcular_sueldos_kiptor_obra(sip_id=100)

        mock_ensure.assert_called_once()
        self.assertEqual(mock_calc.call_count, 2)
        mock_calc.assert_any_call(c1, centro_costo='OTROCC')
