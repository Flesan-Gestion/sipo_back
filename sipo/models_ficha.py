from django.db import models


class SipoFichaIngreso(models.Model):
    ESTADO_BORRADOR_SUPERVISOR = 'BORRADOR_SUPERVISOR'
    ESTADO_PENDIENTE_DATOS_COLABORADOR = 'PENDIENTE_DATOS_COLABORADOR'
    ESTADO_PENDIENTE_JEFE_TERRENO = 'PENDIENTE_JEFE_TERRENO'
    ESTADO_PENDIENTE_JEFE = ESTADO_PENDIENTE_JEFE_TERRENO
    ESTADO_PENDIENTE_ADMIN = 'PENDIENTE_ADMIN'
    ESTADO_PENDIENTE_RRHH = 'PENDIENTE_RRHH'
    ESTADO_APROBADA = 'APROBADA'
    ESTADO_RECHAZADA = 'RECHAZADA'

    ESTADO_CHOICES = (
        (ESTADO_BORRADOR_SUPERVISOR, 'Borrador supervisor'),
        (ESTADO_PENDIENTE_DATOS_COLABORADOR, 'Pendiente colaborador'),
        (ESTADO_PENDIENTE_RRHH, 'Pendiente RRHH'),
        (ESTADO_PENDIENTE_JEFE_TERRENO, 'Pendiente Jefe de Terreno'),
        (ESTADO_APROBADA, 'Aprobada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
    )

    ESTADO_LABELS = {
        ESTADO_BORRADOR_SUPERVISOR: 'Borrador supervisor',
        ESTADO_PENDIENTE_DATOS_COLABORADOR: 'Pendiente colaborador',
        ESTADO_PENDIENTE_JEFE_TERRENO: 'Pendiente Jefe de Terreno',
        'PENDIENTE_JEFE': 'Pendiente Jefe de Terreno',
        ESTADO_PENDIENTE_ADMIN: 'Pendiente RRHH',
        ESTADO_PENDIENTE_RRHH: 'Pendiente RRHH',
        ESTADO_APROBADA: 'Aprobada',
        ESTADO_RECHAZADA: 'Rechazada',
    }

    # Sección 1 — RRHH / Solicitante
    razon_social_id = models.CharField(max_length=50, blank=True, null=True)
    razon_social_nombre = models.CharField(max_length=255, blank=True, null=True)
    obra = models.CharField(max_length=255, blank=True, null=True)
    centro_costo_id = models.CharField(max_length=100, blank=True, null=True)
    centro_costo_nombre = models.CharField(max_length=255, blank=True, null=True)
    cargo = models.CharField(max_length=255, blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)
    correo_jefe_directo = models.EmailField(blank=True, null=True)
    correo_admin_obra = models.EmailField(blank=True, null=True)
    correo_colaborador = models.EmailField(blank=True, null=True)
    jefe_user_id = models.CharField(max_length=50, blank=True, null=True)
    jefe_nombre = models.CharField(max_length=255, blank=True, null=True)
    jefe_correo = models.CharField(max_length=150, blank=True, null=True)

    # Sección 2 — Colaborador
    nombres = models.CharField(max_length=150, blank=True, null=True)
    apellido_paterno = models.CharField(max_length=100, blank=True, null=True)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)
    rut = models.CharField(max_length=20, blank=True, null=True)
    tratamiento = models.CharField(max_length=20, blank=True, null=True)
    genero = models.CharField(max_length=30, blank=True, null=True)
    afp = models.CharField(max_length=100, blank=True, null=True)
    isapre_fonasa = models.CharField(max_length=100, blank=True, null=True)
    jubilado = models.BooleanField(default=False, verbose_name='Jubilado')
    estado_civil = models.CharField(max_length=50, blank=True, null=True)
    edad = models.PositiveSmallIntegerField(blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    pais_nacimiento = models.CharField(max_length=100, blank=True, null=True)
    region_nacimiento = models.CharField(max_length=100, blank=True, null=True)
    nacionalidad = models.CharField(max_length=80, blank=True, null=True)
    nacionalidad_ext = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    domicilio = models.CharField(max_length=255, blank=True, null=True)
    villa = models.CharField(max_length=150, blank=True, null=True)
    numero_direccion = models.CharField(max_length=30, blank=True, null=True)
    num_depto = models.CharField(max_length=30, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    comuna = models.CharField(max_length=100, blank=True, null=True)
    email_personal = models.EmailField(blank=True, null=True)
    banco = models.CharField(max_length=100, blank=True, null=True)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)

    # Sección 3 — Contratación
    sueldo_liquido = models.PositiveIntegerField(blank=True, null=True)
    dias_contrato = models.PositiveIntegerField(blank=True, null=True)
    cuenta_gasto = models.CharField(max_length=150, blank=True, null=True)
    tipo_contrato = models.CharField(max_length=50, blank=True, null=True)
    termino_contrato = models.CharField(max_length=255, blank=True, null=True)
    fecha_termino_ito = models.DateField(blank=True, null=True)
    tipo_jornada = models.CharField(max_length=30, blank=True, null=True)
    horario = models.CharField(max_length=120, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    doc_domicilio = models.FileField(
        upload_to='fichas_ingreso/adjuntos/%Y/%m/', null=True, blank=True
    )
    doc_titulo = models.FileField(
        upload_to='fichas_ingreso/adjuntos/%Y/%m/', null=True, blank=True
    )
    doc_afp = models.FileField(
        upload_to='fichas_ingreso/adjuntos/%Y/%m/', null=True, blank=True
    )
    doc_salud = models.FileField(
        upload_to='fichas_ingreso/adjuntos/%Y/%m/', null=True, blank=True
    )
    doc_cedula = models.FileField(
        upload_to='fichas_ingreso/adjuntos/%Y/%m/', null=True, blank=True
    )

    estado = models.CharField(
        max_length=30,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE_JEFE_TERRENO,
        db_index=True,
    )
    aprobado_jefe_por = models.CharField(max_length=150, blank=True, null=True)
    aprobado_jefe_at = models.DateTimeField(blank=True, null=True)
    aprobado_admin_por = models.CharField(max_length=150, blank=True, null=True)
    aprobado_admin_at = models.DateTimeField(blank=True, null=True)
    aprobado_rrhh_por = models.CharField(max_length=150, blank=True, null=True)
    aprobado_rrhh_at = models.DateTimeField(blank=True, null=True)
    rechazo_comentario = models.TextField(blank=True, null=True)
    rechazo_por = models.CharField(max_length=150, blank=True, null=True)
    rechazo_at = models.DateTimeField(blank=True, null=True)

    creado_por = models.CharField(max_length=150, blank=True, null=True)
    creado_por_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sipo_ficha_ingreso'
        ordering = ['-id']

    @property
    def nombre_colaborador(self) -> str:
        parts = [
            (self.nombres or '').strip(),
            (self.apellido_paterno or '').strip(),
            (self.apellido_materno or '').strip(),
        ]
        return ' '.join(p for p in parts if p)

    @property
    def estado_label(self) -> str:
        return self.ESTADO_LABELS.get(self.estado, self.estado or '')
