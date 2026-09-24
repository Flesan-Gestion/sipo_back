from __future__ import annotations

import logging
import re

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from ..models_cargos_horarios import SipoEmpresaCargo, SipoHorario

logger = logging.getLogger(__name__)
SIPO_OBRA_DB = 'sip_db'
DW_CHILE_DB = 'dw_chile'

_TIME_RANGE_RE = re.compile(
    r'(\d{1,2}:\d{2})\s*(?:a|hasta|-|–)\s*(\d{1,2}:\d{2})',
    re.IGNORECASE,
)


def _norm_empresa(value: str | None) -> str:
    return (value or '').strip()


def _parse_horario_times(description: str | None) -> tuple[str, str]:
    text = (description or '').strip()
    match = _TIME_RANGE_RE.search(text)
    if not match:
        return '', ''
    return match.group(1), match.group(2)


def _horario_detalle_from_row(row: dict) -> dict:
    descripcion = (row.get('horario_trabajo') or '').strip()
    entrada, salida = _parse_horario_times(descripcion)
    return {
        'external_code': (row.get('external_code') or '').strip(),
        'descripcion': descripcion,
        'dias_trabajo': row.get('dias_trabajado_por_semana'),
        'hora_entrada': entrada,
        'hora_salida': salida,
        'tiempo_colacion': (row.get('horario_colacion') or '').strip() or None,
        'horas_semanales': row.get('horas_por_semana'),
        'detalle': descripcion,
    }


def _fetch_sap_horario_map(codes: list[str]) -> dict[str, dict]:
    codes = [c for c in {(_norm_empresa(c)) for c in codes} if c]
    if not codes:
        return {}
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT external_code, horario_trabajo, hora_por_dia,
                       dias_trabajado_por_semana, horario_colacion, horas_por_semana
                FROM sap_maestro_horarios_trabajo
                WHERE external_code = ANY(%s)
                """,
                [codes],
            )
            rows = cursor.fetchall()
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar detalles SAP de horarios: %s', exc)
        return {}

    result: dict[str, dict] = {}
    for code, descripcion, _hora_dia, dias, colacion, horas in rows:
        item = _horario_detalle_from_row(
            {
                'external_code': code,
                'horario_trabajo': descripcion,
                'dias_trabajado_por_semana': dias,
                'horario_colacion': colacion,
                'horas_por_semana': horas,
            }
        )
        if item['external_code']:
            result[item['external_code']] = item
    return result


def _empresas_from_maestros_sip() -> list[dict]:
    from .maestros import build_maestros_cascada

    return [
        {
            'id': (empresa.get('external_code') or '').strip(),
            'rut': (empresa.get('external_code') or '').strip(),
            'razon_social': (empresa.get('nombre') or '').strip(),
        }
        for empresa in build_maestros_cascada().get('empresas', [])
        if (empresa.get('external_code') or '').strip() and (empresa.get('nombre') or '').strip()
    ]


def _attach_empresa_counts(empresas: list[dict]) -> list[dict]:
    if not empresas:
        return []

    ruts = [e['rut'] for e in empresas]
    cargo_counts: dict[str, int] = {rut: 0 for rut in ruts}
    horario_counts: dict[str, int] = {rut: 0 for rut in ruts}

    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(ruts))
            cursor.execute(
                f"""
                SELECT TRIM(rut_empresa), COUNT(*)
                FROM cf_rrhh_sip_obra_cargos
                WHERE TRIM(rut_empresa) IN ({placeholders})
                GROUP BY TRIM(rut_empresa)
                """,
                ruts,
            )
            for rut, count in cursor.fetchall():
                cargo_counts[(rut or '').strip()] = int(count or 0)

            cursor.execute(
                f"""
                SELECT TRIM(rut_empresa), COUNT(*)
                FROM cf_rrhh_sip_obra_horario_trabajo
                WHERE TRIM(rut_empresa) IN ({placeholders})
                GROUP BY TRIM(rut_empresa)
                """,
                ruts,
            )
            for rut, count in cursor.fetchall():
                horario_counts[(rut or '').strip()] = int(count or 0)
    except (OperationalError, ProgrammingError) as exc:
        logger.warning('No se pudieron contar cargos/horarios por empresa: %s', exc)

    for empresa in empresas:
        rut = empresa['rut']
        empresa['cargos_asignados'] = cargo_counts.get(rut, 0)
        empresa['horarios_asignados'] = horario_counts.get(rut, 0)
    return empresas


def list_empresas_config() -> list[dict]:
    empresas: list[dict] = []
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    TRIM(external_code_empresa) AS rut,
                    TRIM(MAX(nombre_empresa)) AS razon_social
                FROM sap_maestro_empresa_dep_un_cc
                WHERE COALESCE(TRIM(external_code_empresa), '') <> ''
                  AND COALESCE(TRIM(nombre_empresa), '') <> ''
                GROUP BY TRIM(external_code_empresa)
                ORDER BY razon_social
                """
            )
            empresas = [
                {'id': rut, 'rut': rut, 'razon_social': razon}
                for rut, razon in cursor.fetchall()
                if rut and razon
            ]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar empresas config desde DW: %s', exc)

    if not empresas:
        empresas = _empresas_from_maestros_sip()

    return _attach_empresa_counts(empresas)


