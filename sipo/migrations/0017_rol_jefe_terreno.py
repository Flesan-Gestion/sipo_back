"""Asegura rol Jefe de Terreno (cf_rol_id=5) en sip_db."""

from django.db import migrations


def forwards(apps, schema_editor):
    from django.db import connections

    with connections['sip_db'].cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO cf_rrhh_sip_rol (cf_rol_id, cf_rol_name)
            VALUES (5, 'Jefe de Terreno')
            ON DUPLICATE KEY UPDATE cf_rol_name = 'Jefe de Terreno'
            """
        )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('sipo', '0016_rol_supervisor'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
