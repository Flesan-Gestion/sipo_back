from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0012_ficha_jefe_directo'),
    ]

    operations = [
        migrations.CreateModel(
            name='SipoCandidatoAcceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('candidato_id', models.CharField(max_length=100, unique=True)),
                ('sip_id', models.IntegerField()),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('expira_at', models.DateTimeField()),
                ('estado', models.CharField(default='PENDIENTE', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'sipo_candidato_acceso'},
        ),
    ]
