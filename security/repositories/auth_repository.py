import os

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.tokens import AccessToken

from ..models import User
from ..serializers import UserSerializer
from ..user_display import build_display_name


class AuthRepository:

    def _google_client_id(self) -> str:
        return (os.getenv('GOOGLE_CLIENT_ID') or '').strip().strip('"')

    def generateToken(self, user: User):
        token = AccessToken.for_user(user)
        token['user'] = UserSerializer(user, relations=['roles']).data
        token['isValid'] = True
        return token

    def generate_sip_token(
        self,
        *,
        email: str,
        sip_rol_id: int,
        sip_rol_name: str = '',
        google_data: dict | None = None,
    ) -> AccessToken:
        google_data = google_data or {}
        normalized_email = (email or '').strip().lower()
        rol_id = int(sip_rol_id)
        rol_name = (sip_rol_name or '').strip()
        nombres = google_data.get('given_name') or google_data.get('name') or ''
        apellidos = google_data.get('family_name') or ''
        avatar_url = (google_data.get('picture') or google_data.get('avatar_url') or '').strip()

        token = AccessToken.for_user(User(pk=None))
        token['user_id'] = None
        token['isValid'] = True
        token['sip_rol_id'] = rol_id
        token['email'] = normalized_email
        token['user'] = {
            'id_aplicacion_usuario': 0,
            'username': normalized_email,
            'nombres': nombres,
            'apellidos': apellidos,
            'display_name': build_display_name(nombres, apellidos),
            'avatar_url': avatar_url,
            'estado_sesion': 1,
            'sip_rol_id': rol_id,
            'sip_rol_name': rol_name,
            'roles': [{'rol': {'id_rol': rol_id, 'nombre': rol_name}}],
        }
        return token

    def generateCustomToken(self, properties):
        token = AccessToken.for_user(User(pk=None))
        token.payload.update(properties)
        token['isValid'] = False
        return token

    def generateScopedToken(self, routes):
        token = AccessToken.for_user(User(pk=None))
        token.payload.update({
            'routes': routes,
            'user': None,
            'isValid': True,
        })
        return token

    def _normalize_google_user_data(self, user_info: dict) -> dict:
        email_verified = user_info.get('email_verified')
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == 'true'

        return {
            'email': (user_info.get('email') or '').strip().lower(),
            'email_verified': bool(email_verified),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'given_name': user_info.get('given_name'),
            'family_name': user_info.get('family_name'),
            'sub': user_info.get('sub'),
        }

    def google_validate_id_token(self, token_value: str) -> dict:
        try:
            idinfo = id_token.verify_oauth2_token(
                token_value,
                google_requests.Request(),
                self._google_client_id(),
            )
        except ValueError as exc:
            raise APIException('Sign In Failed', status.HTTP_400_BAD_REQUEST) from exc

        issuer = idinfo.get('iss')
        if issuer not in ('accounts.google.com', 'https://accounts.google.com'):
            raise APIException('Sign In Failed', status.HTTP_400_BAD_REQUEST)

        return self._normalize_google_user_data(idinfo)

    def google_validate_access_token(self, access_token: str) -> dict:
        token_info = requests.get(
            f"{os.getenv('GOOGLE_TOKEN_INFO_URL')}{access_token}",
            timeout=10,
        )

        if not token_info.ok or token_info.json().get('aud') != self._google_client_id():
            raise APIException('Sign In Failed', status.HTTP_400_BAD_REQUEST)

        user_info = requests.get(
            os.getenv('GOOGLE_USER_INFO_URL'),
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )

        if not user_info.ok:
            raise APIException('Sign In Failed', status.HTTP_400_BAD_REQUEST)

        return self._normalize_google_user_data(user_info.json())

    def google_validate_token(self, *, credential: str | None = None, access_token: str | None = None) -> dict:
        if credential:
            return self.google_validate_id_token(credential)
        if access_token:
            return self.google_validate_access_token(access_token)
        raise APIException('Token requerido', status.HTTP_400_BAD_REQUEST)
