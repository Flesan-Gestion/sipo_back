from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import AccessToken

from utils.responses import ApiResponseSuccess

from ..access import resolve_sipo_access_for_email
from ..permissions import TokenAuth
from ..repositories.auth_repository import AuthRepository
from ..token_blacklist import TokenBlacklist


class AuthView(ViewSet):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = AuthRepository()

    def _authenticate_google_user(self, request):
        credential = request.data.get('credential') or request.data.get('id_token')
        access_token = request.data.get('access_token')
        user_data = self.repository.google_validate_token(
            credential=credential,
            access_token=access_token,
        )

        email = user_data.get('email')
        if not email or not user_data.get('email_verified'):
            raise APIException('Sign In Failed', status.HTTP_400_BAD_REQUEST)

        access = resolve_sipo_access_for_email(email)
        if access is None:
            raise APIException('Usuario sin acceso a la aplicación', status.HTTP_400_BAD_REQUEST)

        return self.repository.generate_sip_token(
            email=email,
            sip_rol_id=access.rol_id,
            sip_rol_name=access.rol_name,
            google_data=user_data,
        )

    @action(
        methods=['POST'],
        detail=False,
        permission_classes=[AllowAny],
        url_path='google',
    )
    def google(self, request):
        token = self._authenticate_google_user(request)
        return ApiResponseSuccess(token.__str__()).response()

    @action(methods=['POST'], detail=False, permission_classes=[AllowAny])
    def verify(self, request):
        token = self._authenticate_google_user(request)
        return ApiResponseSuccess(token.__str__()).response()

    @action(detail=False, methods=['POST'], permission_classes=[TokenAuth])
    def extendSession(self, request):
        token_raw = str(request.headers['Authorization']).split(' ')[1]
        TokenBlacklist().add(token_raw)

        decoded_token = AccessToken(token_raw)
        old_user = decoded_token.get('user') or {}

        user = request.user
        email = getattr(user, 'email', None) or getattr(user, 'username', None)
        sip_rol_id = getattr(user, 'sip_rol_id', None)
        if not email or sip_rol_id is None:
            raise APIException('Invalid token or expired', status.HTTP_401_UNAUTHORIZED)

        access = resolve_sipo_access_for_email(email)
        token = self.repository.generate_sip_token(
            email=email,
            sip_rol_id=int(access.rol_id) if access else int(sip_rol_id),
            sip_rol_name=(access.rol_name if access else old_user.get('sip_rol_name') or ''),
            google_data={
                'given_name': old_user.get('nombres') or getattr(user, 'first_name', ''),
                'family_name': old_user.get('apellidos') or getattr(user, 'last_name', ''),
                'picture': old_user.get('avatar_url') or '',
            },
        )
        return ApiResponseSuccess(token.__str__()).response()
