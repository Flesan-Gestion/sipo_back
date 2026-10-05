import uuid

from django.db import models
from django.utils import timezone


class SipoCandidatoAcceso(models.Model):
    PENDIENTE = 'PENDIENTE'
    EN_PROGRESO = 'EN_PROGRESO'
    COMPLETADO = 'COMPLETADO'
    ESTADO_CHOICES = (
        (PENDIENTE, 'Pendiente'),
        (EN_PROGRESO, 'En progreso'),
        (COMPLETADO, 'Completado'),
    )

    candidato_id = models.CharField(max_length=100, unique=True)
    sip_id = models.IntegerField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expira_at = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sipo_candidato_acceso'

    @property
    def expirado(self) -> bool:
        return self.expira_at <= timezone.now()
