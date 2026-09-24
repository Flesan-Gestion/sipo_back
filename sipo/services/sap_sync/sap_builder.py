from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ...models import SipoCandidatoObra, SipoObra
from ..candidato_validaciones import (
    clean_address_field,
    format_rut_sap_national_id,
    format_rut_sap_pad,
    parse_numero_depto_fields,
)
from .position import get_posicion_sap

SAP_EPOCH = datetime(1970, 1, 1)


def _datetime_to_sap_ms(dt: datetime) -> int:
    """Epoch ms sin timezone local (evita OSError 22 en Windows con fechas < 1970)."""
    return int((dt - SAP_EPOCH).total_seconds() * 1000)


def to_sap_date(value: str | None) -> str:
    if not value:
        return f"/Date({_datetime_to_sap_ms(datetime.utcnow())})/"
    raw = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            dt = datetime.strptime(raw[:10], fmt)
            return f'/Date({_datetime_to_sap_ms(dt)})/'
        except ValueError:
            continue
    return f"/Date({_datetime_to_sap_ms(datetime.utcnow())})/"


def _user_id(candidato: SipoCandidatoObra) -> str:
    return str(candidato.cf_rrhh_sip_obra_user_id or '').strip()


def _first_name(candidato: SipoCandidatoObra) -> str:
    parts = [
        candidato.cf_rrhh_sip_obra_candidato_nombre,
        candidato.cf_rrhh_sip_obra_candidato_segundo_nombre,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip())


def _last_name(candidato: SipoCandidatoObra) -> str:
    parts = [
        candidato.cf_rrhh_sip_obra_candidato_ap,
        candidato.cf_rrhh_sip_obra_candidato_am,
    ]
    return ' '.join(p.strip() for p in parts if p and str(p).strip())


def _sueldo_liquido(candidato: SipoCandidatoObra) -> int:
    raw = str(candidato.cf_rrhh_sip_obra_candidato_sueldo or '').replace('.', '').replace(',', '')
    digits = ''.join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 0


def _is_sueldo_especial_250(candidato: SipoCandidatoObra) -> bool:
    """Paridad legado: match literal string '250.000'."""
    return str(candidato.cf_rrhh_sip_obra_candidato_sueldo or '').strip() == '250.000'


def _paycomp_m020_value(candidato: SipoCandidatoObra) -> int:
    """Paridad legado: M020 usa sueldo_base Kiptor; caso '250.000' → 1."""
    if _is_sueldo_especial_250(candidato):
        return 1
    base = candidato.cf_rrhh_sip_obra_sueldo_base
    if base is not None:
        try:
            base_int = int(Decimal(str(base)))
            if base_int > 0:
                return base_int
        except Exception:
            pass
    return _sueldo_liquido(candidato)


def _end_date(candidato: SipoCandidatoObra) -> str:
    ito = (candidato.cf_rrhh_sip_obra_candidato_fecha_termino_ito or '').strip()
    if ito:
        return to_sap_date(ito)
    return to_sap_date(candidato.cf_rrhh_sip_obra_candidato_termino_contrato)


@dataclass
class SapSyncContext:
    candidato: SipoCandidatoObra
    obra: SipoObra
    job_code: str = ''
    cargo_grade: str = ''
    employment_type: str = ''
    business_unit: str = ''
    pay_group: str = 'RG'
    pay_scale_level: str = 'CHL/01/01/01/01'
    pay_scale_group: str = 'CHL/01/01/01'
    nationality_code: str = ''
    colacion_movilizacion: int = 0


def map_gender_sap(value: str | None) -> str:
    """SAP User.gender espera M/F (paridad legado)."""
    raw = str(value or '').strip()
    key = raw.upper()
    if key in ('M', 'MASCULINO', 'H', 'HOMBRE', 'MALE'):
        return 'M'
    if key in ('F', 'FEMENINO', 'MUJER', 'FEMALE'):
        return 'F'
    return raw[:1].upper() if raw else ''


