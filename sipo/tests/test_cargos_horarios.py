"""Tests configuración cargos y horarios por empresa."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from sipo.constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH
from sipo.views_cargos_horarios import SipoConfigCargosView, SipoConfigEmpresasView, SipoConfigHorariosView


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    return user


def _rrhh_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_RRHH
    return user


def _payload(response):
    return json.loads(response.content.decode('utf-8'))['data']


class SipoConfigAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('sipo.views_cargos_horarios.list_empresas_config', return_value=[])
    def test_empresas_solo_admin(self, _mock):
        request = self.factory.get('/api/sipo/config/empresas/')
        force_authenticate(request, user=_rrhh_user())
        response = SipoConfigEmpresasView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('sipo.views_cargos_horarios.list_empresas_config')
    def test_empresas_admin_ok(self, mock_list):
        mock_list.return_value = [{'id': 'CFM', 'razon_social': 'FLESAN MINERIA', 'cargos_asignados': 1}]
        request = self.factory.get('/api/sipo/config/empresas/')
        force_authenticate(request, user=_admin_user())
        response = SipoConfigEmpresasView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_payload(response)), 1)


class SipoConfigCargosHorariosViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('sipo.views_cargos_horarios.list_cargos_catalogo_sap', return_value=[])
    @patch('sipo.views_cargos_horarios.list_cargos_empresa', return_value=[])
    def test_get_cargos_empresa(self, mock_cargos, _mock_cat):
        request = self.factory.get('/api/sipo/config/cargos/', {'empresa_id': 'CFM'})
        force_authenticate(request, user=_admin_user())
        response = SipoConfigCargosView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_cargos.assert_called_once_with('CFM')

    @patch('sipo.views_cargos_horarios.assign_cargo_empresa')
    def test_post_cargo(self, mock_assign):
        mock_assign.return_value = {'id': 1, 'nombre': 'MAESTRO', 'activo': True}
        request = self.factory.post(
            '/api/sipo/config/cargos/',
            {'empresa_id': 'CFM', 'external_code': '10001'},
            format='json',
        )
        force_authenticate(request, user=_admin_user())
        response = SipoConfigCargosView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('sipo.views_cargos_horarios.list_horarios_catalogo_sap', return_value=[])
    @patch('sipo.views_cargos_horarios.list_horarios_empresa', return_value=[])
    def test_get_horarios_empresa(self, mock_horarios, _mock_cat):
        request = self.factory.get('/api/sipo/config/horarios/', {'empresa_id': 'CFM'})
        force_authenticate(request, user=_admin_user())
        response = SipoConfigHorariosView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_horarios.assert_called_once_with('CFM')
