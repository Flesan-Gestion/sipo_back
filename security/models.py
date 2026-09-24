from django.db import models



class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    id_aplicacion = models.IntegerField(blank=True, null=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'rol_aplicacion'
        

class User(models.Model):
    id_aplicacion_usuario = models.BigAutoField(primary_key=True)
    id_aplicacion = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    fecha_ini = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    provider = models.CharField(max_length=255, blank=True, null=True)
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    remember_token = models.CharField(max_length=100, blank=True, null=True)
    estado_sesion = models.IntegerField(default=1)
    fecha_validacion = models.DateField(blank=True, null=True)
    dni = models.CharField(max_length=150, blank=True, null=True)
    nombres = models.CharField(max_length=100, blank=True, null=True)
    apellidos = models.CharField(max_length=100, blank=True, null=True)
    estado_validacion = models.IntegerField(default=1)
    pais = models.CharField(max_length=50, blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    old_id = models.IntegerField(blank=True, null=True)
    fecha_purga = models.DateField(blank=True, null=True)

    USER_ID_FIELD="id_aplicacion_usuario"

    class Meta:
        managed = False
        db_table = 'aplicacion_usuario'
        unique_together = (('id_aplicacion', 'username'),)
        
    @property
    def is_authenticated(self):
        return True


class UserRol(models.Model):
    id_usuario_rol = models.BigAutoField(primary_key=True)
    aplicacion_usuario = models.ForeignKey(User, models.DO_NOTHING, db_column='id_aplicacion_usuario', to_field="id_aplicacion_usuario",related_name="roles")
    rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='id_rol', to_field="id_rol", )
    id_empresa = models.CharField(max_length=100, blank=True, null=True)
    objeto_permitido = models.CharField(max_length=5120, blank=True, null=True)
    fecha_ini = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(blank=True, null=True)
    id_unidad_negocio = models.CharField(max_length=10, blank=True, null=True)
    old_id_usu = models.IntegerField(blank=True, null=True)
    pais = models.CharField(max_length=255, blank=True, null=True)
    estado = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = 'usuario_rol'


class SipoRol(models.Model):
    cf_rol_id = models.IntegerField(primary_key=True)
    cf_rol_name = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_rol'


class SipoPerfil(models.Model):
    cf_rrhh_sip_perfil_id = models.IntegerField(primary_key=True)
    usuario_email = models.CharField(max_length=250)
    cf_rol_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_perfil'
        unique_together = (('usuario_email', 'cf_rol_id'),)