def map_anticipo_sap(value: str | None) -> str:
    """Picklist Anticipo de Sueldo en SAP: 'Sí' / 'No' (paridad legado)."""
    raw = str(value or '').strip()
    key = raw.upper().replace('Í', 'I').replace('í', 'i')
    if key in ('SI', 'S', 'YES', 'Y', 'TRUE', '1'):
        return 'Sí'
    if key in ('NO', 'N', 'FALSE', '0'):
        return 'No'
    if raw in ('Sí', 'Si'):
        return 'Sí'
    return raw or 'No'


def map_marital_status_sap(value: str | None) -> str:
    """SAP PerPersonal.maritalStatus espera el nombre (Soltero/Casado...), no el external_code."""
    raw = str(value or '').strip()
    if not raw or raw == '0':
        return ''
    if not raw.isdigit():
        return raw
    from ..candidato_maestros import get_estado_civil

    for opt in get_estado_civil():
        if str(opt.get('code') or '') == raw:
            return str(opt.get('value') or opt.get('label') or '')
    return raw


def map_payment_method_sap(value: str | None) -> str:
    """SAP paymentMethod: códigos legado 05=Transferencia, 06=Cheque. Default 05."""
    raw = str(value or '').strip()
    if raw in ('05', '06'):
        return raw
    key = raw.lower()
    if key in ('cheque',):
        return '06'
    return '05'


def build_user_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    birth = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_nacimiento)
    return {
        '__metadata': {'type': 'SFOData.User', 'uri': f"User('{code}')"},
        'username': code,
        'userId': code,
        'status': 'active',
        'dateOfBirth': birth,
        'displayName': '',
        'firstName': _first_name(ctx.candidato),
        'lastName': _last_name(ctx.candidato),
        'nickname': '',
        'gender': map_gender_sap(ctx.candidato.cf_rrhh_sip_obra_candidato_genero),
        'empId': code,
    }


def build_per_person_payload(ctx: SapSyncContext) -> list[dict[str, Any]]:
    code = _user_id(ctx.candidato)
    birth = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_nacimiento)
    return [{
        '__metadata': {'type': 'SFOData.PerPerson', 'uri': f"PerPerson('{code}')"},
        'personIdExternal': code,
        'userId': code,
        'dateOfBirth': birth,
        'regionOfBirth': str(ctx.candidato.cf_rrhh_sip_obra_candidato_region_nacimiento or ''),
        'countryOfBirth': str(ctx.candidato.cf_rrhh_sip_obra_candidato_pais_nacimiento or ''),
    }]


