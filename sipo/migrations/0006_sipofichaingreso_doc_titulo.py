from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0005_rename_doc_titulo_doc_domicilio'),
    ]

    operations = [
        migrations.AddField(
            model_name='sipofichaingreso',
            name='doc_titulo',
            field=models.FileField(blank=True, null=True, upload_to='fichas_ingreso/adjuntos/%Y/%m/'),
        ),
    ]
