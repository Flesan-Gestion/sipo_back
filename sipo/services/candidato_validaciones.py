"""Validaciones de negocio candidato obra (paridad legado PHP)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from rest_framework.exceptions import ValidationError

SUELDO_MINIMO_ESTANDAR = 581_000

# external_code horario → (umbral_validacion, mensaje_piso)
SUELDO_PISO_POR_HORARIO = {
    'PHT00017': (405_000, 376_606),
    'PHT00019': (405_000, 376_606),
    'PHT00021': (302_000, 263_704),
    'PTH00134': (253_000, 280_000),
    'PHT00068': (278_000, 280_000),
    'PTH00136': (341_000, 280_000),
    'PHT00136': (341_000, 280_000),
    'PHT00027': (266_000, 280_000),
    'PHT00036': (341_000, 293_005),
    'PHT00051': (253_000, 210_963),
    'PTH00135': (253_000, 210_963),
}

CARGOS_EXENTOS_SUELDO_MINIMO = (
    'ALUMNO EN PRACTICA',
    'PRACTICA PROFESIONAL',
)

FONASA_SIN_PLAN = frozenset({'005', '014', '015'})

ADDRESS_PIPE_FIELDS = (
    'cf_rrhh_sip_obra_candidato_direccion',
    'cf_rrhh_sip_obra_candidato_numero_dire',
    'cf_rrhh_sip_obra_candidato_num_depto',
    'cf_rrhh_sip_obra_candidato_villa',
)


def clean_address_field(value) -> str:
    """Elimina delimitadores pipe legado y espacios sobrantes."""
    if value is None:
        return ''
    text = str(value).strip()
    if not text or text == '|':
        return ''
    return text.strip('|').strip()


def parse_numero_depto_fields(numero_raw, depto_raw) -> tuple[str, str]:
    """
    Separa número y depto cuando vienen concatenados con ``|`` (réplica legado/SAP).
    Ej.: ``348|`` + ``|`` → (``348``, ````); ``348|12`` → (``348``, ``12``).
    """
    depto = clean_address_field(depto_raw)
    raw_num = str(numero_raw or '').strip()
    if '|' in raw_num:
        parts = [p.strip() for p in raw_num.split('|') if p.strip()]
        numero = parts[0] if parts else ''
        if len(parts) > 1 and not depto:
            depto = parts[1]
        return numero, depto
    return clean_address_field(numero_raw), depto


def sanitize_address_data(data: dict) -> dict:
    """Normaliza campos de dirección en lectura/escritura."""
    if not data:
        return data
    numero, depto = parse_numero_depto_fields(
        data.get('cf_rrhh_sip_obra_candidato_numero_dire'),
        data.get('cf_rrhh_sip_obra_candidato_num_depto'),
    )
    data['cf_rrhh_sip_obra_candidato_numero_dire'] = numero or None
    data['cf_rrhh_sip_obra_candidato_num_depto'] = depto or None
    for field in ('cf_rrhh_sip_obra_candidato_direccion', 'cf_rrhh_sip_obra_candidato_villa'):
        if field in data:
            cleaned = clean_address_field(data.get(field))
            data[field] = cleaned or None
    return data


def rut_key(value: str) -> str:
    return normalize_rut(value).replace('.', '').replace('-', '').upper()


def is_rut_bloqueado(rut: str) -> bool:
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    target = rut_key(rut)
    if not target:
        return False
    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(
                'SELECT rut FROM cf_rrhh_sip_obra_bloquedos '
                'WHERE COALESCE(TRIM(rut), \'\') <> \'\''
            )
            rows = cursor.fetchall()
    except (OperationalError, ProgrammingError, KeyError):
        return False
    return any(rut_key(str(raw or '')) == target for (raw,) in rows)


def requires_valor_plan(salud_code: str | None) -> bool:
    code = (salud_code or '').strip()
    return bool(code) and code not in FONASA_SIN_PLAN


def parse_sueldo(value) -> int:
    if value is None:
        return 0
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def normalize_rut(value: str) -> str:
    cleaned = (
        (value or '')
        .strip()
        .upper()
        .replace('.', '')
        .replace('-', '')
        .replace(' ', '')
    )
    if len(cleaned) < 2:
        return ''
    body, dv = cleaned[:-1], cleaned[-1]
    if len(body) == 8 and body.startswith('0'):
        body = body[1:]
    return f'{body}-{dv}'


def format_rut_sap_pad(value: str) -> str:
    """
    RUT compatible PerNationalId SAP: cuerpo a 8 dígitos con cero a la izquierda.
    """
    cleaned = (
        (value or '')
        .strip()
        .upper()
        .replace('.', '')
        .replace('-', '')
        .replace(' ', '')
    )
    if len(cleaned) < 2:
        return ''
    body, dv = cleaned[:-1], cleaned[-1]
    digits = ''.join(ch for ch in body if ch.isdigit())
    digits = digits.lstrip('0') or '0'
    body = digits.zfill(8)
    return f'{body}-{dv}'


def format_rut_sap_national_id(value: str) -> str:
    """
    RUT PerNationalId exigido por SF CHL: XX.XXX.XXX-Z (cuerpo 8 dígitos).
    Ej: 9.676.775-7 → 09.676.775-7
    """
    padded = format_rut_sap_pad(value)
    if not padded or '-' not in padded:
        return padded
    body, dv = padded.split('-', 1)
    if body.isdigit() and len(body) == 8:
        return f'{body[0:2]}.{body[2:5]}.{body[5:8]}-{dv}'
    if body.isdigit() and len(body) == 7:
        return f'{body[0]}.{body[1:4]}.{body[4:7]}-{dv}'
    return padded


def format_rut_display(value: str) -> str:
    rut = normalize_rut(value)
    if not rut or '-' not in rut:
        return value or ''
    body, dv = rut.split('-', 1)
    body_fmt = f'{int(body):,}'.replace(',', '.') if body.isdigit() else body
    return f'{body_fmt}-{dv}'


def is_valid_rut(value: str) -> bool:
    rut = normalize_rut(value)
    if not rut or '-' not in rut:
        return False
    body, dv = rut.split('-', 1)
    if len(body) < 7 or not body.isdigit():
        return False
    suma = 0
    multiplo = 2
    for i in range(1, len(body) + 1):
        suma += multiplo * int(body[-i])
        multiplo = multiplo + 1 if multiplo < 7 else 2
    expected = 11 - (suma % 11)
    dv_num = 10 if dv == 'K' else (11 if dv == '0' else int(dv) if dv.isdigit() else -1)
    return expected == dv_num


def parse_date(value) -> Optional[date]:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def age_at(birth: date, ref: date) -> int:
    years = ref.year - birth.year
    if (ref.month, ref.day) < (birth.month, birth.day):
        years -= 1
    return years


CFM_RUT = 'CFM'


def is_chivato_huechun_cc(centro_costo: str | None) -> bool:
    from sipo.constants import CC_CHIVATO_HUECHUN

    return (centro_costo or '').strip().upper() == CC_CHIVATO_HUECHUN


def resolve_colacion_movilizacion(
    *,
    sueldo_liquido: int,
    centro_costo: str | None = None,
) -> int:
    """
    Monto colación/movilización (mismo valor para ambos, paridad legado).
    Regla Chivato Huechún (CFMCFM130048): fuerza $1.
    """
    from sipo.constants import COL_MOV_CHIVATO_HUECHUN

    if is_chivato_huechun_cc(centro_costo):
        return COL_MOV_CHIVATO_HUECHUN

    liquido = int(sueldo_liquido or 0)
    if liquido == 250_000:
        return 125_000
    if liquido <= 0:
        return 0

    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(
                """
                SELECT ROUND(movilizacion)
                FROM escala
                WHERE liquido <= %s
                ORDER BY liquido DESC
                LIMIT 1
                """,
                [liquido],
            )
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError, KeyError):
        return 0
    if not row or row[0] is None:
        return 0
    return int(row[0])


def match_estandarizacion(cargo: str | None, ubicacion: str | None) -> bool:
    """True si cargo+ubicación existe en estandarizacion_renta_cfm (paridad legado)."""
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    nombre_cargo = (cargo or '').strip()
    ubic = (ubicacion or '').strip()
    if not nombre_cargo or not ubic:
        return False
    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM estandarizacion_renta_cfm er
                INNER JOIN cargos c
                    ON c.external_code = er.cargo AND c.status = 'A'
                WHERE UPPER(TRIM(c.nombre_cargo)) = UPPER(TRIM(%s))
                  AND TRIM(er.ubicacion) = TRIM(%s)
                LIMIT 1
                """,
                [nombre_cargo, ubic],
            )
            return cursor.fetchone() is not None
    except (OperationalError, ProgrammingError):
        return False


