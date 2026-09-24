from __future__ import annotations

from django.conf import settings
from django.db import connections
from rest_framework import status
from rest_framework.exceptions import APIException

from ...constants import (
    SIPO_CANDIDATO_ACTIVO,
    SIPO_CANDIDATO_CONTRATADO_SAP,
    SIPO_CANDIDATO_SELECCIONADO,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
)
from ...models import SipoCandidatoObra, SipoObra
from ..crud import get_obra_for_user
from ..notifications import collect_integration_errors

from .client import upsert_entity, write_sap_log
from .sap_builder import SAP_ENTITY_BUILDERS, SapSyncContext


def _require_admin_rrhh(user) -> None:
    rol_id = int(getattr(user, 'sip_rol_id', -1))
    if rol_id not in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        raise APIException(
            "Don't have access to this resource",
            status.HTTP_403_FORBIDDEN,
        )


def _load_cargo_meta(nombre_cargo: str | None) -> tuple[str, str, str]:
    if not nombre_cargo:
        return '', '', ''
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            SELECT external_code, grade, external_code_area_personal
            FROM cargos
            WHERE nombre_cargo = %s AND status = 'A'
            LIMIT 1
            """,
            [nombre_cargo],
        )
        row = cursor.fetchone()
    if not row:
        return '', '', ''
    return str(row[0] or ''), str(row[1] or ''), str(row[2] or '')


def _load_business_unit(obra: SipoObra) -> tuple[str, str]:
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            SELECT external_code_pais
            FROM sap_maestro_empresa_dep_un_cc
            WHERE external_code_empresa = %s AND external_code_cc = %s
            LIMIT 1
            """,
            [obra.cf_rrhh_sip_rut, obra.cf_rrhh_sip_cc],
        )
        row = cursor.fetchone()
    if not row:
        return '', 'RG'
    pais = str(row[0] or '')
    pay_group = 'RG' if pais == '10000001' else 'R1' if pais == '10000004' else 'RG'
    return pais, pay_group


def _load_payscale(sueldo_liquido: int) -> tuple[str, str]:
    """Paridad legado EmpJob: escala.subgrupo_profesional / grupo_profesional."""
    default_level = 'CHL/01/01/01/01'
    default_group = 'CHL/01/01/01'
    if sueldo_liquido < 366_044:
        return default_level, default_group
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            SELECT subgrupo_profesional, grupo_profesional
            FROM escala
            WHERE liquido <= %s
            ORDER BY liquido DESC
            LIMIT 1
            """,
            [sueldo_liquido],
        )
        row = cursor.fetchone()
    if not row:
        return default_level, default_group
    return str(row[0] or default_level), str(row[1] or default_group)


def _load_nationality_code(pais_nacimiento: str | None) -> str:
    if not pais_nacimiento:
        return ''
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            SELECT external_code
            FROM sap_maestro_pais_nacionalidad
            WHERE pais = %s
            LIMIT 1
            """,
            [pais_nacimiento],
        )
        row = cursor.fetchone()
    return str(row[0] or '') if row else ''


def _load_colacion_movilizacion(sueldo_liquido: int, centro_costo: str | None = None) -> int:
    """Valor colación/movilización (escala o regla Chivato Huechún)."""
    from ..candidato_validaciones import resolve_colacion_movilizacion

    return resolve_colacion_movilizacion(
        sueldo_liquido=sueldo_liquido,
        centro_costo=centro_costo,
    )


