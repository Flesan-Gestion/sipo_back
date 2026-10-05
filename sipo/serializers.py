from rest_framework import serializers

from .constants import (
    SIPO_ESTADO_LABELS,
    SIPO_STATUS_FINALIZADA,
    SIPO_STATUS_REGISTRO_DT,
)
from .models import SipoCandidatoObra, SipoObra, SipoSolicitudHistorial


class SipoSolicitudHistorialSerializer(serializers.ModelSerializer):
    estado_anterior_label = serializers.SerializerMethodField()
    estado_nuevo_label = serializers.SerializerMethodField()

    class Meta:
        model = SipoSolicitudHistorial
        fields = (
            'id',
            'solicitud',
            'estado_anterior',
            'estado_anterior_label',
            'estado_nuevo',
            'estado_nuevo_label',
            'usuario',
            'comentario',
            'fecha_creacion',
        )

    def get_estado_anterior_label(self, obj):
        return SIPO_ESTADO_LABELS.get(int(obj.estado_anterior), str(obj.estado_anterior))

    def get_estado_nuevo_label(self, obj):
        return SIPO_ESTADO_LABELS.get(int(obj.estado_nuevo), str(obj.estado_nuevo))


class SipoObraListSerializer(serializers.ModelSerializer):
    estado_label = serializers.SerializerMethodField()
    cargo_display = serializers.SerializerMethodField()
    cargo_subtext = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='cf_rrhh_sip_create_date', read_only=True)
    created_by_email = serializers.CharField(source='cf_rrhh_sip_create_user', read_only=True)
    closed_at = serializers.SerializerMethodField()
    closed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = SipoObra
        fields = (
            'cf_rrhh_sip_id',
            'cf_rrhh_sip_adm',
            'cf_rrhh_sip_as',
            'cf_rrhh_sip_create_user',
            'cf_rrhh_sip_rut',
            'cf_rrhh_sip_cc',
            'cf_rrhh_sip_status',
            'estado_label',
            'cf_rrhh_sip_razonsocial',
            'cf_rrhh_sip_uni',
            'cf_rrhh_sip_nombre_uni',
            'cf_rrhh_sip_nombre_cc',
            'cf_rrhh_sip_create_date',
            'cf_rrhh_sip_status_date',
            'cf_rrhh_sip_status_user',
            'cargo_display',
            'cargo_subtext',
            'created_at',
            'created_by_email',
            'closed_at',
            'closed_by_email',
        )

    def get_estado_label(self, obj):
        return SIPO_ESTADO_LABELS.get(int(obj.cf_rrhh_sip_status), str(obj.cf_rrhh_sip_status))

    def get_cargo_subtext(self, obj):
        nombre_uni = (obj.cf_rrhh_sip_nombre_uni or '').strip()
        nombre_cc = (obj.cf_rrhh_sip_nombre_cc or '').strip()
        cc = (obj.cf_rrhh_sip_cc or '').strip()
        parts = []
        if nombre_uni:
            parts.append(f'[{nombre_uni}]')
        if nombre_cc:
            parts.append(nombre_cc)
        if cc:
            parts.append(f'[{cc}]')
        return ' '.join(parts) if parts else ''

    def get_closed_at(self, obj):
        if int(obj.cf_rrhh_sip_status) in (SIPO_STATUS_FINALIZADA, SIPO_STATUS_REGISTRO_DT):
            return obj.cf_rrhh_sip_status_date
        return None

    def get_closed_by_email(self, obj):
        if int(obj.cf_rrhh_sip_status) in (SIPO_STATUS_FINALIZADA, SIPO_STATUS_REGISTRO_DT):
            return obj.cf_rrhh_sip_status_user
        return None

    def get_cargo_display(self, obj):
        razon = (obj.cf_rrhh_sip_razonsocial or '').strip()
        return razon or f'Solicitud N°{obj.cf_rrhh_sip_id}'


