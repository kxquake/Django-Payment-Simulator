from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Account

from payapp.services import to_user_currency
from django.conf import settings
from django.db import transaction


# Django's UserCreationForm plus email, first/last name, and currency.
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    currency = forms.ChoiceField(choices=Account.CURRENCY_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        # Keep User and Account creation together for both registration routes.
        user = super().save(commit=False)
        if not commit:
            return user
        user.save()
        Account.objects.create(
            user=user, currency=self.cleaned_data['currency'],
            balance=to_user_currency(
                settings.INITIAL_BALANCE_GBP, 'GBP', self.cleaned_data['currency']
            ),
        )
        return user


class LoginForm(AuthenticationForm):
    pass
