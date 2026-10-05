"""Catálogos para modal candidato obra (paridad legado / DW flesan_rrhh)."""

from __future__ import annotations

import logging

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError

from sipo.services.maestros import get_cargos_catalogo
DW_CHILE_DB = 'dw_chile'

AFP_OPTIONS = (
    {'value': '001', 'label': 'AFP: Capital'},
    {'value': '002', 'label': 'AFP: Cuprum'},
    {'value': '003', 'label': 'AFP: Habitat'},
    {'value': '004', 'label': 'AFP: Plan Vital'},
    {'value': '005', 'label': 'AFP: Provida'},
    {'value': '006', 'label': 'AFP: Modelo'},
    {'value': '013', 'label': 'AFP: Uno'},
    {'value': '007', 'label': 'INP Canaempu'},
    {'value': '008', 'label': 'INP Empart'},
    {'value': '009', 'label': 'INP SSS'},
    {'value': '010', 'label': 'INP Capremer'},
    {'value': '011', 'label': 'INP Triomar'},
    {'value': '040', 'label': 'Sin AFP'},
)

SALUD_OPTIONS = (
    {'value': '005', 'label': 'FONASA'},
    {'value': '006', 'label': 'ISAPRE Banmedica'},
    {'value': '002', 'label': 'ISAPRE Bco. Estado'},
    {'value': '030', 'label': 'ISAPRE Codelco'},
    {'value': '004', 'label': 'ISAPRE Consalud'},
    {'value': '001', 'label': 'ISAPRE Colmena'},
    {'value': '008', 'label': 'ISAPRE Chuqicamata'},
    {'value': '003', 'label': 'ISAPRE Cruz Blanca'},
    {'value': '010', 'label': 'ISAPRE Cruz del Norte'},
    {'value': '031', 'label': 'ISAPRE Escencial'},
    {'value': '007', 'label': 'ISAPRE Mas vida'},
    {'value': '013', 'label': 'ISAPRE Nueva Mas Vida'},
    {'value': '012', 'label': 'ISAPRE Rio Blanco'},
    {'value': '009', 'label': 'ISAPRE San Lorenzo'},
    {'value': '011', 'label': 'ISAPRE Vidatres'},
    {'value': '014', 'label': 'Inst Salud previ Fusat Ltda'},
)

METODO_PAGO_OPTIONS = (
    {'value': '05', 'label': 'Transferencia Bancaria'},
    {'value': '06', 'label': 'Cheque'},
)

TIPO_CUENTA_OPTIONS = (
    {'value': 'Cuenta Corriente', 'label': 'Cuenta Corriente'},
    {'value': 'Cuenta Vista', 'label': 'Cuenta Vista'},
    {'value': 'Cuenta Rut', 'label': 'Cuenta Rut'},
)

TIPO_CONTRATO_OPTIONS = (
    {'value': 'Plazo Fijo', 'label': 'Plazo Fijo'},
    {'value': 'Obra o Faena', 'label': 'Obra o Faena'},
)

SI_NO_OPTIONS = (
    {'value': 'Si', 'label': 'Sí'},
    {'value': 'No', 'label': 'No'},
)

NACIONALIDAD_TIPO_OPTIONS = (
    {'value': 'Chile', 'label': 'Chilena'},
    {'value': 'Extranjero', 'label': 'Extranjero'},
    {'value': 'Extranjero-Definitiva', 'label': 'Extranjero - Definitiva'},
)

VALOR_PLAN_OPTIONS = (
    {'value': 'UF', 'label': 'UF'},
    {'value': 'Porcentaje 7%', 'label': 'Porcentaje 7%'},
)


def _query_dw(sql: str, params: list | None = None) -> list[tuple]:
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return list(cursor.fetchall())
    except (OperationalError, ProgrammingError, KeyError, IndexError) as exc:
        logger.warning('DW query failed: %s | %s', exc, sql[:120])
        return []


def get_bancos() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(external_code), UPPER(TRIM(nombre_banco))
        FROM sap_maestro_banco
        WHERE status = 'A'
          AND COALESCE(TRIM(external_code), '') <> ''
          AND COALESCE(TRIM(nombre_banco), '') <> ''
        ORDER BY nombre_banco
        """
    )
    return [{'value': code, 'label': nombre} for code, nombre in rows if code and nombre]


def get_horarios() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(external_code), TRIM(horario_trabajo)
        FROM sap_maestro_horarios_trabajo
        WHERE COALESCE(TRIM(external_code), '') <> ''
          AND COALESCE(TRIM(horario_trabajo), '') <> ''
          AND UPPER(horario_trabajo) NOT LIKE '%OBSOLETO%'
        ORDER BY horario_trabajo
        """
    )
    return [
        {'value': code, 'label': f'{nombre} ({code})', 'nombre': nombre}
        for code, nombre in rows
        if code and nombre
    ]


