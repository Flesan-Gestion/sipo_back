"""Upload de documentos candidato obra (paridad legado 4MB)."""

from __future__ import annotations

import os
import re

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError

DOC_FIELD_MAP = {
    'ci': 'cf_rrhh_sip_obra_candidato_ci',
    'afp': 'cf_rrhh_sip_obra_candidato_afp',
    'salud': 'cf_rrhh_sip_obra_candidato_salud',
    'domi': 'cf_rrhh_sip_obra_candidato_domi',
    'domicilio': 'cf_rrhh_sip_obra_candidato_domi',
    'seguro_covid': 'cf_rrhh_sip_obra_candidato_copia_seguro_covid',
    'copia_seguro_covid': 'cf_rrhh_sip_obra_candidato_copia_seguro_covid',
}

DOC_TYPE_BY_FIELD = {
    'cf_rrhh_sip_obra_candidato_ci': 'ci',
    'cf_rrhh_sip_obra_candidato_afp': 'afp',
    'cf_rrhh_sip_obra_candidato_salud': 'salud',
    'cf_rrhh_sip_obra_candidato_domi': 'domi',
    'cf_rrhh_sip_obra_candidato_copia_seguro_covid': 'seguro_covid',
}

CANDIDATO_DOC_DB_FIELDS = tuple(DOC_TYPE_BY_FIELD.keys())

ALLOWED_EXTENSIONS = frozenset({'pdf', 'png', 'jpg', 'jpeg', 'webp'})
MAX_BYTES = 4 * 1024 * 1024  # 4 MB
FILE_PREFIX = {
    'ci': 'CI',
    'afp': 'AFP',
    'salud': 'SALUD',
    'domi': 'DOMI',
    'domicilio': 'DOMI',
    'seguro_covid': 'COVID',
    'copia_seguro_covid': 'COVID',
}


def _sanitize_rut(rut: str) -> str:
    cleaned = re.sub(r'[^0-9Kk]', '', (rut or '').strip())
    return cleaned or 'sinrut'


def normalize_candidato_doc_value(value: str | None) -> str | None:
    raw = (value or '').strip()
    if not raw:
        return None

    media_marker = '/media/'
    if raw.startswith('http://') or raw.startswith('https://'):
        idx = raw.lower().find(media_marker)
        if idx >= 0:
            return raw[idx + len(media_marker) :].lstrip('/')
        return raw

    if raw.startswith('/media/'):
        return raw[len('/media/') :].lstrip('/')
    if raw.startswith('media/'):
        return raw[len('media/') :].lstrip('/')
    return raw.lstrip('/')


def is_external_candidato_doc_url(value: str | None) -> bool:
    raw = (value or '').strip()
    if not raw.startswith('http://') and not raw.startswith('https://'):
        return False
    return '/media/' not in raw.lower()


def resolve_local_candidato_doc_path(value: str | None) -> str | None:
    normalized = normalize_candidato_doc_value(value)
    if not normalized or is_external_candidato_doc_url(normalized):
        return None
    absolute_path = os.path.join(settings.MEDIA_ROOT, *normalized.split('/'))
    return absolute_path if os.path.isfile(absolute_path) else None


def candidato_doc_is_available(value: str | None) -> bool:
    raw = (value or '').strip()
    if not raw:
        return False
    if is_external_candidato_doc_url(raw):
        return True
    return resolve_local_candidato_doc_path(raw) is not None


def validate_candidato_document(uploaded_file) -> str:
    if uploaded_file is None:
        raise ValidationError({'file': 'Debe adjuntar un archivo.'})

    original = getattr(uploaded_file, 'name', '') or ''
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            {
                'file': (
                    f'Extensión no permitida. Use: '
                    f'{", ".join(sorted(ALLOWED_EXTENSIONS))}.'
                )
            }
        )

    size = getattr(uploaded_file, 'size', None)
    if size is None:
        try:
            uploaded_file.seek(0, os.SEEK_END)
            size = uploaded_file.tell()
            uploaded_file.seek(0)
        except Exception:
            size = 0
    if size > MAX_BYTES:
        raise ValidationError({'file': 'No puede subir un archivo que pese más de 4 MB.'})

    return ext


def save_candidato_document(
    *,
    uploaded_file,
    doc_type: str,
    sip_id: int,
    rut: str,
) -> dict:
    """
    Guarda en MEDIA_ROOT/candidatos_obra/sip_<id>/PREFIX<rut>.<ext>
    Retorna {url, path, field, doc_type}.
    """
    key = (doc_type or '').strip().lower()
    if key not in DOC_FIELD_MAP:
        raise ValidationError(
            {'doc_type': f'Tipo inválido. Use: {", ".join(sorted(set(DOC_FIELD_MAP)))}.'}
        )

    ext = validate_candidato_document(uploaded_file)
    prefix = FILE_PREFIX[key]
    rut_safe = _sanitize_rut(rut)
    relative_dir = f'candidatos_obra/sip_{sip_id}'
    filename = f'{prefix}{rut_safe}.{ext}'
    relative_path = f'{relative_dir}/{filename}'

    media_root = settings.MEDIA_ROOT
    absolute_dir = os.path.join(media_root, *relative_dir.split('/'))
    absolute_path = os.path.join(absolute_dir, filename)
    os.makedirs(absolute_dir, exist_ok=True)

    if hasattr(uploaded_file, 'seek'):
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

    with open(absolute_path, 'wb') as destination:
        if hasattr(uploaded_file, 'chunks'):
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        else:
            destination.write(uploaded_file.read())

    media_url = (settings.MEDIA_URL or '/media/').rstrip('/')
    public_url = f'{media_url}/{relative_path}'
    return {
        'doc_type': key if key != 'domicilio' else 'domi',
        'field': DOC_FIELD_MAP[key],
        'path': relative_path,
        'url': public_url,
        'filename': filename,
        'size': getattr(uploaded_file, 'size', None),
    }
