import logging

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError

from ..models import SapMaestroEmpresaDepUnCc
from .pais_segregation import apply_external_code_pais_filter, normalize_pais

logger = logging.getLogger(__name__)
SIPO_OBRA_DB = 'sip_db'
DW_CHILE_DB = 'dw_chile'


def build_maestros_cascada(external_code_pais: str | None = None) -> dict:
    qs = (
        SapMaestroEmpresaDepUnCc.objects.using(SIPO_OBRA_DB)
        .filter(status_cc='A', status_departamento='A')
        .exclude(external_code_cc__startswith='FL')
    )
    qs = apply_external_code_pais_filter(qs, external_code_pais)
    rows = qs.order_by(
        'nombre_empresa', 'nombre_un', 'nombre_departamento', 'nombre_cc'
    ).values(
        'external_code_empresa',
        'nombre_empresa',
        'external_code_un',
        'nombre_un',
        'external_code_departamento',
        'nombre_departamento',
        'external_code_cc',
        'nombre_cc',
        'external_code_pais',
    )

    empresas_by_rut: dict[str, dict] = {}
    for row in rows:
        emp_code = (row['external_code_empresa'] or '').strip()
        un_code = (row['external_code_un'] or '').strip()
        dep_code = (row['external_code_departamento'] or '').strip()
        cc_code = (row['external_code_cc'] or '').strip()
        pais = normalize_pais(row.get('external_code_pais'))
        if not emp_code or not un_code or not dep_code:
            continue

        empresa = empresas_by_rut.setdefault(
            emp_code,
            {
                'external_code': emp_code,
                'nombre': (row['nombre_empresa'] or '').strip(),
                'external_code_pais': pais,
                'unidades': {},
            },
        )
        if not empresa.get('external_code_pais') and pais:
            empresa['external_code_pais'] = pais

        unidad = empresa['unidades'].setdefault(
            un_code,
            {
                'external_code': un_code,
                'nombre': (row['nombre_un'] or '').strip(),
                'departamentos': {},
            },
        )
        departamento = unidad['departamentos'].setdefault(
            dep_code,
            {
                'external_code': dep_code,
                'nombre': (row['nombre_departamento'] or '').strip(),
                'centros_costo': {},
            },
        )
        if cc_code:
            departamento['centros_costo'][cc_code] = {
                'external_code': cc_code,
                'nombre': (row['nombre_cc'] or '').strip(),
                'external_code_pais': pais,
            }

    empresas = []
    for empresa in empresas_by_rut.values():
        unidades = []
        for unidad in empresa['unidades'].values():
            departamentos = []
            for departamento in unidad['departamentos'].values():
                centros = sorted(
                    departamento['centros_costo'].values(),
                    key=lambda item: (item['nombre'] or '', item['external_code']),
                )
                departamentos.append(
                    {
                        'external_code': departamento['external_code'],
                        'nombre': departamento['nombre'],
                        'centros_costo': centros,
                    }
                )
            departamentos.sort(key=lambda item: (item['nombre'] or '', item['external_code']))
            unidades.append(
                {
                    'external_code': unidad['external_code'],
                    'nombre': unidad['nombre'],
                    'departamentos': departamentos,
                }
            )
        unidades.sort(key=lambda item: (item['nombre'] or '', item['external_code']))
        empresas.append(
            {
                'external_code': empresa['external_code'],
                'nombre': empresa['nombre'],
                'external_code_pais': empresa.get('external_code_pais'),
                'unidades': unidades,
            }
        )
    empresas.sort(key=lambda item: (item['nombre'] or '', item['external_code']))
    return {'empresas': empresas}


def list_razones_sociales(external_code_pais: str | None = None) -> list[dict]:
    cascada = build_maestros_cascada(external_code_pais=external_code_pais)
    return [
        {
            'id': emp['external_code'],
            'external_code': emp['external_code'],
            'nombre': emp['nombre'],
            'external_code_pais': emp.get('external_code_pais'),
        }
        for emp in cascada.get('empresas') or []
    ]


def list_centros_costo(
    *,
    external_code_pais: str | None = None,
    razon_social_id: str | None = None,
) -> list[dict]:
    cascada = build_maestros_cascada(external_code_pais=external_code_pais)
    rs = (razon_social_id or '').strip()
    items: list[dict] = []
    for emp in cascada.get('empresas') or []:
        if rs and emp['external_code'] != rs:
            continue
        for uni in emp.get('unidades') or []:
            for dep in uni.get('departamentos') or []:
                for cc in dep.get('centros_costo') or []:
                    items.append(
                        {
                            'id': cc['external_code'],
                            'external_code': cc['external_code'],
                            'nombre': cc['nombre'],
                            'external_code_pais': cc.get('external_code_pais')
                            or emp.get('external_code_pais'),
                            'razon_social_id': emp['external_code'],
                            'razon_social_nombre': emp['nombre'],
                            'unidad_id': uni['external_code'],
                            'departamento_id': dep['external_code'],
                        }
                    )
    items.sort(key=lambda item: (item['nombre'] or '', item['external_code']))
    return items


