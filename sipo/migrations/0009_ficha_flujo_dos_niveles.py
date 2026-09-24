from django.db import migrations, models


def migrate_estados(apps, schema_editor):
    Ficha = apps.get_model('sipo', 'SipoFichaIngreso')
    Ficha.objects.filter(estado='PENDIENTE_JEFE').update(estado='PENDIENTE_JEFE_TERRENO')
    Ficha.objects.filter(estado='PENDIENTE_ADMIN').update(estado='PENDIENTE_RRHH')


def reverse_estados(apps, schema_editor):
    Ficha = apps.get_model('sipo', 'SipoFichaIngreso')
    Ficha.objects.filter(estado='PENDIENTE_JEFE_TERRENO').update(estado='PENDIENTE_JEFE')


class Migration(migrations.Migration):
    dependencies = [
        ('sipo', '0008_siposolicitudhistorial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sipofichaingreso',
            name='rechazo_comentario',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='rechazo_por',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='rechazo_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sipofichaingreso',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PENDIENTE_JEFE_TERRENO', 'Pendiente Jefe de Terreno'),
                    ('PENDIENTE_RRHH', 'Pendiente RRHH'),
                    ('APROBADA', 'Aprobada'),
                    ('RECHAZADA', 'Rechazada'),
                ],
                db_index=True,
                default='PENDIENTE_JEFE_TERRENO',
                max_length=30,
            ),
        ),
        migrations.RunPython(migrate_estados, reverse_estados),
    ]
