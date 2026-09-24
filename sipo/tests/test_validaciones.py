"""Tests regla Chivato Huechún (colación/movilización = $1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from sipo.constants import CC_CHIVATO_HUECHUN, COL_MOV_CHIVATO_HUECHUN
from sipo.services.candidato_validaciones import (
    is_chivato_huechun_cc,
    resolve_colacion_movilizacion,
)
from sipo.services.kiptor import KiptorService
from sipo.services.sap_sync.sap_builder import SapSyncContext, build_pay_comp_payloads


class ChivatoHuechunValidacionesTests(SimpleTestCase):
    def test_detecta_cc_chivato(self):
        self.assertTrue(is_chivato_huechun_cc(CC_CHIVATO_HUECHUN))
        self.assertTrue(is_chivato_huechun_cc(' cfmcfm130048 '))
        self.assertFalse(is_chivato_huechun_cc('DVFR120001DVF'))
        self.assertFalse(is_chivato_huechun_cc(None))

    def test_resolve_fuerza_1_en_chivato(self):
        self.assertEqual(
            resolve_colacion_movilizacion(
                sueldo_liquido=900_000,
                centro_costo=CC_CHIVATO_HUECHUN,
            ),
            COL_MOV_CHIVATO_HUECHUN,
        )
        self.assertEqual(
            resolve_colacion_movilizacion(
                sueldo_liquido=250_000,
                centro_costo=CC_CHIVATO_HUECHUN,
            ),
            1,
        )

    @patch('django.db.connections')
    def test_resolve_otro_cc_usa_escala(self, mock_connections):
        cursor = MagicMock()
        cursor.fetchone.return_value = (80_000,)
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = (
            cursor
        )

        self.assertEqual(
            resolve_colacion_movilizacion(
                sueldo_liquido=900_000,
                centro_costo='OTROCC001',
            ),
            80_000,
        )
        cursor.execute.assert_called_once()

    def test_kiptor_get_col_mov_chivato(self):
        self.assertEqual(
            KiptorService.get_col_mov(900_000, centro_costo=CC_CHIVATO_HUECHUN),
            1,
        )

    def test_sap_paycomp_chivato_fuerza_1(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200001'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = date(2026, 1, 15)
        candidato.cf_rrhh_sip_obra_candidato_sueldo = '900000'
        candidato.cf_rrhh_sip_obra_sueldo_base = Decimal('700000')

        obra = MagicMock()
        obra.cf_rrhh_sip_rut = 'CFM'
        obra.cf_rrhh_sip_cc = CC_CHIVATO_HUECHUN
        ctx = SapSyncContext(candidato=candidato, obra=obra, colacion_movilizacion=80_000)

        payloads = build_pay_comp_payloads(ctx)
        components = {p['payComponent']: p['paycompvalue'] for p in payloads}
        self.assertEqual(components['1018'], 1)
        self.assertEqual(components['1029'], 1)

    def test_sap_paycomp_otro_cc_respeta_escala_contexto(self):
        candidato = MagicMock()
        candidato.cf_rrhh_sip_obra_user_id = '200002'
        candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso = date(2026, 1, 15)
        candidato.cf_rrhh_sip_obra_candidato_sueldo = '900000'
        candidato.cf_rrhh_sip_obra_sueldo_base = Decimal('700000')

        obra = MagicMock()
        obra.cf_rrhh_sip_rut = 'DVF'
        obra.cf_rrhh_sip_cc = 'DVFR120001DVF'
        ctx = SapSyncContext(candidato=candidato, obra=obra, colacion_movilizacion=80_000)

        payloads = build_pay_comp_payloads(ctx)
        components = {p['payComponent']: p['paycompvalue'] for p in payloads}
        self.assertEqual(components['1018'], 80_000)
        self.assertEqual(components['1029'], 80_000)
