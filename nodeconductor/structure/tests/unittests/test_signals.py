from django.test import TestCase

from nodeconductor.openstack import models as openstack_models
from nodeconductor.structure import models, SupportedServices
from nodeconductor.structure.tests import factories


class ProjectSignalsTest(TestCase):

    def setUp(self):
        self.project = factories.ProjectFactory()

    def test_admin_project_role_is_created_upon_project_creation(self):
        self.assertTrue(self.project.roles.filter(role_type=models.ProjectRole.ADMINISTRATOR).exists(),
                        'Administrator role should have been created')

    def test_manager_project_role_is_created_upon_project_creation(self):
        self.assertTrue(self.project.roles.filter(role_type=models.ProjectRole.MANAGER).exists(),
                        'Manager role should have been created')


class ProjectGroupSignalsTest(TestCase):

    def setUp(self):
        self.project_group = factories.ProjectGroupFactory()

    def test_group_manager_role_is_created_upon_project_group_creation(self):
        self.assertTrue(self.project_group.roles.filter(role_type=models.ProjectGroupRole.MANAGER).exists(),
                        'Group manager role should have been created')


class ServiceSettingsSignalsTest(TestCase):

    def setUp(self):
        self.openstack_shared_service_settings = factories.ServiceSettingsFactory(
            type=SupportedServices.Types.OpenStack, shared=True)

    def test_shared_service_is_created_for_new_customer(self):
        customer = factories.CustomerFactory()

        self.assertTrue(openstack_models.OpenStackService.objects.filter(
            customer=customer, settings=self.openstack_shared_service_settings).exists())

    def test_new_shared_services_connects_to_existed_customers(self):
        customer = factories.CustomerFactory()
        new_shared_service_settings = factories.ServiceSettingsFactory(
            type=SupportedServices.Types.OpenStack, shared=True)

        self.assertTrue(openstack_models.OpenStackService.objects.filter(
            customer=customer, settings=new_shared_service_settings).exists())
