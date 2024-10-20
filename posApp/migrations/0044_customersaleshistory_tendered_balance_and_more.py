# Generated by Django 5.0.4 on 2024-07-31 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0043_company_configured'),
    ]

    operations = [
        migrations.AddField(
            model_name='customersaleshistory',
            name='tendered_balance',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='customersaleshistory',
            name='tendered_initial_loan_amount',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='customersaleshistory',
            name='tendered_paid_amount',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='customersaleshistory',
            name='tendered_total_paid_amount',
            field=models.FloatField(default=0),
        ),
    ]
