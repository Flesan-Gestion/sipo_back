from django.db import connections
from rest_framework import status
from rest_framework.exceptions import APIException

from ..models import SipoCandidatoObra
from .candidato_validaciones import format_rut_display, normalize_rut


def list_reintegrar_trabajadores(search: str | None = None) -> list[dict]:
    """Ex-trabajadores con contrato vencido (paridad getNomTrabajadores)."""
    base_sql = """
        SELECT
            MIN(UPPER(TRIM(REPLACE(CONCAT(
                cf_rrhh_sip_obra_candidato_nombre, ' ',
                CASE
                    WHEN cf_rrhh_sip_obra_candidato_segundo_nombre IN ('.', ',') THEN ''
                    ELSE IFNULL(cf_rrhh_sip_obra_candidato_segundo_nombre, '')
                END, ' ',
                IFNULL(cf_rrhh_sip_obra_candidato_ap, ''), ' ',
                CASE
                    WHEN cf_rrhh_sip_obra_candidato_am IN ('.', ',') THEN ''
                    ELSE IFNULL(cf_rrhh_sip_obra_candidato_am, '')
                END
            ), '  ', ' ')))) AS nombre_completo,
            TRIM(cf_rrhh_sip_obra_candidato_rut) AS rut,
            MAX(cf_rrhh_sip_obra_candidato_fecha_ingreso) AS fecha_ingreso,
            CAST(MAX(cf_rrhh_sip_obra_candidato_termino_contrato) AS DATE) AS fecha_termino
        FROM cf_rrhh_sip_candidato_obra
        WHERE cf_rrhh_sip_obra_candidato_rut IS NOT NULL
          AND TRIM(cf_rrhh_sip_obra_candidato_rut) <> ''
        GROUP BY TRIM(cf_rrhh_sip_obra_candidato_rut)
        HAVING CAST(MAX(cf_rrhh_sip_obra_candidato_termino_contrato) AS DATE) < CURRENT_DATE()
    """
    search = (search or '').strip()
    if search:
        sql = f"""
            SELECT * FROM ({base_sql}) AS t
            WHERE t.nombre_completo LIKE %s OR t.rut LIKE %s
            ORDER BY t.nombre_completo
            LIMIT 200
        """
        params = [f'%{search}%', f'%{search}%']
    else:
        sql = f'{base_sql} ORDER BY nombre_completo LIMIT 500'
        params = []

    with connections['sip_db'].cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_reintegrar_detalle(rut: str) -> SipoCandidatoObra:
    """Registro más reciente del RUT para autocompletar ficha."""
    rut_norm = normalize_rut(rut)
    if not rut_norm:
        raise APIException('RUT inválido', status.HTTP_400_BAD_REQUEST)

    body = rut_norm.split('-')[0]
    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            SELECT cf_rrhh_sip_obra_candidato_id
            FROM cf_rrhh_sip_candidato_obra
            WHERE REPLACE(REPLACE(TRIM(cf_rrhh_sip_obra_candidato_rut), '.', ''), '-', '')
                  LIKE %s
            ORDER BY cf_rrhh_sip_obra_candidato_fecha_ingreso DESC
            LIMIT 1
            """,
            [f'{body}%'],
        )
        row = cursor.fetchone()

    if not row:
        raise APIException('Trabajador no encontrado', status.HTTP_404_NOT_FOUND)

    candidato = (
        SipoCandidatoObra.objects.using('sip_db')
        .filter(cf_rrhh_sip_obra_candidato_id=row[0])
        .first()
    )
    if not candidato:
        raise APIException('Trabajador no encontrado', status.HTTP_404_NOT_FOUND)
    return candidato
