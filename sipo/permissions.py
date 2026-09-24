from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from .constants import SIPO_ROL_ADMIN, SIPO_ROL_RRHH


def _require_authenticated(request):
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        raise APIException(
            'Authorization credentials were not provided',
            status.HTTP_401_UNAUTHORIZED,
        )
    return user


class IsSipoAuthenticated(BasePermission):
    def has_permission(self, request, view):
        _require_authenticated(request)
        return True


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
