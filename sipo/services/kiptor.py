"""
Integración Kiptor — simulador sueldo base para candidatos obra (paridad legado).
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.db import connections

from ..constants import SIPO_CANDIDATO_ACTIVO, SIPO_CANDIDATO_SELECCIONADO
from ..models import SipoCandidatoObra, SipoObra

logger = logging.getLogger(__name__)

SIP_DB = 'sip_db'
DW_CHILE_DB = 'dw_chile'

# Sueldo base imponible razonable vs líquido (paridad tolerancia legado)
KIPTOR_SUELDO_BASE_MAX_RATIO = 5.0
KIPTOR_SUELDO_BASE_MIN_RATIO = 0.5

AFP_KIPTOR_MAP = {
    '001': 1,
    '002': 2,
    '003': 3,
    '004': 4,
    '005': 5,
    '006': 6,
    '013': 20,
    '007': 14,
    '008': 14,
    '009': 14,
    '010': 14,
    '011': 14,
    '012': 14,
}

ESCALA_COL_MOV_SQL = """
SELECT ROUND(movilizacion) AS col_mov
FROM escala
WHERE liquido <= %s
ORDER BY liquido DESC
LIMIT 1
"""

UF_UTM_SQL = """
WITH jb_base AS (
    SELECT max(fecha) AS fecha
    FROM flesan_procesos.api_uf_utm
    WHERE to_char(fecha, 'YYYY-MM') = to_char(current_date, 'YYYY-MM')
)
SELECT
    replace(replace(api_uf_utm.valor_uf, '.', ''), ',', '.')::double precision AS valor_uf,
    replace(api_uf_utm.valor_utm, '.', '')::integer AS valor_utm
