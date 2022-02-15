# Generated by Django 3.1.4 on 2022-02-02 10:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    def transfer_trustedservices_to_plugins(apps, schema_editor):
        TrustedService = apps.get_model("myauth", "TrustedService")
        Plugin = apps.get_model("myauth", "Plugin")
        trusted_services = TrustedService.objects.all()

        for ts in trusted_services:
            plugin = Plugin.objects.create(
                name=ts.name,
                type=ts.type,
                team_id=ts.team.id,
                url=ts.url,
                products=ts.products,
                enabled=ts.enabled,
            )
            ts.plugin = plugin
            ts.save()

    dependencies = [
        ("myauth", "0028_plugin_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="trustedservice",
            name="plugin",
            field=models.ForeignKey(
                default=None, on_delete=django.db.models.deletion.CASCADE, to="myauth.plugin", unique=True, null=True
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="plugin",
            name="team",
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to="myauth.team"),
        ),
        migrations.AlterField(
            model_name="plugin",
            name="url",
            field=models.URLField(),
        ),
        migrations.RunPython(transfer_trustedservices_to_plugins),
    ]
