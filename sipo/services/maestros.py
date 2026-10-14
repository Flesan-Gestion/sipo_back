import logging

from django.db import connections
from django.db.models import Min
from django.db.utils import OperationalError, ProgrammingError

from ..models import SapMaestroEmpresaDepUnCc
from .pais_segregation import apply_external_code_pais_filter, normalize_pais

logger = logging.getLogger(__name__)
SIPO_OBRA_DB = 'sip_db'
DW_CHILE_DB = 'dw_chile'


def _base_maestro_qs(
    *,
    external_code_pais: str | None = None,
    empresa_rut: str | None = None,
):
    qs = (
        SapMaestroEmpresaDepUnCc.objects.using(SIPO_OBRA_DB)
        .filter(status_cc='A', status_departamento='A')
        .exclude(external_code_cc__startswith='FL')
    )
    qs = apply_external_code_pais_filter(qs, external_code_pais)
    rut = (empresa_rut or '').strip()
    if rut:
        qs = qs.filter(external_code_empresa=rut)
    return qs


def list_empresas_lite(external_code_pais: str | None = None) -> list[dict]:
    """Solo razones sociales (sin UN/Dep/CC). Para combos iniciales."""
    qs = _base_maestro_qs(external_code_pais=external_code_pais)
    rows = (
        qs.exclude(external_code_empresa__isnull=True)
        .exclude(external_code_empresa='')
        .values('external_code_empresa')
        .annotate(
            nombre=Min('nombre_empresa'),
            pais=Min('external_code_pais'),
        )
        .order_by('nombre', 'external_code_empresa')
    )
    items = []
    for row in rows:
        code = (row.get('external_code_empresa') or '').strip()
        if not code:
            continue
        items.append(
            {
                'id': code,
                'external_code': code,
                'nombre': (row.get('nombre') or '').strip(),
                'external_code_pais': normalize_pais(row.get('pais')),
                'unidades': [],
            }
        )
    return items


def build_maestros_cascada(
    external_code_pais: str | None = None,
    *,
    empresa_rut: str | None = None,
) -> dict:
    qs = _base_maestro_qs(
        external_code_pais=external_code_pais,
        empresa_rut=empresa_rut,
    )
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
    return [
        {
            'id': emp['external_code'],
            'external_code': emp['external_code'],
            'nombre': emp['nombre'],
            'external_code_pais': emp.get('external_code_pais'),
        }
        for emp in list_empresas_lite(external_code_pais=external_code_pais)
    ]


def list_centros_costo(
    *,
    external_code_pais: str | None = None,
    razon_social_id: str | None = None,
) -> list[dict]:
    rs = (razon_social_id or '').strip()
    if not rs:
        return []
    qs = _base_maestro_qs(
        external_code_pais=external_code_pais,
        empresa_rut=rs,
    )
    rows = qs.order_by('nombre_cc', 'external_code_cc').values(
        'external_code_empresa',
        'nombre_empresa',
        'external_code_un',
        'external_code_departamento',
        'external_code_cc',
        'nombre_cc',
        'external_code_pais',
    )
    items: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        cc_code = (row.get('external_code_cc') or '').strip()
        emp_code = (row.get('external_code_empresa') or '').strip()
        if not cc_code or not emp_code:
            continue
        key = f'{emp_code}|{cc_code}'
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                'id': cc_code,
                'external_code': cc_code,
                'nombre': (row.get('nombre_cc') or '').strip(),
                'external_code_pais': normalize_pais(row.get('external_code_pais')),
                'razon_social_id': emp_code,
                'razon_social_nombre': (row.get('nombre_empresa') or '').strip(),
                'unidad_id': (row.get('external_code_un') or '').strip(),
                'departamento_id': (row.get('external_code_departamento') or '').strip(),
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


def get_cargos_catalogo() -> list[dict]:
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT TRIM(cargo)
                FROM cf_rrhh_sip_obra_cargos
                WHERE COALESCE(TRIM(cargo), '') <> ''
                GROUP BY TRIM(cargo)
                ORDER BY TRIM(cargo)
                """
            )
            return [
                {'external_code': nombre, 'nombre': nombre}
                for (nombre,) in cursor.fetchall()
                if nombre
            ]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar cargos: %s', exc)
        return []


def get_ruts_empresa_con_cargo(cargo: str | None) -> list[str]:
    """RUTs de razón social que tienen el cargo (nombre o external_code)."""
    cargo_norm = (cargo or '').strip()
    if not cargo_norm:
        return []
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT TRIM(c.rut_empresa)
                FROM cf_rrhh_sip_obra_cargos c
                LEFT JOIN cargos sap ON sap.external_code = c.external_code
                WHERE COALESCE(TRIM(c.rut_empresa), '') <> ''
                  AND COALESCE(TRIM(c.cargo), '') <> ''
                  AND (sap.`status` = 'A' OR sap.`status` IS NULL)
                  AND (
                    UPPER(TRIM(c.cargo)) = UPPER(%s)
                    OR UPPER(TRIM(c.external_code)) = UPPER(%s)
                  )
                ORDER BY TRIM(c.rut_empresa)
                """,
                [cargo_norm, cargo_norm],
            )
            rows = [str(r[0]).strip() for r in cursor.fetchall() if r and r[0]]
            if rows:
                return rows
            cursor.execute(
                """
                SELECT DISTINCT TRIM(rut_empresa)
                FROM cf_rrhh_sip_obra_cargos
                WHERE COALESCE(TRIM(rut_empresa), '') <> ''
                  AND COALESCE(TRIM(cargo), '') <> ''
                  AND (
                    UPPER(TRIM(cargo)) = UPPER(%s)
                    OR UPPER(TRIM(external_code)) = UPPER(%s)
                  )
                ORDER BY TRIM(rut_empresa)
                """,
                [cargo_norm, cargo_norm],
            )
            return [str(r[0]).strip() for r in cursor.fetchall() if r and r[0]]
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar empresas por cargo: %s', exc)
        return []


