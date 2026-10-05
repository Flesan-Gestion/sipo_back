from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0014_ficha_acceso_portal'),
    ]

    operations = [
        migrations.AddField(
            model_name='sipofichaingreso',
            name='correo_colaborador',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
