"""Tests unitarios bloqueadores críticos SIPO Obra."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from sipo.services.candidato_validaciones import (
    calcular_bono_mineria_cfm,
    match_estandarizacion,
    resolve_sueldo_minimo,
)
from sipo.services.notifications import (
    EVENTO_REVISION,
    collect_integration_errors,
    enviar_notificacion_email,
)
from sipo.services.sap_sync.sap_builder import (
    SapSyncContext,
    build_per_address_payload,
    build_pay_comp_payloads,
    build_position_payload,
    build_user_payload,
    map_gender_sap,
)


class MatchEstandarizacionTests(SimpleTestCase):
    @patch('django.db.connections')
    def test_match_estandarizacion_true(self, mock_connections):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = cursor

        self.assertTrue(match_estandarizacion('OPERADOR', 'NORTE'))

    @patch('django.db.connections')
    def test_match_estandarizacion_false_sin_fila(self, mock_connections):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = cursor

        self.assertFalse(match_estandarizacion('OPERADOR', 'NORTE'))


class Sueldo962Tests(SimpleTestCase):
    def test_piso_962_con_estandarizacion(self):
        ok, piso, msg = resolve_sueldo_minimo(
            sueldo='900000',
            cargo='OPERADOR',
            horario='PHT00001',
            estandarizacion_match=True,
        )
        self.assertFalse(ok)
        self.assertEqual(piso, 962_000)
        self.assertIn('962.000', msg)

    def test_piso_liquido_estandar_585000(self):
        from sipo.constants import SUELDO_LIQUIDO_MINIMO

        ok, piso, msg = resolve_sueldo_minimo(
            sueldo='584999',
            cargo='ANALISTA',
            horario='PHT00001',
        )
        self.assertFalse(ok)
        self.assertEqual(piso, SUELDO_LIQUIDO_MINIMO)
        self.assertIn('585.000', msg)

        ok2, piso2, _ = resolve_sueldo_minimo(
            sueldo='585000',
            cargo='ANALISTA',
            horario='PHT00001',
        )
        self.assertTrue(ok2)
        self.assertEqual(piso2, SUELDO_LIQUIDO_MINIMO)


class SueldoBaseImmTests(SimpleTestCase):
    def test_apply_sueldo_base_piso_imm(self):
        from sipo.constants import IMM_ACTUAL
        from sipo.services.candidato_validaciones import apply_sueldo_base_piso

        self.assertEqual(apply_sueldo_base_piso(500_000), IMM_ACTUAL)
        self.assertEqual(apply_sueldo_base_piso(IMM_ACTUAL), IMM_ACTUAL)
        self.assertEqual(apply_sueldo_base_piso(700_000), 700_000)
        self.assertEqual(apply_sueldo_base_piso(0), 0)


class BonoMineriaTests(SimpleTestCase):
    def test_bono_mineria_retorna_entero(self):
        bono = calcular_bono_mineria_cfm(
            liquido_objetivo=1_200_000,
            sueldo_base_tabla=800_000,
            bono_pie=100_000,
            tasa_afp=0.1144,
            valor_uf=39_000,
            valor_utm=68_000,
        )
        self.assertIsInstance(bono, int)
        self.assertGreaterEqual(bono, 0)


class PerAddressPayloadTests(SimpleTestCase):
    def test_sanitiza_pipes_en_direccion(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200001'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = date(2026, 1, 15)
        candidato.cf_rrhh_sip_obra_candidato_direccion = '|Av. Principal|'
        candidato.cf_rrhh_sip_obra_candidato_numero_dire = '348|'
        candidato.cf_rrhh_sip_obra_candidato_num_depto = '|12'
        candidato.cf_rrhh_sip_obra_candidato_comuna = 'Santiago'
        candidato.cf_rrhh_sip_obra_candidato_ciudad = 'Santiago'
        candidato.cf_rrhh_sip_obra_candidato_region = 'RM'

        obra = MagicMock()
        ctx = SapSyncContext(candidato=candidato, obra=obra)
        payload = build_per_address_payload(ctx)

        self.assertEqual(payload['address1'], 'Av. Principal')
        self.assertEqual(payload['address2'], '348')
        self.assertEqual(payload['address4'], '12')
        self.assertNotIn('|', payload['address1'])


class PayCompCfmTests(SimpleTestCase):
    def test_cfm_no_upserta_1100_paridad_legado(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200001'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = date(2026, 1, 15)
        candidato.cf_rrhh_sip_obra_candidato_sueldo = '1200000'
        candidato.cf_rrhh_sip_obra_sueldo_base = Decimal('900000')
        candidato.cf_rrhh_sip_obra_bono_mineria = Decimal('150000')

        obra = MagicMock()
        obra.cf_rrhh_sip_rut = 'CFM'
        ctx = SapSyncContext(candidato=candidato, obra=obra, colacion_movilizacion=80_000)

        payloads = build_pay_comp_payloads(ctx)
        components = {p['payComponent']: p['paycompvalue'] for p in payloads}
        self.assertIn('M020', components)
        self.assertEqual(components['1029'], 80_000)
        self.assertEqual(components['1018'], 80_000)
        self.assertNotIn('1100', components)
        self.assertEqual(len(payloads), 3)


class SapGenderAndPositionTests(SimpleTestCase):
    def test_map_gender_masculino_a_m(self):
        self.assertEqual(map_gender_sap('Masculino'), 'M')
        self.assertEqual(map_gender_sap('Femenino'), 'F')
        self.assertEqual(map_gender_sap('M'), 'M')
        self.assertEqual(map_gender_sap('f'), 'F')

    def test_user_payload_usa_codigo_genero(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200007'
        candidato.cf_rrhh_sip_obra_candidato_fecha_nacimiento = '2002-10-12'
        candidato.cf_rrhh_sip_obra_candidato_nombre = 'Juan'
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre = ''
        candidato.cf_rrhh_sip_obra_candidato_ap = 'Perez'
        candidato.cf_rrhh_sip_obra_candidato_am = ''
        candidato.cf_rrhh_sip_obra_candidato_genero = 'Masculino'
        ctx = SapSyncContext(candidato=candidato, obra=MagicMock())
        payload = build_user_payload(ctx)
        self.assertEqual(payload['gender'], 'M')

    def test_position_incluye_cust_employment_type(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200007'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = '2026-09-14'
        candidato.cf_rrhh_sip_obra_candidato_nomcar = 'OPERADOR'
        obra = MagicMock()
        obra.cf_rrhh_sip_rut = 'DVF'
        obra.cf_rrhh_sip_cc = 'DVFR120001DVF'
        obra.cf_rrhh_sip_dep = '10000297'
        obra.cf_rrhh_sip_uni = 'UNI'
        obra.cf_rrhh_sip_ubicacion = 'LOC'
        ctx = SapSyncContext(
            candidato=candidato,
            obra=obra,
            job_code='10000039',
            employment_type='GOV',
            business_unit='10000001',
        )
        payload = build_position_payload(ctx)
        self.assertEqual(payload['cust_employmentType'], 'GOV')
        self.assertEqual(payload['code'], '20200007')

    def test_empjob_incluye_manager_id(self):
        from sipo.services.sap_sync.sap_builder import build_emp_job_payload

        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200007'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = '2026-09-14'
        candidato.cf_rrhh_sip_obra_candidato_tipo_contrato = 'Plazo Fijo'
        candidato.cf_rrhh_sip_obra_candidato_jefe_user_id = '109076'
        obra = MagicMock()
        obra.cf_rrhh_sip_rut = 'DVF'
        ctx = SapSyncContext(candidato=candidato, obra=obra)
        payload = build_emp_job_payload(ctx)
        self.assertEqual(payload['managerId'], '109076')

    def test_national_id_formato_sap_xx_xxx_xxx_z(self):
        from sipo.services.candidato_validaciones import format_rut_sap_national_id

        self.assertEqual(format_rut_sap_national_id('9.676.775-7'), '09.676.775-7')
        self.assertEqual(format_rut_sap_national_id('09676775-7'), '09.676.775-7')
        self.assertEqual(format_rut_sap_national_id('9676775-7'), '09.676.775-7')

    def test_anticipo_si_con_tilde(self):
        from sipo.services.sap_sync.sap_builder import map_anticipo_sap

        self.assertEqual(map_anticipo_sap('Si'), 'Sí')
        self.assertEqual(map_anticipo_sap('Sí'), 'Sí')
        self.assertEqual(map_anticipo_sap('No'), 'No')

    def test_payment_method_mapea_cuenta_rut_a_05(self):
        from sipo.services.sap_sync.sap_builder import map_payment_method_sap

        self.assertEqual(map_payment_method_sap('Cuenta Rut'), '05')
        self.assertEqual(map_payment_method_sap('05'), '05')
        self.assertEqual(map_payment_method_sap('Cheque'), '06')
        self.assertEqual(map_payment_method_sap(None), '05')
        self.assertEqual(map_payment_method_sap(''), '05')

    @patch('sipo.services.candidato_maestros.get_estado_civil')
    def test_marital_status_resuelve_codigo(self, mock_estados):
        from sipo.services.sap_sync.sap_builder import map_marital_status_sap

        mock_estados.return_value = [
            {'value': 'Soltero', 'label': 'Soltero', 'code': '5'},
        ]
        self.assertEqual(map_marital_status_sap('5'), 'Soltero')
        self.assertEqual(map_marital_status_sap('Casado'), 'Casado')

    def test_next_national_id_card_type(self):
        from sipo.services.sap_sync.sap_builder import next_national_id_card_type

        self.assertEqual(next_national_id_card_type('RUN1'), 'RUN2')
        self.assertEqual(next_national_id_card_type('RUN2'), 'RUN3')
        self.assertEqual(next_national_id_card_type(None), 'RUN2')


class NotificationsTests(SimpleTestCase):
    @override_settings(
        SIP_EMAIL_ENABLED=True,
        SIP_EMAIL_FORCE_OVERRIDE=False,
        DEFAULT_FROM_EMAIL='test@flesan.cl',
        SIP_EMAIL_FROM='test@flesan.cl',
        SIP_EMAIL_FROM_NAME='SIPO Test',
        SIP_EMAIL_IMG_BASE='https://example.com/img',
        SIPO_PORTAL_BASE_URL='http://localhost:5173/panel/sipo',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_enviar_notificacion_revision(self):
        from django.core import mail

        mail.outbox.clear()
        obra = MagicMock()
        obra.cf_rrhh_sip_id = 1234
        obra.cf_rrhh_sip_rut = 'CFM'
        obra.cf_rrhh_sip_razonsocial = 'CFM'
        obra.cf_rrhh_sip_uni = 'UN01'
        obra.cf_rrhh_sip_nombre_uni = 'Unidad'
        obra.cf_rrhh_sip_cc = 'CC01'
        obra.cf_rrhh_sip_nombre_cc = 'Centro'
        obra.cf_rrhh_sip_ubicacion = 'NORTE'
        obra.cf_rrhh_sip_adm = 'adm@flesan.cl'
        obra.cf_rrhh_sip_as = 'as@flesan.cl'
        obra.cf_rrhh_sip_create_user = 'creator@flesan.cl'

        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_candidato_nombre = 'Juan'
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre = ''
        candidato.cf_rrhh_sip_obra_candidato_ap = 'Perez'
        candidato.cf_rrhh_sip_obra_candidato_am = ''
        candidato.cf_rrhh_sip_obra_candidato_rut = '12.345.678-9'
        candidato.cf_rrhh_sip_obra_candidato_nomcar = 'OPERADOR'

        result = enviar_notificacion_email(EVENTO_REVISION, obra, [candidato])
        self.assertTrue(result['sent'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['adm@flesan.cl'])

    def test_collect_integration_errors_builder(self):
        errores = collect_integration_errors(
            builder_result={
                'skipped': False,
                'resultados': [
                    {
                        'candidato_id': 'abc',
                        'builder_ok': False,
                        'error': 'WORKER_STILL_HIRED para el colaborador JUAN sip N° 100',
                    },
                ],
            },
        )
        self.assertEqual(len(errores), 1)
        self.assertIn('WORKER_STILL_HIRED', errores[0])


class IbuilderWorkerPayloadTests(SimpleTestCase):
    def test_rut_y_phone_paridad_legado(self):
        from sipo.services.builder_sync import _build_worker_payload, _rut_ibuilder_worker

        self.assertEqual(_rut_ibuilder_worker('9.676.775-7'), '9676775-7')
        self.assertEqual(_rut_ibuilder_worker('09.676.775-7'), '9676775-7')
        self.assertEqual(_rut_ibuilder_worker('09676775-7'), '9676775-7')

        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_candidato_rut = '9.676.775-7'
        candidato.cf_rrhh_sip_obra_candidato_ap = 'Perez'
        candidato.cf_rrhh_sip_obra_candidato_am = 'Gomez'
        candidato.cf_rrhh_sip_obra_candidato_nombre = 'Juan'
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre = ''
        candidato.cf_rrhh_sip_obra_user_id = '200009'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = '2026-09-01'
        candidato.cf_rrhh_sip_obra_candidato_fecha_nacimiento = '1990-01-01'
        candidato.cf_rrhh_sip_obra_candidato_correo = 'juan@flesan.cl'
        candidato.cf_rrhh_sip_obra_candidato_genero = 'M'
        candidato.cf_rrhh_sip_obra_candidato_telefono = '912345678'
        ctx = {
            'empresa_id': 'e1',
            'cargo_id': 'c1',
            'turno_id': 't1',
            'tipo_contrato': 'tc1',
        }
        payload = _build_worker_payload(candidato, ctx)
        self.assertIsNone(payload['phone'])
        self.assertEqual(payload['rut'], '9676775-7')
        self.assertEqual(payload['gender'], 'GENDER_MALE')
        self.assertEqual(payload['className'], 'Worker')

    def test_parse_error_404_y_errors_message(self):
        from sipo.services.builder_sync import _parse_ibuilder_create_error

        msg_404 = _parse_ibuilder_create_error(
            status_code=404,
            body={'statusCode': 404},
            sip_id=100,
            nombre='JUAN PEREZ',
        )
        self.assertIn('no esta asociada', msg_404)

        msg_err = _parse_ibuilder_create_error(
            status_code=200,
            body={'errors': [{'message': 'WORKER_STILL_HIRED'}]},
            sip_id=100,
            nombre='JUAN PEREZ',
        )
        self.assertIn('WORKER_STILL_HIRED', msg_err)
        self.assertIn('JUAN PEREZ', msg_err)

        self.assertIsNone(
            _parse_ibuilder_create_error(
                status_code=201,
                body={},
                sip_id=100,
                nombre='JUAN',
            )
        )
