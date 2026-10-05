"""Asegura rol Supervisor (cf_rol_id=4) en sip_db."""

from django.db import migrations


def forwards(apps, schema_editor):
    from django.db import connections

    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
            VALUES (4, 'Supervisor')
            ON DUPLICATE KEY UPDATE cf_rol_name = 'Supervisor'
            """
        )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('sipo', '0015_ficha_correo_colaborador'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
