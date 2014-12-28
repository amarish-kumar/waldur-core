# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('structure', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='native_name',
            field=models.CharField(default='', max_length=160, blank=True),
            preserve_default=True,
        ),
    ]
