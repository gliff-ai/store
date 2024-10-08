# Generated by Django 3.1.4 on 2021-08-03 08:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0011_auto_20210802_1609"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tier",
            name="base_collaborator_limit",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="tier",
            name="base_project_limit",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="tier",
            name="base_storage_limit",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="tier",
            name="base_user_limit",
            field=models.IntegerField(null=True),
        ),
    ]
