# Generated by Django 5.2 on 2025-04-29 01:08

import products.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, upload_to='products/', validators=[products.utils.validate_image_format], verbose_name='Imagen'),
        ),
    ]
