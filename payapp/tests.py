from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, LiveServerTestCase, TestCase, override_settings
from django.urls import reverse

from register.forms import RegisterForm
from register.models import Account
from .models import Payment, PaymentRequest
from .services import convert, MAX_AMOUNT


def local_rate(amount, src, dst):
    return (Decimal(amount) * Decimal(str(settings.EXCHANGE_RATES[src][dst]))).quantize(Decimal('0.01'))


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PaymentRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', 'alice@example.test', 'test-only-secret-391')
        cls.bob = User.objects.create_user('bob', 'bob@example.test', 'test-only-secret-392')
        Account.objects.create(user=cls.alice, currency='GBP', balance=1000)
        Account.objects.create(user=cls.bob, currency='USD', balance=100)

    def setUp(self):
        self.client.force_login(self.alice)

    @patch('payapp.views.convert', side_effect=local_rate)
    def test_payment_moves_both_balances_and_creates_one_record(self, _):
        response = self.client.post(reverse('make_payment'), {
            'counterparty_email': self.bob.email, 'amount': '10.00', 'currency': 'GBP'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Account.objects.get(user=self.alice).balance, Decimal('990.00'))
        self.assertEqual(Account.objects.get(user=self.bob).balance, Decimal('112.70'))
        self.assertEqual(Payment.objects.count(), 1)

    @patch('payapp.views.convert', side_effect=local_rate)
    def test_insufficient_funds_has_no_partial_transfer(self, _):
        self.client.post(reverse('make_payment'), {
            'counterparty_email': self.bob.email, 'amount': '1001.00', 'currency': 'GBP'})
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(Account.objects.get(user=self.alice).balance, Decimal('1000.00'))
        self.assertEqual(Account.objects.get(user=self.bob).balance, Decimal('100.00'))

    @patch('payapp.views.convert', side_effect=local_rate)
    def test_balance_overflow_is_rejected(self, _):
        Account.objects.filter(user=self.bob).update(balance=MAX_AMOUNT)
        self.client.post(reverse('make_payment'), {
            'counterparty_email': self.bob.email, 'amount': '1.00', 'currency': 'GBP'})
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(Account.objects.get(user=self.alice).balance, Decimal('1000.00'))

    def test_self_payment_and_invalid_amounts_do_not_create_records(self):
        for email, amount in [(self.alice.email, '1.00'), (self.bob.email, '0'),
                              (self.bob.email, '-1'), (self.bob.email, 'NaN')]:
            self.client.post(reverse('make_payment'), {
                'counterparty_email': email, 'amount': amount, 'currency': 'GBP'})
        self.assertFalse(Payment.objects.exists())

    def make_request(self):
        return PaymentRequest.objects.create(requester=self.bob, target=self.alice,
                                             amount='5.00', currency='GBP')

    @patch('payapp.views.convert', side_effect=local_rate)
    def test_request_is_accepted_only_once(self, _):
        item = self.make_request()
        url = reverse('respond_to_request', args=[item.pk])
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 302)
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 404)
        self.assertEqual(Payment.objects.filter(fulfilled_request=item).count(), 1)
        self.assertEqual(Account.objects.get(user=self.alice).balance, Decimal('995.00'))

    def test_rejection_and_ownership_checks(self):
        item = self.make_request()
        url = reverse('respond_to_request', args=[item.pk])
        self.client.force_login(self.bob)
        self.assertEqual(self.client.post(url, {'action': 'accept'}).status_code, 404)
        self.client.force_login(self.alice)
        self.client.post(url, {'action': 'reject'})
        item.refresh_from_db()
        self.assertEqual(item.status, PaymentRequest.REJECTED)
        self.assertFalse(Payment.objects.exists())

    def test_response_and_logout_require_post_and_csrf(self):
        item = self.make_request()
        self.assertEqual(self.client.get(reverse('respond_to_request', args=[item.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.alice)
        self.assertEqual(csrf_client.post(reverse('respond_to_request', args=[item.pk]), {'action': 'accept'}).status_code, 403)
        self.assertEqual(csrf_client.post(reverse('logout')).status_code, 403)

    def test_admin_pages_are_not_available_to_regular_or_anonymous_users(self):
        for name in ('admin_users', 'admin_transactions', 'admin_register'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_conversion_rejects_nonfinite_and_out_of_range_values(self):
        for amount in ('NaN', 'sNaN', 'Infinity', '-1', '1e99999', 'not-a-number'):
            self.assertEqual(self.client.get(reverse('conversion', args=['GBP', 'USD', amount])).status_code, 400)
        self.assertEqual(self.client.get(reverse('conversion', args=['GBP', 'XYZ', '1'])).status_code, 400)
        self.assertEqual(self.client.post(reverse('conversion', args=['GBP', 'USD', '1'])).status_code, 405)
        self.assertEqual(self.client.get(reverse('conversion', args=['GBP', 'USD', '10'])).json()['converted_amount'], '12.70')

    @patch('register.forms.to_user_currency', side_effect=ValueError('Currency service unavailable.'))
    def test_registration_failure_rolls_back_for_users_and_admins(self, _):
        payload = {'username': 'new-user', 'first_name': 'New', 'last_name': 'User',
                   'email': 'new@example.test', 'currency': 'EUR',
                   'password1': 'test-only-new-secret-198', 'password2': 'test-only-new-secret-198'}
        self.client.post(reverse('register'), payload)
        self.assertFalse(User.objects.filter(username='new-user').exists())
        self.alice.is_staff = True
        self.alice.save()
        self.client.post(reverse('admin_register'), payload)
        self.assertFalse(User.objects.filter(username='new-user').exists())

    @override_settings(DEBUG=True, INTERNAL_API_BASE='https://localhost:8000', INTERNAL_API_CA_BUNDLE=True)
    @patch('payapp.services.requests.get')
    def test_conversion_verifies_tls_and_handles_service_errors(self, get):
        get.return_value = Mock(json=lambda: {'converted_amount': '1.27'})
        self.assertEqual(convert(Decimal('1'), 'GBP', 'USD'), Decimal('1.27'))
        self.assertIs(get.call_args.kwargs['verify'], True)
        get.side_effect = requests.Timeout()
        with self.assertRaises(ValueError):
            convert(Decimal('1'), 'GBP', 'USD')

    @override_settings(DEBUG=False, INTERNAL_API_BASE='http://127.0.0.1:8000')
    def test_insecure_internal_http_is_rejected_outside_debug(self):
        with self.assertRaises(ValueError):
            convert(Decimal('1'), 'GBP', 'USD')

    def test_fresh_database_does_not_contain_automatic_admin(self):
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_cli_superuser_gets_a_zero_balance_profile_on_first_dashboard(self):
        admin = User.objects.create_superuser('portfolio-admin', 'admin@example.test', 'test-only-admin-834')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertEqual(Account.objects.get(user=admin).balance, Decimal('0.00'))

    @patch('register.forms.to_user_currency', side_effect=local_rate)
    def test_registration_keeps_the_original_starting_balance(self, _):
        self.client.post(reverse('register'), {
            'username': 'new-person', 'first_name': 'New', 'last_name': 'Person',
            'email': 'new-person@example.test', 'currency': 'EUR',
            'password1': 'test-only-new-person-513', 'password2': 'test-only-new-person-513'})
        self.assertEqual(Account.objects.get(user__username='new-person').balance, Decimal('1170.00'))


@override_settings(DEBUG=True, SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver'])
class ConversionHTTPTests(LiveServerTestCase):
    def test_conversion_helper_calls_the_real_http_endpoint(self):
        with self.settings(INTERNAL_API_BASE=self.live_server_url):
            self.assertEqual(convert(Decimal('100'), 'GBP', 'EUR'), Decimal('117.00'))
