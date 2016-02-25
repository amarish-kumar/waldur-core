from django.db import transaction
from django.db.models import signals

from nodeconductor.quotas import models, utils, fields
from nodeconductor.quotas.log import alert_logger, event_logger
from nodeconductor.quotas.exceptions import CreationConditionFailedQuotaError


# Deprecated, new style quotas adds them self automatically
def add_quotas_to_scope(sender, instance, created=False, **kwargs):
    if created:
        from nodeconductor.quotas import models
        for quota_name in sender.QUOTAS_NAMES:
            models.Quota.objects.create(name=quota_name, scope=instance)


def check_quota_threshold_breach(sender, instance, **kwargs):
    # XXX: This import creates circular dependency between quotas and structure
    # TODO: Move spl-related logging to structure application.
    from nodeconductor.structure.models import ServiceProjectLink

    quota = instance
    alert_threshold = 0.8

    if quota.scope is not None:
        if quota.is_exceeded(threshold=alert_threshold):
            alert_logger.quota.warning(
                'Quota {quota_name} is over threshold. Limit: {quota_limit}, usage: {quota_usage}',
                scope=quota.scope,
                alert_type='quota_usage_is_over_threshold',
                alert_context={
                    'quota': quota
                })

            if quota.scope in ServiceProjectLink.get_all_models():
                spl = quota.scope
                event_logger.quota.warning(
                    '{quota_name} quota threshold has been reached for project {project_name}.',
                    event_type='quota_threshold_reached',
                    event_context={
                        'quota': quota,
                        'service': spl.service,
                        'project': spl.project,
                        'project_group': spl.project.project_groups.first(),
                        'threshold': alert_threshold * quota.limit,
                    })
        else:
            alert_logger.quota.close(scope=quota.scope, alert_type='quota_usage_is_over_threshold')


# XXX: rewrite global quotas
def create_global_quotas(**kwargs):
    for model in utils.get_models_with_quotas():
        if hasattr(model, 'GLOBAL_COUNT_QUOTA_NAME'):
            models.Quota.objects.get_or_create(name=getattr(model, 'GLOBAL_COUNT_QUOTA_NAME'))


def increase_global_quota(sender, instance=None, created=False, **kwargs):
    if created and hasattr(sender, 'GLOBAL_COUNT_QUOTA_NAME'):
        with transaction.atomic():
            global_quota = models.Quota.objects.select_for_update().get(
                name=getattr(sender, 'GLOBAL_COUNT_QUOTA_NAME'))
            global_quota.usage += 1
            global_quota.save()


def decrease_global_quota(sender, **kwargs):
    if hasattr(sender, 'GLOBAL_COUNT_QUOTA_NAME'):
        with transaction.atomic():
            global_quota = models.Quota.objects.select_for_update().get(
                name=getattr(sender, 'GLOBAL_COUNT_QUOTA_NAME'))
            global_quota.usage -= 1
            global_quota.save()


# new quotas

def init_quotas(sender, instance, created=False, **kwargs):
    """ Initialize new instances quotas """
    if not created:
        return
    for field in sender.get_quotas_fields():
        try:
            field.get_or_create_quota(scope=instance)
        except CreationConditionFailedQuotaError:
            pass


def count_quota_handler_factory(count_quota_field):
    """ Creates handler that will recalculate count_quota on creation/deletion """

    def recalculate_count_quota(sender, instance, **kwargs):
        signal = kwargs['signal']
        if signal == signals.post_save and kwargs.get('created'):
            count_quota_field.add_usage(instance, delta=1)
        elif signal == signals.post_delete:
            count_quota_field.add_usage(instance, delta=-1, fail_silently=True)

    return recalculate_count_quota


def handle_aggregated_quotas(sender, instance, **kwargs):
    """ Call aggregated quotas fields update methods """
    quota = instance
    # aggregation is not supported for global quotas.
    if quota.scope is None:
        return
    quota_field = quota.get_field()
    # usage aggregation should not count another usage aggregator field to avoid calls duplication.
    if isinstance(quota_field, fields.UsageAggregatorQuotaField) or quota_field is None:
        return
    signal = kwargs['signal']
    for aggregator_quota in quota_field.get_aggregator_quotas(quota):
        field = aggregator_quota.get_field()
        if signal == signals.post_save:
            field.post_child_quota_save(aggregator_quota.scope, child_quota=quota, created=kwargs.get('created'))
        elif signal == signals.pre_delete:
            field.pre_child_quota_delete(aggregator_quota.scope, child_quota=quota)
