# Generated by Django 3.1.4 on 2021-09-20 10:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0018_userprofile_is_trusted_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="trustedservice",
            name="user",
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.RESTRICT, to="myauth.user"),
            preserve_default=False,
        ),
    ]
