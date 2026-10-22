from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from register.models import Account
from register.forms import RegisterForm
from .permissions import admin_required
from .forms import MakePaymentForm, RequestPaymentForm
from .models import Payment, PaymentRequest
from .services import convert, MAX_AMOUNT


# landing page - shows account balance
@login_required
def dashboard(request):
    # CLI-created superusers have no coursework Account row yet; never grant demo funds here.
    account, _ = Account.objects.get_or_create(user=request.user)
    unseen_payments = Payment.objects.filter(recipient=request.user, is_seen=False).count()
    unseen_requests = PaymentRequest.objects.filter(
        target=request.user, status=PaymentRequest.PENDING, is_seen=False
    ).count()
    return render(request, 'payapp/dashboard.html', {
        'account': account,
        'unseen_payments': unseen_payments,
        'unseen_requests': unseen_requests,
    })


# all payments and requests involving this user
@login_required
def transactions_list(request):
    user = request.user
    payments_out = Payment.objects.filter(sender=user)
    payments_in = Payment.objects.filter(recipient=user)
    requests_out = PaymentRequest.objects.filter(requester=user)
    requests_in = PaymentRequest.objects.filter(target=user)
    return render(request, 'payapp/transactions.html', {
        'payments_out': payments_out,
        'payments_in': payments_in,
        'requests_out': requests_out,
        'requests_in': requests_in,
    })



@login_required
@csrf_protect
def make_payment(request):
    if request.method != 'POST':
        return render(request, 'payapp/make_payment.html',
                      {'form': MakePaymentForm(sender=request.user)})

    form = MakePaymentForm(request.POST, sender=request.user)
    if not form.is_valid():
        return render(request, 'payapp/make_payment.html', {'form': form})

    counterparty = form.cleaned_data['counterparty']
    amount = form.cleaned_data['amount']
    currency = form.cleaned_data['currency']

    try:
        with transaction.atomic():
            sender_acc = Account.objects.select_for_update().get(user=request.user)
            recipient_acc = Account.objects.select_for_update().get(user=counterparty)

            debit = convert(amount, currency, sender_acc.currency)
            credit = convert(amount, currency, recipient_acc.currency)

            if sender_acc.balance < debit:
                raise ValueError('Insufficient funds.')
            if recipient_acc.balance + credit > MAX_AMOUNT:
                raise ValueError('Recipient balance would exceed the supported limit.')

            sender_acc.balance -= debit
            recipient_acc.balance += credit
            sender_acc.save()
            recipient_acc.save()

            Payment.objects.create(
                sender=request.user, recipient=counterparty,
                amount=amount, currency=currency,
            )
        transaction.on_commit(
            lambda: messages.success(
                request, f'Payment of {amount} {currency} sent to {counterparty.username}.')
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return render(request, 'payapp/make_payment.html', {'form': form})

    return redirect('transactions')


# inserts a row, doesn't move money. money moves in respond_to_request.
@login_required
@csrf_protect
def request_payment(request):
    if request.method != 'POST':
        return render(request, 'payapp/request_payment.html',
                      {'form': RequestPaymentForm(sender=request.user)})

    form = RequestPaymentForm(request.POST, sender=request.user)
    if not form.is_valid():
        return render(request, 'payapp/request_payment.html', {'form': form})

    PaymentRequest.objects.create(
        requester=request.user,
        target=form.cleaned_data['counterparty'],
        amount=form.cleaned_data['amount'],
        currency=form.cleaned_data['currency'],
    )
    messages.success(request, 'Payment request sent.')
    return redirect('transactions')


# unseen payments and pending requests.
# pending requests stay flagged until they're opened
@login_required
def notifications(request):
    user = request.user
    new_payments = list(Payment.objects.filter(recipient=user, is_seen=False))
    pending = list(PaymentRequest.objects.filter(target=user, status=PaymentRequest.PENDING))

    Payment.objects.filter(pk__in=[p.pk for p in new_payments]).update(is_seen=True)
    PaymentRequest.objects.filter(pk__in=[r.pk for r in pending]).update(is_seen=True)

    return render(request, 'payapp/notifications.html', {
        'new_payments': new_payments,
        'pending': pending,
    })



@login_required
@csrf_protect
@require_POST
@transaction.atomic
def respond_to_request(request, request_id):
    pr = get_object_or_404(
        PaymentRequest.objects.select_for_update(), pk=request_id, target=request.user,
        status=PaymentRequest.PENDING,
    )

    action = request.POST.get('action')
    if action == 'reject':
        pr.status = PaymentRequest.REJECTED
        pr.save()
        messages.info(request, 'Request rejected.')
        return redirect('notifications')

    if action != 'accept':
        return redirect('notifications')

    try:
        with transaction.atomic():
            target_acc = Account.objects.select_for_update().get(user=request.user)
            requester_acc = Account.objects.select_for_update().get(user=pr.requester)

            debit = convert(pr.amount, pr.currency, target_acc.currency)
            credit = convert(pr.amount, pr.currency, requester_acc.currency)

            if target_acc.balance < debit:
                raise ValueError('Insufficient funds.')
            if requester_acc.balance + credit > MAX_AMOUNT:
                raise ValueError('Recipient balance would exceed the supported limit.')

            target_acc.balance -= debit
            requester_acc.balance += credit
            target_acc.save()
            requester_acc.save()

            Payment.objects.create(
                sender=request.user, recipient=pr.requester,
                amount=pr.amount, currency=pr.currency,
                fulfilled_request=pr,
            )
            pr.status = PaymentRequest.ACCEPTED
            pr.save()

        transaction.on_commit(
            lambda: messages.success(request, 'Payment sent.')
        )
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('notifications')


@admin_required
def admin_all_users(request):
    users = User.objects.select_related('account').order_by('username')
    return render(request, 'admins/all_users.html', {'users': users})


@admin_required
def admin_all_transactions(request):
    return render(request, 'admins/all_transactions.html', {
        'payments': Payment.objects.select_related('sender', 'recipient'),
        'requests': PaymentRequest.objects.select_related('requester', 'target'),
    })


@admin_required
@csrf_protect
def admin_register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    user.is_staff = True
                    user.save()
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f'Administrator {user.username} created.')
                return redirect('admin_users')
    else:
        form = RegisterForm()
    return render(request, 'admins/register_admin.html', {'form': form})
