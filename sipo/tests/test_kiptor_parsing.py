"""Tests parsing montos Kiptor (regresión $586.000 / sueldobase decimal)."""

from django.test import SimpleTestCase

from sipo.services.kiptor import KiptorService


class KiptorParsingTests(SimpleTestCase):
    def test_liquido_formato_chileno(self):
        self.assertEqual(KiptorService.parse_liquido_digits('586.000'), 586_000)
        self.assertEqual(KiptorService.parse_liquido_digits('586000'), 586_000)

    def test_sueldobase_decimal_us_no_infla(self):
        # Bug: strip all digits → 55243700
        self.assertEqual(
            KiptorService.parse_sueldo_base_response('552437.00', liquido=586_000),
            552_437,
        )

    def test_sueldobase_entero_json(self):
        self.assertEqual(
            KiptorService.parse_sueldo_base_response(850_000, liquido=586_000),
            850_000,
        )

    def test_sueldobase_chileno_miles(self):
        self.assertEqual(
            KiptorService.parse_sueldo_base_response('850.000', liquido=586_000),
            850_000,
        )

    def test_sueldobase_anomalo_dispara_error(self):
        with self.assertRaises(ValueError):
            KiptorService.parse_sueldo_base_response('55.243.700', liquido=586_000)
