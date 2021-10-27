# Generated by Django 3.1.4 on 2021-10-20 10:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myauth', '0022_team_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='tier',
            name='is_custom',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='CustomBilling',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('renewal_date', models.DateTimeField(blank=True, null=True)),
                ('cancel_date', models.DateTimeField(blank=True, null=True)),
                ('team', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='myauth.team')),
            ],
        ),
    ]
