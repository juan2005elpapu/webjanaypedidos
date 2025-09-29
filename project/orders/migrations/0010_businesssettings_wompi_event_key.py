from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_update_payment_methods'),
    ]

    operations = [
        migrations.AddField(
            model_name='businesssettings',
            name='wompi_event_key',
            field=models.CharField(
                blank=True,
                help_text='Llave usada para verificar la firma de los eventos enviados por Wompi',
                max_length=120,
                verbose_name='Llave de eventos Wompi',
            ),
        ),
    ]