def get_cuentas_gasto() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(nombre_clasificacion_gasto)
        FROM sap_maestro_clasificacion_gasto
        WHERE status = 'ACTIVE'
          AND COALESCE(TRIM(nombre_clasificacion_gasto), '') <> ''
        ORDER BY nombre_clasificacion_gasto
        """
    )
    return [{'value': nombre, 'label': nombre} for (nombre,) in rows if nombre]


def get_estado_civil() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(external_code), TRIM(nombre)
        FROM sap_maestro_estado_civil
        WHERE status = 'ACTIVE'
          AND COALESCE(TRIM(nombre), '') <> ''
        ORDER BY nombre
        """
    )
    if rows:
        return [
            {'value': nombre, 'label': nombre, 'code': code or ''}
            for code, nombre in rows
            if nombre
        ]
    return [
        {'value': 'Soltero', 'label': 'Soltero/a'},
        {'value': 'Casado', 'label': 'Casado/a'},
        {'value': 'Divorciado', 'label': 'Divorciado/a'},
        {'value': 'Viudo', 'label': 'Viudo/a'},
        {'value': 'Conviviente Civil', 'label': 'Conviviente Civil'},
    ]


def get_paises_nacimiento() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(pais)
        FROM sap_maestro_pais_nacimiento
        WHERE COALESCE(TRIM(pais), '') <> ''
        ORDER BY pais
        """
    )
    return [{'value': pais, 'label': pais} for (pais,) in rows if pais]


def get_paises_region_nacimiento() -> list[dict]:
    """País → regiones (paridad pais_region_nacimiento / changepais legado)."""
    rows = _query_dw(
        """
        SELECT TRIM(pais), TRIM(region)
        FROM sap_maestro_pais_region_nacimiento
        WHERE COALESCE(TRIM(pais), '') <> ''
          AND COALESCE(TRIM(region), '') <> ''
        ORDER BY pais, region
        """
    )
    paises: dict[str, dict] = {}
    for pais, region in rows:
        entry = paises.setdefault(
            pais,
            {'value': pais, 'label': pais, 'regiones': []},
        )
        seen = {r['value'] for r in entry['regiones']}
        if region not in seen:
            entry['regiones'].append({'value': region, 'label': region})
    return sorted(paises.values(), key=lambda item: item['label'])


def get_regiones_nacimiento() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(region)
        FROM sap_maestro_region_nacimiento
        WHERE COALESCE(TRIM(region), '') <> ''
        ORDER BY region
        """
    )
    return [{'value': region, 'label': region} for (region,) in rows if region]


def get_nacionalidades() -> list[dict]:
    """Tipo nacionalidad SIPO (paridad legado: Chilena / Extranjero / Extranjero - Definitiva)."""
    return list(NACIONALIDAD_TIPO_OPTIONS)


def get_nacionalidades_extranjeras() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(pais)
        FROM sap_maestro_pais_nacionalidad
        WHERE COALESCE(TRIM(pais), '') <> ''
          AND UPPER(TRIM(pais)) <> 'CHILE'
        ORDER BY pais
        """
    )
    return [{'value': pais, 'label': pais} for (pais,) in rows if pais]


def get_regiones_ciudades_comunas() -> list[dict]:
    rows = _query_dw(
        """
        SELECT TRIM(region), TRIM(ciudad), TRIM(comuna)
        FROM sap_maestro_region_ciu_comu
        WHERE COALESCE(TRIM(region), '') <> ''
          AND COALESCE(TRIM(ciudad), '') <> ''
          AND COALESCE(TRIM(comuna), '') <> ''
        ORDER BY region, ciudad, comuna
        """
    )
    regiones: dict[str, dict] = {}
    for region, ciudad, comuna in rows:
        reg = regiones.setdefault(
            region,
            {'value': region, 'label': region, 'ciudades': {}},
        )
        ciu = reg['ciudades'].setdefault(
            ciudad,
            {'value': ciudad, 'label': ciudad, 'comunas': []},
        )
        if comuna not in ciu['comunas']:
            ciu['comunas'].append(comuna)

    result = []
    for reg in regiones.values():
        ciudades = []
        for ciu in reg['ciudades'].values():
            ciudades.append(
                {
                    'value': ciu['value'],
                    'label': ciu['label'],
                    'comunas': [
                        {'value': c, 'label': c} for c in ciu['comunas']
                    ],
                }
            )
        result.append(
            {
                'value': reg['value'],
                'label': reg['label'],
                'ciudades': ciudades,
            }
        )
    return result


def get_candidato_maestros() -> dict:
    return {
        'bancos': get_bancos(),
        'horarios': get_horarios(),
        'cuentas_gasto': get_cuentas_gasto(),
        'estados_civiles': get_estado_civil(),
        'paises_nacimiento': get_paises_nacimiento(),
        'paises_region_nacimiento': get_paises_region_nacimiento(),
        'regiones_nacimiento': get_regiones_nacimiento(),
        'nacionalidades': get_nacionalidades(),
        'nacionalidades_extranjeras': get_nacionalidades_extranjeras(),
        'regiones': get_regiones_ciudades_comunas(),
        'afps': list(AFP_OPTIONS),
        'sistemas_salud': list(SALUD_OPTIONS),
        'metodos_pago': list(METODO_PAGO_OPTIONS),
        'tipos_cuenta': list(TIPO_CUENTA_OPTIONS),
        'tipos_contrato': list(TIPO_CONTRATO_OPTIONS),
        'si_no': list(SI_NO_OPTIONS),
        'valores_plan': list(VALOR_PLAN_OPTIONS),
        'cargos': get_cargos_catalogo(),
    }
