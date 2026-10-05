from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0011_sipofichaingreso_jubilado'),
    ]

    operations = [
        migrations.AddField(
            model_name='sipofichaingreso',
            name='jefe_user_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='jefe_nombre',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='sipofichaingreso',
            name='jefe_correo',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
