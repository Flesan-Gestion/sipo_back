from rest_framework.permissions import BasePermission
from .models import User
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework_simplejwt.settings import api_settings
import jwt
from .token_blacklist import TokenBlacklist
from django.urls import reverse

class TokenAuth(BasePermission):
    def has_permission(self, request, view):
        if not(request.headers.get("Authorization")):
            raise APIException("Authorization credentials were not provided", status.HTTP_401_UNAUTHORIZED)
        
        token = str(request.headers["Authorization"]).split(" ")[1]
        
        if TokenBlacklist().verify(token):
            raise APIException("This token has already been used", status.HTTP_403_FORBIDDEN)
            
        decoded_token = jwt.decode(token, algorithms=[api_settings.AUTH_TOKEN_CLASSES], options={"verify_signature": False})
        
        if decoded_token["isValid"] == False:
            raise APIException("Invalid token or expired", status.HTTP_401_UNAUTHORIZED)

        return True