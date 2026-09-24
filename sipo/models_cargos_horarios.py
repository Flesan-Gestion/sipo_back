from django.db import models


class SipoCargo(models.Model):
    external_code = models.CharField(max_length=100, db_column='external_code', blank=True, null=True)
    nombre_cargo = models.CharField(max_length=100, db_column='nombre_cargo', blank=True, null=True)
    external_code_area_personal = models.CharField(
        max_length=100, db_column='external_code_area_personal', blank=True, null=True
    )
    planta_noplanta = models.CharField(max_length=100, db_column='planta_noplanta', blank=True, null=True)
    status = models.CharField(max_length=100, db_column='status', blank=True, null=True)
    grade = models.CharField(max_length=100, db_column='grade', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cargos'


class SipoEmpresaCargo(models.Model):
    id_cargo = models.AutoField(primary_key=True, db_column='id_cargo')
    cargo = models.CharField(max_length=60, db_column='cargo')
    rut_empresa = models.CharField(max_length=60, db_column='rut_empresa')
    external_code = models.CharField(max_length=50, db_column='external_code', blank=True, null=True)
    area_personal = models.CharField(max_length=50, db_column='area_personal', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_obra_cargos'


class SipoHorario(models.Model):
    rut_empresa = models.CharField(max_length=50, db_column='rut_empresa', blank=True, null=True)
    horario_trabajo = models.CharField(max_length=100, db_column='horario_trabajo', blank=True, null=True)
    external_code = models.CharField(max_length=50, db_column='external_code', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_obra_horario_trabajo'
