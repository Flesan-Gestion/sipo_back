from django.db import models


class SipoSolicitudHistorial(models.Model):
    """Bitácora de cambios de estado de solicitudes Obra (DB default)."""

    solicitud = models.PositiveIntegerField(db_index=True)
    estado_anterior = models.IntegerField()
    estado_nuevo = models.IntegerField()
    usuario = models.CharField(max_length=150)
    comentario = models.TextField(blank=True, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sipo_solicitud_historial'
        ordering = ['-fecha_creacion', '-id']

    def __str__(self) -> str:
        return f'SIP {self.solicitud}: {self.estado_anterior}→{self.estado_nuevo}'