FROM flesan_procesos.api_uf_utm
JOIN jb_base ON api_uf_utm.fecha = jb_base.fecha
ORDER BY api_uf_utm.fecha
LIMIT 1
"""


class KiptorService:
    """Calcula sueldo base vía Kiptor y persiste cf_rrhh_sip_obra_sueldo_base."""

    def __init__(self) -> None:
        self.enabled = bool(getattr(settings, 'KIPTOR_ENABLED', False))
        self.timeout = int(getattr(settings, 'KIPTOR_REQUEST_TIMEOUT', 30))
        self.auth_url = getattr(settings, 'KIPTOR_AUTH_URL', 'https://node.kiptor.com/autenticar')
        self.sim_url = getattr(
            settings,
            'KIPTOR_SIMULADOR_URL',
            'https://node.kiptor.com/simuladorSueldo',
        )
        self.user = getattr(settings, 'KIPTOR_USER', 'flesan-kiptor')
        self.password = getattr(settings, 'KIPTOR_PASSWORD', '')
        self._token: str | None = None
        self._uf_utm: tuple[float, int] | None = None

    @staticmethod
    def parse_clp_amount(value, *, field: str = 'monto') -> int:
        """
        Parsea montos CLP desde string Kiptor/BD.
        Soporta: 586000, "586.000" (miles CL), "552437.00" (decimal), enteros JSON.
        """
        if value is None or value == '':
            return 0
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(round(value)))
        if isinstance(value, Decimal):
            return max(0, int(value))

        raw = str(value).strip()
        if not raw:
            return 0

        # Decimal US/ISO: 552437.00 (un solo punto, 1-2 decimales al final)
        if re.fullmatch(r'\d+\.\d{1,2}', raw):
            return max(0, int(round(float(raw))))

        # Formato chileno miles: 586.000 o 1.234.567
        if re.fullmatch(r'\d{1,3}(\.\d{3})+', raw):
            return max(0, int(raw.replace('.', '')))

        # Chileno con decimales: 586.000,50
        if re.fullmatch(r'\d{1,3}(\.\d{3})*,\d+', raw):
            entero = raw.split(',')[0].replace('.', '')
            return max(0, int(entero))

        if re.fullmatch(r'\d+', raw):
            return max(0, int(raw))

        # Último recurso: solo dígitos (evitar si hay punto decimal US)
        if '.' in raw and ',' not in raw:
            try:
                return max(0, int(round(float(raw.replace(',', '.')))))
            except ValueError:
                pass

        digits = re.sub(r'[^\d]', '', raw)
        if digits:
            logger.warning('Kiptor parse_clp_amount fallback digits field=%s raw=%r', field, raw)
            return int(digits)
        return 0

    @staticmethod
    def parse_liquido_digits(value) -> int:
        """Réplica legado: replace(sueldo,'.','') → entero CLP."""
        return KiptorService.parse_clp_amount(value, field='liquido')

    @staticmethod
    def parse_sueldo_base_response(value, *, liquido: int) -> int:
        """Parsea sueldobase Kiptor con validación de cordura vs líquido."""
        parsed = KiptorService.parse_clp_amount(value, field='sueldobase')
        if parsed <= 0:
            raise ValueError(f'Kiptor sueldobase inválido: {value!r}')

        if liquido > 0:
            ratio = parsed / liquido
            if ratio > KIPTOR_SUELDO_BASE_MAX_RATIO or ratio < KIPTOR_SUELDO_BASE_MIN_RATIO:
                # Reintento: a veces viene como float string mal interpretado
                if isinstance(value, str) and re.fullmatch(r'\d+\.\d{1,2}', value.strip()):
                    retry = int(round(float(value.strip())))
                    retry_ratio = retry / liquido
                    if KIPTOR_SUELDO_BASE_MIN_RATIO <= retry_ratio <= KIPTOR_SUELDO_BASE_MAX_RATIO:
                        logger.warning(
                            'Kiptor sueldobase corregido raw=%r parsed=%s retry=%s liquido=%s',
                            value,
                            parsed,
                            retry,
                            liquido,
                        )
                        return retry
                raise ValueError(
                    f'Kiptor sueldobase fuera de rango: {parsed} vs líquido {liquido} (ratio={ratio:.2f})'
                )
        return parsed

    @staticmethod
    def get_col_mov(liquido: int, centro_costo: str | None = None) -> int:
        from .candidato_validaciones import resolve_colacion_movilizacion

        return resolve_colacion_movilizacion(
            sueldo_liquido=liquido,
            centro_costo=centro_costo,
        )

    @staticmethod
    def get_uf_utm() -> tuple[float, int]:
        try:
            with connections[DW_CHILE_DB].cursor() as cursor:
                cursor.execute(UF_UTM_SQL)
                row = cursor.fetchone()
            if row:
                return float(row[0] or 0), int(row[1] or 0)
        except Exception as exc:
            logger.warning('No se pudieron obtener UF/UTM para Kiptor: %s', exc)
        return 0.0, 0

    @staticmethod
    def _resolve_afp_code(candidato: SipoCandidatoObra) -> int:
        raw = str(candidato.cf_rrhh_sip_obra_candidato_nom_afp or '').strip()
        return AFP_KIPTOR_MAP.get(raw, 5)

    @staticmethod
    def _resolve_salud(candidato: SipoCandidatoObra) -> tuple[str, str]:
        nom_salud = str(candidato.cf_rrhh_sip_obra_candidato_nom_salud or '').strip()
        valor_uf_raw = str(candidato.cf_rrhh_sip_obra_candidato_valor_uf or '').strip()
        valor_uf_num = 0.0
        if valor_uf_raw:
            try:
                valor_uf_num = float(valor_uf_raw.replace(',', '.'))
            except ValueError:
                valor_uf_num = 0.0

        if nom_salud == '005' or (nom_salud != '005' and valor_uf_num <= 0):
            return 'fonasa', '0'
        return 'isapre', valor_uf_raw.replace(',', '.')

    def clear_token_cache(self) -> None:
        self._token = None
        self._uf_utm = None

    def ensure_token(self) -> str:
        if self._token:
            return self._token
        response = requests.post(
            self.auth_url,
            json={'usuario': self.user, 'contrasena': self.password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = (payload.get('token') or '').strip()
        if not token:
            raise ValueError('Kiptor auth response without token')
        self._token = token
        return token

    def autenticar(self) -> str:
        return self.ensure_token()

    def _get_uf_utm_cached(self) -> tuple[float, int]:
        if self._uf_utm is None:
            self._uf_utm = self.get_uf_utm()
        return self._uf_utm

    def _simulate_sueldo_base(
        self,
        *,
        liquido: int,
        col_mov: int,
        afp: int,
        salud: str,
        isapre_uf: str,
        valor_uf: float,
        valor_utm: int,
        token: str,
    ) -> int:
        body = {
            'tipoSimulador': 'sueldoBase',
            'sueldo': str(liquido),
            'gratificacion': '1',
            'comision': '0',
            'colacion': str(col_mov),
            'movilizacion': str(col_mov),
            'bono': '0',
            'horas_extras': '0',
            'salud': salud,
            'isapre_uf': isapre_uf,
            'tipo_contrato': 'plazo_indefinido',
            'afp': str(afp),
            'apv': '0',
            'otros_descuentos': '0',
            'uf': str(valor_uf),
            'utm': str(valor_utm),
        }
        response = requests.request(
            'GET',
            self.sim_url,
            data=json.dumps(body),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        logger.info(
            'Kiptor simulador request liquido=%s body=%s response=%s',
            liquido,
            body,
            payload,
        )
        result = payload.get('result') or {}
        sueldo_base_raw = result.get('sueldobase')
        if sueldo_base_raw is None:
            raise ValueError('Kiptor simulator response without sueldobase')
        return self.parse_sueldo_base_response(sueldo_base_raw, liquido=liquido)

    def calcular_sueldo_base(
        self,
        candidato: SipoCandidatoObra,
        *,
        centro_costo: str | None = None,
    ) -> int:
        liquido = self.parse_liquido_digits(candidato.cf_rrhh_sip_obra_candidato_sueldo)
        if liquido <= 0:
            raise ValueError('Candidato sin sueldo líquido válido')

        col_mov = self.get_col_mov(liquido, centro_costo=centro_costo)
        afp = self._resolve_afp_code(candidato)
        salud, isapre_uf = self._resolve_salud(candidato)
        valor_uf, valor_utm = self._get_uf_utm_cached()

        if not self.enabled:
            raise RuntimeError('Kiptor deshabilitado (KIPTOR_ENABLED=False)')

        token = self.ensure_token()
        return self._simulate_sueldo_base(
            liquido=liquido,
            col_mov=col_mov,
            afp=afp,
            salud=salud,
            isapre_uf=isapre_uf,
            valor_uf=valor_uf,
            valor_utm=valor_utm,
            token=token,
        )

    @staticmethod
    def persist_sueldo_base(candidato: SipoCandidatoObra, sueldo_base: int | Decimal) -> None:
        entero = int(sueldo_base)
        candidato.cf_rrhh_sip_obra_sueldo_base = Decimal(entero)
        candidato.save(
            using=SIP_DB,
            update_fields=['cf_rrhh_sip_obra_sueldo_base'],
        )

    def calcular_y_persistir_sueldo_base(
        self,
        candidato: SipoCandidatoObra,
        *,
        centro_costo: str | None = None,
    ) -> dict[str, Any]:
        liquido = self.parse_liquido_digits(candidato.cf_rrhh_sip_obra_candidato_sueldo)
        col_mov = self.get_col_mov(liquido, centro_costo=centro_costo)
        fallback = liquido if liquido > 0 else 0
        sueldo_base = fallback
        kiptor_ok = False
        error: str | None = None

        try:
            sueldo_base = self.calcular_sueldo_base(candidato, centro_costo=centro_costo)
            kiptor_ok = True
        except Exception as exc:
            error = str(exc)
            logger.error(
                'Kiptor failed candidato=%s obra=%s liquido=%s: %s — fallback liquido',
                candidato.cf_rrhh_sip_obra_candidato_id,
                candidato.cf_rrhh_sip_obra_id,
                liquido,
                exc,
                exc_info=True,
            )

        if sueldo_base > 0:
            self.persist_sueldo_base(candidato, sueldo_base)

        return {
            'candidato_id': candidato.cf_rrhh_sip_obra_candidato_id,
            'liquido': liquido,
            'col_mov': col_mov,
            'sueldo_base': int(sueldo_base) if sueldo_base else None,
            'kiptor_ok': kiptor_ok,
            'fallback_liquido': not kiptor_ok,
            'error': error,
        }


def calcular_sueldos_kiptor_obra(*, sip_id: int) -> list[dict[str, Any]]:
    """Calcula sueldo base Kiptor para candidatos seleccionados de una obra."""
    candidatos = list(
        SipoCandidatoObra.objects.using(SIP_DB)
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado=SIPO_CANDIDATO_SELECCIONADO,
        )
    )
    if not candidatos:
        return []

    obra = SipoObra.objects.using(SIP_DB).filter(cf_rrhh_sip_id=sip_id).first()
    centro_costo = (obra.cf_rrhh_sip_cc if obra else None) or None

    service = KiptorService()
    if service.enabled:
        try:
            service.ensure_token()
            service._get_uf_utm_cached()
        except Exception as exc:
            logger.warning('Kiptor pre-auth batch sip_id=%s: %s', sip_id, exc)
    return [
        service.calcular_y_persistir_sueldo_base(c, centro_costo=centro_costo)
        for c in candidatos
    ]
