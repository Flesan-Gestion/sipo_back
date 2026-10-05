import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0013_candidato_acceso_portal'),
    ]

    operations = [
        migrations.CreateModel(
            name='SipoFichaAcceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ficha_id', models.IntegerField(unique=True)),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('expira_at', models.DateTimeField()),
                ('estado', models.CharField(default='PENDIENTE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'sipo_ficha_acceso'},
        ),
    ]
