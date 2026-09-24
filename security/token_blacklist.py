from django.core.cache import cache
import jwt
from rest_framework_simplejwt.settings import api_settings


class TokenBlacklist():
    
    def add(self, token:str):
        decoded_token = jwt.decode(token, algorithms=[api_settings.AUTH_TOKEN_CLASSES], options={"verify_signature": False})
        jti = decoded_token["jti"]
        cache.set(f"blacklist_{jti}", token)
        
    def verify(self, token:str):
        decoded_token = jwt.decode(token, algorithms=[api_settings.AUTH_TOKEN_CLASSES], options={"verify_signature": False})
        jti = decoded_token["jti"]
        return True if cache.get(f"blacklist_{jti}") else False
