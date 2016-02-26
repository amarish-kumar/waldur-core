from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from nodeconductor.core.models import NameMixin


class ScopeMixin(models.Model):
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    scope = GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True


class ResourceItem(NameMixin, ScopeMixin):
    value = models.FloatField()

    class Meta:
        unique_together = ('name', 'content_type', 'object_id')


class ResourceSla(ScopeMixin):
    period = models.CharField(max_length=10)
    value = models.DecimalField(max_digits=11, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ('period', 'content_type', 'object_id')


class ResourceState(ScopeMixin):
    timestamp = models.IntegerField()
    state = models.BooleanField(default=False)

    class Meta:
        unique_together = ('timestamp', 'content_type', 'object_id')


class MonitoringModelMixin(models.Model):
    class Meta:
        abstract = True

    sla_items = GenericRelation('monitoring.ResourceSla')
    monitoring_items = GenericRelation('monitoring.ResourceItem')
    state_items = GenericRelation('monitoring.ResourceState')
