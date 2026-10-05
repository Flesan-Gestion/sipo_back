import uuid

from django.db import models
from django.utils import timezone


class SipoFichaAcceso(models.Model):
    PENDIENTE = 'PENDIENTE'
    EN_PROGRESO = 'EN_PROGRESO'
    COMPLETADO = 'COMPLETADO'

    ficha_id = models.IntegerField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expira_at = models.DateTimeField()
    estado = models.CharField(max_length=20, default=PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sipo_ficha_acceso'

    @property
    def expirado(self) -> bool:
        return self.expira_at <= timezone.now()
