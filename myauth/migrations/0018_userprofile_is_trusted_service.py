# Generated by Django 3.1.4 on 2021-09-19 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0017_plugin"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_trusted_service",
            field=models.BooleanField(default=False),
        ),
    ]
