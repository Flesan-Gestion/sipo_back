from rest_framework import serializers

from utils.serializers import EssentialSerializer
from .access import resolve_sipo_access_for_email
from .models import User, Rol, UserRol
from .user_display import build_display_name


class RolSerializer(EssentialSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class UserRolSerializer(EssentialSerializer):
    rol = RolSerializer()
    class Meta:
        model = UserRol
        fields = "__all__"


class UserSerializer(EssentialSerializer):
    roles = UserRolSerializer(many=True, read_only=True, relations=["rol"])
    sip_rol_id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = "__all__"

    def get_sip_rol_id(self, obj):
        access = resolve_sipo_access_for_email(getattr(obj, 'username', None))
        return access.rol_id if access is not None else 0

    def get_avatar_url(self, obj):
        return (getattr(obj, 'avatar', None) or '').strip()

    def get_display_name(self, obj):
        return build_display_name(
            getattr(obj, 'nombres', None) or getattr(obj, 'name', None),
            getattr(obj, 'apellidos', None),
        )
