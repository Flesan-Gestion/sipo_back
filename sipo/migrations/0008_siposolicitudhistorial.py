from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0007_ficha_campos_candidato'),
    ]

    operations = [
        migrations.CreateModel(
            name='SipoSolicitudHistorial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('solicitud', models.PositiveIntegerField(db_index=True)),
                ('estado_anterior', models.IntegerField()),
                ('estado_nuevo', models.IntegerField()),
                ('usuario', models.CharField(max_length=150)),
                ('comentario', models.TextField(blank=True, default='')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'sipo_solicitud_historial',
                'ordering': ['-fecha_creacion', '-id'],
            },
        ),
    ]
