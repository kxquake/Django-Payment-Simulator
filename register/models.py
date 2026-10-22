from django.db import models
from django.conf import settings



class Account(models.Model):
    CURRENCY_CHOICES = [
        ('GBP', 'GB Pounds'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account',
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GBP')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.user.username} - {self.balance} {self.currency}'