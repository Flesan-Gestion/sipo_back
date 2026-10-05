"""Tests integración Ficha de Ingreso + PDF Anexo 02."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from sipo.constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH
from sipo.models_ficha import SipoFichaIngreso
from sipo.services.fichas import (
    aprobar_ficha,
    create_ficha,
    eliminar_ficha,
    rechazar_ficha,
    retroceder_ficha,
)
from sipo.services.pdf_ficha import build_ficha_pdf
from sipo.views_ficha import (
    SipoFichaAprobarView,
    SipoFichaDetailView,
    SipoFichaPdfView,
    SipoFichaRechazarView,
    SipoFichaRetrocederView,
    SipoFichasListCreateView,
)


def _response_payload(response):
    return json.loads(response.content.decode('utf-8'))['data']


def _admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_ADMIN
    user.email = 'admin@flesan.cl'
    user.id = 1
    user.pk = 1
    return user


def _rrhh_user():
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = SIPO_ROL_RRHH
    user.email = 'rrhh@flesan.cl'
    user.id = 2
    user.pk = 2
    return user


def _jefe_user(email='jefe@flesan.cl'):
    user = MagicMock()
    user.is_authenticated = True
    user.sip_rol_id = 3
    user.email = email
    user.id = 3
    user.pk = 3
    return user


def _required_docs():
    return {
        'doc_domicilio': SimpleUploadedFile(
            'domicilio.pdf', b'%PDF-1.4 fake', content_type='application/pdf'
        ),
        'doc_afp': SimpleUploadedFile(
            'afp.pdf', b'%PDF-1.4 fake', content_type='application/pdf'
        ),
        'doc_salud': SimpleUploadedFile(
            'salud.pdf', b'%PDF-1.4 fake', content_type='application/pdf'
        ),
        'doc_cedula': SimpleUploadedFile(
            'cedula.pdf', b'%PDF-1.4 fake', content_type='application/pdf'
        ),
    }


def _full_ficha_data(**overrides):
    data = {
        'razon_social_id': '76123456-7',
        'razon_social_nombre': 'Empresa Demo',
        'obra': 'Obra Demo',
        'centro_costo_id': 'CC001',
        'centro_costo_nombre': 'Centro 1',
        'cargo': 'Analista',
        'fecha_ingreso': '2026-09-04',
        'correo_jefe_directo': 'jefe@flesan.cl',
        'correo_admin_obra': 'adminobra@flesan.cl',
        'correo_colaborador': 'colaborador@flesan.cl',
        'jefe_user_id': '109076',
        'jefe_nombre': 'Jefe Demo',
        'jefe_correo': 'jefe.planta@flesan.cl',
        'nombres': 'Martin Alonso',
        'apellido_paterno': 'Norambuena',
        'apellido_materno': 'Herrera',
        'rut': '9.678.773-7',
        'genero': 'M',
        'tratamiento': 'Sr.',
        'fecha_nacimiento': '1990-01-15',
        'edad': '36',
        'nacionalidad': 'Chilena',
        'pais_nacimiento': 'Chile',
        'region_nacimiento': 'Metropolitana',
        'afp': 'Habitat',
        'isapre_fonasa': 'FONASA A',
        'jubilado': 'false',
        'estado_civil': 'Soltero',
        'telefono': '56912345678',
        'domicilio': 'Calle Demo',
        'numero_direccion': '100',
        'region': 'Metropolitana',
        'ciudad': 'Santiago',
        'comuna': 'Santiago',
        'email_personal': 'test@flesan.cl',
        'metodo_pago': 'Cuenta Corriente',
        'banco': 'Banco Estado',
        'numero_cuenta': '123456',
        'sueldo_liquido': '650000',
        'cuenta_gasto': 'CG001',
        'tipo_contrato': 'Plazo Fijo',
        'termino_contrato': '2027-09-04',
        'horario': 'L-V 08-17',
        'external_code_pais': '10000004',
    }
    data.update(overrides)
    return data


def _seed_ficha(**overrides):
    defaults = {
        'rut': '9.678.773-7',
        'nombres': 'Martin',
        'apellido_paterno': 'Norambuena',
        'apellido_materno': 'Herrera',
        'correo_jefe_directo': 'jefe@flesan.cl',
        'cargo': 'Analista',
        'estado': SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
        'creado_por': 'admin@flesan.cl',
    }
    defaults.update(overrides)
    return SipoFichaIngreso.objects.create(**defaults)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SipoFichaCreateTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _admin_user()

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
    def test_create_ficha_completa_ok(self, _mock_label, _mock_labels, _mock_pais):
        data = {**_full_ficha_data(), **_required_docs()}
        request = self.factory.post('/api/sipo/fichas/', data, format='multipart')
        force_authenticate(request, user=self.user)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichasListCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = _response_payload(response)
        self.assertEqual(payload['rut'], '9.678.773-7')
        self.assertEqual(payload['nombres'], 'MARTIN ALONSO')
        self.assertEqual(payload['estado'], SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO)
        self.assertTrue(SipoFichaIngreso.objects.filter(pk=payload['id']).exists())

    @patch(
        'sipo.services.pais_segregation.lookup_pais_empresa_cc',
        return_value='10000004',
    )
    def test_create_ficha_campos_faltantes_400(self, _mock_pais):
        data = {
            'rut': '9.678.773-7',
            'nombres': 'Martin',
            'razon_social_id': '76123456-7',
            'centro_costo_id': 'CC001',
            'external_code_pais': '10000004',
        }
        request = self.factory.post('/api/sipo/fichas/', data, format='multipart')
        force_authenticate(request, user=self.user)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichasListCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_ficha_service_requiere_obligatorios(self):
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            with self.assertRaises(ValidationError):
                create_ficha(
                    data={'rut': '1-9', 'nombres': 'Test'},
                    files={},
                    user=self.user,
                )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SipoFichaAprobacionFlujoTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = _admin_user()
        self.rrhh = _rrhh_user()
        self.jefe = _jefe_user()
        self.ficha = _seed_ficha()

    def test_flujo_rrhh_luego_jefe_hasta_aprobada(self):
        self.ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_RRHH
        self.ficha.save(update_fields=['estado'])
        with patch('sipo.services.fichas.apply_ficha_scope', side_effect=lambda qs, _u: qs):
            ficha = aprobar_ficha(ficha_id=self.ficha.id, user=self.rrhh)
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO)
        self.assertEqual(ficha.aprobado_rrhh_por, 'rrhh@flesan.cl')

        with patch('sipo.services.fichas.apply_ficha_scope', side_effect=lambda qs, _u: qs):
            ficha = aprobar_ficha(ficha_id=self.ficha.id, user=self.jefe)
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_APROBADA)
        self.assertEqual(ficha.aprobado_jefe_por, 'jefe@flesan.cl')

    def test_admin_aprueba_nivel_rrhh_directo(self):
        self.ficha.estado = SipoFichaIngreso.ESTADO_PENDIENTE_RRHH
        self.ficha.save(update_fields=['estado'])
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            ficha = aprobar_ficha(ficha_id=self.ficha.id, user=self.admin)
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO)

    def test_sin_paso_admin_obra(self):
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            ficha = aprobar_ficha(ficha_id=self.ficha.id, user=self.admin)
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_APROBADA)
        self.assertNotEqual(ficha.estado, 'PENDIENTE_ADMIN')

    def test_rechazar_con_comentario(self):
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            ficha = rechazar_ficha(
                ficha_id=self.ficha.id,
                user=self.admin,
                comentario='Faltan documentos',
            )
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_RECHAZADA)
        self.assertEqual(ficha.rechazo_comentario, 'Faltan documentos')

    def test_rechazar_sin_comentario_falla(self):
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            with self.assertRaises(ValidationError):
                rechazar_ficha(ficha_id=self.ficha.id, user=self.admin, comentario='')

    def test_rrhh_no_aprueba_etapa_jefe(self):
        with patch('sipo.services.fichas.apply_ficha_scope', side_effect=lambda qs, _u: qs):
            with self.assertRaises(PermissionDenied):
                aprobar_ficha(ficha_id=self.ficha.id, user=self.rrhh)

    def test_retroceder_ficha_aprobada(self):
        self.ficha.estado = SipoFichaIngreso.ESTADO_APROBADA
        self.ficha.aprobado_jefe_por = 'jefe@flesan.cl'
        self.ficha.aprobado_rrhh_por = 'rrhh@flesan.cl'
        self.ficha.save()
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            ficha = retroceder_ficha(ficha_id=self.ficha.id, user=self.admin)
        self.assertEqual(ficha.estado, SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO)
        self.assertIsNone(ficha.aprobado_jefe_por)
        self.assertIsNone(ficha.aprobado_rrhh_por)

    def test_endpoint_retroceder(self):
        self.ficha.estado = SipoFichaIngreso.ESTADO_APROBADA
        self.ficha.save(update_fields=['estado'])
        request = self.factory.post(f'/api/sipo/fichas/{self.ficha.id}/retroceder/')
        force_authenticate(request, user=self.admin)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichaRetrocederView.as_view()(request, ficha_id=self.ficha.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            _response_payload(response)['estado'],
            SipoFichaIngreso.ESTADO_PENDIENTE_JEFE_TERRENO,
        )

    def test_eliminar_ficha(self):
        ficha_id = self.ficha.id
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            result = eliminar_ficha(ficha_id=ficha_id, user=self.admin)
        self.assertEqual(result['id'], ficha_id)
        self.assertTrue(result['deleted'])
        self.assertFalse(SipoFichaIngreso.objects.filter(id=ficha_id).exists())

    def test_endpoint_eliminar(self):
        ficha_id = self.ficha.id
        request = self.factory.delete(f'/api/sipo/fichas/{ficha_id}/')
        force_authenticate(request, user=self.admin)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichaDetailView.as_view()(request, ficha_id=ficha_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = _response_payload(response)
        self.assertTrue(payload['deleted'])
        self.assertEqual(payload['id'], ficha_id)
        self.assertFalse(SipoFichaIngreso.objects.filter(id=ficha_id).exists())

    def test_endpoint_aprobar_y_rechazar(self):
        request = self.factory.post(f'/api/sipo/fichas/{self.ficha.id}/aprobar/')
        force_authenticate(request, user=self.admin)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response = SipoFichaAprobarView.as_view()(request, ficha_id=self.ficha.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            _response_payload(response)['estado'],
            SipoFichaIngreso.ESTADO_APROBADA,
        )

        ficha2 = _seed_ficha(rut='2-7', nombres='Otro')
        request2 = self.factory.post(
            f'/api/sipo/fichas/{ficha2.id}/rechazar/',
            {'comentario': 'Datos incompletos'},
            format='json',
        )
        force_authenticate(request2, user=self.admin)
        with patch('sipo.services.fichas.get_scope_for_user', return_value={'is_admin': True}):
            response2 = SipoFichaRechazarView.as_view()(request2, ficha_id=ficha2.id)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            _response_payload(response2)['estado'],
            SipoFichaIngreso.ESTADO_RECHAZADA,
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SipoFichaPatchTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _admin_user()
        self.ficha = _seed_ficha(cargo='Analista')

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
    def test_patch_ficha_pendiente_ok(self, _mock_label, _mock_labels, _mock_pais):
        data = {
            **_full_ficha_data(nombres='Martin Alonso', cargo='Supervisor', sueldo_liquido='700000'),
            **_required_docs(),
        }
        request = self.factory.patch(
            f'/api/sipo/fichas/{self.ficha.id}/', data, format='multipart'
        )
        force_authenticate(request, user=self.user)
        with patch(
            'sipo.services.fichas.get_scope_for_user',
            return_value={'is_admin': True, 'empresas_ids': [], 'centros_costo_ids': []},
        ):
            response = SipoFichaDetailView.as_view()(request, ficha_id=self.ficha.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = _response_payload(response)
        self.assertEqual(payload['nombres'], 'MARTIN ALONSO')
        self.assertEqual(payload['cargo'], 'Supervisor')
        self.assertEqual(payload['sueldo_liquido'], 700000)
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.cargo, 'Supervisor')

    def test_patch_ficha_aprobada_rechaza_400(self):
        self.ficha.estado = SipoFichaIngreso.ESTADO_APROBADA
        self.ficha.save(update_fields=['estado'])
        data = {'rut': '9.678.773-7', 'nombres': 'Martin', 'cargo': 'Otro'}
        request = self.factory.patch(
            f'/api/sipo/fichas/{self.ficha.id}/', data, format='multipart'
        )
        force_authenticate(request, user=self.user)
        with patch(
            'sipo.services.fichas.get_scope_for_user',
            return_value={'is_admin': True, 'empresas_ids': [], 'centros_costo_ids': []},
        ):
            response = SipoFichaDetailView.as_view()(request, ficha_id=self.ficha.id)

        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        body = (
            response.data
            if hasattr(response, 'data')
            else json.loads(response.content.decode('utf-8'))
        )
        detail = str(body.get('detail') or body)
        self.assertIn('no puede modificarse', detail.lower())
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.cargo, 'Analista')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SipoFichaPdfTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _admin_user()
        self.ficha = _seed_ficha(cargo='Analista', fecha_ingreso='2026-09-04')

    def test_pdf_bytes_not_empty(self):
        pdf = build_ficha_pdf(self.ficha)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 500)

    def test_pdf_endpoint_200(self):
        request = self.factory.get(f'/api/sipo/fichas/{self.ficha.id}/pdf/')
        force_authenticate(request, user=self.user)
        with patch(
            'sipo.services.fichas.get_scope_for_user',
            return_value={'is_admin': True, 'empresas_ids': [], 'centros_costo_ids': []},
        ):
            response = SipoFichaPdfView.as_view()(request, ficha_id=self.ficha.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Ficha_Ingreso_', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))