def _build_context(candidato: SipoCandidatoObra, obra: SipoObra) -> SapSyncContext:
    from .sap_builder import _sueldo_liquido

    liquido = _sueldo_liquido(candidato)
    job_code, cargo_grade, area_personal = _load_cargo_meta(
        candidato.cf_rrhh_sip_obra_candidato_nomcar
    )
    business_unit, pay_group = _load_business_unit(obra)
    pay_scale_level, pay_scale_group = _load_payscale(liquido)
    nationality = _load_nationality_code(candidato.cf_rrhh_sip_obra_candidato_pais_nacimiento)
    return SapSyncContext(
        candidato=candidato,
        obra=obra,
        job_code=job_code,
        cargo_grade=cargo_grade,
        employment_type=area_personal,
        business_unit=business_unit,
        pay_group=pay_group,
        pay_scale_level=pay_scale_level,
        pay_scale_group=pay_scale_group,
        nationality_code=nationality,
        colacion_movilizacion=_load_colacion_movilizacion(
            liquido,
            centro_costo=obra.cf_rrhh_sip_cc,
        ),
    )


def _upsert_safe(*, entity_type: str, payload: dict | list) -> dict:
    try:
        return upsert_entity(entity_type=entity_type, payload=payload)
    except Exception as exc:
        return {
            'dry_run': False,
            'status': 'ERROR',
            'message': f'Error de conexión con SAP: {exc}',
        }


_SOFT_ERROR_MARKERS = (
    'solo un método de pago principal',
    'only one primary payment method',
)


def _soften_known_resync_conflicts(*, log_type: str, result: dict) -> dict:
    """
    En re-sync, SAP rechaza un segundo PaymentInformationDetail MAIN.
    Se degrada a OK+Warning (el método principal ya existe).
    """
    status = str(result.get('status') or '').upper()
    message = str(result.get('message') or '')
    if status != 'ERROR':
        return result
    if 'PaymentInformationDetail' not in str(log_type):
        return result
    lower = message.lower()
    if any(marker in lower for marker in _SOFT_ERROR_MARKERS):
        return {
            **result,
            'status': 'OK',
            'message': f'[Warning!] {message}'.strip(),
        }
    return result


def _is_national_id_duplicate_error(message: str) -> bool:
    lower = (message or '').lower()
    return 'ya existe' in lower and (
        'nacional' in lower or 'national' in lower or 'run' in lower
    )


def _upsert_per_national_id_with_run_retry(*, sip_id: int, user_id: str, payload: dict) -> dict:
    """
    Recontratación mismo RUT / nuevo userId: si RUN1 choca, reintenta RUN2..RUN5.
    """
    from .sap_builder import next_national_id_card_type

    current = dict(payload)
    last = _upsert_safe(entity_type='PerNationalId', payload=current)
    for _ in range(4):
        if str(last.get('status') or '').upper() != 'ERROR':
            break
        if not _is_national_id_duplicate_error(str(last.get('message') or '')):
            break
        current['cardType'] = next_national_id_card_type(current.get('cardType'))
        last = _upsert_safe(entity_type='PerNationalId', payload=current)
    return last