def _ubicacion_display_name(code: str, nombre: str | None, ubicacion: str | None) -> str:
    """Prefiere texto descriptivo; si nombre == código, usa columna ubicacion."""
    code_n = (code or '').strip()
    nombre_n = (nombre or '').strip()
    ubic_n = (ubicacion or '').strip()
    if ubic_n and ubic_n != code_n and (
        not nombre_n or nombre_n == code_n or nombre_n.upper() == code_n.upper()
    ):
        return ubic_n
    if nombre_n:
        return nombre_n
    if ubic_n:
        return ubic_n
    return code_n


def get_ubicaciones_sap(rut: str | None = None) -> list[dict]:
    """Ubicaciones DW filtradas por empresa. Sin rut no consulta (evita full-scan)."""
    rut_norm = (rut or '').strip()
    if not rut_norm:
        return []
    try:
        with connections[DW_CHILE_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    TRIM(external_code),
                    TRIM(nombre),
                    TRIM(ubicacion)
                FROM sap_maestro_ubicacion
                WHERE TRIM(external_code_empresa) = %s
                  AND COALESCE(TRIM(external_code), '') <> ''
                  AND (
                    COALESCE(TRIM(nombre), '') <> ''
                    OR COALESCE(TRIM(ubicacion), '') <> ''
                  )
                ORDER BY 2, 1
                """,
                [rut_norm],
            )
            items = []
            seen: set[str] = set()
            for code, nombre, ubicacion in cursor.fetchall():
                code_n = (code or '').strip()
                if not code_n or code_n in seen:
                    continue
                seen.add(code_n)
                items.append(
                    {
                        'external_code': code_n,
                        'nombre': _ubicacion_display_name(code_n, nombre, ubicacion),
                    }
                )
            return items
    except (OperationalError, ProgrammingError, KeyError) as exc:
        logger.warning('No se pudieron cargar ubicaciones SAP desde DW: %s', exc)
        return []


def get_ubicaciones_fallback(rut: str | None = None) -> list[dict]:
    rut_norm = (rut or '').strip()
    if not rut_norm:
        return []
    try:
        with connections[SIPO_OBRA_DB].cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT TRIM(cf_rrhh_sip_ubicacion) AS ubicacion
                FROM cf_rrhh_sip_obra
                WHERE cf_rrhh_sip_ubicacion IS NOT NULL
                  AND TRIM(cf_rrhh_sip_ubicacion) <> ''
                  AND TRIM(cf_rrhh_sip_rut) = %s
                ORDER BY ubicacion
                """,
                [rut_norm],
            )
            return [
                {'external_code': row[0], 'nombre': row[0]}
                for row in cursor.fetchall()
                if row and row[0]
            ]
    except OperationalError:
        logger.exception('No se pudieron cargar ubicaciones fallback')
        return []


def get_ubicaciones(rut: str | None = None) -> list[dict]:
    rut_norm = (rut or '').strip()
    if not rut_norm:
        return []
    items = get_ubicaciones_sap(rut_norm)
    if items:
        return items
    return get_ubicaciones_fallback(rut_norm)


def get_sipo_maestros(
    rut: str | None = None,
    user=None,
    external_code_pais: str | None = None,
    *,
    full: bool = False,
    include_ubicaciones: bool = False,
) -> dict:
    """
    Cascada + cargos. Ubicaciones DW van aparte (lentas / timeout);
    usar get_ubicaciones(rut) o include_ubicaciones=True.
    """
    rut_norm = (rut or '').strip() or None
    if rut_norm:
        data = build_maestros_cascada(
            external_code_pais=external_code_pais,
            empresa_rut=rut_norm,
        )
        data['cargos'] = get_cargos_by_empresa(rut_norm)
        data['ubicaciones'] = get_ubicaciones(rut_norm) if include_ubicaciones else []
    elif full:
        data = build_maestros_cascada(external_code_pais=external_code_pais)
        data['ubicaciones'] = []
        data['cargos'] = []
    else:
        data = {
            'empresas': list_empresas_lite(external_code_pais=external_code_pais),
            'ubicaciones': [],
            'cargos': [],
        }
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
            if allowed_cc and (rut_norm or full):
                empresas = filter_centros_in_empresa_tree(empresas, allowed_cc)
            data['empresas'] = empresas
            if rut_norm and rut_norm not in set(scope.get('empresas_ids') or []):
                data['ubicaciones'] = []
                data['cargos'] = []

    return data
