# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-05-22 00:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0021_pagevisit_preview'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='note',
            field=models.TextField(default=''),
        ),
    ]