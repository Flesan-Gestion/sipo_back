import logging

import requests
from django.conf import settings
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


def validar_correo_smtp(correo: str) -> bool:
    """Réplica ValidacionCorreo / SIP Nuevo verificar-correo (Abstract API)."""
    correo = (correo or '').strip()
    if not correo:
        return False

    api_key = (getattr(settings, 'ABSTRACT_EMAIL_VALIDATION_API_KEY', None) or '').strip()
    base_url = (
        getattr(settings, 'ABSTRACT_EMAIL_VALIDATION_BASE_URL', None)
        or 'https://emailvalidation.abstractapi.com/v1/'
    ).rstrip('/')
    try:
        timeout = max(1, int(getattr(settings, 'ABSTRACT_EMAIL_VALIDATION_TIMEOUT', 10)))
    except (TypeError, ValueError):
        timeout = 10

    if not api_key:
        logger.warning('Abstract email: API key ausente; fallback valido=true correo=%s', correo)
        return True

    try:
        response = requests.get(
            base_url + '/',
            params={'api_key': api_key, 'email': correo},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        smtp_valid = payload.get('is_smtp_valid')
        if isinstance(smtp_valid, dict):
            return bool(smtp_valid.get('value'))
        return bool(smtp_valid)
    except (RequestException, Timeout, ValueError, TypeError) as exc:
        logger.exception('Abstract email failed correo=%s: %s', correo, exc)
        return True
