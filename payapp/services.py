from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlparse

import requests
from django.conf import settings

MAX_AMOUNT = Decimal('9999999999.99')


_CONVERSION_URL = "{base}/webapps2026/conversion/{c1}/{c2}/{amount}/"


# convert amount from src to dst via the REST endpoint.
def convert(amount: Decimal, src: str, dst: str) -> Decimal:
    amount = Decimal(amount)
    if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
        raise ValueError('Amount is outside the supported range.')
    if src == dst:
        return Decimal(amount)

    base = settings.INTERNAL_API_BASE.rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme != 'https' and not (
        settings.DEBUG and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')
    ):
        raise ValueError('Currency service requires HTTPS outside local development.')
    url = _CONVERSION_URL.format(
        base=base,
        c1=quote(src),
        c2=quote(dst),
        amount=quote(str(amount)),
    )
    try:
        resp = requests.get(url, timeout=5, verify=settings.INTERNAL_API_CA_BUNDLE)
        resp.raise_for_status()
        result = Decimal(resp.json()['converted_amount'])
        if not result.is_finite() or result < 0 or result > MAX_AMOUNT:
            raise ValueError('Invalid converted amount')
        return result
    except (requests.RequestException, InvalidOperation, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Currency service is unavailable or returned invalid data.') from exc


# convert the initial balance into the user's chosen currency
def to_user_currency(gbp_amount, src: str, dst: str) -> Decimal:
    return convert(Decimal(str(gbp_amount)), src, dst)
