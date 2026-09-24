"""Crea tablas de alcance territorial en sip_db."""

from django.db import migrations


def forwards(apps, schema_editor):
    from sipo.services.usuario_scope import ensure_scope_tables

    ensure_scope_tables()


def backwards(apps, schema_editor):
    from django.db import connections

    with connections['sip_db'].cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS cf_rrhh_sip_perfil_cc')
        cursor.execute('DROP TABLE IF EXISTS cf_rrhh_sip_perfil_empresa')


class Migration(migrations.Migration):
    dependencies = [
        ('sipo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
