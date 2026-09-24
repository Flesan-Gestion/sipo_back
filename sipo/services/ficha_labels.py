"""Resuelve códigos de catálogo a etiquetas legibles para ficha de ingreso."""

from __future__ import annotations

from sipo.services.candidato_maestros import (
    AFP_OPTIONS,
    SALUD_OPTIONS,
    get_bancos,
    get_estado_civil,
    get_horarios,
)

_LABEL_CACHE: dict[str, dict[str, str]] | None = None


def _options_to_map(options: list[dict] | tuple) -> dict[str, str]:
    result: dict[str, str] = {}
    for opt in options or []:
        value = str(opt.get('value') or '').strip()
        label = str(opt.get('label') or '').strip()
        nombre = str(opt.get('nombre') or '').strip()
        if not value:
            continue
        display = nombre or label or value
        result[value] = display
        result[value.upper()] = display
        result[value.lstrip('0') or '0'] = display
        if label:
            result[label] = display
        if nombre:
            result[nombre] = display
    return result


def _catalog_maps() -> dict[str, dict[str, str]]:
    global _LABEL_CACHE
    if _LABEL_CACHE is None:
        _LABEL_CACHE = {
            'afp': _options_to_map(AFP_OPTIONS),
            'isapre_fonasa': _options_to_map(SALUD_OPTIONS),
            'estado_civil': _options_to_map(get_estado_civil()),
            'banco': _options_to_map(get_bancos()),
            'horario': _options_to_map(get_horarios()),
        }
    return _LABEL_CACHE


def resolve_catalog_label(field: str, raw) -> str | None:
    if raw in (None, ''):
        return None
    text = str(raw).strip()
    mapping = _catalog_maps().get(field) or {}
    if text in mapping:
        return mapping[text]
    stripped = text.lstrip('0') or '0'
    if stripped in mapping:
        return mapping[stripped]
    # Ya es etiqueta (o código desconocido)
    return text


def resolve_ficha_catalog_fields(data: dict) -> dict:
    """Devuelve afp/isapre/estado_civil/banco/horario como etiquetas."""
    return {
        'afp': resolve_catalog_label('afp', data.get('afp')),
        'isapre_fonasa': resolve_catalog_label('isapre_fonasa', data.get('isapre_fonasa')),
        'estado_civil': resolve_catalog_label('estado_civil', data.get('estado_civil')),
        'banco': resolve_catalog_label('banco', data.get('banco')),
        'horario': resolve_catalog_label('horario', data.get('horario')),
    }
