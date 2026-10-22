from django.db import models
from django.conf import settings


# completed transfer of money from sender to recipient
class Payment(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments_sent',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments_received',
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)

    timestamp = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    fulfilled_request = models.OneToOneField(
        'PaymentRequest', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='resulting_payment',
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.sender} -> {self.recipient}: {self.amount} {self.currency}'


# requester asks target for money.
# status: PENDING -> ACCEPTED or REJECTED
class PaymentRequest(models.Model):
    PENDING, ACCEPTED, REJECTED = 'P', 'A', 'R'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='requests_made',
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='requests_received',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (f'{self.requester} <- {self.target}: '
                f'{self.amount} {self.currency} [{self.get_status_display()}]')