# Generated by Django 3.1.4 on 2022-01-25 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myauth", "0025_add_STSFT_tier"),
    ]

    operations = [
        migrations.RenameField(
            model_name="trustedservice",
            old_name="base_url",
            new_name="url",
        ),
        migrations.RemoveField(
            model_name="plugin",
            name="product",
        ),
        migrations.AddField(
            model_name="plugin",
            name="name",
            field=models.CharField(default="some-name", max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="plugin",
            name="products",
            field=models.CharField(
                choices=[("CURATE", "CURATE"), ("ANNOTATE", "ANNOTATE"), ("ALL", "ALL")], default="ALL", max_length=20
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="trustedservice",
            name="enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trustedservice",
            name="products",
            field=models.CharField(
                choices=[("CURATE", "CURATE"), ("ANNOTATE", "ANNOTATE"), ("ALL", "ALL")], default="ALL", max_length=20
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="trustedservice",
            name="type",
            field=models.CharField(choices=[("Python", "Python"), ("AI", "AI")], default="Python", max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="trustedservice",
            name="name",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
