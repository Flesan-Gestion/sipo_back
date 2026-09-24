"""Tests segregación Grupo 2 (external_code_pais=10000004)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from sipo.constants import EXTERNAL_CODE_PAIS_CHILE, EXTERNAL_CODE_PAIS_GRUPO_2
from sipo.services.pais_segregation import (
    apply_external_code_pais_filter,
    assert_create_only_grupo2,
    is_grupo2_pais,
    validate_razon_social_centro_costo,
)
from sipo.serializers import SipoObraWriteSerializer
from sipo.serializers_ficha import SipoFichaRsCcWriteSerializer


class PaisSegregationFilterTests(SimpleTestCase):
    def test_is_grupo2(self):
        self.assertTrue(is_grupo2_pais(EXTERNAL_CODE_PAIS_GRUPO_2))
        self.assertFalse(is_grupo2_pais(EXTERNAL_CODE_PAIS_CHILE))
        self.assertFalse(is_grupo2_pais(None))

    def test_filter_grupo2(self):
        qs = MagicMock()
        qs.filter.return_value = 'g2'
        result = apply_external_code_pais_filter(qs, EXTERNAL_CODE_PAIS_GRUPO_2)
        qs.filter.assert_called_once_with(external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2)
        self.assertEqual(result, 'g2')

    def test_filter_sin_valor_sin_filtro(self):
        qs = MagicMock()
        result = apply_external_code_pais_filter(qs, None)
        qs.filter.assert_not_called()
        qs.exclude.assert_not_called()
        self.assertEqual(result, qs)

    def test_filter_chile_explicito(self):
        qs = MagicMock()
        qs.exclude.return_value = 'sin_g2'
        result = apply_external_code_pais_filter(qs, EXTERNAL_CODE_PAIS_CHILE)
        qs.exclude.assert_called_once_with(external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2)
        self.assertEqual(result, 'sin_g2')


class PaisSegregationValidateTests(SimpleTestCase):
    def test_assert_create_solo_grupo2(self):
        self.assertEqual(assert_create_only_grupo2(None), EXTERNAL_CODE_PAIS_GRUPO_2)
        self.assertEqual(
            assert_create_only_grupo2(EXTERNAL_CODE_PAIS_GRUPO_2),
            EXTERNAL_CODE_PAIS_GRUPO_2,
        )
        with self.assertRaises(ValidationError):
            assert_create_only_grupo2(EXTERNAL_CODE_PAIS_CHILE)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_GRUPO_2)
    def test_rechaza_g2_sin_contexto(self, _mock):
        with self.assertRaises(ValidationError):
            validate_razon_social_centro_costo(
                razon_social_id='G2-EMP',
                centro_costo_id='G2-CC',
                external_code_pais=None,
            )

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_GRUPO_2)
    def test_acepta_g2_con_contexto(self, _mock):
        pais = validate_razon_social_centro_costo(
            razon_social_id='G2-EMP',
            centro_costo_id='G2-CC',
            external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2,
        )
        self.assertEqual(pais, EXTERNAL_CODE_PAIS_GRUPO_2)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_CHILE)
    def test_rechaza_chile_en_contexto_g2(self, _mock):
        with self.assertRaises(ValidationError):
            validate_razon_social_centro_costo(
                razon_social_id='CL-EMP',
                centro_costo_id='CL-CC',
                external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2,
            )

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_CHILE)
    def test_acepta_chile_sin_contexto(self, _mock):
        pais = validate_razon_social_centro_costo(
            razon_social_id='CL-EMP',
            centro_costo_id='CL-CC',
        )
        self.assertEqual(pais, EXTERNAL_CODE_PAIS_CHILE)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=None)
    def test_par_incoherente(self, _mock):
        with self.assertRaises(ValidationError):
            validate_razon_social_centro_costo(
                razon_social_id='X',
                centro_costo_id='Y',
                external_code_pais=EXTERNAL_CODE_PAIS_CHILE,
            )


class SerializerPaisTests(SimpleTestCase):
    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_CHILE)
    def test_obra_write_rechaza_chile(self, _mock):
        ser = SipoObraWriteSerializer(
            data={
                'cf_rrhh_sip_rut': 'CL',
                'cf_rrhh_sip_razonsocial': 'Chile SA',
                'cf_rrhh_sip_uni': 'U1',
                'cf_rrhh_sip_nombre_uni': 'UN',
                'cf_rrhh_sip_dep': 'D1',
                'cf_rrhh_sip_nombre_dep': 'DEP',
                'cf_rrhh_sip_cc': 'CC-CL',
                'cf_rrhh_sip_nombre_cc': 'CC',
                'cf_rrhh_sip_adm': 'a@flesan.cl',
                'cf_rrhh_sip_as': 'b@flesan.cl',
                'cf_rrhh_sip_ubicacion': 'Santiago',
                'external_code_pais': EXTERNAL_CODE_PAIS_CHILE,
            }
        )
        self.assertFalse(ser.is_valid())

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_GRUPO_2)
    def test_obra_write_fuerza_g2_sin_pais(self, _mock):
        ser = SipoObraWriteSerializer(
            data={
                'cf_rrhh_sip_rut': 'G2',
                'cf_rrhh_sip_razonsocial': 'G2 SA',
                'cf_rrhh_sip_uni': 'U1',
                'cf_rrhh_sip_nombre_uni': 'UN',
                'cf_rrhh_sip_dep': 'D1',
                'cf_rrhh_sip_nombre_dep': 'DEP',
                'cf_rrhh_sip_cc': 'CC-G2',
                'cf_rrhh_sip_nombre_cc': 'CC',
                'cf_rrhh_sip_adm': 'a@flesan.cl',
                'cf_rrhh_sip_as': 'b@flesan.cl',
                'cf_rrhh_sip_ubicacion': 'Santiago',
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data['external_code_pais'], EXTERNAL_CODE_PAIS_GRUPO_2)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_GRUPO_2)
    def test_obra_write_acepta_g2_con_pais(self, _mock):
        ser = SipoObraWriteSerializer(
            data={
                'cf_rrhh_sip_rut': 'G2',
                'cf_rrhh_sip_razonsocial': 'G2 SA',
                'cf_rrhh_sip_uni': 'U1',
                'cf_rrhh_sip_nombre_uni': 'UN',
                'cf_rrhh_sip_dep': 'D1',
                'cf_rrhh_sip_nombre_dep': 'DEP',
                'cf_rrhh_sip_cc': 'CC-G2',
                'cf_rrhh_sip_nombre_cc': 'CC',
                'cf_rrhh_sip_adm': 'a@flesan.cl',
                'cf_rrhh_sip_as': 'b@flesan.cl',
                'cf_rrhh_sip_ubicacion': 'Santiago',
                'external_code_pais': EXTERNAL_CODE_PAIS_GRUPO_2,
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_GRUPO_2)
    def test_ficha_serializer_create_fuerza_g2(self, _mock):
        ser = SipoFichaRsCcWriteSerializer(
            data={
                'razon_social_id': 'G2',
                'centro_costo_id': 'CC-G2',
            }
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data['external_code_pais'], EXTERNAL_CODE_PAIS_GRUPO_2)

    @patch('sipo.services.pais_segregation.lookup_pais_empresa_cc', return_value=EXTERNAL_CODE_PAIS_CHILE)
    def test_ficha_serializer_create_rechaza_chile(self, _mock):
        ser = SipoFichaRsCcWriteSerializer(
            data={
                'razon_social_id': 'CL',
                'centro_costo_id': 'CC-CL',
                'external_code_pais': EXTERNAL_CODE_PAIS_CHILE,
            }
        )
        self.assertFalse(ser.is_valid())
