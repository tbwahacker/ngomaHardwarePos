# Generated by Django 5.0.4 on 2024-06-12 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0015_alter_sales_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
