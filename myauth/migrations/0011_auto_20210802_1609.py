# Generated by Django 3.1.4 on 2021-08-02 16:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myauth', '0010_auto_20210730_0847'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tier',
            old_name='stripe_collaborator_project_id',
            new_name='stripe_project_price_id',
        ),
    ]