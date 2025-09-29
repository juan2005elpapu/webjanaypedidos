from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_wompi_integration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='businesssettings',
            name='accept_card',
        ),
        migrations.RemoveField(
            model_name='businesssettings',
            name='accept_pse',
        ),
        migrations.RemoveField(
            model_name='businesssettings',
            name='accept_transfer',
        ),
        migrations.AlterField(
            model_name='businesssettings',
            name='accept_wompi',
            field=models.BooleanField(
                default=True,
                verbose_name='Aceptar pagos con Wompi',
            ),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='wompi_integrity_key',
            field=models.CharField(
                blank=True,
                help_text='Llave usada para firmar los pagos iniciados desde el widget de Wompi',
                max_length=120,
                verbose_name='Llave de integridad Wompi',
            ),
        ),
    ]
