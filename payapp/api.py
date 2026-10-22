from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import MAX_AMOUNT



@api_view(['GET'])
def conversion(request, currency1, currency2, amount_of_currency1):
    c1 = currency1.upper()
    c2 = currency2.upper()

    rates = settings.EXCHANGE_RATES
    if c1 not in rates or c2 not in rates[c1]:
        return Response(
            {'error': f'Currency pair {c1}->{c2} is not supported.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = Decimal(amount_of_currency1)
        if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
            raise InvalidOperation
        rate = Decimal(str(rates[c1][c2]))
        converted = (amount * rate).quantize(Decimal('0.01'))
        if converted > MAX_AMOUNT:
            raise InvalidOperation
    except InvalidOperation:
        return Response(
            {'error': f"Amount '{amount_of_currency1}' is not a valid number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'currency1': c1,
        'currency2': c2,
        'rate': str(rate),
        'amount': str(amount),
        'converted_amount': str(converted),
    })
