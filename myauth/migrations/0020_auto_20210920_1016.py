# Generated by Django 3.1.4 on 2021-09-20 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0019_trustedservice_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="recovery_key",
            field=models.TextField(null=True),
        ),
    ]