class SipoObraDetailSerializer(serializers.ModelSerializer):
    estado_label = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    acciones_estado = serializers.SerializerMethodField()
    candidatos_count = serializers.SerializerMethodField()
    candidatos_seleccionados_count = serializers.SerializerMethodField()
    historial = serializers.SerializerMethodField()

    class Meta:
        model = SipoObra
        fields = (
            'cf_rrhh_sip_id',
            'cf_rrhh_sip_rut',
            'cf_rrhh_sip_razonsocial',
            'cf_rrhh_sip_uni',
            'cf_rrhh_sip_nombre_uni',
            'cf_rrhh_sip_dep',
            'cf_rrhh_sip_nombre_dep',
            'cf_rrhh_sip_cc',
            'cf_rrhh_sip_nombre_cc',
            'cf_rrhh_sip_adm',
            'cf_rrhh_sip_as',
            'cf_rrhh_sip_ubicacion',
            'cf_rrhh_sip_status',
            'estado_label',
            'cf_rrhh_sip_create_date',
            'cf_rrhh_sip_create_user',
            'cf_rrhh_sip_update_date',
            'cf_rrhh_sip_update_user',
            'cf_rrhh_sip_status_date',
            'cf_rrhh_sip_status_user',
            'can_edit',
            'acciones_estado',
            'candidatos_count',
            'candidatos_seleccionados_count',
            'historial',
        )

    def get_estado_label(self, obj):
        return SIPO_ESTADO_LABELS.get(int(obj.cf_rrhh_sip_status), str(obj.cf_rrhh_sip_status))

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        from .services.crud import user_can_edit_obra
        return user_can_edit_obra(obj, request.user)

    def get_acciones_estado(self, obj):
        request = self.context.get('request')
        if not request:
            return []
        from .services.estados import get_acciones_estado
        return get_acciones_estado(obj, request.user)

    def get_candidatos_count(self, obj):
        from .services.estados import count_candidatos_activos
        return count_candidatos_activos(obj.cf_rrhh_sip_id)

    def get_candidatos_seleccionados_count(self, obj):
        from .services.candidatos_seleccionados import count_candidatos_seleccionados
        return count_candidatos_seleccionados(obj.cf_rrhh_sip_id)

    def get_historial(self, obj):
        from .services.estados import list_historial_solicitud
        rows = list_historial_solicitud(obj.cf_rrhh_sip_id)
        return SipoSolicitudHistorialSerializer(rows, many=True).data


class SipoObraWriteSerializer(serializers.Serializer):
    cf_rrhh_sip_rut = serializers.CharField(max_length=15)
    cf_rrhh_sip_razonsocial = serializers.CharField(max_length=200)
    cf_rrhh_sip_uni = serializers.CharField(max_length=10)
    cf_rrhh_sip_nombre_uni = serializers.CharField(max_length=100)
    cf_rrhh_sip_dep = serializers.CharField(max_length=100)
    cf_rrhh_sip_nombre_dep = serializers.CharField(max_length=100)
    cf_rrhh_sip_cc = serializers.CharField(max_length=100)
    cf_rrhh_sip_nombre_cc = serializers.CharField(max_length=100)
    cf_rrhh_sip_adm = serializers.EmailField()
    cf_rrhh_sip_as = serializers.EmailField()
    cf_rrhh_sip_ubicacion = serializers.CharField(max_length=100)
    external_code_pais = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate(self, attrs):
        from .services.pais_segregation import (
            assert_create_only_grupo2,
            validate_razon_social_centro_costo,
        )

        attrs['external_code_pais'] = assert_create_only_grupo2(attrs.get('external_code_pais'))
        validate_razon_social_centro_costo(
            razon_social_id=attrs.get('cf_rrhh_sip_rut'),
            centro_costo_id=attrs.get('cf_rrhh_sip_cc'),
            external_code_pais=attrs['external_code_pais'],
        )
        return attrs


