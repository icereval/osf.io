# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-03-11 22:56
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('addons_osfstorage', '0002_nodesettings_root_node'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodesettings',
            name='root_node',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='osf.StoredFileNode'),
        ),
    ]
