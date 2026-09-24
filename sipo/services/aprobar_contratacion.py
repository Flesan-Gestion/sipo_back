from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from ..constants import (
    SIPO_CANDIDATO_ACTIVO,
    SIPO_CANDIDATO_CONTRATADO_SAP,
    SIPO_CANDIDATO_SELECCIONADO,
    SIPO_ROL_ADMIN,
    SIPO_ROL_RRHH,
    SIPO_STATUS_APROBADA,
    SIPO_STATUS_EN_REVISION,
    SIPO_STATUS_FINALIZADA,
)
from ..models import SipoObra
from .candidato_validaciones import calcular_bonos_mineria_obra
from .crud import get_obra_for_user
from .estados import count_candidatos_activos
from .kiptor import calcular_sueldos_kiptor_obra
from .list import _actor_email, _user_rol_id
from .notifications import (
    send_email_contrato_disponible,
    send_email_obra_finalizada,
)
from .sap_sync.orchestrator import sync_candidatos_to_sap

ESTADOS_APROBAR_CONTRATACION = (SIPO_STATUS_EN_REVISION, SIPO_STATUS_APROBADA)


def _require_admin_rrhh(user) -> None:
    rol_id = _user_rol_id(user)
    if rol_id not in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
        raise APIException(
            "Don't have access to this resource",
            status.HTTP_403_FORBIDDEN,
        )


def _count_seleccionados_explicitos(sip_id: int) -> int:
    from ..models import SipoCandidatoObra

    return (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado=SIPO_CANDIDATO_SELECCIONADO,
        )
        .count()
    )


def _auto_seleccionar_activos(sip_id: int) -> int:
    now = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    from django.db import connections

    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            UPDATE cf_rrhh_sip_candidato_obra
            SET cf_rrhh_sip_obra_candidato_seleccionado = %s,
                cf_rrhh_sip_obra_candidato_estado_documentos = 0,
                cf_rrhh_sip_obra_candidato_seleccionado_date = %s
            WHERE cf_rrhh_sip_obra_id = %s
              AND cf_rrhh_sip_obra_candidato_estado = %s
              AND (cf_rrhh_sip_obra_candidato_seleccionado IS NULL
                   OR cf_rrhh_sip_obra_candidato_seleccionado <> %s)
            """,
            [
                SIPO_CANDIDATO_SELECCIONADO,
                now,
                sip_id,
                SIPO_CANDIDATO_ACTIVO,
                SIPO_CANDIDATO_CONTRATADO_SAP,
            ],
        )
        return cursor.rowcount


def _marcar_contratados_sap(sip_id: int) -> int:
    from django.db import connections

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


def _candidatos_seleccionados_activos(sip_id: int):
    from ..models import SipoCandidatoObra

    return list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado__in=(
                SIPO_CANDIDATO_SELECCIONADO,
                SIPO_CANDIDATO_CONTRATADO_SAP,
            ),
        )
    )


def aprobar_contratacion_obra(*, sip_id: int, user) -> dict:
    _require_admin_rrhh(user)
    obra = get_obra_for_user(sip_id, user)
    current = int(obra.cf_rrhh_sip_status)

    if current not in ESTADOS_APROBAR_CONTRATACION:
        raise APIException(
            'La solicitud no está en un estado válido para aprobar contratación',
            status.HTTP_400_BAD_REQUEST,
        )

    activos = count_candidatos_activos(sip_id)
    if activos < 1:
        raise APIException(
            'Debe registrar al menos un candidato activo',
            status.HTTP_400_BAD_REQUEST,
        )

    email = _actor_email(user)
    now = timezone.now()

    with transaction.atomic(using='sip_db'):
        explicitos = _count_seleccionados_explicitos(sip_id)
        if explicitos >= 1:
            seleccionados = explicitos
            modo_seleccion = 'parcial'
        else:
            seleccionados = _auto_seleccionar_activos(sip_id)
            modo_seleccion = 'auto'
            if seleccionados < 1:
                raise APIException(
                    'No hay candidatos activos para seleccionar',
                    status.HTTP_400_BAD_REQUEST,
                )

        kiptor_result = calcular_sueldos_kiptor_obra(sip_id=sip_id)
        bono_result = calcular_bonos_mineria_obra(sip_id=sip_id, obra=obra)
        sync_result = sync_candidatos_to_sap(sip_id=sip_id, obra=obra)
        contratados = _marcar_contratados_sap(sip_id)

        SipoObra.objects.using('sip_db').filter(cf_rrhh_sip_id=sip_id).update(
            cf_rrhh_sip_status=SIPO_STATUS_FINALIZADA,
            cf_rrhh_sip_status_date=now.date(),
            cf_rrhh_sip_status_user=email,
            cf_rrhh_sip_update_user=email,
            cf_rrhh_sip_update_date=now,
            cf_rrhh_sip_apro_user=email,
            cf_rrhh_sip_apro_date=now,
        )

    obra.refresh_from_db(using='sip_db')
    candidatos = _candidatos_seleccionados_activos(sip_id)
    email_aprobar = send_email_obra_finalizada(
        obra,
        total_contratos=len(candidatos) or contratados,
    )
    email_contratos = [
        send_email_contrato_disponible(obra, c) for c in candidatos
    ]

    return {
        'sip_id': sip_id,
        'nuevo_estado': SIPO_STATUS_FINALIZADA,
        'modo_seleccion': modo_seleccion,
        'candidatos_seleccionados': seleccionados,
        'candidatos_contratados_sap': contratados,
        'kiptor': kiptor_result,
        'bono_mineria': bono_result,
        'sap_sync': sync_result,
        'email_aprobar': email_aprobar,
        'email_contratos': email_contratos,
        'closed_by_email': email,
        'closed_at': now.isoformat(),
    }
