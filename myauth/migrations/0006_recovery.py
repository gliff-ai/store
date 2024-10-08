# Generated by Django 3.1.4 on 2021-06-24 15:49

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0005_auto_20210624_1120"),
    ]

    operations = [
        migrations.CreateModel(
            name="Recovery",
            fields=[
                (
                    "uid",
                    models.CharField(
                        db_index=True,
                        max_length=43,
                        primary_key=True,
                        serialize=False,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Not a valid UID", regex="^[a-zA-Z0-9\\-_]{20,}$"
                            )
                        ],
                    ),
                ),
                ("expiry_date", models.DateTimeField()),
                (
                    "user_profile",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="myauth.userprofile"),
                ),
            ],
        ),
    ]
