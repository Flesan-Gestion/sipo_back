from functools import wraps
from rest_framework.exceptions import APIException
from rest_framework import status
import jwt
from rest_framework_simplejwt.settings import api_settings
from .token_blacklist import TokenBlacklist
from django.urls import reverse
from rest_framework.request import Request

def scoped_token():
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(view_instance, request, *args, **kwargs):
            token = str(request.headers["Authorization"]).split(" ")[1]
            decoded_token = jwt.decode(token, algorithms=[api_settings.AUTH_TOKEN_CLASSES], options={"verify_signature": False})

            if decoded_token.get("routes"):
                if request.path not in [reverse(route) for route in decoded_token["routes"]]:
                    raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)
                TokenBlacklist().add(token)

            request.scope_token_validation = True
            return view_func(view_instance, request, *args, **kwargs)

        return wrapper

    return decorator


def role_required(roles = []):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(view_instance, request, *args, **kwargs):
            if hasattr(request, 'scope_token_validation') :
                return view_func(view_instance, request, *args, **kwargs)
            
            hasAcccess = False
            rolesInDb = request.user.roles.all()
            for rol in rolesInDb:
                if str(rol.rol.id_rol) in roles:
                    hasAcccess = True
            
            if (hasAcccess):
                return view_func(view_instance, request, *args, **kwargs)
                        
            raise APIException("Don't have access to this resource", status.HTTP_403_FORBIDDEN)
        return wrapper

    return decorator
