from decimal import Decimal
from django import forms
from django.contrib.auth.models import User
from register.models import Account


# shared parent for 'make a payment' and 'request payment'.
class _BaseTransferForm(forms.Form):
    counterparty_email = forms.EmailField(
        label='Recipient email',
        help_text='The email address of the registered user.',
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
    )
    currency = forms.ChoiceField(choices=Account.CURRENCY_CHOICES)

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = sender

    def clean_counterparty_email(self):
        email = self.cleaned_data['counterparty_email']
        matches = User.objects.filter(email__iexact=email)
        if not matches.exists():
            raise forms.ValidationError('No registered user has this email.')
        if matches.count() > 1:
            raise forms.ValidationError('Email in use already.')
        counterparty = matches.first()
        if self.sender and counterparty.pk == self.sender.pk:
            raise forms.ValidationError('You cannot send to / request from yourself.')
        self.cleaned_data['counterparty'] = counterparty
        return email


class MakePaymentForm(_BaseTransferForm):
    pass


class RequestPaymentForm(_BaseTransferForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['counterparty_email'].label = 'Pay-from email'