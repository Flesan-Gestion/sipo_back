"""Tests de selección de candidatos y aprobación de contratación (Brecha A2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from sipo.constants import SIPO_ROL_ADMIN, SIPO_STATUS_EN_REVISION, SIPO_STATUS_FINALIZADA
from sipo.services.aprobar_contratacion import aprobar_contratacion_obra


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    user.email = 'rrhh@flesan.cl'
    return user


def _obra_mock(*, status: int = SIPO_STATUS_EN_REVISION):
    obra = MagicMock()
    obra.cf_rrhh_sip_id = 100
    obra.cf_rrhh_sip_status = status
    return obra


class AprobarContratacionSeleccionTests(SimpleTestCase):
    @patch('sipo.services.aprobar_contratacion.send_email_contrato_disponible', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion.send_email_obra_finalizada', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion._candidatos_seleccionados_activos', return_value=[])
    @patch('sipo.services.aprobar_contratacion.SipoObra')
    @patch('sipo.services.aprobar_contratacion.transaction')
    @patch('sipo.services.aprobar_contratacion.sync_candidatos_to_sap')
    @patch('sipo.services.aprobar_contratacion.calcular_bonos_mineria_obra', return_value=[])
    @patch('sipo.services.aprobar_contratacion.calcular_sueldos_kiptor_obra', return_value=[])
    @patch('sipo.services.aprobar_contratacion._marcar_contratados_sap', return_value=3)
    @patch('sipo.services.aprobar_contratacion._auto_seleccionar_activos', return_value=3)
    @patch('sipo.services.aprobar_contratacion._count_seleccionados_explicitos', return_value=0)
    @patch('sipo.services.aprobar_contratacion.count_candidatos_activos', return_value=3)
    @patch('sipo.services.aprobar_contratacion.get_obra_for_user')
    def test_aprobacion_masiva_auto_si_ninguno_seleccionado(
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
        mock_get_obra.return_value = _obra_mock()
        mock_sap.return_value = {'sip_id': 100, 'candidatos_procesados': 3, 'resultados': []}

        result = aprobar_contratacion_obra(sip_id=100, user=_admin_user())

        mock_auto_sel.assert_called_once_with(100)
        self.assertEqual(result['modo_seleccion'], 'auto')
        self.assertEqual(result['candidatos_seleccionados'], 3)
        self.assertEqual(result['nuevo_estado'], SIPO_STATUS_FINALIZADA)
        mock_kiptor.assert_called_once_with(sip_id=100)
        mock_sap.assert_called_once()

    @patch('sipo.services.aprobar_contratacion.send_email_contrato_disponible', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion.send_email_obra_finalizada', return_value={'sent': True})
    @patch('sipo.services.aprobar_contratacion._candidatos_seleccionados_activos', return_value=[])
    @patch('sipo.services.aprobar_contratacion.SipoObra')
    @patch('sipo.services.aprobar_contratacion.transaction')
    @patch('sipo.services.aprobar_contratacion.sync_candidatos_to_sap')
    @patch('sipo.services.aprobar_contratacion.calcular_bonos_mineria_obra', return_value=[])
    @patch('sipo.services.aprobar_contratacion.calcular_sueldos_kiptor_obra', return_value=[])
    @patch('sipo.services.aprobar_contratacion._marcar_contratados_sap', return_value=1)
    @patch('sipo.services.aprobar_contratacion._auto_seleccionar_activos', return_value=3)
    @patch('sipo.services.aprobar_contratacion._count_seleccionados_explicitos', return_value=1)
    @patch('sipo.services.aprobar_contratacion.count_candidatos_activos', return_value=3)
    @patch('sipo.services.aprobar_contratacion.get_obra_for_user')
    def test_aprobacion_parcial_solo_seleccionados_explicitos(
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
        mock_get_obra.return_value = _obra_mock()
        mock_sap.return_value = {'sip_id': 100, 'candidatos_procesados': 1, 'resultados': []}

        result = aprobar_contratacion_obra(sip_id=100, user=_admin_user())

        mock_auto_sel.assert_not_called()
        self.assertEqual(result['modo_seleccion'], 'parcial')
        self.assertEqual(result['candidatos_seleccionados'], 1)
        self.assertEqual(result['nuevo_estado'], SIPO_STATUS_FINALIZADA)
        mock_kiptor.assert_called_once_with(sip_id=100)
        mock_sap.assert_called_once()
        mock_marcar.assert_called_once_with(100)
