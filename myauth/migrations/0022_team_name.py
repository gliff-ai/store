# Generated by Django 3.1.4 on 2021-10-14 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myauth', '0021_update_stripe_storage_prices'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='name',
            field=models.CharField(default='', max_length=200),
        ),
    ]
