from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_remove_ordermodificationrequest_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_reference',
            field=models.CharField(
                blank=True,
                help_text='Identificador de la transacción en la pasarela de pago',
                max_length=120,
                verbose_name='Referencia de pago',
            ),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='accept_wompi',
            field=models.BooleanField(
                default=False,
                verbose_name='Aceptar pagos con Wompi',
            ),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='wompi_environment',
            field=models.CharField(
                choices=[('test', 'Sandbox/Pruebas'), ('production', 'Producción')],
                default='test',
                max_length=20,
                verbose_name='Entorno de Wompi',
            ),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='wompi_private_key',
            field=models.CharField(
                blank=True,
                help_text='Llave privada provista por Wompi para consultar transacciones',
                max_length=120,
                verbose_name='Llave privada Wompi',
            ),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='wompi_public_key',
            field=models.CharField(
                blank=True,
                help_text='Llave pública provista por Wompi (pub_test_xxx o pub_prod_xxx)',
                max_length=120,
                verbose_name='Llave pública Wompi',
            ),
        ),
    ]
