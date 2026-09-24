"""
Modelos de usuarios y perfiles SIP Obra (paridad legado cf_rrhh_sip_perfil / cf_rrhh_sip_rol).

Los datos extendidos (nombres, apellidos, RUT, estado) viven en security.User (aplicacion_usuario).
El acceso SIP se resuelve desde cf_rrhh_sip_perfil + cf_rrhh_sip_rol en sip_db.

Alcance territorial (razones sociales / centros de costo) en:
- cf_rrhh_sip_perfil_empresa
- cf_rrhh_sip_perfil_cc
"""

from django.db import models

from security.models import SipoPerfil, SipoRol, User

__all__ = [
    'SipoPerfil',
    'SipoRol',
    'User',
    'SipoPerfilEmpresa',
    'SipoPerfilCentroCosto',
    'SipoUsuarioPerfil',
]


class SipoPerfilEmpresa(models.Model):
    id = models.AutoField(primary_key=True)
    cf_rrhh_sip_perfil_id = models.IntegerField()
    empresa_rut = models.CharField(max_length=32)
    empresa_nombre = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_perfil_empresa'


class SipoPerfilCentroCosto(models.Model):
    id = models.AutoField(primary_key=True)
    cf_rrhh_sip_perfil_id = models.IntegerField()
    empresa_rut = models.CharField(max_length=32)
    centro_costo_id = models.CharField(max_length=100)
    centro_costo_nombre = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cf_rrhh_sip_perfil_cc'


class SipoUsuarioPerfil:
    """Vista compuesta usuario SIP (perfil + datos aplicacion_usuario)."""

    def __init__(
        self,
        *,
        perfil_id: int,
        email: str,
        cf_rol_id: int,
        rol_nombre: str = '',
        nombres: str = '',
        apellidos: str = '',
        rut: str = '',
        is_active: bool = True,
        fecha_creacion=None,
        empresas=None,
        centros_costo=None,
    ):
        self.perfil_id = perfil_id
        self.email = email
        self.cf_rol_id = cf_rol_id
        self.rol_nombre = rol_nombre
        self.nombres = nombres
        self.apellidos = apellidos
        self.rut = rut
        self.is_active = is_active
        self.fecha_creacion = fecha_creacion
        self.empresas = empresas or []
        self.centros_costo = centros_costo or []

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombres.strip(), self.apellidos.strip()]
        full = ' '.join(p for p in parts if p)
        return full or self.email
