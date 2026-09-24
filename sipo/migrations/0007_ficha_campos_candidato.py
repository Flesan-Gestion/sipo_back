from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0006_sipofichaingreso_doc_titulo'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sipofichaingreso',
            old_name='tipo_cuenta',
            new_name='metodo_pago',
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='tratamiento',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='genero',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='pais_nacimiento',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='region_nacimiento',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='nacionalidad',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='nacionalidad_ext',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='villa',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='numero_direccion',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='num_depto',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='cuenta_gasto',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='tipo_contrato',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='termino_contrato',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='fecha_termino_ito',
            field=models.DateField(blank=True, null=True),
        ),
    ]
