# Generated by Django 3.1.4 on 2021-09-14 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myauth', '0016_merge_20210914_1019'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plugin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(unique=True)),
                ('product', models.CharField(choices=[('CURATE', 'CURATE'), ('ANNOTATE', 'ANNOTATE')], max_length=20)),
                ('enabled', models.BooleanField(default=False)),
                ('teams', models.ManyToManyField(to='myauth.Team')),
            ],
        ),
    ]