def is_cfm_obra(obra_rut: str | None) -> bool:
    return (obra_rut or '').strip().upper() == CFM_RUT


def _afp_tasa(nom_afp: str | None) -> float:
    tasas = {
        '001': 0.1144, '002': 0.1144, '003': 0.1127, '004': 0.1116,
        '005': 0.1145, '006': 0.1058, '013': 0.1049, '007': 0.1884,
        '008': 0.2262, '009': 0.1880, '010': 0.1884, '011': 0.1884,
    }
    return tasas.get((nom_afp or '').strip(), 0.1144)


def _calcular_impuesto_sii(base: float, utm: float) -> float:
    if utm <= 0 or base <= 0:
        return 0.0
    base_utm = base / utm
    if base_utm <= 13.5:
        return 0.0
    if base_utm <= 30:
        return (base * 0.04) - (0.54 * utm)
    if base_utm <= 50:
        return (base * 0.08) - (1.74 * utm)
    if base_utm <= 70:
        return (base * 0.135) - (4.49 * utm)
    if base_utm <= 90:
        return (base * 0.23) - (11.14 * utm)
    if base_utm <= 120:
        return (base * 0.304) - (17.8 * utm)
    if base_utm <= 150:
        return (base * 0.35) - (23.32 * utm)
    return (base * 0.40) - (30.82 * utm)


