# Generated by Django 3.1.4 on 2022-02-02 12:31

from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("django_etebase", "0037_auto_20210127_1237"),
        ("myauth", "0029_auto_20220202_1054"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="trustedservice",
            name="enabled",
        ),
        migrations.RemoveField(
            model_name="trustedservice",
            name="name",
        ),
        migrations.RemoveField(
            model_name="trustedservice",
            name="products",
        ),
        migrations.RemoveField(
            model_name="trustedservice",
            name="team",
        ),
        migrations.RemoveField(
            model_name="trustedservice",
            name="type",
        ),
        migrations.RemoveField(
            model_name="trustedservice",
            name="url",
        ),
        migrations.AlterField(
            model_name="trustedservice",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="trustedservice",
            name="plugin",
            field=models.OneToOneField(null=False, on_delete=django.db.models.deletion.CASCADE, to="myauth.plugin"),
        ),
        migrations.AddField(
            model_name="plugin",
            name="collections",
            field=models.ManyToManyField(blank=True, to="django_etebase.Collection"),
        ),
        migrations.AlterField(
            model_name="trustedservice",
            name="plugin",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="myauth.plugin"),
        ),
    ]