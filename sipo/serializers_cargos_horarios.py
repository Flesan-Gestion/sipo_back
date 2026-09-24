from rest_framework import serializers


class SipoConfigCargoAssignSerializer(serializers.Serializer):
    empresa_id = serializers.CharField(max_length=60)
    external_code = serializers.CharField(max_length=50)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area_personal = serializers.CharField(max_length=50, required=False, allow_blank=True)


class SipoConfigCargoToggleSerializer(serializers.Serializer):
    empresa_id = serializers.CharField(max_length=60)
    id = serializers.IntegerField(required=False)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True)
    activo = serializers.BooleanField()


class SipoConfigHorarioAssignSerializer(serializers.Serializer):
    empresa_id = serializers.CharField(max_length=60)
    external_code = serializers.CharField(max_length=50)
    descripcion = serializers.CharField(max_length=200, required=False, allow_blank=True)


class SipoConfigHorarioDeleteSerializer(serializers.Serializer):
    empresa_id = serializers.CharField(max_length=60)
    external_code = serializers.CharField(max_length=50)
