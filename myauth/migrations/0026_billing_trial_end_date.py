# Generated by Django 3.1.4 on 2022-01-25 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myauth', '0025_add_STSFT_tier'),
    ]

    operations = [
        migrations.AddField(
            model_name='billing',
            name='trial_end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]