def _load_bono_pie_cfm(*, cargo: str, ubicacion: str) -> tuple[float, float]:
    """Retorna (sueldo_base_tabla, bono_pie) desde estandarizacion_renta_cfm."""
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(
                """
                SELECT base.monto, est.monto + bono.monto
                FROM estandarizacion_renta_cfm est
                INNER JOIN cargos c
                    ON c.external_code = est.cargo AND c.status = 'A'
                LEFT JOIN estandarizacion_renta_cfm base
                    ON base.cc_nomina = 'M020' AND base.cargo = est.cargo
                LEFT JOIN estandarizacion_renta_cfm bono
                    ON bono.cc_nomina = '1100' AND bono.cargo = est.cargo
                WHERE UPPER(TRIM(c.nombre_cargo)) = UPPER(TRIM(%s))
                  AND TRIM(est.ubicacion) = TRIM(%s)
                  AND est.cargo IS NOT NULL
                LIMIT 1
                """,
                [cargo, ubicacion],
            )
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError):
        return 0.0, 0.0
    if not row or row[0] is None:
        return 0.0, 0.0
    return float(row[0] or 0), float(row[1] or 0)


def _load_uf_utm() -> tuple[float, float]:
    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    try:
        with connections['dw_chile'].cursor() as cursor:
            cursor.execute(
                """
                WITH jb AS (
                    SELECT MAX(fecha) AS fecha
                    FROM api_uf_utm
                    WHERE TO_CHAR(fecha, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
                )
                SELECT
                    REPLACE(REPLACE(valor_uf, '.', ''), ',', '.')::DOUBLE PRECISION,
                    REPLACE(valor_utm, '.', '')::INTEGER
                FROM api_uf_utm
                JOIN jb ON api_uf_utm.fecha = jb.fecha
                ORDER BY api_uf_utm.fecha DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
    except (OperationalError, ProgrammingError, KeyError):
        return 0.0, 0.0
    if not row:
        return 0.0, 0.0
    return float(row[0] or 0), float(row[1] or 0)


def calcular_bono_mineria_cfm(
    *,
    liquido_objetivo: float,
    sueldo_base_tabla: float,
    bono_pie: float,
    tasa_afp: float,
    valor_uf: float,
    valor_utm: float,
) -> int:
    """Réplica simplificada del bucle legado sendNotificacionRechazoProceso2 (CFM)."""
    if liquido_objetivo <= 0 or sueldo_base_tabla <= 0 or bono_pie <= 0:
        return 0

    movilizacion = 50_000.0
    colacion = 50_000.0
    tasa_salud = 0.07
    tasa_cesantia = 0.0
    imm = 539_000.0
    tope_gratificacion_mensual = (imm * 4.75) / 12
    tope_imponible_afp = 90 * valor_uf if valor_uf > 0 else float('inf')
    tope_imponible_cesantia = 135.2 * valor_uf if valor_uf > 0 else float('inf')

    sueldo_base = sueldo_base_tabla
    bono_total = bono_pie
    liquido_actual = 0.0
    guard = 0

    while liquido_actual < liquido_objetivo and guard < 50_000:
        guard += 1
        imponible_sin_grat = sueldo_base + bono_total
        gratificacion = min(imponible_sin_grat * 0.25, tope_gratificacion_mensual)
        total_imponible = sueldo_base + bono_total + gratificacion

        base_previsional = min(total_imponible, tope_imponible_afp)
        base_cesantia = min(total_imponible, tope_imponible_cesantia)

        desc_afp = base_previsional * tasa_afp
        desc_salud = base_previsional * tasa_salud
        desc_cesantia = base_cesantia * tasa_cesantia

        base_impuesto = total_imponible - desc_afp - desc_salud - desc_cesantia
        impuesto = max(0.0, _calcular_impuesto_sii(base_impuesto, valor_utm))
        liquido_actual = base_impuesto - impuesto + movilizacion + colacion

        if liquido_actual < liquido_objetivo:
            dif = liquido_objetivo - liquido_actual
            bono_total += 500 if dif > 1000 else 1

    bono_final = round(bono_total)
    return max(0, int(round(bono_final - bono_pie)))


def calcular_y_persistir_bono_mineria_cfm(candidato, obra) -> int | None:
    """Calcula cf_rrhh_sip_obra_bono_mineria para candidatos CFM con estandarización."""
    from ..models import SipoCandidatoObra

    if not is_cfm_obra(getattr(obra, 'cf_rrhh_sip_rut', None)):
        return None

    cargo = (candidato.cf_rrhh_sip_obra_candidato_nomcar or '').strip()
    ubicacion = (getattr(obra, 'cf_rrhh_sip_ubicacion', None) or '').strip()
    if not match_estandarizacion(cargo, ubicacion):
        return None

    sueldo_base_tabla, bono_pie = _load_bono_pie_cfm(cargo=cargo, ubicacion=ubicacion)
    if bono_pie <= 0:
        return None

    liquido = float(parse_sueldo(candidato.cf_rrhh_sip_obra_candidato_sueldo))
    valor_uf, valor_utm = _load_uf_utm()
    bono = calcular_bono_mineria_cfm(
        liquido_objetivo=liquido,
        sueldo_base_tabla=sueldo_base_tabla,
        bono_pie=bono_pie,
        tasa_afp=_afp_tasa(candidato.cf_rrhh_sip_obra_candidato_nom_afp),
        valor_uf=valor_uf,
        valor_utm=float(valor_utm),
    )

    SipoCandidatoObra.objects.using('sip_db').filter(
        cf_rrhh_sip_obra_candidato_id=candidato.cf_rrhh_sip_obra_candidato_id,
    ).update(cf_rrhh_sip_obra_bono_mineria=bono)
    candidato.cf_rrhh_sip_obra_bono_mineria = bono
    return bono


def calcular_bonos_mineria_obra(*, sip_id: int, obra) -> list[dict]:
    from ..constants import SIPO_CANDIDATO_ACTIVO, SIPO_CANDIDATO_SELECCIONADO
    from ..models import SipoCandidatoObra

    candidatos = list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado=SIPO_CANDIDATO_SELECCIONADO,
        )
    )
    resultados = []
    for candidato in candidatos:
        bono = calcular_y_persistir_bono_mineria_cfm(candidato, obra)
        resultados.append({
            'candidato_id': candidato.cf_rrhh_sip_obra_candidato_id,
            'bono_mineria': bono,
        })
    return resultados


def resolve_sueldo_minimo(
    *,
    sueldo,
    cargo: str | None,
    horario: str | None,
    ubicacion: str | None = None,
    estandarizacion_match: bool = False,
) -> tuple[bool, int, str]:
    """
    Retorna (ok, piso_aplicado, mensaje_error).
    Réplica de la lógica en view_rrhh_sip_obra_2.php (#button_add_candidato).
    """
    monto = parse_sueldo(sueldo)
    cargo_u = (cargo or '').strip().upper()
    turno = (horario or '').strip().upper()

    if estandarizacion_match and monto < 962_000:
        return False, 962_000, 'El monto Liquido Pactado, no puede ser menor a 962.000 pesos'

    if turno in SUELDO_PISO_POR_HORARIO:
        umbral, mensaje_piso = SUELDO_PISO_POR_HORARIO[turno]
        if monto < umbral:
            fmt = f'{mensaje_piso:,}'.replace(',', '.')
            return False, mensaje_piso, f'El monto Liquido Pactado, no puede ser menor a {fmt} pesos'
        return True, mensaje_piso, ''

    if cargo_u in CARGOS_EXENTOS_SUELDO_MINIMO:
        return True, 0, ''

    if monto <= SUELDO_MINIMO_ESTANDAR:
        return (
            False,
            SUELDO_MINIMO_ESTANDAR,
            'El monto Liquido Pactado, no puede ser menor a 581.000 pesos',
        )
    return True, SUELDO_MINIMO_ESTANDAR, ''


def validate_fechas_contrato(data: dict) -> dict[str, str]:
    """P1: término HITO / plazo fijo debe ser estrictamente posterior a fecha ingreso."""
    errors: dict[str, str] = {}
    ingreso = parse_date(data.get('cf_rrhh_sip_obra_candidato_fecha_ingreso'))
    if not ingreso:
        return errors

    tipo = (data.get('cf_rrhh_sip_obra_candidato_tipo_contrato') or '').strip()
    if tipo == 'Obra o Faena':
        termino = parse_date(data.get('cf_rrhh_sip_obra_candidato_fecha_termino_ito'))
        if termino and termino <= ingreso:
            errors['cf_rrhh_sip_obra_candidato_fecha_termino_ito'] = (
                'La fecha término HITO debe ser posterior a la fecha de ingreso'
            )
    elif tipo == 'Plazo Fijo':
        termino = parse_date(data.get('cf_rrhh_sip_obra_candidato_termino_contrato'))
        if termino and termino <= ingreso:
            errors['cf_rrhh_sip_obra_candidato_termino_contrato'] = (
                'La fecha término plazo fijo debe ser posterior a la fecha de ingreso'
            )
    return errors


def validate_candidato_negocio(data: dict, *, ubicacion: str | None = None) -> dict:
    """Valida RUT, blacklist, edad ≥ 18, sueldo y correo SMTP. Devuelve data con RUT normalizado."""
    from .email_validation import validar_correo_smtp

    errors = {}
    rut_raw = data.get('cf_rrhh_sip_obra_candidato_rut')
    if not is_valid_rut(str(rut_raw or '')):
        errors['cf_rrhh_sip_obra_candidato_rut'] = 'El RUT no es válido.'
    else:
        data['cf_rrhh_sip_obra_candidato_rut'] = format_rut_display(str(rut_raw))
        if is_rut_bloqueado(str(rut_raw)):
            errors['cf_rrhh_sip_obra_candidato_rut'] = (
                'RUT bloqueado; contactar a oficina central.'
            )

    nacimiento = parse_date(data.get('cf_rrhh_sip_obra_candidato_fecha_nacimiento'))
    ingreso = parse_date(data.get('cf_rrhh_sip_obra_candidato_fecha_ingreso'))
    if nacimiento and ingreso and age_at(nacimiento, ingreso) < 18:
        errors['cf_rrhh_sip_obra_candidato_fecha_nacimiento'] = (
            'El trabajador debe tener más de 18 años.'
        )

    estandarizacion_match = match_estandarizacion(
        data.get('cf_rrhh_sip_obra_candidato_nomcar'),
        ubicacion,
    )
    ok, _piso, msg = resolve_sueldo_minimo(
        sueldo=data.get('cf_rrhh_sip_obra_candidato_sueldo'),
        cargo=data.get('cf_rrhh_sip_obra_candidato_nomcar'),
        horario=data.get('cf_rrhh_sip_obra_candidato_horario_trabajo'),
        ubicacion=ubicacion,
        estandarizacion_match=estandarizacion_match,
    )
    if not ok:
        errors['cf_rrhh_sip_obra_candidato_sueldo'] = msg

    correo = (data.get('cf_rrhh_sip_obra_candidato_correo') or '').strip()
    if correo and not validar_correo_smtp(correo):
        errors['cf_rrhh_sip_obra_candidato_correo'] = (
            'El correo no existe, favor ingresar un correo válido'
        )

    errors.update(validate_fechas_contrato(data))

    if errors:
        raise ValidationError(errors)
    return data
