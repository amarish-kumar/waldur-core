import collections
import six

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Q

from nodeconductor.structure.models import Customer, Project, Service
from nodeconductor.cost_tracking.models import PriceEstimate, PayableMixin


class Command(BaseCommand):
    """
    This management command removes following price estimates:

    1) Price estimates with invalid content type.
       For example, resource plugin has been uninstalled,
       but its price estimates remained.

    2) Price estimates without valid scope and without details.
       For example, resource has been deleted, but its
       price estimate doesn't contain updated details,
       or its price estimates should be deleted.

    3) Price estimates for invalid month.
       Price estimates for each month should contain price estimate
       for at least one resource, one service, and one project.
       Otherwise it is considered invalid.
    """
    help = 'Delete invalid price estimates'

    def add_arguments(self, parser):
        parser.add_argument('--assume-yes', dest='assume_yes', action='store_true')
        parser.set_defaults(assume_yes=False)

    def handle(self, assume_yes, **options):
        self.assume_yes = assume_yes
        self.delete_price_estimates_for_invalid_content_types()
        self.delete_price_estimates_without_scope_and_details()
        self.delete_price_estimates_for_invalid_month()

    def confirm(self):
        if self.assume_yes:
            return True
        confirm = raw_input('Enter [y] to continue: ')
        return confirm.strip().lower() == 'y'

    def delete_price_estimates_for_invalid_month(self):
        invalid_estimates = self.get_all_estimates_wihout_scope_in_month()
        count = invalid_estimates.count()
        if count:
            self.stdout.write('{} price estimates without scope in month would be deleted.'.
                              format(count))
            if self.confirm():
                invalid_estimates.delete()

    def get_all_estimates_wihout_scope_in_month(self):
        invalid_estimates = []
        for customer in Customer.objects.all().only('pk'):
            customer_estimates = self.get_estimates_without_scope_in_month(customer.pk)
            invalid_estimates.extend(customer_estimates)
        ids = [estimate.pk for estimate in invalid_estimates]
        return PriceEstimate.objects.filter(pk__in=ids)

    def get_estimates_without_scope_in_month(self, customer_pk):
        qs = self.get_price_estimates_for_customer(customer_pk).only('year', 'month')
        estimates = list(qs)
        if not estimates:
            return []

        project_estimates = collections.defaultdict(list)
        service_estimates = collections.defaultdict(list)
        resource_estimates = collections.defaultdict(list)
        tables = (project_estimates, service_estimates, resource_estimates)

        dates = set()
        for estimate in estimates:
            cls = estimate.content_type.model_class()
            target = None
            if issubclass(cls, Project):
                target = project_estimates
            elif issubclass(cls, Service):
                target = service_estimates
            elif issubclass(cls, PayableMixin):
                target = resource_estimates
            date = (estimate.year, estimate.month)
            dates.add(date)
            if target in tables:
                target[date].append(estimate)

        invalid_estimates = []
        for date in dates:
            if any(map(lambda table: len(table[date]) == 0, tables)):
                for table in tables:
                    invalid_estimates.extend(table[date])
        return invalid_estimates

    def get_price_estimates_for_customer(self, customer_pk):
        qs = Q(scope_customer__pk=customer_pk)
        for model in PriceEstimate.get_estimated_models():
            content_type = ContentType.objects.get_for_model(model)
            ids = set(model.objects.filter(customer__pk=customer_pk).values_list('pk', flat=True))
            if ids:
                qs |= Q(content_type=content_type, object_id__in=ids)
        return PriceEstimate.objects.all().filter(qs)

    def delete_price_estimates_without_scope_and_details(self):
        invalid_estimates = self.get_invalid_price_estimates()
        count = invalid_estimates.count()
        if count:
            self.stdout.write('{} price estimates without scope and details would be deleted.'.
                              format(count))
            if self.confirm():
                invalid_estimates.delete()

    def get_invalid_price_estimates(self):
        query = Q(details='', object_id=None)
        for model in PriceEstimate.get_estimated_models():
            content_type = ContentType.objects.get_for_model(model)
            ids = set(model.objects.all().values_list('id', flat=True))
            if ids:
                query |= Q(content_type=content_type, object_id__in=ids)
        return PriceEstimate.objects.all().exclude(query)

    def delete_price_estimates_for_invalid_content_types(self):
        content_types = self.get_invalid_content_types()
        content_types_list = ', '.join(map(six.text_type, content_types))

        query = Q(content_type__in=content_types) | Q(content_type__isnull=True)
        invalid_estimates = PriceEstimate.objects.all().filter(query).filter()
        count = invalid_estimates.count()

        if count:
            self.stdout.write('{} price estimates for invalid content types would be deleted: {}'.
                              format(count, content_types_list))
            if self.confirm():
                invalid_estimates.delete()

    def get_invalid_content_types(self):
        valid = [
            ContentType.objects.get_for_model(model)
            for model in PriceEstimate.get_estimated_models()
        ]
        invalid = set(
            PriceEstimate.objects.all()
            .exclude(content_type__in=valid)
            .distinct()
            .values_list('content_type_id', flat=True)
        )

        return ContentType.objects.all().filter(id__in=invalid)