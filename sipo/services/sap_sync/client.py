from __future__ import annotations

import base64
import json
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

from ...models import SipoObraLog

_oauth_header_cache: str | None = None


def clear_sap_auth_cache() -> None:
    global _oauth_header_cache
    _oauth_header_cache = None


def _has_basic_auth() -> bool:
    return bool(
        (getattr(settings, 'SAP_SF_BASIC_USER', '') or '').strip()
        and (getattr(settings, 'SAP_SF_BASIC_PASSWORD', '') or '').strip()
    )


def _has_oauth() -> bool:
    return bool(
        (getattr(settings, 'SAP_SF_CLIENT_ID', '') or '').strip()
        and (getattr(settings, 'SAP_SF_CLIENT_SECRET', '') or '').strip()
    )


def _sap_enabled() -> bool:
    if not getattr(settings, 'SAP_SF_SYNC_ENABLED', False):
        return False
    return _has_basic_auth() or _has_oauth()


def _get_authorization_header() -> str:
    global _oauth_header_cache

    if _has_basic_auth():
        raw = f'{settings.SAP_SF_BASIC_USER}:{settings.SAP_SF_BASIC_PASSWORD}'
        return f'Basic {base64.b64encode(raw.encode()).decode()}'

    if _oauth_header_cache:
        return _oauth_header_cache

    response = requests.post(
        settings.SAP_SF_OAUTH_URL,
        data={
            'grant_type': 'client_credentials',
            'client_id': settings.SAP_SF_CLIENT_ID,
            'client_secret': settings.SAP_SF_CLIENT_SECRET,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get('access_token')
    if not token:
        raise ValueError('SAP OAuth no retornó access_token')
    _oauth_header_cache = f'Bearer {token}'
    return _oauth_header_cache


def upsert_entity(*, entity_type: str, payload: dict | list) -> dict[str, Any]:
    if not _sap_enabled():
        return {
            'dry_run': True,
            'status': 'SKIPPED',
            'message': 'SAP_SF_SYNC_ENABLED desactivado o sin credenciales',
            'payload': payload,
        }

    auth_header = _get_authorization_header()
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    timeout = int(getattr(settings, 'SAP_SF_REQUEST_TIMEOUT', 60))
    response = requests.post(
        settings.SAP_SF_UPSERT_URL,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': auth_header,
        },
        timeout=timeout,
    )
    raw = response.text
    try:
        parsed = response.json()
    except ValueError:
        parsed = {'raw': raw}
    status = 'ERROR'
    message = ''
    if isinstance(parsed, dict) and isinstance(parsed.get('d'), list) and parsed['d']:
        first = parsed['d'][0] or {}
        status = str(first.get('status') or 'UNKNOWN')
        sap_msg = first.get('message')
        if sap_msg is not None and str(sap_msg).strip():
            message = str(sap_msg).strip()
        elif str(status).upper() not in ('OK', 'SUCCESS'):
            message = (raw or '')[:500]
    elif raw:
        message = raw[:500]
    return {
        'dry_run': False,
        'http_status': response.status_code,
        'status': status,
        'message': message,
        'response': parsed,
    }


def write_sap_log(*, sip_id: int, user_id: str, log_type: str, result: dict[str, Any]) -> None:
    """Persiste log SAP. log_data vacío en OK limpio; solo errores/warnings (paridad legado)."""
    status = str(result.get('status') or 'UNKNOWN')
    message = str(result.get('message') or '').strip()
    if str(status).upper() in ('OK', 'SUCCESS') and not message:
        message = ''
    SipoObraLog.objects.using('sip_db').create(
        sipo_id=sip_id,
        userid=user_id,
        log_type=log_type,
        log_estado=status,
        log_data=message[:2000],
        log_date=timezone.now(),
    )
