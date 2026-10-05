"""Validación estricta de campos obligatorios (candidato + ficha)."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from sipo.serializers import SipoCandidatoWriteSerializer
from sipo.serializers_ficha import SipoFichaIngresoWriteSerializer
from sipo.services.candidato_fields import is_blank_value


def _candidato_base(**overrides):
    data = {
        'cf_rrhh_sip_obra_candidato_tratamiento': 'Sr.',
        'cf_rrhh_sip_obra_candidato_rut': '11.111.111-1',
        'cf_rrhh_sip_obra_candidato_nombre': 'Martin',
        'cf_rrhh_sip_obra_candidato_ap': 'Norambuena',
        'cf_rrhh_sip_obra_candidato_am': 'Herrera',
        'cf_rrhh_sip_obra_candidato_genero': 'M',
        'cf_rrhh_sip_obra_candidato_fecha_nacimiento': '1990-01-15',
        'cf_rrhh_sip_obra_candidato_estado_civil': 'Soltero',
        'cf_rrhh_sip_obra_candidato_telefono': '56912345678',
        'cf_rrhh_sip_obra_candidato_correo': 'test@flesan.cl',
        'cf_rrhh_sip_obra_candidato_pais_nacimiento': 'Chile',
        'cf_rrhh_sip_obra_candidato_region_nacimiento': 'Metropolitana',
        'cf_rrhh_sip_obra_candidato_nacionalidad': 'Chilena',
        'cf_rrhh_sip_obra_candidato_region': 'Metropolitana',
        'cf_rrhh_sip_obra_candidato_ciudad': 'Santiago',
        'cf_rrhh_sip_obra_candidato_comuna': 'Santiago',
        'cf_rrhh_sip_obra_candidato_direccion': 'Calle Demo',
        'cf_rrhh_sip_obra_candidato_numero_dire': '100',
        'cf_rrhh_sip_obra_candidato_metodo_pago': 'Cuenta Corriente',
        'cf_rrhh_sip_obra_candidato_banco': 'Banco Estado',
        'cf_rrhh_sip_obra_candidato_numcta': '123456',
        'cf_rrhh_sip_obra_candidato_nom_afp': 'Habitat',
        'cf_rrhh_sip_obra_candidato_nom_salud': '005',
        'cf_rrhh_sip_obra_candidato_jubilado': 'No',
        'cf_rrhh_sip_obra_candidato_nomcar': 'Analista',
        'cf_rrhh_sip_obra_candidato_jefe_user_id': '109076',
        'cf_rrhh_sip_obra_candidato_jefe_nombre': 'Jefe Demo',
        'cf_rrhh_sip_obra_candidato_jefe_correo': 'jefe@flesan.cl',
        'cf_rrhh_sip_obra_candidato_horario_trabajo': 'L-V 08-17',
        'cf_rrhh_sip_obra_candidato_sueldo': '650000',
        'cf_rrhh_sip_obra_candidato_cuenta_gasto': 'CG001',
        'cf_rrhh_sip_obra_candidato_tipo_contrato': 'Indefinido',
        'cf_rrhh_sip_obra_candidato_fecha_ingreso': '2026-09-04',
        'cf_rrhh_sip_obra_candidato_ci': 'docs/ci.pdf',
        'cf_rrhh_sip_obra_candidato_afp': 'docs/afp.pdf',
        'cf_rrhh_sip_obra_candidato_salud': 'docs/salud.pdf',
        'cf_rrhh_sip_obra_candidato_domi': 'docs/domi.pdf',
    }
    data.update(overrides)
    return data


def _ficha_base(**overrides):
    data = {
        'razon_social_id': '76123456-7',
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
    }
    data.update(overrides)
    return data


class IsBlankValueTests(SimpleTestCase):
    def test_blank_variants(self):
        self.assertTrue(is_blank_value(None))
        self.assertTrue(is_blank_value(''))
        self.assertTrue(is_blank_value('   '))
        self.assertFalse(is_blank_value('ok'))
        self.assertFalse(is_blank_value(0))
        self.assertFalse(is_blank_value(False))


class SipoCandidatoWriteRequiredTests(SimpleTestCase):
    @patch(
        'sipo.services.candidato_validaciones.validate_candidato_negocio',
        side_effect=lambda data, **kw: data,
    )
    def test_ok_payload(self, _mock):
        ser = SipoCandidatoWriteSerializer(data=_candidato_base())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_missing_required_400(self):
        data = _candidato_base()
        del data['cf_rrhh_sip_obra_candidato_nombre']
        ser = SipoCandidatoWriteSerializer(data=data)
        self.assertFalse(ser.is_valid())
        self.assertIn('cf_rrhh_sip_obra_candidato_nombre', ser.errors)

    @patch(
        'sipo.services.candidato_validaciones.validate_candidato_negocio',
        side_effect=lambda data, **kw: data,
    )
    def test_whitespace_only_rejected(self, _mock):
        ser = SipoCandidatoWriteSerializer(
            data=_candidato_base(cf_rrhh_sip_obra_candidato_nombre='   ')
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('cf_rrhh_sip_obra_candidato_nombre', ser.errors)

    def test_segundo_apellido_required(self):
        data = _candidato_base()
        del data['cf_rrhh_sip_obra_candidato_am']
        ser = SipoCandidatoWriteSerializer(data=data)
        self.assertFalse(ser.is_valid())
        self.assertIn('cf_rrhh_sip_obra_candidato_am', ser.errors)

    @patch(
        'sipo.services.candidato_validaciones.validate_candidato_negocio',
        side_effect=lambda data, **kw: data,
    )
    def test_obra_faena_requires_hito(self, _mock):
        ser = SipoCandidatoWriteSerializer(
            data=_candidato_base(
                cf_rrhh_sip_obra_candidato_tipo_contrato='Obra o Faena',
                cf_rrhh_sip_obra_candidato_termino_contrato='',
                cf_rrhh_sip_obra_candidato_fecha_termino_ito='',
            )
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('cf_rrhh_sip_obra_candidato_termino_contrato', ser.errors)


class SipoFichaWriteRequiredTests(SimpleTestCase):
    def test_ok_payload(self):
        ser = SipoFichaIngresoWriteSerializer(data=_ficha_base())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_missing_required(self):
        data = _ficha_base()
        del data['apellido_materno']
        ser = SipoFichaIngresoWriteSerializer(data=data)
        self.assertFalse(ser.is_valid())
        self.assertIn('apellido_materno', ser.errors)

    def test_whitespace_rejected(self):
        ser = SipoFichaIngresoWriteSerializer(data=_ficha_base(nombres='   '))
        self.assertFalse(ser.is_valid())
        self.assertIn('nombres', ser.errors)

    def test_extranjero_requires_nacionalidad_ext(self):
        ser = SipoFichaIngresoWriteSerializer(
            data=_ficha_base(nacionalidad='Extranjero', nacionalidad_ext='')
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('nacionalidad_ext', ser.errors)

    def test_sueldo_liquido_minimo_585000(self):
        ser = SipoFichaIngresoWriteSerializer(data=_ficha_base(sueldo_liquido='584999'))
        self.assertFalse(ser.is_valid())
        self.assertIn('sueldo_liquido', ser.errors)

    def test_sueldo_liquido_igual_minimo_ok(self):
        ser = SipoFichaIngresoWriteSerializer(data=_ficha_base(sueldo_liquido='585000'))
        self.assertTrue(ser.is_valid(), ser.errors)
