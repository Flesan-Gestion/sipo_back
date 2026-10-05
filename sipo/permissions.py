from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from .constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH, SIPO_ROL_SUPERVISOR

SUPERVISOR_ALLOWED_PREFIXES = (
    '/api/sipo/fichas',
    '/sipo/fichas',
    '/api/sipo/maestros',
    '/sipo/maestros',
    '/api/sipo/razones-sociales',
    '/sipo/razones-sociales',
    '/api/sipo/centros-costo',
    '/sipo/centros-costo',
    '/api/sipo/candidatos/maestros',
    '/sipo/candidatos/maestros',
    '/api/sipo/candidatos/validar-correo',
    '/sipo/candidatos/validar-correo',
    '/api/sipo/candidatos/validar-rut',
    '/sipo/candidatos/validar-rut',
)


def _require_authenticated(request):
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        raise APIException(
            'Authorization credentials were not provided',
            status.HTTP_401_UNAUTHORIZED,
        )
    return user


class IsSipoAuthenticated(BasePermission):
    message = "Don't have access to this resource"

    def has_permission(self, request, view):
        user = _require_authenticated(request)
        rol = int(getattr(user, 'sip_rol_id', -1) or -1)
        if rol != SIPO_ROL_SUPERVISOR:
            return True
        path = request.path or ''
        if any(path.startswith(prefix) for prefix in SUPERVISOR_ALLOWED_PREFIXES):
            return True
        raise APIException(self.message, status.HTTP_403_FORBIDDEN)


class IsSipoAdmin(BasePermission):
    message = "Don't have access to this resource"

    def has_permission(self, request, view):
        user = _require_authenticated(request)
        if int(getattr(user, 'sip_rol_id', -1)) == SIPO_ROL_ADMIN:
            return True
        raise APIException(self.message, status.HTTP_403_FORBIDDEN)


class IsSipoAdminOrRrhh(BasePermission):
    message = "Don't have access to this resource"

    def has_permission(self, request, view):
        user = _require_authenticated(request)
        if int(getattr(user, 'sip_rol_id', -1)) in (SIPO_ROL_ADMIN, SIPO_ROL_RRHH):
            return True
        raise APIException(self.message, status.HTTP_403_FORBIDDEN)