def resolve_national_id_card_type(rut: str | None) -> str:
    """
    Paridad legado: si el RUT ya existe en colaboradores → RUN{n+1}, si no → RUN1.
    Permite recontratar con nuevo userId y el mismo RUT.
    """
    padded = format_rut_sap_pad(rut or '')
    digits = padded.replace('.', '').replace('-', '')
    if not digits:
        return 'RUN1'

    from django.db import connections
    from django.db.utils import OperationalError, ProgrammingError

    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM colaboradores
                WHERE REPLACE(REPLACE(COALESCE(national_id, ''), '.', ''), '-', '') = %s
                """,
                [digits],
            )
            count = int((cursor.fetchone() or [0])[0] or 0)
            if count < 1:
                return 'RUN1'
            try:
                cursor.execute(
                    """
                    SELECT MAX(
                        CAST(
                            CASE
                                WHEN LENGTH(COALESCE(run, '')) = 4 THEN RIGHT(run, 1)
                                WHEN LENGTH(COALESCE(run, '')) >= 4 THEN RIGHT(run, 2)
                                ELSE '0'
                            END AS UNSIGNED
                        )
                    )
                    FROM colaboradores
                    WHERE REPLACE(REPLACE(COALESCE(national_id, ''), '.', ''), '-', '') = %s
                      AND COALESCE(run, '') LIKE 'RUN%%'
                    """,
                    [digits],
                )
                max_n = (cursor.fetchone() or [None])[0]
                next_n = int(max_n or 0) + 1
            except (OperationalError, ProgrammingError):
                next_n = count + 1
            return f'RUN{max(next_n, 2)}'
    except (OperationalError, ProgrammingError, KeyError):
        return 'RUN1'


def next_national_id_card_type(card_type: str | None) -> str:
    raw = str(card_type or 'RUN1').strip().upper()
    if raw.startswith('RUN'):
        suffix = raw[3:]
        if suffix.isdigit():
            return f'RUN{int(suffix) + 1}'
    return 'RUN2'


def build_per_national_id_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    rut = format_rut_sap_national_id(ctx.candidato.cf_rrhh_sip_obra_candidato_rut or '')
    return {
        '__metadata': {'type': 'SFOData.PerNationalId', 'uri': 'PerNationalId'},
        'personIdExternal': code,
        'country': 'CHL',
        'cardType': resolve_national_id_card_type(
            ctx.candidato.cf_rrhh_sip_obra_candidato_rut
        ),
        'isPrimary': True,
        'nationalId': rut,
    }


def build_emp_employment_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    return {
        '__metadata': {
            'type': 'SFOData.EmpEmployment',
            'uri': f"EmpEmployment(personIdExternal='{code}',userId='{code}')",
        },
        'startDate': start,
        'personIdExternal': code,
        'userId': code,
        'seniorityDate': start,
        'customDate1': start,
        'customDate2': start,
        'customDate3': start,
        'originalStartDate': start,
    }


def build_emp_job_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    end = _end_date(ctx.candidato)
    tipo = str(ctx.candidato.cf_rrhh_sip_obra_candidato_tipo_contrato or '')
    custom_string1 = ''
    if tipo == 'Obra o Faena':
        custom_string1 = str(ctx.candidato.cf_rrhh_sip_obra_candidato_termino_contrato or '')

    return {
        '__metadata': {'type': 'SFOData.EmpJob', 'uri': 'EmpJob'},
        'seqNumber': '1',
        'userId': code,
        'startDate': start,
        'workscheduleCode': str(ctx.candidato.cf_rrhh_sip_obra_candidato_horario_trabajo or ''),
        'endDate': end,
        'contractType': tipo,
        'timeRecordingVariant': 'DURATION',
        'eventReason': 'C1',
        'position': get_posicion_sap(code),
        'company': str(ctx.obra.cf_rrhh_sip_rut or ''),
        'hireDate': start,
        'contractEndDate': end,
        'employeeType': 'GOV',
        'timeTypeProfileCode': 'CHL_EC_TIMEOFF',
        'holidayCalendarCode': 'C1',
        'payScaleLevel': ctx.pay_scale_level,
        'payScaleArea': 'CHL/01',
        'payScaleType': 'CHL/01',
        'payScaleGroup': ctx.pay_scale_group,
        'customString1': custom_string1,
        'customString2': str(ctx.candidato.cf_rrhh_sip_obra_candidato_cuenta_gasto or ''),
        'customString3': 'No Planta',
        'customString4': ctx.cargo_grade,
        'customString5': 'No',
        'customString6': 'No',
        'customString7': map_anticipo_sap(ctx.candidato.cf_rrhh_sip_obra_candidato_anticipo),
    }


def build_per_personal_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    end = _end_date(ctx.candidato)
    ingreso = str(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso or '')[:10]
    gender = map_gender_sap(ctx.candidato.cf_rrhh_sip_obra_candidato_genero)
    salutation = 'Sr.' if gender == 'M' else 'Sra.'
    formal = ' '.join(
        p for p in [
            _first_name(ctx.candidato),
            _last_name(ctx.candidato),
        ] if p
    )
    return {
        '__metadata': {
            'type': 'SFOData.PerPersonal',
            'uri': f"PerPersonal(personIdExternal='{code}',startDate=datetime'{ingreso}T00:00:00')",
        },
        'personIdExternal': code,
        'startDate': start,
        'formalName': formal,
        'lastName': _last_name(ctx.candidato),
        'firstName': _first_name(ctx.candidato),
        'secondLastName': '',
        'gender': gender,
        'endDate': end,
        'nationality': ctx.nationality_code,
        'nativePreferredLang': 'Español',
        'salutation': salutation,
        'maritalStatus': map_marital_status_sap(
            ctx.candidato.cf_rrhh_sip_obra_candidato_estado_civil
        ),
    }


def build_emp_compensation_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    end = _end_date(ctx.candidato)
    return {
        '__metadata': {'type': 'SFOData.EmpCompensation', 'uri': 'EmpCompensation'},
        'userId': code,
        'startDate': start,
        'endDate': end,
        'eventReason': 'C1',
        'payGroup': ctx.pay_group,
        'payType': 'Asalariado',
    }


def build_payment_information_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    return {
        '__metadata': {'type': 'SFOData.PaymentInformationV3', 'uri': 'PaymentInformationV3'},
        'effectiveStartDate': start,
        'worker': code,
    }


def build_payment_information_detail_payload(ctx: SapSyncContext) -> list[dict[str, Any]]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    banco = str(ctx.candidato.cf_rrhh_sip_obra_candidato_banco or '').strip()
    if banco == '0':
        banco = ''
    owner = ' '.join(
        p for p in [
            str(ctx.candidato.cf_rrhh_sip_obra_candidato_nombre or '').strip(),
            str(ctx.candidato.cf_rrhh_sip_obra_candidato_segundo_nombre or '').strip(),
            str(ctx.candidato.cf_rrhh_sip_obra_candidato_am or '').strip(),
            str(ctx.candidato.cf_rrhh_sip_obra_candidato_ap or '').strip(),
        ] if p
    )
    return [{
        '__metadata': {
            'type': 'SFOData.PaymentInformationDetailV3',
            'uri': 'PaymentInformationDetailV3',
        },
        'PaymentInformationV3_effectiveStartDate': start,
        'PaymentInformationV3_worker': code,
        'bankCountry': 'CHL',
        'bank': banco,
        'payType': 'MAIN',
        'businessIdentifierCode': banco,
        'accountOwner': owner,
        'paymentMethod': map_payment_method_sap(
            ctx.candidato.cf_rrhh_sip_obra_candidato_metodo_pago
        ),
        'currency': 'CLP',
        'accountNumber': str(ctx.candidato.cf_rrhh_sip_obra_candidato_numcta or ''),
        'routingNumber': banco,
    }]


def build_per_email_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    return {
        '__metadata': {'type': 'SFOData.PerEmail', 'uri': 'PerEmail'},
        'emailType': 'Personal',
        'personIdExternal': code,
        'emailAddress': str(ctx.candidato.cf_rrhh_sip_obra_candidato_correo or ''),
        'isPrimary': True,
    }


def build_per_phone_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    return {
        '__metadata': {'type': 'SFOData.PerPhone', 'uri': 'PerPhone'},
        'phoneType': 'Célular',
        'personIdExternal': code,
        'phoneNumber': str(ctx.candidato.cf_rrhh_sip_obra_candidato_telefono or ''),
        'isPrimary': True,
    }


def _pay_comp_payload(
    ctx: SapSyncContext,
    *,
    pay_component: str,
    paycompvalue: int,
) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    return {
        '__metadata': {'type': 'SFOData.EmpPayCompRecurring', 'uri': 'EmpPayCompRecurring'},
        'userId': code,
        'startDate': start,
        'payComponent': pay_component,
        'frequency': 'MON',
        'currencyCode': 'CLP',
        'paycompvalue': paycompvalue,
        'endDate': to_sap_date('9999-12-31'),
    }


def build_per_address_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = _user_id(ctx.candidato)
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    numero, depto = parse_numero_depto_fields(
        ctx.candidato.cf_rrhh_sip_obra_candidato_numero_dire,
        ctx.candidato.cf_rrhh_sip_obra_candidato_num_depto,
    )
    return {
        '__metadata': {'type': 'SFOData.PerAddressDEFLT', 'uri': 'PerAddressDEFLT'},
        'addressType': 'home',
        'personIdExternal': code,
        'startDate': start,
        'address1': clean_address_field(ctx.candidato.cf_rrhh_sip_obra_candidato_direccion),
        'address2': clean_address_field(numero),
        'address4': clean_address_field(depto),
        'city': clean_address_field(ctx.candidato.cf_rrhh_sip_obra_candidato_comuna),
        'country': 'CHL',
        'county': clean_address_field(ctx.candidato.cf_rrhh_sip_obra_candidato_ciudad),
        'endDate': to_sap_date('9999-12-31'),
        'state': clean_address_field(ctx.candidato.cf_rrhh_sip_obra_candidato_region),
    }


def build_comp_info_payload(ctx: SapSyncContext) -> dict[str, Any]:
    return _pay_comp_payload(
        ctx,
        pay_component='M020',
        paycompvalue=_paycomp_m020_value(ctx.candidato),
    )


def _colacion_movilizacion_value(ctx: SapSyncContext) -> int:
    """1018/1029: escala o regla Chivato Huechún ($1)."""
    from sipo.constants import COL_MOV_CHIVATO_HUECHUN

    from ..candidato_validaciones import is_chivato_huechun_cc, resolve_colacion_movilizacion

    cc = getattr(ctx.obra, 'cf_rrhh_sip_cc', None)
    if is_chivato_huechun_cc(cc):
        return COL_MOV_CHIVATO_HUECHUN
    if _is_sueldo_especial_250(ctx.candidato):
        return 125_000
    if ctx.colacion_movilizacion:
        return max(0, int(ctx.colacion_movilizacion))
    return resolve_colacion_movilizacion(
        sueldo_liquido=_sueldo_liquido(ctx.candidato),
        centro_costo=cc,
    )


def build_pay_comp_payloads(ctx: SapSyncContext) -> list[dict[str, Any]]:
    """M020 + 1029 movilización + 1018 colación (legado no upserta 1100)."""
    col_mov = _colacion_movilizacion_value(ctx)
    return [
        build_comp_info_payload(ctx),
        _pay_comp_payload(ctx, pay_component='1029', paycompvalue=col_mov),
        _pay_comp_payload(ctx, pay_component='1018', paycompvalue=col_mov),
    ]


def build_position_payload(ctx: SapSyncContext) -> dict[str, Any]:
    code = get_posicion_sap(_user_id(ctx.candidato))
    start = to_sap_date(ctx.candidato.cf_rrhh_sip_obra_candidato_fecha_ingreso)
    return {
        '__metadata': {'type': 'SFOData.Position', 'uri': 'Position'},
        'code': code,
        'effectiveStartDate': start,
        'businessUnit': ctx.business_unit,
        'company': str(ctx.obra.cf_rrhh_sip_rut or ''),
        'costCenter': str(ctx.obra.cf_rrhh_sip_cc or ''),
        'cust_employmentType': ctx.employment_type or None,
        'department': str(ctx.obra.cf_rrhh_sip_dep or ''),
        'division': str(ctx.obra.cf_rrhh_sip_uni or ''),
        'effectiveStatus': 'A',
        'externalName_defaultValue': str(ctx.candidato.cf_rrhh_sip_obra_candidato_nomcar or ''),
        'jobCode': ctx.job_code,
        'cust_subarea': None,
        'location': str(ctx.obra.cf_rrhh_sip_ubicacion or ''),
        'multipleIncumbentsAllowed': False,
        'vacant': True,
    }


SAP_ENTITY_BUILDERS: list[tuple[str, Any]] = [
    ('Position', build_position_payload),
    ('User', build_user_payload),
    ('PerPerson', build_per_person_payload),
    ('EmpEmployment', build_emp_employment_payload),
    ('EmpJob', build_emp_job_payload),
    ('PerPersonal', build_per_personal_payload),
    ('EmpCompensation', build_emp_compensation_payload),
    ('PaymentInformationV3', build_payment_information_payload),
    ('PaymentInformationDetailV3', build_payment_information_detail_payload),
    ('PerNationalId', build_per_national_id_payload),
    ('PerAddressDEFLT', build_per_address_payload),
    ('EmpPayCompRecurring', build_pay_comp_payloads),
    ('PerEmail', build_per_email_payload),
    ('PerPhone', build_per_phone_payload),
]
