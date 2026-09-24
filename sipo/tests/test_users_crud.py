"""Tests integración CRUD usuarios SIP Obra (paridad legado)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from sipo.constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH
from sipo.services.usuarios import create_sipo_usuario, delete_sipo_usuario, update_sipo_usuario
from sipo.views_users import SipoUsuarioDetailView, SipoUsuariosListCreateView


def _response_payload(response):
    return json.loads(response.content.decode('utf-8'))['data']


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    user.email = 'admin@flesan.cl'
    return user


def _rrhh_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_RRHH
    user.email = 'rrhh@flesan.cl'
    return user


class SipoUsuariosAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_list_usuarios_solo_admin(self):
        request = self.factory.get('/api/sipo/usuarios/')
        force_authenticate(request, user=_rrhh_user())
        response = SipoUsuariosListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('sipo.views_users.list_sipo_usuarios', return_value=[])
    def test_list_usuarios_admin_ok(self, _mock_list):
        request = self.factory.get('/api/sipo/usuarios/')
        force_authenticate(request, user=_admin_user())
        response = SipoUsuariosListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(_response_payload(response), [])


class SipoUsuariosCrudServiceTests(SimpleTestCase):
    @patch('sipo.services.usuarios.set_assignments_for_perfil')
    @patch('sipo.services.usuarios.get_sipo_usuario_by_id')
    @patch('sipo.services.usuarios.connections')
    @patch('sipo.services.usuarios._perfil_exists', return_value=False)
    @patch('sipo.services.usuarios.SipoRol')
    @patch('sipo.services.usuarios._next_perfil_id', return_value=101)
    def test_create_usuario_success(
        self, _mock_next_id, mock_rol, _mock_exists, _mock_conn, mock_get, mock_scope
    ):
        mock_rol.objects.using.return_value.filter.return_value.exists.return_value = True
        mock_get.return_value = {
            'id': 101,
            'correo': 'juan.perez@flesan.cl',
            'rol_id': 2,
            'rol': 'RRHH',
            'empresas_ids': ['76123456-7'],
            'centros_costo_ids': ['CC001'],
            'empresas': [{'id': '76123456-7', 'nombre': 'Empresa Demo'}],
            'centros_costo': [{'id': 'CC001', 'nombre': 'Centro 1'}],
        }

        created = create_sipo_usuario(
            correo='juan.perez@flesan.cl',
            rol_id=2,
            empresas_ids=['76123456-7'],
            centros_costo_ids=['CC001'],
        )
        self.assertEqual(created['correo'], 'juan.perez@flesan.cl')
        self.assertEqual(created['rol_id'], 2)
        mock_scope.assert_called_once()

    @patch('sipo.services.usuarios.set_assignments_for_perfil')
    @patch('sipo.services.usuarios.get_sipo_usuario_by_id')
    @patch('sipo.services.usuarios.connections')
    @patch('sipo.services.usuarios._perfil_exists', return_value=False)
    @patch('sipo.services.usuarios.SipoRol')
    def test_update_usuario_rol(self, mock_rol, _mock_exists, _mock_conn, mock_get, _mock_scope):
        mock_rol.objects.using.return_value.filter.return_value.exists.return_value = True
        mock_get.side_effect = [
            {
                'id': 10,
                'correo': 'ana@flesan.cl',
                'rol_id': 2,
                'rol': 'RRHH',
                'empresas_ids': ['76123456-7'],
                'centros_costo_ids': ['CC001'],
                'empresas': [],
                'centros_costo': [],
            },
            {
                'id': 10,
                'correo': 'ana@flesan.cl',
                'rol_id': 1,
                'rol': 'Administrador',
                'empresas_ids': ['76123456-7'],
                'centros_costo_ids': ['CC001'],
                'empresas': [],
                'centros_costo': [],
            },
        ]

        updated = update_sipo_usuario(10, rol_id=1)
        self.assertEqual(updated['rol_id'], 1)

    @patch('sipo.services.usuarios.SipoRol')
    @patch('sipo.services.usuarios._perfil_exists', return_value=True)
    def test_create_usuario_email_duplicado(self, _mock_exists, mock_rol):
        mock_rol.objects.using.return_value.filter.return_value.exists.return_value = True
        with self.assertRaises(ValidationError) as ctx:
            create_sipo_usuario(
                correo='dup@flesan.cl',
                rol_id=2,
                empresas_ids=['76123456-7'],
                centros_costo_ids=['CC001'],
            )
        self.assertIn('correo', ctx.exception.detail)

    @patch('sipo.views_users.create_sipo_usuario')
    def test_post_usuario_admin(self, mock_create):
        mock_create.return_value = {
            'id': 5,
            'correo': 'maria@flesan.cl',
            'rol_id': 2,
            'rol': 'RRHH',
            'empresas_ids': ['76123456-7'],
            'centros_costo_ids': ['CC001'],
            'empresas': [{'id': '76123456-7', 'nombre': 'Empresa Demo'}],
            'centros_costo': [{'id': 'CC001', 'nombre': 'Centro 1'}],
        }
        factory = APIRequestFactory()
        request = factory.post(
            '/api/sipo/usuarios/',
            {
                'correo': 'maria@flesan.cl',
                'rol_id': 2,
                'empresas_ids': ['76123456-7'],
                'centros_costo_ids': ['CC001'],
            },
            format='json',
        )
        force_authenticate(request, user=_admin_user())
        response = SipoUsuariosListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(_response_payload(response)['correo'], 'maria@flesan.cl')

    @patch('sipo.views_users.delete_sipo_usuario')
    def test_delete_usuario_admin(self, mock_delete):
        factory = APIRequestFactory()
        request = factory.delete('/api/sipo/usuarios/9/')
        force_authenticate(request, user=_admin_user())
        response = SipoUsuarioDetailView.as_view()(request, usuario_id=9)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_delete.assert_called_once_with(9)
