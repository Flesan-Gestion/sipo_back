"""Tests de persistencia de comentarios en cambio de estado."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from sipo.constants import (
    SIPO_ROL_ADMIN,
    SIPO_STATUS_EN_ESPERA,
    SIPO_STATUS_EN_REVISION,
)
from sipo.services.estados import cambiar_estado_obra, registrar_historial_estado


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


class RegistrarHistorialEstadoTests(SimpleTestCase):
    @patch('sipo.services.estados.SipoSolicitudHistorial')
    def test_persiste_comentario(self, mock_historial):
        user = _admin_user()
        mock_historial.objects.create.return_value = MagicMock(id=1)

        registrar_historial_estado(
            sip_id=100,
            estado_anterior=SIPO_STATUS_EN_ESPERA,
            estado_nuevo=SIPO_STATUS_EN_REVISION,
            user=user,
            comentario='  Motivo de revisión  ',
        )

        mock_historial.objects.create.assert_called_once_with(
            solicitud=100,
            estado_anterior=SIPO_STATUS_EN_ESPERA,
            estado_nuevo=SIPO_STATUS_EN_REVISION,
            usuario='rrhh@flesan.cl',
            comentario='Motivo de revisión',
        )


class CambiarEstadoPersisteComentarioTests(SimpleTestCase):
    @patch('sipo.services.estados.send_email_paso_revision')
    @patch('sipo.services.estados.list_candidatos_activos_obra', return_value=[])
    @patch('sipo.services.estados.sync_trabajadores_ibuilder_obra')
    @patch('sipo.services.estados.registrar_historial_estado')
    @patch('sipo.services.estados.SipoObra')
    @patch('sipo.services.estados.count_candidatos_activos', return_value=2)
    @patch('sipo.services.estados.get_obra_for_user')
    def test_cambiar_estado_registra_historial_con_comentario(
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

        cambiar_estado_obra(
            sip_id=100,
            nuevo_estado=SIPO_STATUS_EN_REVISION,
            user=user,
            comentario='Enviado a revisión por RRHH',
        )

        mock_historial.assert_called_once_with(
            sip_id=100,
            estado_anterior=SIPO_STATUS_EN_ESPERA,
            estado_nuevo=SIPO_STATUS_EN_REVISION,
            user=user,
            comentario='Enviado a revisión por RRHH',
        )
