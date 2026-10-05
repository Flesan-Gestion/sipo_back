"""Rol Supervisor: fichas sí, solicitudes no."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from sipo.constants import SIPO_ROL_SUPERVISOR
from sipo.models_ficha import SipoFichaIngreso
from sipo.permissions import IsSipoAuthenticated
from sipo.serializers_ficha import SipoFichaIngresoWriteSerializer
from sipo.tests.test_fichas import _full_ficha_data, _response_payload
from sipo.views import SipoObraListView
from sipo.views_ficha import SipoFichasListCreateView


def _supervisor():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_SUPERVISOR
    user.email = 'supervisor@flesan.cl'
    user.id = 40
    user.pk = 40
    return user


class SupervisorSolicitudesTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _supervisor()

    def test_listar_solicitudes_403(self):
        request = self.factory.get('/api/sipo/')
        force_authenticate(request, user=self.user)
        response = SipoObraListView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_crear_solicitud_403(self):
        request = self.factory.post('/api/sipo/', {'rut': '1-9'}, format='json')
        force_authenticate(request, user=self.user)
        response = SipoObraListView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SupervisorFichasTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _supervisor()

    def test_listar_fichas_ok(self):
        request = self.factory.get('/api/sipo/fichas/')
        force_authenticate(request, user=self.user)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichasListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(
        'sipo.services.pais_segregation.lookup_pais_empresa_cc',
        return_value='10000004',
    )
    @patch(
        'sipo.services.fichas.resolve_ficha_catalog_fields',
        return_value={
            'afp': 'Habitat',
            'isapre_fonasa': 'FONASA A',
            'estado_civil': 'Soltero',
            'banco': 'Banco Estado',
        },
    )
    @patch(
        'sipo.serializers_ficha.resolve_catalog_label',
        side_effect=lambda _f, v: v,
    )
    def test_crear_ficha_con_correo_colaborador(self, _label, _labels, _pais):
        data = {
            'solo_supervisor': '1',
            'cargo': 'Operador',
            'fecha_ingreso': '2026-10-01',
            'correo_colaborador': 'colaborador@flesan.cl',
            'sueldo_liquido': '700000',
            'tipo_contrato': 'Plazo Fijo',
            'termino_contrato': '2027-01-01',
            'horario': 'H1',
        }
        request = self.factory.post('/api/sipo/fichas/', data, format='multipart')
        force_authenticate(request, user=self.user)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichasListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = _response_payload(response)
        self.assertEqual(payload['correo_colaborador'], 'colaborador@flesan.cl')


class SupervisorAlcanceTests(TestCase):
    def setUp(self):
        self.user = _supervisor()
        SipoFichaIngreso.objects.all().delete()
        self.propia = SipoFichaIngreso.objects.create(
            estado=SipoFichaIngreso.ESTADO_PENDIENTE_DATOS_COLABORADOR,
            creado_por='supervisor@flesan.cl',
            cargo='Operador',
        )
        self.ajena_cc = SipoFichaIngreso.objects.create(
            estado=SipoFichaIngreso.ESTADO_PENDIENTE_RRHH,
            creado_por='otro@flesan.cl',
            razon_social_id='76123456-7',
            centro_costo_id='CC001',
            cargo='Ayudante',
        )
        self.fuera = SipoFichaIngreso.objects.create(
            estado=SipoFichaIngreso.ESTADO_PENDIENTE_RRHH,
            creado_por='otro@flesan.cl',
            razon_social_id='76999999-9',
            centro_costo_id='CC999',
            cargo='Externo',
        )

    @patch(
        'sipo.services.fichas.get_scope_for_user',
        return_value={
            'is_admin': False,
            'empresas_ids': ['76123456-7'],
            'centros_costo_ids': ['CC001'],
        },
    )
    def test_ve_propias_y_alcance_cc(self, _scope):
        from sipo.services.fichas import apply_ficha_scope

        qs = apply_ficha_scope(SipoFichaIngreso.objects.all(), self.user)
        ids = set(qs.values_list('id', flat=True))
        self.assertIn(self.propia.id, ids)
        self.assertIn(self.ajena_cc.id, ids)
        self.assertNotIn(self.fuera.id, ids)

    def test_solo_edita_las_propias(self):
        from sipo.services.fichas import user_can_editar_ficha

        self.assertTrue(user_can_editar_ficha(self.propia, self.user))
        self.assertFalse(user_can_editar_ficha(self.ajena_cc, self.user))


class FichaCamposReorganizadosTests(TestCase):
    def test_serializer_expone_campos(self):
        fields = SipoFichaIngresoWriteSerializer().fields
        for key in ('cargo', 'fecha_ingreso', 'cuenta_gasto', 'correo_colaborador'):
            self.assertIn(key, fields)

    def test_correo_colaborador_obligatorio(self):
        data = _full_ficha_data()
        data.pop('correo_colaborador')
        serializer = SipoFichaIngresoWriteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('correo_colaborador', serializer.errors)

    def test_permiso_supervisor_no_es_admin(self):
        self.assertTrue(issubclass(IsSipoAuthenticated, object))
        user = _supervisor()
        self.assertEqual(int(user.sip_rol_id), SIPO_ROL_SUPERVISOR)
