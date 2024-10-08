# Generated by Django 3.1.4 on 2022-07-21 13:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0036_usage"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserFeedback",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[(4, "excellent"), (3, "very good"), (2, "good"), (1, "fair"), (0, "poor")],
                        null=True,
                    ),
                ),
                ("comment", models.TextField(blank=True, max_length=500)),
                ("date", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
    ]
