# Generated by Django 5.0.4 on 2024-06-12 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0017_alter_stockmovement_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovement',
            name='quantity_returned',
            field=models.FloatField(default=0),
        ),
    ]