def _marcar_contratados_sap(sip_id: int) -> int:
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            UPDATE cf_rrhh_sip_candidato_obra
            SET cf_rrhh_sip_obra_candidato_seleccionado = %s
            WHERE cf_rrhh_sip_obra_id = %s
              AND cf_rrhh_sip_obra_candidato_estado = %s
              AND cf_rrhh_sip_obra_candidato_seleccionado = %s
            """,
            [
                SIPO_CANDIDATO_CONTRATADO_SAP,
                sip_id,
                SIPO_CANDIDATO_ACTIVO,
                SIPO_CANDIDATO_SELECCIONADO,
            ],
        )
        return cursor.rowcount


def sync_candidatos_to_sap(
    *,
    sip_id: int,
    obra: SipoObra,
    seleccionado_values: tuple[int, ...] = (SIPO_CANDIDATO_SELECCIONADO,),
) -> dict:
    if not getattr(settings, 'SAP_SF_SYNC_ENABLED', False):
        return {
            'sip_id': sip_id,
            'candidatos_procesados': 0,
            'skipped': True,
            'message': 'SAP_SF_SYNC_ENABLED=False — sin escritura en SuccessFactors',
            'resultados': [],
        }

    candidatos = list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado__in=seleccionado_values,
        )
    )
    if not candidatos:
        raise APIException(
            'No hay candidatos seleccionados para sincronizar',
            status.HTTP_400_BAD_REQUEST,
        )

    summary: list[dict] = []
    for candidato in candidatos:
        ctx = _build_context(candidato, obra)
        user_id = str(candidato.cf_rrhh_sip_obra_user_id or '')
        entity_results: list[dict] = []
        for log_type, builder in SAP_ENTITY_BUILDERS:
            payload = builder(ctx)
            payloads = payload if isinstance(payload, list) else [payload]
            for item in payloads:
                pay_component = item.get('payComponent') if isinstance(item, dict) else None
                log_label = (
                    f'{log_type} - {pay_component}' if pay_component else log_type
                )
                if log_type == 'PerNationalId' and isinstance(item, dict):
                    result = _upsert_per_national_id_with_run_retry(
                        sip_id=sip_id,
                        user_id=user_id,
                        payload=item,
                    )
                else:
                    result = _upsert_safe(entity_type=log_label, payload=item)
                result = _soften_known_resync_conflicts(
                    log_type=log_label,
                    result=result,
                )
                write_sap_log(
                    sip_id=sip_id,
                    user_id=user_id,
                    log_type=log_label,
                    result=result,
                )
                entity_results.append({
                    'entity': log_label,
                    'status': result.get('status'),
                    'message': result.get('message'),
                    'dry_run': result.get('dry_run', False),
                })
        summary.append({
            'candidato_id': candidato.cf_rrhh_sip_obra_candidato_id,
            'user_id': user_id,
            'entities': entity_results,
        })

    return {
        'sip_id': sip_id,
        'candidatos_procesados': len(summary),
        'resultados': summary,
    }


def sync_sipo_candidatos_sap(*, sip_id: int, user) -> dict:
    """Sincronización manual SAP (Admin/RRHH). Reintenta candidatos seleccionado 1|2."""
    _require_admin_rrhh(user)
    obra = get_obra_for_user(sip_id, user)
    current_status = int(obra.cf_rrhh_sip_status)

    try:
        result = sync_candidatos_to_sap(
            sip_id=sip_id,
            obra=obra,
            seleccionado_values=(
                SIPO_CANDIDATO_SELECCIONADO,
                SIPO_CANDIDATO_CONTRATADO_SAP,
            ),
        )
    except APIException:
        raise
    except Exception as exc:
        raise APIException(
            f'Error de conexión con SAP: {exc}',
            status.HTTP_400_BAD_REQUEST,
        ) from exc

    # Paridad legado: siempre avanza estado local aunque SAP reporte ERROR.
    contratados = 0
    if not result.get('skipped'):
        contratados = _marcar_contratados_sap(sip_id)

    from ..estados import registrar_historial_estado

    procesados = int(result.get('candidatos_procesados') or 0)
    errores = collect_integration_errors(sap_result=result)
    if result.get('skipped'):
        comentario = result.get('message') or 'Sincronización SAP omitida (deshabilitada).'
        message = comentario
    elif errores:
        comentario = (
            f'Sincronización manual SAP con errores: {procesados} candidato(s); '
            f'{"; ".join(errores[:3])}'
        )
        message = 'Sincronización con SAP ejecutada con errores'
    else:
        comentario = (
            f'Sincronización manual SAP OK: {procesados} candidato(s) procesados.'
        )
        message = 'Sincronización con SAP ejecutada correctamente'

    registrar_historial_estado(
        sip_id=sip_id,
        estado_anterior=current_status,
        estado_nuevo=current_status,
        user=user,
        comentario=comentario,
    )

    if errores:
        raise APIException(
            '; '.join(errores[:5]),
            status.HTTP_400_BAD_REQUEST,
        )

    return {
        **result,
        'message': message,
        'candidatos_contratados_sap': contratados,
    }
