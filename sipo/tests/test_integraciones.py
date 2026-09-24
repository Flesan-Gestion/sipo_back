"""Tests de sincronización manual SAP (Brecha M1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import APIException

from sipo.constants import SIPO_ROL_ADMIN, SIPO_STATUS_FINALIZADA
from sipo.services.sap_sync.orchestrator import sync_sipo_candidatos_sap


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    user.email = 'rrhh@flesan.cl'
    return user


def _obra_mock(*, status: int = SIPO_STATUS_FINALIZADA):
    obra = MagicMock()
    obra.cf_rrhh_sip_id = 100
    obra.cf_rrhh_sip_status = status
    return obra


class SyncSapManualTests(SimpleTestCase):
    @patch('sipo.services.estados.registrar_historial_estado')
    @patch('sipo.services.sap_sync.orchestrator._marcar_contratados_sap', return_value=1)
    @patch('sipo.services.sap_sync.orchestrator.sync_candidatos_to_sap')
    @patch('sipo.services.sap_sync.orchestrator.get_obra_for_user')
    def test_sync_sap_exitoso_registra_historial(
        self,
        mock_get_obra,
        mock_sync,
        mock_marcar,
        mock_historial,
    ):
        mock_get_obra.return_value = _obra_mock()
        mock_sync.return_value = {
            'sip_id': 100,
            'candidatos_procesados': 1,
            'skipped': False,
            'resultados': [
                {
                    'candidato_id': 'c1',
                    'user_id': 'u1',
                    'entities': [{'entity': 'CompInfo', 'status': 'OK', 'message': 'ok'}],
                }
            ],
        }

        result = sync_sipo_candidatos_sap(sip_id=100, user=_admin_user())

        self.assertEqual(result['message'], 'Sincronización con SAP ejecutada correctamente')
        self.assertEqual(result['candidatos_procesados'], 1)
        mock_marcar.assert_called_once_with(100)
        mock_historial.assert_called_once()
        mock_sync.assert_called_once()

    @patch('sipo.services.estados.registrar_historial_estado')
    @patch('sipo.services.sap_sync.orchestrator._marcar_contratados_sap', return_value=1)
    @patch('sipo.services.sap_sync.orchestrator.get_obra_for_user')
    def test_sync_sap_falla_con_400_descriptivo(
        self,
        mock_get_obra,
        mock_marcar,
        mock_historial,
    ):
        mock_get_obra.return_value = _obra_mock()

        with patch(
            'sipo.services.sap_sync.orchestrator.sync_candidatos_to_sap',
            return_value={
                'sip_id': 100,
                'candidatos_procesados': 1,
                'skipped': False,
                'resultados': [
                    {
                        'candidato_id': 'c1',
                        'user_id': 'u1',
                        'entities': [
                            {
                                'entity': 'CompInfo',
                                'status': 'ERROR',
                                'message': 'Timeout SAP SF',
                                'dry_run': False,
                            }
                        ],
                    }
                ],
            },
        ):
            with self.assertRaises(APIException) as ctx:
                sync_sipo_candidatos_sap(sip_id=100, user=_admin_user())

        self.assertIn('Timeout SAP SF', str(ctx.exception.detail))
        mock_marcar.assert_called_once_with(100)
        mock_historial.assert_called_once()

    @patch('sipo.services.sap_sync.orchestrator.get_obra_for_user')
    def test_sync_sap_error_conexion_degrada_a_400(self, mock_get_obra):
        mock_get_obra.return_value = _obra_mock()

        with patch(
            'sipo.services.sap_sync.orchestrator.sync_candidatos_to_sap',
            side_effect=ConnectionError('network down'),
        ):
            with self.assertRaises(APIException) as ctx:
                sync_sipo_candidatos_sap(sip_id=100, user=_admin_user())

        self.assertIn('Error de conexión con SAP', str(ctx.exception.detail))
