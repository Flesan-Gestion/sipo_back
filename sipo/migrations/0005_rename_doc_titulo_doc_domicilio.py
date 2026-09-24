from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0004_ficha_estado_aprobacion'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sipofichaingreso',
            old_name='doc_titulo',
            new_name='doc_domicilio',
        ),
    ]
