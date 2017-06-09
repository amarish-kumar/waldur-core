# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-05-18 09:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields
import nodeconductor.core.fields
import nodeconductor.core.models
import nodeconductor.core.validators
import nodeconductor.logging.loggers
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('structure', '0050_reset_cloud_spl_quota_limits'),
        ('taggit', '0002_auto_20150616_2121'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestNewInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('description', models.CharField(blank=True, max_length=500, verbose_name='description')),
                ('name', models.CharField(max_length=150, validators=[nodeconductor.core.validators.validate_name], verbose_name='name')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('error_message', models.TextField(blank=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('runtime_state', models.CharField(blank=True, max_length=150, verbose_name='runtime state')),
                ('state', django_fsm.FSMIntegerField(choices=[(5, 'Creation Scheduled'), (6, 'Creating'), (1, 'Update Scheduled'), (2, 'Updating'), (7, 'Deletion Scheduled'), (8, 'Deleting'), (3, 'OK'), (4, 'Erred')], default=5)),
                ('backend_id', models.CharField(blank=True, max_length=255)),
                ('cores', models.PositiveSmallIntegerField(default=0, help_text='Number of cores in a VM')),
                ('ram', models.PositiveIntegerField(default=0, help_text='Memory size in MiB')),
                ('disk', models.PositiveIntegerField(default=0, help_text='Disk size in MiB')),
                ('min_ram', models.PositiveIntegerField(default=0, help_text='Minimum memory size in MiB')),
                ('min_disk', models.PositiveIntegerField(default=0, help_text='Minimum disk size in MiB')),
                ('image_name', models.CharField(blank=True, max_length=150)),
                ('key_name', models.CharField(blank=True, max_length=50)),
                ('key_fingerprint', models.CharField(blank=True, max_length=47)),
                ('user_data', models.TextField(blank=True, help_text='Additional data that will be added to instance on provisioning')),
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('flavor_name', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'abstract': False,
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.core.models.BackendModelMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TestService',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('available_for_all', models.BooleanField(default=False, help_text='Service will be automatically added to all customers projects if it is available for all')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.Customer', verbose_name='organization')),
            ],
            options={
                'abstract': False,
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TestServiceProjectLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.Project')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure_tests.TestService')),
            ],
            options={
                'abstract': False,
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.AddField(
            model_name='testservice',
            name='projects',
            field=models.ManyToManyField(through='structure_tests.TestServiceProjectLink', to='structure.Project'),
        ),
        migrations.AddField(
            model_name='testservice',
            name='settings',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.ServiceSettings'),
        ),
        migrations.AddField(
            model_name='testnewinstance',
            name='service_project_link',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='structure_tests.TestServiceProjectLink'),
        ),
        migrations.AddField(
            model_name='testnewinstance',
            name='tags',
            field=taggit.managers.TaggableManager(blank=True, help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
        migrations.AlterUniqueTogether(
            name='testserviceprojectlink',
            unique_together=set([('service', 'project')]),
        ),
        migrations.AlterUniqueTogether(
            name='testservice',
            unique_together=set([('customer', 'settings')]),
        ),
    ]