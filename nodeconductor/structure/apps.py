from __future__ import unicode_literals

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models import signals

from nodeconductor.quotas import handlers as quotas_handlers
from nodeconductor.structure import filters
from nodeconductor.structure import handlers


class StructureConfig(AppConfig):
    name = 'nodeconductor.structure'
    verbose_name = "NodeConductor Structure"

    # See, https://docs.djangoproject.com/en/1.7/ref/applications/#django.apps.AppConfig.ready
    def ready(self):
        User = get_user_model()
        Customer = self.get_model('Customer')
        Project = self.get_model('Project')
        ProjectGroup = self.get_model('ProjectGroup')

        signals.post_save.connect(
            handlers.log_customer_save,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_save',
        )

        signals.post_delete.connect(
            handlers.log_customer_delete,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_delete',
        )

        signals.post_save.connect(
            handlers.create_customer_roles,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.create_customer_roles',
        )

        signals.post_save.connect(
            handlers.create_project_roles,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.create_project_roles',
        )

        signals.post_save.connect(
            handlers.log_project_save,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_save',
        )

        signals.post_delete.connect(
            handlers.log_project_delete,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_delete',
        )

        signals.post_save.connect(
            handlers.create_project_group_roles,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.create_project_group_roles',
        )

        signals.pre_delete.connect(
            handlers.prevent_non_empty_project_group_deletion,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.prevent_non_empty_project_group_deletion',
        )

        signals.post_save.connect(
            handlers.log_project_group_save,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_save',
        )

        signals.post_delete.connect(
            handlers.log_project_group_delete,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_delete',
        )

        filters.set_permissions_for_model(
            User.groups.through,
            customer_path='group__projectrole__project__customer',
            project_group_path='group__projectrole__project__project_groups',
            project_path='group__projectrole__project',
        )

        signals.post_save.connect(
            quotas_handlers.add_quotas_to_scope,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.add_quotas_to_project',
        )
