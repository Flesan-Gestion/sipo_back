from rest_framework import serializers

from sipo.models_ficha import SipoFichaIngreso
from sipo.services.ficha_labels import resolve_catalog_label
from sipo.services.fichas import (
    accion_aprobar_label,
    user_can_aprobar_ficha,
    user_can_editar_ficha,
    user_can_eliminar_ficha,
    user_can_rechazar_ficha,
    user_can_retroceder_ficha,
)


class SipoFichaIngresoListSerializer(serializers.ModelSerializer):
    nombre_colaborador = serializers.CharField(read_only=True)
    centro_costo = serializers.SerializerMethodField()
    razon_social = serializers.CharField(source='razon_social_nombre', read_only=True)
    estado_label = serializers.CharField(read_only=True)
    can_aprobar = serializers.SerializerMethodField()
    can_rechazar = serializers.SerializerMethodField()
    can_editar = serializers.SerializerMethodField()
    can_retroceder = serializers.SerializerMethodField()
    can_eliminar = serializers.SerializerMethodField()
    accion_aprobar_label = serializers.SerializerMethodField()

    class Meta:
        model = SipoFichaIngreso
        fields = (
            'id',
            'rut',
            'nombre_colaborador',
            'centro_costo',
            'centro_costo_id',
            'centro_costo_nombre',
            'razon_social',
            'razon_social_id',
            'razon_social_nombre',
            'fecha_ingreso',
            'cargo',
            'estado',
            'estado_label',
            'can_aprobar',
            'can_rechazar',
            'can_editar',
            'can_retroceder',
            'can_eliminar',
            'accion_aprobar_label',
            'correo_jefe_directo',
            'correo_admin_obra',
            'created_at',
        )

    def get_centro_costo(self, obj):
        if obj.centro_costo_nombre and obj.centro_costo_id:
            return f'{obj.centro_costo_id} — {obj.centro_costo_nombre}'
        return obj.centro_costo_nombre or obj.centro_costo_id or ''

    def get_can_aprobar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_aprobar_ficha(obj, user)

    def get_can_rechazar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_rechazar_ficha(obj, user)

    def get_can_editar(self, obj):
        return user_can_editar_ficha(obj, None)

    def get_can_retroceder(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_retroceder_ficha(obj, user)

    def get_can_eliminar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_eliminar_ficha(obj, user)

    def get_accion_aprobar_label(self, obj):
        return accion_aprobar_label(obj.estado)


class SipoFichaIngresoDetailSerializer(serializers.ModelSerializer):
    nombre_colaborador = serializers.CharField(read_only=True)
    estado_label = serializers.CharField(read_only=True)
    can_aprobar = serializers.SerializerMethodField()
    can_rechazar = serializers.SerializerMethodField()
    can_editar = serializers.SerializerMethodField()
    can_retroceder = serializers.SerializerMethodField()
    can_eliminar = serializers.SerializerMethodField()
    accion_aprobar_label = serializers.SerializerMethodField()
    afp = serializers.SerializerMethodField()
    isapre_fonasa = serializers.SerializerMethodField()
    estado_civil = serializers.SerializerMethodField()
    banco = serializers.SerializerMethodField()
    horario = serializers.SerializerMethodField()
    doc_domicilio_url = serializers.SerializerMethodField()
    doc_titulo_url = serializers.SerializerMethodField()
    doc_afp_url = serializers.SerializerMethodField()
    doc_salud_url = serializers.SerializerMethodField()
    doc_cedula_url = serializers.SerializerMethodField()

    class Meta:
        model = SipoFichaIngreso
        fields = (
            'id',
            'razon_social_id',
            'razon_social_nombre',
            'obra',
            'centro_costo_id',
            'centro_costo_nombre',
            'cargo',
            'fecha_ingreso',
            'correo_jefe_directo',
            'correo_admin_obra',
            'nombres',
            'apellido_paterno',
            'apellido_materno',
            'nombre_colaborador',
            'rut',
            'tratamiento',
            'genero',
            'afp',
            'isapre_fonasa',
            'jubilado',
            'estado_civil',
            'edad',
            'fecha_nacimiento',
            'pais_nacimiento',
            'region_nacimiento',
            'nacionalidad',
            'nacionalidad_ext',
            'telefono',
            'domicilio',
            'villa',
            'numero_direccion',
            'num_depto',
            'region',
            'ciudad',
            'comuna',
            'email_personal',
            'banco',
            'metodo_pago',
            'numero_cuenta',
            'sueldo_liquido',
            'dias_contrato',
            'cuenta_gasto',
            'tipo_contrato',
            'termino_contrato',
            'fecha_termino_ito',
            'tipo_jornada',
            'horario',
            'observaciones',
            'doc_domicilio',
            'doc_titulo',
            'doc_afp',
            'doc_salud',
            'doc_cedula',
            'doc_domicilio_url',
            'doc_titulo_url',
            'doc_afp_url',
            'doc_salud_url',
            'doc_cedula_url',
            'estado',
            'estado_label',
            'can_aprobar',
            'can_rechazar',
            'can_editar',
            'can_retroceder',
            'can_eliminar',
            'accion_aprobar_label',
            'aprobado_jefe_por',
            'aprobado_jefe_at',
            'aprobado_admin_por',
            'aprobado_admin_at',
            'aprobado_rrhh_por',
            'aprobado_rrhh_at',
            'rechazo_comentario',
            'rechazo_por',
            'rechazo_at',
            'creado_por',
            'creado_por_id',
            'created_at',
            'updated_at',
        )

    def get_can_aprobar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_aprobar_ficha(obj, user)

    def get_can_rechazar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_rechazar_ficha(obj, user)

    def get_can_editar(self, obj):
        return user_can_editar_ficha(obj, None)

    def get_can_retroceder(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_retroceder_ficha(obj, user)

    def get_can_eliminar(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            return False
        return user_can_eliminar_ficha(obj, user)

    def get_accion_aprobar_label(self, obj):
        return accion_aprobar_label(obj.estado)

    def get_afp(self, obj):
        return resolve_catalog_label('afp', obj.afp)

    def get_isapre_fonasa(self, obj):
        return resolve_catalog_label('isapre_fonasa', obj.isapre_fonasa)

    def get_estado_civil(self, obj):
        return resolve_catalog_label('estado_civil', obj.estado_civil)

    def get_banco(self, obj):
        return resolve_catalog_label('banco', obj.banco)

    def get_horario(self, obj):
        return resolve_catalog_label('horario', obj.horario)

    def _adjunto_api_url(self, obj, doc_type: str):
        field_map = {
            'domicilio': obj.doc_domicilio,
            'titulo': obj.doc_titulo,
            'afp': obj.doc_afp,
            'salud': obj.doc_salud,
            'cedula': obj.doc_cedula,
        }
        field = field_map.get(doc_type)
        if not field:
            return None
        request = self.context.get('request')
        path = f'/api/sipo/fichas/{obj.id}/adjuntos/{doc_type}/'
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_doc_domicilio_url(self, obj):
        return self._adjunto_api_url(obj, 'domicilio')

    def get_doc_titulo_url(self, obj):
        return self._adjunto_api_url(obj, 'titulo')

    def get_doc_afp_url(self, obj):
        return self._adjunto_api_url(obj, 'afp')

    def get_doc_salud_url(self, obj):
        return self._adjunto_api_url(obj, 'salud')

    def get_doc_cedula_url(self, obj):
        return self._adjunto_api_url(obj, 'cedula')


class SipoFichaRsCcWriteSerializer(serializers.Serializer):
    """Valida coherencia RS↔CC y segregación Grupo 2 en create/update ficha."""

    razon_social_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    centro_costo_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    external_code_pais = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        from sipo.services.pais_segregation import (
            assert_create_only_grupo2,
            validate_razon_social_centro_costo,
        )

        base = self.context.get('ficha')
        rs = attrs.get('razon_social_id')
        cc = attrs.get('centro_costo_id')
        if rs is None and base is not None:
            rs = getattr(base, 'razon_social_id', None)
        if cc is None and base is not None:
            cc = getattr(base, 'centro_costo_id', None)
        rs = (rs or '').strip()
        cc = (cc or '').strip()
        if not rs or not cc:
            return attrs

        # Alta nueva: solo Grupo 2. En edición se respeta el país enviado / de la ficha.
        if base is None:
            attrs['external_code_pais'] = assert_create_only_grupo2(
                attrs.get('external_code_pais')
            )

        validate_razon_social_centro_costo(
            razon_social_id=rs,
            centro_costo_id=cc,
            external_code_pais=attrs.get('external_code_pais'),
        )
        return attrs


def _ficha_req_char(max_length=255):
    return serializers.CharField(
        max_length=max_length, required=True, allow_blank=False, allow_null=False
    )


def _ficha_opt_char(max_length=255):
    return serializers.CharField(
        max_length=max_length, required=False, allow_blank=True, allow_null=True
    )


FICHA_REQUIRED_TEXT_FIELDS = (
    'razon_social_id',
    'obra',
    'centro_costo_id',
    'centro_costo_nombre',
    'cargo',
    'fecha_ingreso',
    'correo_jefe_directo',
    'correo_admin_obra',
    'nombres',
    'apellido_paterno',
    'apellido_materno',
    'rut',
    'genero',
    'tratamiento',
    'fecha_nacimiento',
    'edad',
    'nacionalidad',
    'pais_nacimiento',
    'region_nacimiento',
    'afp',
    'isapre_fonasa',
    'estado_civil',
    'telefono',
    'domicilio',
    'numero_direccion',
    'region',
    'ciudad',
    'comuna',
    'email_personal',
    'metodo_pago',
    'banco',
    'numero_cuenta',
    'sueldo_liquido',
    'cuenta_gasto',
    'tipo_contrato',
    'horario',
)


class SipoFichaIngresoWriteSerializer(serializers.Serializer):
    """Validación estricta de campos obligatorios de ficha de ingreso."""

    razon_social_id = _ficha_req_char(50)
    obra = _ficha_req_char(255)
    centro_costo_id = _ficha_req_char(100)
    centro_costo_nombre = _ficha_req_char(255)
    cargo = _ficha_req_char(255)
    fecha_ingreso = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    correo_jefe_directo = serializers.EmailField(required=True, allow_blank=False, allow_null=False)
    correo_admin_obra = serializers.EmailField(required=True, allow_blank=False, allow_null=False)
    nombres = _ficha_req_char(150)
    apellido_paterno = _ficha_req_char(100)
    apellido_materno = _ficha_req_char(100)
    rut = _ficha_req_char(20)
    genero = _ficha_req_char(30)
    tratamiento = _ficha_req_char(20)
    fecha_nacimiento = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    edad = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    nacionalidad = _ficha_req_char(80)
    nacionalidad_ext = _ficha_opt_char(100)
    pais_nacimiento = _ficha_req_char(100)
    region_nacimiento = _ficha_req_char(100)
    afp = _ficha_req_char(100)
    isapre_fonasa = _ficha_req_char(100)
    jubilado = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    estado_civil = _ficha_req_char(50)
    telefono = _ficha_req_char(30)
    domicilio = _ficha_req_char(255)
    numero_direccion = _ficha_req_char(30)
    villa = _ficha_opt_char(150)
    num_depto = _ficha_opt_char(30)
    region = _ficha_req_char(100)
    ciudad = _ficha_req_char(100)
    comuna = _ficha_req_char(100)
    email_personal = serializers.EmailField(required=True, allow_blank=False, allow_null=False)
    metodo_pago = _ficha_req_char(50)
    banco = _ficha_req_char(100)
    numero_cuenta = _ficha_req_char(50)
    sueldo_liquido = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    cuenta_gasto = _ficha_req_char(150)
    tipo_contrato = _ficha_req_char(50)
    termino_contrato = _ficha_opt_char(255)
    fecha_termino_ito = _ficha_opt_char(30)
    horario = _ficha_req_char(120)
    observaciones = _ficha_opt_char(2000)
    external_code_pais = _ficha_opt_char(50)

    def validate(self, attrs):
        from rest_framework.exceptions import ValidationError

        errors = {}
        for key, value in list(attrs.items()):
            if isinstance(value, str):
                stripped = value.strip()
                attrs[key] = stripped
                if key in FICHA_REQUIRED_TEXT_FIELDS and stripped == '':
                    errors[key] = ['Este campo no puede estar vacío ni contener solo espacios.']

        for key in FICHA_REQUIRED_TEXT_FIELDS:
            val = attrs.get(key)
            if val is None or (isinstance(val, str) and val.strip() == ''):
                errors[key] = ['Este campo es obligatorio.']

        jub = attrs.get('jubilado')
        if jub is None or (isinstance(jub, str) and jub.strip() == ''):
            errors['jubilado'] = ['Este campo es obligatorio.']

        nac = (attrs.get('nacionalidad') or '').strip()
        if nac in ('Extranjero', 'Extranjero-Definitiva'):
            if not (attrs.get('nacionalidad_ext') or '').strip():
                errors['nacionalidad_ext'] = ['Debe indicar la nacionalidad extranjera.']

        tipo = (attrs.get('tipo_contrato') or '').strip()
        if tipo == 'Plazo Fijo':
            if not (attrs.get('termino_contrato') or '').strip():
                errors['termino_contrato'] = ['Debe indicar la fecha término plazo fijo.']
        elif tipo == 'Obra o Faena':
            if not (attrs.get('termino_contrato') or '').strip():
                errors['termino_contrato'] = ['Debe indicar el HITO.']
            if not (attrs.get('fecha_termino_ito') or '').strip():
                errors['fecha_termino_ito'] = ['Debe indicar la fecha de término HITO.']

        if errors:
            raise ValidationError(errors)
        return attrs
