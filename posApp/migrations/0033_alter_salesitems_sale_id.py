# Generated by Django 5.0 on 2024-07-11 10:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0032_alter_customproforma_customer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesitems',
            name='sale_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salesitems', to='posApp.sales'),
        ),
    ]
