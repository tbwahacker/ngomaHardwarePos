# Generated by Django 5.0.4 on 2024-05-31 20:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0007_stockmovement_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovement',
            name='quantity_in_past',
            field=models.IntegerField(default=0),
        ),
    ]
