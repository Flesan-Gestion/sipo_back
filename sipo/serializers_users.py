from rest_framework import serializers

from sipo.constants import SIPO_ROL_ADMIN

CORPORATE_EMAIL_SUFFIXES = ('@flesan.cl', '@dls.cl', '@inexchile.com', '@dvc.cl')


def validate_corporate_email(value: str) -> str:
    email = (value or '').strip().lower()
    if not email:
        raise serializers.ValidationError('El correo es obligatorio.')
    if '@' not in email:
        raise serializers.ValidationError('Formato de correo inválido.')
    if not any(email.endswith(domain) for domain in CORPORATE_EMAIL_SUFFIXES):
        raise serializers.ValidationError('El correo debe ser corporativo.')
    return email


class SipoAlcanceItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    external_code = serializers.CharField(required=False, allow_blank=True)
    nombre = serializers.CharField(required=False, allow_blank=True)
    empresa_rut = serializers.CharField(required=False, allow_blank=True)


class SipoPerfilRolSerializer(serializers.Serializer):
    cf_rol_id = serializers.IntegerField()
    cf_rol_name = serializers.CharField()


class SipoUsuarioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    correo = serializers.EmailField()
    rol_id = serializers.IntegerField()
    rol = serializers.CharField(allow_blank=True)
    empresas_ids = serializers.ListField(child=serializers.CharField(), required=False)
    centros_costo_ids = serializers.ListField(child=serializers.CharField(), required=False)
    empresas = SipoAlcanceItemSerializer(many=True, required=False)
    centros_costo = SipoAlcanceItemSerializer(many=True, required=False)


class SipoUsuarioCreateSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    rol_id = serializers.IntegerField(required=False)
    rol_nombre = serializers.CharField(required=False, allow_blank=True)
    cf_rol_id = serializers.IntegerField(required=False)
    empresas_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    centros_costo_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    empresas_meta = serializers.DictField(required=False)
    centros_meta = serializers.DictField(required=False)

    def validate_correo(self, value):
        return validate_corporate_email(value)

    def validate(self, attrs):
        rol_id = attrs.get('rol_id') or attrs.get('cf_rol_id')
        rol_nombre = attrs.get('rol_nombre')
        if rol_id is None and not (rol_nombre or '').strip():
            raise serializers.ValidationError({'rol_id': 'El rol es obligatorio.'})

        is_admin = int(rol_id or 0) == SIPO_ROL_ADMIN or (
            (rol_nombre or '').strip().lower() == 'administrador'
        )
        if is_admin:
            attrs['empresas_ids'] = []
            attrs['centros_costo_ids'] = []
        else:
            attrs.setdefault('empresas_ids', [])
            attrs.setdefault('centros_costo_ids', [])
        return attrs


class SipoUsuarioUpdateSerializer(serializers.Serializer):
    rol_id = serializers.IntegerField(required=False)
    rol_nombre = serializers.CharField(required=False, allow_blank=True)
    cf_rol_id = serializers.IntegerField(required=False)
    empresas_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    centros_costo_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    empresas_meta = serializers.DictField(required=False)
    centros_meta = serializers.DictField(required=False)

    def validate(self, attrs):
        has_rol = any(attrs.get(key) is not None for key in ('rol_id', 'rol_nombre', 'cf_rol_id'))
        has_scope = 'empresas_ids' in attrs or 'centros_costo_ids' in attrs
        if not has_rol and not has_scope:
            raise serializers.ValidationError(
                {'rol_id': 'Debe indicar rol y/o alcance territorial a actualizar.'}
            )

        rol_id = attrs.get('rol_id') or attrs.get('cf_rol_id')
        is_admin = rol_id is not None and int(rol_id) == SIPO_ROL_ADMIN
        if is_admin:
            attrs['empresas_ids'] = []
            attrs['centros_costo_ids'] = []
        elif has_scope:
            if 'empresas_ids' in attrs and not attrs.get('empresas_ids'):
                raise serializers.ValidationError(
                    {'empresas_ids': 'Debe asignar al menos una razón social.'}
                )
            if 'centros_costo_ids' in attrs and not attrs.get('centros_costo_ids'):
                raise serializers.ValidationError(
                    {'centros_costo_ids': 'Debe asignar al menos un centro de costo.'}
                )
        return attrs
