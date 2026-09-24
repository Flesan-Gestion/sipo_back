from django.db import models


class SipoObra(models.Model):
    cf_rrhh_sip_id = models.IntegerField(primary_key=True, db_column='cf_rrhh_sip_id')
    cf_rrhh_sip_rut = models.CharField(max_length=15, db_column='cf_rrhh_sip_rut', blank=True, null=True)
    cf_rrhh_sip_razonsocial = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_razonsocial', blank=True, null=True
    )
    cf_rrhh_sip_uni = models.CharField(max_length=10, db_column='cf_rrhh_sip_uni', blank=True, null=True)
    cf_rrhh_sip_nombre_uni = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_nombre_uni', blank=True, null=True
    )
    cf_rrhh_sip_dep = models.CharField(max_length=100, db_column='cf_rrhh_sip_dep', blank=True, null=True)
    cf_rrhh_sip_nombre_dep = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_nombre_dep', blank=True, null=True
    )
    cf_rrhh_sip_cc = models.CharField(max_length=100, db_column='cf_rrhh_sip_cc', blank=True, null=True)
    cf_rrhh_sip_nombre_cc = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_nombre_cc', blank=True, null=True
    )
    cf_rrhh_sip_adm = models.CharField(max_length=100, db_column='cf_rrhh_sip_adm', blank=True, null=True)
    cf_rrhh_sip_as = models.CharField(max_length=100, db_column='cf_rrhh_sip_as', blank=True, null=True)
    cf_rrhh_sip_ubicacion = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_ubicacion', blank=True, null=True
    )
    cf_rrhh_sip_status = models.IntegerField(db_column='cf_rrhh_sip_status')
    cf_rrhh_sip_status_date = models.DateField(db_column='cf_rrhh_sip_status_date', blank=True, null=True)
    cf_rrhh_sip_status_user = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_status_user', blank=True, null=True
    )
    cf_rrhh_sip_status_datos = models.IntegerField(
        db_column='cf_rrhh_sip_status_datos', blank=True, null=True
    )
    cf_rrhh_sip_create_date = models.DateTimeField(
        db_column='cf_rrhh_sip_create_date', blank=True, null=True
    )
    cf_rrhh_sip_create_user = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_create_user', blank=True, null=True
    )
    cf_rrhh_sip_update_date = models.DateTimeField(
        db_column='cf_rrhh_sip_update_date', blank=True, null=True
    )
    cf_rrhh_sip_update_user = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_update_user', blank=True, null=True
    )
    cf_rrhh_sip_apro_date = models.DateTimeField(
        db_column='cf_rrhh_sip_apro_date', blank=True, null=True
    )
    cf_rrhh_sip_apro_user = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_apro_user', blank=True, null=True
    )
    cf_rrhh_sip_end_date = models.DateField(db_column='cf_rrhh_sip_end_date', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_obra'


class SapMaestroEmpresaDepUnCc(models.Model):
    external_code_empresa = models.CharField(max_length=50, db_column='external_code_empresa', blank=True, null=True)
    nombre_empresa = models.CharField(max_length=255, db_column='nombre_empresa', blank=True, null=True)
    external_code_un = models.CharField(max_length=50, db_column='external_code_un', blank=True, null=True)
    nombre_un = models.CharField(max_length=255, db_column='nombre_un', blank=True, null=True)
    external_code_departamento = models.CharField(
        max_length=50, db_column='external_code_departamento', blank=True, null=True
    )
    nombre_departamento = models.CharField(
        max_length=255, db_column='nombre_departamento', blank=True, null=True
    )
    external_code_cc = models.CharField(max_length=50, db_column='external_code_cc', primary_key=True)
    nombre_cc = models.CharField(max_length=255, db_column='nombre_cc', blank=True, null=True)
    status_cc = models.CharField(max_length=10, db_column='status_cc', blank=True, null=True)
    status_departamento = models.CharField(
        max_length=10, db_column='status_departamento', blank=True, null=True
    )
    external_code_pais = models.CharField(
        max_length=50, db_column='external_code_pais', blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'sap_maestro_empresa_dep_un_cc'


class SipoObraCargo(models.Model):
    """Alias legado; definición canónica en models_cargos_horarios.SipoEmpresaCargo."""

    id_cargo = models.AutoField(primary_key=True)
    rut_empresa = models.CharField(max_length=60, blank=True, null=True)
    cargo = models.CharField(max_length=60, blank=True, null=True)
    external_code = models.CharField(max_length=50, blank=True, null=True)
    area_personal = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_obra_cargos'


class SipoCandidatoObra(models.Model):
    cf_rrhh_sip_obra_id = models.IntegerField(db_column='cf_rrhh_sip_obra_id')
    cf_rrhh_sip_obra_candidato_id = models.CharField(
        max_length=100, primary_key=True, db_column='cf_rrhh_sip_obra_candidato_id'
    )
    cf_rrhh_sip_obra_user_id = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_user_id', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_tratamiento = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_tratamiento', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_rut = models.CharField(
        max_length=15, db_column='cf_rrhh_sip_obra_candidato_rut', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nombre = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nombre', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_segundo_nombre = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_segundo_nombre', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_ap = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_ap', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_am = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_am', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_genero = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_genero', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_fecha_nacimiento = models.DateField(
        db_column='cf_rrhh_sip_obra_candidato_fecha_nacimiento', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_pais_nacimiento = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_pais_nacimiento', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_region_nacimiento = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_region_nacimiento', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nacionalidad = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nacionalidad', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nacionalidad_ext = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nacionalidad_ext', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_region = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_region', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_ciudad = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_ciudad', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_comuna = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_comuna', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_villa = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_villa', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_direccion = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_direccion', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_numero_dire = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_numero_dire', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_num_depto = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_num_depto', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_estado_civil = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_estado_civil', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_telefono = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_telefono', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_correo = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_correo', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_metodo_pago = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_metodo_pago', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_banco = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_banco', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_numcta = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_numcta', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_anticipo = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_anticipo', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nomcar = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nomcar', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_horario_trabajo = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_horario_trabajo', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_sueldo = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_sueldo', blank=True, null=True
    )
    cf_rrhh_sip_obra_sueldo_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column='cf_rrhh_sip_obra_sueldo_base',
        blank=True,
        null=True,
    )
    cf_rrhh_sip_obra_bono_mineria = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_column='cf_rrhh_sip_obra_bono_mineria',
        blank=True,
        null=True,
    )
    cf_rrhh_sip_obra_candidato_cuenta_gasto = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_cuenta_gasto', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_tipo_contrato = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_tipo_contrato', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_fecha_ingreso = models.DateField(
        db_column='cf_rrhh_sip_obra_candidato_fecha_ingreso', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_termino_contrato = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_termino_contrato', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_fecha_termino_ito = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_fecha_termino_ito', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_jubilado = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_jubilado', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nom_afp = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nom_afp', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_nom_salud = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_nom_salud', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_valor_plan = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_valor_plan', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_valor_uf = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_valor_uf', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_seguro_covid = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_seguro_covid', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_create_user = models.CharField(
        max_length=100, db_column='cf_rrhh_sip_obra_candidato_create_user', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_ci = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_ci', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_afp = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_afp', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_salud = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_salud', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_domi = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_domi', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_doc_jubi = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_doc_jubi', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_jubi = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_jubi', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_visa = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_visa', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_permiso_trabajo = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_permiso_trabajo', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_copia_seguro_covid = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_copia_seguro_covid', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_seleccionado = models.IntegerField(
        db_column='cf_rrhh_sip_obra_candidato_seleccionado', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_registro_dt = models.CharField(
        max_length=200, db_column='cf_rrhh_sip_obra_candidato_registro_dt', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_estado = models.IntegerField(
        db_column='cf_rrhh_sip_obra_candidato_estado', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_estado_documentos = models.IntegerField(
        db_column='cf_rrhh_sip_obra_candidato_estado_documentos', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_estado_builder = models.IntegerField(
        db_column='cf_rrhh_sip_obra_candidato_estado_builder', blank=True, null=True
    )
    cf_rrhh_sip_obra_create_date = models.DateTimeField(
        db_column='cf_rrhh_sip_obra_create_date', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_user_eliminador = models.CharField(
        max_length=50, db_column='cf_rrhh_sip_obra_candidato_user_eliminador', blank=True, null=True
    )
    cf_rrhh_sip_obra_candidato_date_eliminador = models.DateTimeField(
        db_column='cf_rrhh_sip_obra_candidato_date_eliminador', blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_candidato_obra'


class SipoObraLog(models.Model):
    id = models.AutoField(primary_key=True)
    sipo_id = models.IntegerField(db_column='sipo_id')
    userid = models.CharField(max_length=50, db_column='userid', blank=True, null=True)
    log_type = models.CharField(max_length=50, db_column='log_type', blank=True, null=True)
    log_estado = models.CharField(max_length=50, db_column='log_estado', blank=True, null=True)
    log_data = models.TextField(db_column='log_data', blank=True, null=True)
    log_date = models.DateTimeField(db_column='log_date', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'log_sip_obra'


from .models_ficha import SipoFichaIngreso  # noqa: E402,F401
from .models_historial import SipoSolicitudHistorial  # noqa: E402,F401
