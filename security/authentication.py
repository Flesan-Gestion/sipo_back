from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .sip_session_user import SipSessionUser


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        return user, validated_token

    def get_user(self, validated_token):
        try:
            return SipSessionUser.from_token(validated_token)
        except ValueError as exc:
            raise InvalidToken(
                'Token contained no recognizable user identification',
            ) from exc

    def get_validated_token(self, raw_token):
        for AuthToken in api_settings.AUTH_TOKEN_CLASSES:
            try:
                return AuthToken(raw_token)
            except TokenError as exc:
                raise InvalidToken('Invalid token or expired') from exc

        raise InvalidToken('Invalid token or expired')
