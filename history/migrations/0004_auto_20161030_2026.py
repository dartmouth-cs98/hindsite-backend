# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-30 20:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0003_auto_20161028_2211'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeActive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(auto_now_add=True)),
                ('end', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ('start',),
            },
        ),
        migrations.AddField(
            model_name='domain',
            name='active_times',
            field=models.ManyToManyField(blank=True, to='history.TimeActive'),
        ),
    ]
