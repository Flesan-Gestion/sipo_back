from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sipo', '0009_ficha_flujo_dos_niveles'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='sapmaestroempresadepuncc',
                    name='external_code_pais',
                    field=models.CharField(
                        blank=True,
                        db_column='external_code_pais',
                        max_length=50,
                        null=True,
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