class SipoObraPatchSerializer(serializers.Serializer):
    cf_rrhh_sip_rut = serializers.CharField(max_length=15, required=False)
    cf_rrhh_sip_razonsocial = serializers.CharField(max_length=200, required=False)
    cf_rrhh_sip_uni = serializers.CharField(max_length=10, required=False)
    cf_rrhh_sip_nombre_uni = serializers.CharField(max_length=100, required=False)
    cf_rrhh_sip_dep = serializers.CharField(max_length=100, required=False)
    cf_rrhh_sip_nombre_dep = serializers.CharField(max_length=100, required=False)
    cf_rrhh_sip_cc = serializers.CharField(max_length=100, required=False)
    cf_rrhh_sip_nombre_cc = serializers.CharField(max_length=100, required=False)
    cf_rrhh_sip_adm = serializers.EmailField(required=False)
    cf_rrhh_sip_as = serializers.EmailField(required=False)
    cf_rrhh_sip_ubicacion = serializers.CharField(max_length=100, required=False)
    external_code_pais = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate(self, attrs):
        from .services.pais_segregation import validate_razon_social_centro_costo

        obra = self.context.get('obra')
        rs_changed = 'cf_rrhh_sip_rut' in attrs
        cc_changed = 'cf_rrhh_sip_cc' in attrs
        pais_in_payload = 'external_code_pais' in attrs
        if not (rs_changed or cc_changed or pais_in_payload):
            return attrs

        rs = attrs.get('cf_rrhh_sip_rut')
        cc = attrs.get('cf_rrhh_sip_cc')
        if rs is None and obra is not None:
            rs = getattr(obra, 'cf_rrhh_sip_rut', None)
        if cc is None and obra is not None:
            cc = getattr(obra, 'cf_rrhh_sip_cc', None)
        validate_razon_social_centro_costo(
            razon_social_id=rs,
            centro_costo_id=cc,
            external_code_pais=attrs.get('external_code_pais'),
        )
        return attrs


class SipoCambiarEstadoSerializer(serializers.Serializer):
    nuevo_estado = serializers.IntegerField()
    comentario = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SipoCancelarSerializer(serializers.Serializer):
    comentario = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SipoCandidatoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    docs_ok = serializers.SerializerMethodField()

    class Meta:
        model = SipoCandidatoObra
        fields = '__all__'
        read_only_fields = (
            'cf_rrhh_sip_obra_sueldo_base',
            'cf_rrhh_sip_obra_bono_mineria',
            'cf_rrhh_sip_obra_candidato_estado_builder',
        )

    def to_representation(self, instance):
        from .services.candidato_validaciones import sanitize_address_data

        data = super().to_representation(instance)
        return sanitize_address_data(data)

    def get_nombre_completo(self, obj):
        parts = [
            obj.cf_rrhh_sip_obra_candidato_nombre,
            obj.cf_rrhh_sip_obra_candidato_segundo_nombre,
            obj.cf_rrhh_sip_obra_candidato_ap,
            obj.cf_rrhh_sip_obra_candidato_am,
        ]
        return ' '.join(p.strip() for p in parts if p and str(p).strip())

    def get_docs_ok(self, obj):
        return all(
            bool((getattr(obj, f) or '').strip())
            for f in (
                'cf_rrhh_sip_obra_candidato_ci',
                'cf_rrhh_sip_obra_candidato_afp',
                'cf_rrhh_sip_obra_candidato_salud',
                'cf_rrhh_sip_obra_candidato_domi',
            )
        )


_CANDIDATO_DOC_FIELDS = (
    'cf_rrhh_sip_obra_candidato_ci',
    'cf_rrhh_sip_obra_candidato_afp',
    'cf_rrhh_sip_obra_candidato_salud',
    'cf_rrhh_sip_obra_candidato_domi',
)


def _resolve_candidato_doc_url(request, instance, field_name, stored_value):
    from django.urls import reverse

    from .services.candidato_docs import (
        DOC_TYPE_BY_FIELD,
        candidato_doc_is_available,
        is_external_candidato_doc_url,
    )

    raw = (stored_value or '').strip()
    if not raw:
        return None
    if is_external_candidato_doc_url(raw):
        return raw
    if not candidato_doc_is_available(raw):
        return None
    if request is None:
        return raw

    doc_type = DOC_TYPE_BY_FIELD.get(field_name)
    if not doc_type:
        return raw

    path = reverse(
        'sipo-candidato-documento',
        kwargs={
            'sip_id': int(instance.cf_rrhh_sip_obra_id),
            'candidato_id': str(instance.cf_rrhh_sip_obra_candidato_id),
            'doc_type': doc_type,
        },
    )
    return request.build_absolute_uri(path)


class SipoCandidatoSeleccionadoSerializer(SipoCandidatoSerializer):
    revision_dt = serializers.SerializerMethodField()

    class Meta(SipoCandidatoSerializer.Meta):
        pass

    def get_revision_dt(self, obj):
        return str(obj.cf_rrhh_sip_obra_candidato_registro_dt or '').strip() == '1'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        for field in _CANDIDATO_DOC_FIELDS:
            stored = getattr(instance, field, None)
            data[field] = _resolve_candidato_doc_url(request, instance, field, stored)
        return data


