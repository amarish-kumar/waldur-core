import re
import urllib
import hashlib
import datetime
import urlparse
import requests
import logging

from nodeconductor.billing.backend import BillingBackendError
from nodeconductor.core.utils import pwgen
from nodeconductor import __version__


logger = logging.getLogger(__name__)


class WHMCSAPI(object):
    """ WHMCS API client -- http://docs.whmcs.com/API
        Test settings:

            NODECONDUCTOR['BILLING'] = {
                'backend': 'nodeconductor.billing.backend.whmcs.WHMCSAPI',
                'api_url': 'http://demo.whmcs.com/includes/api.php',
                'username': 'Admin',
                'password': 'demo',
                'currency_code': 1,
                'currency_name': 'USD',
            }
    """

    class Request(object):
        class ResultSet(object):
            def __new__(cls, request, data):
                if request.resultset_path:
                    instance = object.__new__(cls)
                    instance.start = int(data.pop('startnumber', 0))
                    instance.limit = int(data.pop('numreturned', 0))
                    instance.total = int(data.pop('totalresults', 0))
                    return instance

                return type(cls.__name__, (dict,), {})(data)

            def __init__(self, request, data):
                self.request = request
                self.results = self._get_results(data)
                self.current = 0

            def __iter__(self):
                return self

            def _get_results(self, data):
                try:
                    return reduce(dict.get, self.request.resultset_path.split('.'), data)
                except TypeError:
                    logging.debug('Unexpected structure received as a response. Empty or missing response. %s', data)
                    raise StopIteration

            def __next__(self):
                return self.next()

            def next(self):
                try:
                    val = self.results.pop(0)
                except IndexError:
                    if self.current >= self.total:
                        raise StopIteration
                    else:
                        self.start = self.start + self.limit
                        self.results = self._get_results(
                            self.request.fetch(limitstart=self.start, limitnum=self.limit))
                        return self.next()
                else:
                    self.current += 1
                    return val

        def __init__(self, url, request_data, resultset_path=None):
            self.url = url
            self.request_data = request_data
            self.resultset_path = resultset_path

        def data(self):
            return self.ResultSet(self, self.fetch())

        def fetch(self, **kwargs):
            headers = {'User-Agent': 'NodeConductor/%s' % __version__,
                       'Content-Type': 'application/x-www-form-urlencoded'}

            data = self.request_data
            data.update(**kwargs)

            response = requests.post(self.url, data=data, headers=headers, verify=False)
            if response.status_code != 200:
                raise BillingBackendError(
                    "%s. Request to WHMCS backend failed: %s" %
                    (response.status_code, response.text))

            data = response.json()
            status = data.pop('result', None) or data.pop('status')
            if status != 'success':
                raise BillingBackendError(
                    "Can't perform '%s' on WHMCS backend: %s" %
                    (self.request_data['action'], data['message']))

            return data

    def __init__(self, api_url=None, username=None, password=None, currency_code=1, currency_name='USD', **kwargs):
        if not all((api_url, username, password)):
            raise BillingBackendError(
                "Missed billing credentials. They must be supplied explicitly "
                "or defined within settings.NODECONDUCTOR.BILLING")

        self.api_url = api_url
        self.username = username
        self.password = password
        self.currency_code = currency_code
        self.currency_name = currency_name

    def _parse_date(self, date):
        try:
            return datetime.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError as e:
            raise BillingBackendError("Can't parse date %s: %s" % (date, e))

    def _get_backend_url(self, path, args=()):
        url_parts = list(urlparse.urlparse(self.api_url))
        # XXX: a hack to support default deployments of whmcs that expose whmcs as the suffix name
        if url_parts[2].startswith('/whmcs/'):
            path = '/whmcs/%s' % path
        url_parts[2] = path
        url_parts[4] = urllib.urlencode(args)
        return urlparse.urlunparse(url_parts)

    def request(self, action, resultset_path=None, **kwargs):
        data = {'action': action, 'responsetype': 'json'}
        data.update(kwargs)
        data.update({
            'password': hashlib.md5(self.password).hexdigest(),
            'username': self.username})

        req = self.Request(self.api_url, data, resultset_path=resultset_path)
        return req.data()

    def add_client(self, name=None, email=None, organization=None, **kwargs):
        data = self.request(
            'addclient',
            firstname=name,
            lastname='n/a',
            companyname=organization,
            email=email,
            address1='n/a',
            city='n/a',
            state='n/a',
            postcode='00000',
            country='OM',
            phonenumber='1234567',
            password2=pwgen(),
            currency=self.currency_code,
        )

        return data['clientid']

    def get_client_details(self, client_id):
        data = self.request('getclientsdetails', clientid=client_id)
        return {'balance': data.get('credit')}

    def get_invoices(self, client_id, with_pdf=False):
        invoices = self.request(
            'getinvoices',
            userid=client_id,
            resultset_path='invoices.invoice')

        for invoice in invoices:
            data = dict(
                backend_id=invoice['id'],
                date=self._parse_date(invoice['date']),
                amount=invoice['total'],
                status=invoice['status']
            )

            if with_pdf:
                data['pdf'] = self.get_invoice_pdf(invoice['id'])

            yield data

    def get_invoice_items(self, invoice_id):
        data = self.request('getinvoice', invoiceid=invoice_id)
        return [{'backend_id': item['id'],
                 'name': item['description'],
                 'type': item['type'],
                 'amount': item['amount']}
                for item in data['items']['item']]

    def get_invoice_pdf(self, invoice_id):
        if not hasattr(self, 'session'):
            self.session = requests.Session()
            self.session.verify = False
            self.session.get(self._get_backend_url('/admin/login.php'))
            self.session.post(
                self._get_backend_url('/admin/dologin.php'),
                data={'username': self.username, 'password': self.password},
                headers={'Content-Type': 'application/x-www-form-urlencoded'})

        pdf = self.session.get(self._get_backend_url('/dl.php', {'type': 'i', 'id': invoice_id}))
        return pdf.content

    def get_products(self):
        products = self.request('getproducts', resultset_path='products.product')
        for product in products:
            yield {'backend_id': product['pid'],
                   'price': product['pricing'][self.currency_name]['monthly'],
                   'description': product['description'] or '',
                   'name': product['name']}

    def create_invoice(self, items, payment_method='banktransfer'):
        response = self.request('createinvoice', paymentmethod=payment_method, **items)

        return response['invoiceid']
