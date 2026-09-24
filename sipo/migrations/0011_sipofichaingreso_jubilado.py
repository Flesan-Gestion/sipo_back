from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0010_sapmaestro_external_code_pais'),
    ]

    operations = [
        migrations.AddField(
            model_name='sipofichaingreso',
            name='jubilado',
            field=models.BooleanField(default=False, verbose_name='Jubilado'),
        ),
    ]
