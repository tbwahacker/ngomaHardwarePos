# Generated by Django 5.0.4 on 2024-06-27 10:44

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posApp', '0030_customproforma'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='customproforma',
            old_name='price',
            new_name='grand_total',
        ),
        migrations.RenameField(
            model_name='customproforma',
            old_name='tendered_price',
            new_name='sub_total',
        ),
        migrations.RemoveField(
            model_name='customproforma',
            name='product_id',
        ),
        migrations.RemoveField(
            model_name='customproforma',
            name='qty',
        ),
        migrations.RemoveField(
            model_name='customproforma',
            name='total',
        ),
        migrations.AddField(
            model_name='customproforma',
            name='code',
            field=models.CharField(default=0, max_length=100000000),
        ),
        migrations.AddField(
            model_name='customproforma',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='posApp.supplier'),
        ),
        migrations.AddField(
            model_name='customproforma',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='products',
            name='code',
            field=models.CharField(max_length=1000000000),
        ),
        migrations.AlterField(
            model_name='purchases',
            name='code',
            field=models.CharField(max_length=100000000),
        ),
        migrations.AlterField(
            model_name='sales',
            name='code',
            field=models.CharField(max_length=100000000),
        ),
        migrations.CreateModel(
            name='CustomProformaItems',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tendered_price', models.FloatField(default=0)),
                ('price', models.FloatField(default=0)),
                ('qty', models.IntegerField(default=0)),
                ('total', models.FloatField(default=0)),
                ('date_added', models.DateTimeField(default=django.utils.timezone.now)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('product_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='posApp.products')),
                ('proforma_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='posApp.customproforma')),
            ],
        ),
    ]
