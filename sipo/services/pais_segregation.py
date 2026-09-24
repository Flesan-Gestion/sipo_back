from __future__ import annotations

from rest_framework.exceptions import ValidationError

from ..constants import EXTERNAL_CODE_PAIS_GRUPO_2
from ..models import SapMaestroEmpresaDepUnCc

SIPO_OBRA_DB = 'sip_db'


def normalize_pais(value: str | None) -> str | None:
    code = (value or '').strip()
    return code or None


def is_grupo2_pais(value: str | None) -> bool:
    return normalize_pais(value) == EXTERNAL_CODE_PAIS_GRUPO_2


def apply_external_code_pais_filter(queryset, external_code_pais: str | None = None):
    """
    Matriz país:
    - 10000004 → solo filas Grupo 2
    - 10000001 → excluye Grupo 2 (Chile / no-G2)
    - all / * → sin filtro de país
    - sin valor → sin filtro (catálogo completo para listados / vista)
    """
    from ..constants import EXTERNAL_CODE_PAIS_CHILE

    pais = normalize_pais(external_code_pais)
    if not pais or pais in ('all', '*'):
        return queryset
    if is_grupo2_pais(pais):
        return queryset.filter(external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2)
    if pais == EXTERNAL_CODE_PAIS_CHILE:
        return queryset.exclude(external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2)
    return queryset.exclude(external_code_pais=EXTERNAL_CODE_PAIS_GRUPO_2).filter(
        external_code_pais=pais
    )


def assert_create_only_grupo2(external_code_pais: str | None = None) -> str:
    """Nuevas solicitudes/fichas solo Grupo 2."""
    pais = normalize_pais(external_code_pais) or EXTERNAL_CODE_PAIS_GRUPO_2
    if not is_grupo2_pais(pais):
        raise ValidationError(
            {
                'external_code_pais': [
                    'Solo se permite crear registros para Grupo 2 '
                    f'(external_code_pais={EXTERNAL_CODE_PAIS_GRUPO_2}).'
                ]
            }
        )
    return EXTERNAL_CODE_PAIS_GRUPO_2


def lookup_pais_empresa_cc(
    *,
    razon_social_id: str | None,
    centro_costo_id: str | None,
) -> str | None:
    rs = (razon_social_id or '').strip()
    cc = (centro_costo_id or '').strip()
    if not rs or not cc:
        return None
    row = (
        SapMaestroEmpresaDepUnCc.objects.using(SIPO_OBRA_DB)
        .filter(
            external_code_empresa=rs,
            external_code_cc=cc,
            status_cc='A',
            status_departamento='A',
        )
        .values('external_code_pais')
        .first()
    )
    if not row:
        return None
    return normalize_pais(row.get('external_code_pais'))


def empresa_tiene_pais(*, razon_social_id: str | None, external_code_pais: str | None) -> bool:
    rs = (razon_social_id or '').strip()
    pais = normalize_pais(external_code_pais)
    if not rs or not pais:
        return False
    return (
        SapMaestroEmpresaDepUnCc.objects.using(SIPO_OBRA_DB)
        .filter(
            external_code_empresa=rs,
            external_code_pais=pais,
            status_cc='A',
            status_departamento='A',
        )
        .exclude(external_code_cc__startswith='FL')
        .exists()
    )


def validate_razon_social_centro_costo(
    *,
    razon_social_id: str | None,
    centro_costo_id: str | None,
    external_code_pais: str | None = None,
) -> str:
    """
    Valida coherencia RS↔CC y segregación Grupo 2.
    Retorna el external_code_pais de la fila maestro.
    """
    rs = (razon_social_id or '').strip()
    cc = (centro_costo_id or '').strip()
    if not rs or not cc:
        raise ValidationError(
            {'non_field_errors': ['Razón social y centro de costo son obligatorios.']}
        )

    pais_row = lookup_pais_empresa_cc(razon_social_id=rs, centro_costo_id=cc)
    if not pais_row:
        raise ValidationError(
            {
                'centro_costo': [
                    'El centro de costo no pertenece a la razón social indicada '
                    'o no está activo en el maestro.'
                ]
            }
        )

    ctx = normalize_pais(external_code_pais)
    ctx_is_g2 = is_grupo2_pais(ctx)
    row_is_g2 = is_grupo2_pais(pais_row)

    if ctx is None:
        # Contexto implícito no-G2: rechaza entidades Grupo 2 (create / cambio RS-CC).
        if row_is_g2:
            raise ValidationError(
                {
                    'non_field_errors': [
                        'No se permiten razón social / centro de costo de Grupo 2 '
                        f'fuera de external_code_pais={EXTERNAL_CODE_PAIS_GRUPO_2}.'
                    ]
                }
            )
    elif ctx_is_g2 and not row_is_g2:
        raise ValidationError(
            {
                'non_field_errors': [
                    'Para Grupo 2 solo se permiten razón social y centro de costo '
                    f'con external_code_pais={EXTERNAL_CODE_PAIS_GRUPO_2}.'
                ]
            }
        )
    elif not ctx_is_g2 and row_is_g2:
        raise ValidationError(
            {
                'non_field_errors': [
                    'No se permiten razón social / centro de costo de Grupo 2 '
                    f'fuera de external_code_pais={EXTERNAL_CODE_PAIS_GRUPO_2}.'
                ]
            }
        )
    elif ctx and ctx != pais_row:
        raise ValidationError(
            {
                'non_field_errors': [
                    'La razón social / centro de costo no corresponden al país activo.'
                ]
            }
        )

    return pais_row
