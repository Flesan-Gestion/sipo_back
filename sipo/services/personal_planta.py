"""Personal de planta activo por centro de costo (tabla colaboradores)."""

from __future__ import annotations

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError


def personal_planta_label(nombre: str, correo: str) -> str:
    nombre = (nombre or '').strip()
    correo = (correo or '').strip()
    if nombre and correo:
        return f'{nombre} ({correo})'
    return nombre or correo


def list_personal_planta(centro_costo: str) -> list[dict]:
    cc = (centro_costo or '').strip()
    if not cc:
        return []
    sql = """
        SELECT
            CAST(user_id AS UNSIGNED) AS user_id,
            TRIM(CONCAT_WS(' ',
                NULLIF(TRIM(first_name), ''),
                NULLIF(TRIM(middle_name), ''),
                NULLIF(TRIM(last_name), ''),
                NULLIF(TRIM(second_last_name), '')
            )) AS nombre,
            COALESCE(
                NULLIF(TRIM(correo_flesan), ''),
                NULLIF(TRIM(correo_gmail), '')
            ) AS correo
        FROM colaboradores
        WHERE empl_status = '41111'
          AND TRIM(centro_costo) = %s
        ORDER BY nombre
    """
    try:
        with connections['sip_db'].cursor() as cursor:
            cursor.execute(sql, [cc])
            rows = cursor.fetchall()
    except (OperationalError, ProgrammingError, KeyError):
        return []

    items = []
    seen = set()
    for user_id, nombre, correo in rows:
        uid = str(user_id or '').strip()
        if uid.endswith('.0'):
            uid = uid[:-2]
        if not uid or uid in seen:
            continue
        seen.add(uid)
        nom = str(nombre or '').strip()
        mail = str(correo or '').strip()
        items.append({
            'user_id': uid,
            'nombre': nom,
            'correo': mail,
            'label': personal_planta_label(nom, mail),
        })
    return items