def get_cargos_by_empresa(rut: str | None) -> list[dict]:
    """Cargos de la razón social (paridad getListCargo legado)."""
    rut_norm = (rut or '').strip()
    if not rut_norm:
        return []
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    TRIM(c.external_code),
                    TRIM(c.cargo),
                    TRIM(c.area_personal)
                FROM cf_rrhh_sip_obra_cargos c
                LEFT JOIN cargos sap ON sap.external_code = c.external_code
                WHERE TRIM(c.rut_empresa) = %s
                  AND (sap.`status` = 'A' OR sap.`status` IS NULL)
                  AND COALESCE(TRIM(c.cargo), '') <> ''
                ORDER BY c.cargo
                """,
                [rut_norm],
            )
            rows = cursor.fetchall()
            if not rows:
                cursor.execute(
                    """
                    SELECT
                        TRIM(external_code),
                        TRIM(cargo),
                        TRIM(area_personal)
                    FROM cf_rrhh_sip_obra_cargos
                    WHERE TRIM(rut_empresa) = %s
                      AND COALESCE(TRIM(cargo), '') <> ''
                    ORDER BY cargo
                    """,
                    [rut_norm],
                )
                rows = cursor.fetchall()
            return [
                {
                    'external_code': (code or '').strip(),
                    'nombre': (nombre or '').strip(),
                    'area_personal': (area or '').strip(),
                }
                for code, nombre, area in rows
                if nombre
            ]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar cargos por empresa: %s', exc)
        return []


def get_ubicaciones_sap(rut: str | None = None) -> list[dict]:
    """Ubicaciones desde flesan_rrhh.sap_maestro_ubicacion (DW), filtradas por empresa."""
    rut_norm = (rut or '').strip()
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            if rut_norm:
                cursor.execute(
                    """
                    SELECT TRIM(external_code), TRIM(nombre)
                    FROM sap_maestro_ubicacion
                    WHERE COALESCE(TRIM(ubicacion), '') <> ''
                      AND TRIM(external_code_empresa) = %s
                      AND COALESCE(TRIM(external_code), '') <> ''
                      AND COALESCE(TRIM(nombre), '') <> ''
                    ORDER BY nombre
                    """,
                    [rut_norm],
                )
            else:
                cursor.execute(
                    """
                    SELECT TRIM(external_code), TRIM(nombre)
                    FROM sap_maestro_ubicacion
                    WHERE COALESCE(TRIM(ubicacion), '') <> ''
                      AND COALESCE(TRIM(external_code), '') <> ''
                      AND COALESCE(TRIM(nombre), '') <> ''
                    ORDER BY nombre
                    """
                )
            return [
                {'external_code': code, 'nombre': nombre}
                for code, nombre in cursor.fetchall()
                if code and nombre
            ]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar ubicaciones SAP desde DW: %s', exc)
        return []


def get_ubicaciones_fallback() -> list[dict]:
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT TRIM(cf_rrhh_sip_ubicacion) AS ubicacion
                FROM cf_rrhh_sip_obra
                WHERE cf_rrhh_sip_ubicacion IS NOT NULL
                  AND TRIM(cf_rrhh_sip_ubicacion) <> ''
                ORDER BY ubicacion
                """
            )
            return [{'external_code': row[0], 'nombre': row[0]} for row in cursor.fetchall()]
    except OperationalError:
        logger.exception('No se pudieron cargar ubicaciones fallback')
        return []


def get_ubicaciones(rut: str | None = None) -> list[dict]:
    items = get_ubicaciones_sap(rut)
    if items:
        return items
    if (rut or '').strip():
        return []
    return get_ubicaciones_fallback()


def get_sipo_maestros(
    rut: str | None = None,
    user=None,
    external_code_pais: str | None = None,
) -> dict:
    data = build_maestros_cascada(external_code_pais=external_code_pais)
    data['ubicaciones'] = get_ubicaciones(rut)
    data['cargos'] = get_cargos_by_empresa(rut)
    data['external_code_pais'] = normalize_pais(external_code_pais)

    if user is not None:
        from .usuario_scope import (
            filter_centros_in_empresa_tree,
            filter_empresas_by_scope,
            get_scope_for_user,
        )

        scope = get_scope_for_user(user)
        if not scope.get('is_admin'):
            empresas = filter_empresas_by_scope(data.get('empresas') or [], scope)
            allowed_cc = set(scope.get('centros_costo_ids') or [])
            if allowed_cc:
                empresas = filter_centros_in_empresa_tree(empresas, allowed_cc)
            data['empresas'] = empresas
            if rut and str(rut).strip() not in set(scope.get('empresas_ids') or []):
                data['ubicaciones'] = []
                data['cargos'] = []

    return data