def _opt_char(max_length=100):
    return serializers.CharField(
        max_length=max_length, required=False, allow_blank=True, allow_null=True
    )


def _req_char(max_length=100):
    return serializers.CharField(
        max_length=max_length, required=True, allow_blank=False, allow_null=False
    )


class SipoCandidatoWriteSerializer(serializers.Serializer):
    cf_rrhh_sip_obra_candidato_tratamiento = _req_char(50)
    cf_rrhh_sip_obra_candidato_rut = _req_char(15)
    cf_rrhh_sip_obra_candidato_nombre = _req_char(100)
    cf_rrhh_sip_obra_candidato_segundo_nombre = _opt_char(100)
    cf_rrhh_sip_obra_candidato_ap = _req_char(100)
    cf_rrhh_sip_obra_candidato_am = _req_char(100)
    cf_rrhh_sip_obra_candidato_genero = _req_char(50)
    cf_rrhh_sip_obra_candidato_fecha_nacimiento = serializers.DateField(
        required=True, allow_null=False
    )
    cf_rrhh_sip_obra_candidato_pais_nacimiento = _req_char(100)
    cf_rrhh_sip_obra_candidato_region_nacimiento = _req_char(100)
    cf_rrhh_sip_obra_candidato_nacionalidad = _req_char(100)
    cf_rrhh_sip_obra_candidato_nacionalidad_ext = _opt_char(100)
    cf_rrhh_sip_obra_candidato_region = _req_char(100)
    cf_rrhh_sip_obra_candidato_ciudad = _req_char(100)
    cf_rrhh_sip_obra_candidato_comuna = _req_char(100)
    cf_rrhh_sip_obra_candidato_villa = _opt_char(200)
    cf_rrhh_sip_obra_candidato_direccion = _req_char(200)
    cf_rrhh_sip_obra_candidato_numero_dire = _req_char(50)
    cf_rrhh_sip_obra_candidato_num_depto = _opt_char(50)
    cf_rrhh_sip_obra_candidato_estado_civil = _req_char(50)
    cf_rrhh_sip_obra_candidato_telefono = _req_char(50)
    cf_rrhh_sip_obra_candidato_correo = serializers.EmailField(
        required=True, allow_blank=False, allow_null=False
    )
    cf_rrhh_sip_obra_candidato_metodo_pago = _req_char(50)
    cf_rrhh_sip_obra_candidato_banco = _req_char(50)
    cf_rrhh_sip_obra_candidato_numcta = _req_char(100)
    cf_rrhh_sip_obra_candidato_anticipo = _opt_char(50)
    cf_rrhh_sip_obra_candidato_nomcar = _req_char(100)
    cf_rrhh_sip_obra_candidato_jefe_user_id = _req_char(50)
    cf_rrhh_sip_obra_candidato_jefe_nombre = _req_char(255)
    cf_rrhh_sip_obra_candidato_jefe_correo = _opt_char(150)
    cf_rrhh_sip_obra_candidato_horario_trabajo = _req_char(100)
    cf_rrhh_sip_obra_candidato_sueldo = _req_char(100)
    cf_rrhh_sip_obra_candidato_cuenta_gasto = _req_char(100)
    cf_rrhh_sip_obra_candidato_tipo_contrato = _req_char(100)
    cf_rrhh_sip_obra_candidato_fecha_ingreso = serializers.DateField(
        required=True, allow_null=False
    )
    cf_rrhh_sip_obra_candidato_termino_contrato = _opt_char(200)
    cf_rrhh_sip_obra_candidato_fecha_termino_ito = _opt_char(100)
    cf_rrhh_sip_obra_candidato_jubilado = _req_char(50)
    cf_rrhh_sip_obra_candidato_nom_afp = _req_char(100)
    cf_rrhh_sip_obra_candidato_nom_salud = _req_char(100)
    cf_rrhh_sip_obra_candidato_valor_plan = _opt_char(50)
    cf_rrhh_sip_obra_candidato_valor_uf = _opt_char(50)
    cf_rrhh_sip_obra_candidato_seguro_covid = _opt_char(50)
    cf_rrhh_sip_obra_candidato_ci = _opt_char(200)
    cf_rrhh_sip_obra_candidato_afp = _opt_char(200)
    cf_rrhh_sip_obra_candidato_salud = _opt_char(200)
    cf_rrhh_sip_obra_candidato_domi = _opt_char(200)
    cf_rrhh_sip_obra_candidato_doc_jubi = _opt_char(200)
    cf_rrhh_sip_obra_candidato_jubi = _opt_char(200)
    cf_rrhh_sip_obra_candidato_visa = _opt_char(200)
    cf_rrhh_sip_obra_candidato_permiso_trabajo = _opt_char(200)
    cf_rrhh_sip_obra_candidato_copia_seguro_covid = _opt_char(200)

    def validate(self, attrs):
        from .services.candidato_fields import REQUIRED_FIELDS, is_blank_value
        from .services.candidato_validaciones import (
            FONASA_SIN_PLAN,
            requires_valor_plan,
            sanitize_address_data,
            validate_candidato_negocio,
        )
        from rest_framework.exceptions import ValidationError

        errors = {}
        for key, value in list(attrs.items()):
            if isinstance(value, str):
                stripped = value.strip()
                if stripped != value:
                    attrs[key] = stripped
                if key in REQUIRED_FIELDS and is_blank_value(attrs[key]):
                    errors[key] = ['Este campo no puede estar vacío ni contener solo espacios.']

        for key in REQUIRED_FIELDS:
            if key not in attrs or is_blank_value(attrs.get(key)):
                errors[key] = ['Este campo es obligatorio.']

        if errors:
            raise ValidationError(errors)

        data = validate_candidato_negocio(dict(attrs))

        salud = (data.get('cf_rrhh_sip_obra_candidato_nom_salud') or '').strip()
        if requires_valor_plan(salud):
            if not (data.get('cf_rrhh_sip_obra_candidato_valor_plan') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_valor_plan'] = (
                    'Debe indicar el valor del plan de salud.'
                )
            elif (data.get('cf_rrhh_sip_obra_candidato_valor_plan') or '').strip() == 'UF':
                if not (data.get('cf_rrhh_sip_obra_candidato_valor_uf') or '').strip():
                    errors['cf_rrhh_sip_obra_candidato_valor_uf'] = (
                        'Debe indicar el valor en UF.'
                    )
        elif salud in FONASA_SIN_PLAN:
            data['cf_rrhh_sip_obra_candidato_valor_plan'] = None
            data['cf_rrhh_sip_obra_candidato_valor_uf'] = None

        tipo = (data.get('cf_rrhh_sip_obra_candidato_tipo_contrato') or '').strip()
        if tipo == 'Plazo Fijo':
            if not (data.get('cf_rrhh_sip_obra_candidato_termino_contrato') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_termino_contrato'] = (
                    'Debe indicar la fecha término plazo fijo.'
                )
        elif tipo == 'Obra o Faena':
            if not (data.get('cf_rrhh_sip_obra_candidato_termino_contrato') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_termino_contrato'] = (
                    'Debe indicar el HITO.'
                )
            if not (data.get('cf_rrhh_sip_obra_candidato_fecha_termino_ito') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_fecha_termino_ito'] = (
                    'Debe indicar la fecha de término HITO.'
                )
        elif tipo == 'Indefinido':
            data['cf_rrhh_sip_obra_candidato_termino_contrato'] = 'Indefinido'
            data['cf_rrhh_sip_obra_candidato_fecha_termino_ito'] = None

        seguro = (data.get('cf_rrhh_sip_obra_candidato_seguro_covid') or '').strip().lower()
        if seguro in ('si', 'sí'):
            if not (data.get('cf_rrhh_sip_obra_candidato_copia_seguro_covid') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_copia_seguro_covid'] = (
                    'Debe adjuntar la copia del seguro COVID.'
                )

        nac = (data.get('cf_rrhh_sip_obra_candidato_nacionalidad') or '').strip()
        if nac in ('Extranjero', 'Extranjero-Definitiva'):
            if not (data.get('cf_rrhh_sip_obra_candidato_nacionalidad_ext') or '').strip():
                errors['cf_rrhh_sip_obra_candidato_nacionalidad_ext'] = (
                    'Debe indicar la nacionalidad extranjera.'
                )

        if errors:
            raise ValidationError(errors)
        return sanitize_address_data(data)


class SipoSeleccionarTodosSerializer(serializers.Serializer):
    seleccionado = serializers.IntegerField(min_value=0, max_value=1)