def list_cargos_catalogo_sap() -> list[dict]:
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT TRIM(c.external_code),
                       UPPER(TRIM(c.nombre_cargo)) AS nombre_cargo,
                       TRIM(c.external_code_area_personal),
                       TRIM(ap.nombre)
                FROM sap_maestro_cargos c
                LEFT JOIN sap_maestro_area_personal ap
                    ON TRIM(ap.external_code) = TRIM(c.external_code_area_personal)
                WHERE (c.planta_noplanta = 'NP' AND c.status = 'A')
                   OR c.external_code = '10000415'
                ORDER BY nombre_cargo
                """
            )
            return [
                {
                    'external_code': code,
                    'nombre': nombre,
                    'area_personal_code': area_code,
                    'area_personal': area_nombre or area_code,
                }
                for code, nombre, area_code, area_nombre in cursor.fetchall()
                if code and nombre
            ]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudo cargar catálogo SAP de cargos: %s', exc)
        return []


def list_cargos_empresa(empresa_id: str) -> list[dict]:
    rut = _norm_empresa(empresa_id)
    if not rut:
        raise ValidationError({'empresa_id': 'Empresa requerida.'})

    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT ec.id_cargo,
                       TRIM(ec.cargo),
                       TRIM(ec.external_code),
                       TRIM(ec.area_personal),
                       TRIM(c.status)
                FROM cf_rrhh_sip_obra_cargos ec
                LEFT JOIN cargos c ON TRIM(c.external_code) = TRIM(ec.external_code)
                WHERE TRIM(ec.rut_empresa) = %s
                ORDER BY ec.cargo
                """,
                [rut],
            )
            rows = cursor.fetchall()
    except (OperationalError, ProgrammingError) as exc:
        logger.exception('Error listando cargos empresa %s', rut)
        raise APIException('No se pudieron cargar los cargos.', status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

    return [
        {
            'id': id_cargo,
            'nombre': nombre,
            'external_code': external_code,
            'area_personal': area_personal,
            'estado': estado or 'A',
            'activo': True,
        }
        for id_cargo, nombre, external_code, area_personal, estado in rows
        if nombre
    ]


def assign_cargo_empresa(
    *,
    empresa_id: str,
    external_code: str,
    nombre: str | None = None,
    area_personal: str | None = None,
) -> dict:
    rut = _norm_empresa(empresa_id)
    code = _norm_empresa(external_code)
    if not rut or not code:
        raise ValidationError('empresa_id y external_code son obligatorios.')

    catalog = {item['external_code']: item for item in list_cargos_catalogo_sap()}
    catalog_item = catalog.get(code)
    cargo_nombre = (nombre or (catalog_item or {}).get('nombre') or '').strip()
    area = (area_personal or (catalog_item or {}).get('area_personal') or '').strip()
    if not cargo_nombre:
        raise ValidationError({'external_code': 'Cargo SAP no encontrado.'})

    exists = (
        SipoEmpresaCargo.objects.using(SIPO_OBRA_DB)
        .filter(rut_empresa=rut, external_code=code)
        .exists()
    )
    if not exists:
        exists = (
            SipoEmpresaCargo.objects.using(SIPO_OBRA_DB)
            .filter(rut_empresa=rut, cargo__iexact=cargo_nombre)
            .exists()
        )
    if exists:
        raise ValidationError('El cargo ya está asignado a la empresa.')

    row = SipoEmpresaCargo.objects.using(SIPO_OBRA_DB).create(
        rut_empresa=rut,
        cargo=cargo_nombre,
        external_code=code,
        area_personal=area,
    )
    return {
        'id': row.id_cargo,
        'nombre': row.cargo,
        'external_code': row.external_code,
        'area_personal': row.area_personal,
        'estado': 'A',
        'activo': True,
    }


def set_cargo_activo(*, empresa_id: str, cargo_id: int | None = None, nombre: str | None = None, activo: bool) -> None:
    rut = _norm_empresa(empresa_id)
    if not rut:
        raise ValidationError({'empresa_id': 'Empresa requerida.'})

    if activo:
        raise ValidationError('Para activar un cargo use POST /config/cargos/.')

    qs = SipoEmpresaCargo.objects.using(SIPO_OBRA_DB).filter(rut_empresa=rut)
    if cargo_id:
        qs = qs.filter(id_cargo=cargo_id)
    elif nombre:
        qs = qs.filter(cargo=nombre)
    else:
        raise ValidationError('Debe indicar id o nombre del cargo.')

    deleted, _ = qs.delete()
    if not deleted:
        raise ValidationError('Cargo no encontrado para la empresa.')


def list_horarios_catalogo_sap() -> list[dict]:
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT external_code, horario_trabajo, hora_por_dia,
                       dias_trabajado_por_semana, horario_colacion, horas_por_semana
                FROM sap_maestro_horarios_trabajo
                WHERE COALESCE(TRIM(horario_trabajo), '') <> ''
                  AND UPPER(horario_trabajo) NOT LIKE '%OBSOLETO%'
                  AND UPPER(horario_trabajo) NOT LIKE '%OBSOLETA%'
                ORDER BY horario_trabajo
                """
            )
            rows = cursor.fetchall()
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudo cargar catálogo SAP de horarios: %s', exc)
        return []

    items = []
    for code, descripcion, _hora_dia, dias, colacion, horas in rows:
        detail = _horario_detalle_from_row(
            {
                'external_code': code,
                'horario_trabajo': descripcion,
                'dias_trabajado_por_semana': dias,
                'horario_colacion': colacion,
                'horas_por_semana': horas,
            }
        )
        if detail['external_code']:
            items.append(detail)
    return items


def list_horarios_empresa(empresa_id: str) -> list[dict]:
    rut = _norm_empresa(empresa_id)
    if not rut:
        raise ValidationError({'empresa_id': 'Empresa requerida.'})

    rows = list(
        SipoHorario.objects.using(SIPO_OBRA_DB)
        .filter(rut_empresa=rut)
        .order_by('horario_trabajo')
        .values('rut_empresa', 'horario_trabajo', 'external_code')
    )
    codes = [(row.get('external_code') or '').strip() for row in rows]
    sap_map = _fetch_sap_horario_map(codes)

    items = []
    for row in rows:
        code = (row.get('external_code') or '').strip()
        base = sap_map.get(code) or _horario_detalle_from_row(
            {
                'external_code': code,
                'horario_trabajo': row.get('horario_trabajo'),
            }
        )
        items.append(
            {
                **base,
                'empresa_id': rut,
                'activo': True,
            }
        )
    return items


def assign_horario_empresa(*, empresa_id: str, external_code: str, descripcion: str | None = None) -> dict:
    rut = _norm_empresa(empresa_id)
    code = _norm_empresa(external_code)
    if not rut or not code:
        raise ValidationError('empresa_id y external_code son obligatorios.')

    sap_map = _fetch_sap_horario_map([code])
    descripcion_final = (
        (descripcion or '').strip()
        or (sap_map.get(code) or {}).get('descripcion')
        or code
    )

    exists = (
        SipoHorario.objects.using(SIPO_OBRA_DB)
        .filter(rut_empresa=rut, external_code=code)
        .exists()
    )
    if not exists:
        exists = (
            SipoHorario.objects.using(SIPO_OBRA_DB)
            .filter(rut_empresa=rut, horario_trabajo__iexact=descripcion_final)
            .exists()
        )
    if exists:
        raise ValidationError('El horario ya está asignado a la empresa.')

    SipoHorario.objects.using(SIPO_OBRA_DB).create(
        rut_empresa=rut,
        horario_trabajo=descripcion_final,
        external_code=code,
    )
    detail = sap_map.get(code) or _horario_detalle_from_row(
        {'external_code': code, 'horario_trabajo': descripcion_final}
    )
    return {**detail, 'empresa_id': rut, 'activo': True}


def delete_horario_empresa(*, empresa_id: str, external_code: str) -> None:
    rut = _norm_empresa(empresa_id)
    code = _norm_empresa(external_code)
    if not rut or not code:
        raise ValidationError('empresa_id y external_code son obligatorios.')

    deleted, _ = (
        SipoHorario.objects.using(SIPO_OBRA_DB)
        .filter(rut_empresa=rut, external_code=code)
        .delete()
    )
    if not deleted:
        raise ValidationError('Horario no encontrado para la empresa.')
