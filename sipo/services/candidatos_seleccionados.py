"""Candidatos seleccionados/contratados (tab auditoría documentos)."""

from __future__ import annotations

from ..constants import SIPO_CANDIDATO_ACTIVO
from ..models import SipoCandidatoObra
from .crud import get_obra_for_user

SELECCIONADO_VALUES = (1, 2)


def count_candidatos_seleccionados(sip_id: int) -> int:
    return (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado__in=SELECCIONADO_VALUES,
        )
        .count()
    )


def list_candidatos_seleccionados(sip_id: int, user) -> list[SipoCandidatoObra]:
    get_obra_for_user(sip_id, user)
    return list(
        SipoCandidatoObra.objects.using('sip_db')
        .filter(
            cf_rrhh_sip_obra_id=sip_id,
            cf_rrhh_sip_obra_candidato_estado=SIPO_CANDIDATO_ACTIVO,
            cf_rrhh_sip_obra_candidato_seleccionado__in=SELECCIONADO_VALUES,
        )
        .order_by('cf_rrhh_sip_obra_candidato_ap', 'cf_rrhh_sip_obra_candidato_am')
    )


def toggle_revision_dt_candidato(*, candidato_id: str, user) -> SipoCandidatoObra:
    candidato = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(cf_rrhh_sip_obra_candidato_id=str(candidato_id))
        .first()
    )
    if candidato is None:
        from rest_framework import status
        from rest_framework.exceptions import APIException

        raise APIException('Candidato no encontrado.', status.HTTP_404_NOT_FOUND)

    get_obra_for_user(int(candidato.cf_rrhh_sip_obra_id), user)

    current = str(candidato.cf_rrhh_sip_obra_candidato_registro_dt or '').strip()
    if current == '1':
        candidato.cf_rrhh_sip_obra_candidato_registro_dt = ''
    else:
        candidato.cf_rrhh_sip_obra_candidato_registro_dt = '1'

    candidato.save(using='sip_db', update_fields=['cf_rrhh_sip_obra_candidato_registro_dt'])
    return candidato
