"""
Currency display conversion.

Model: the site has ONE base currency (Settings -> Payment Config ->
Site Currency, e.g. NGN). The admin manually enters a rate for every
OTHER currency, meaning "how many units of the base currency equal 1
unit of this currency" — e.g. if the base is NGN and the admin enters
USD = 1500, that means 1 USD = 1500 NGN. This matches how a Nigerian
site owner actually thinks about it ("dollar is 1500 today"), and it's
fully manual/deterministic — no external exchange-rate API, no rates
drifting behind your back, no network dependency at checkout time or
on the homepage.

Prices are stored in the database in whatever currency they were
created in (each model's own `currency` column) — this module converts
for DISPLAY (and for summing money across currencies on report pages)
using that manual rate table. It does not change what a payment
gateway actually charges: Paystack still settles in NGN, Stripe in
whatever you configured it for, etc. Making the actual CHECKOUT
currency dynamic per-gateway is a separate, larger project tied to
each gateway's own supported-currency rules — this is the honest,
deliverable half: "show/sum prices in a currency of my choosing" while
checkout still happens through whichever gateway is set up.
"""
import json

from app.utils.settings import get_setting

SUPPORTED_CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar"},
    "NGN": {"symbol": "₦", "name": "Nigerian Naira"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
    "GHS": {"symbol": "GH₵", "name": "Ghanaian Cedi"},
    "KES": {"symbol": "KSh", "name": "Kenyan Shilling"},
    "ZAR": {"symbol": "R", "name": "South African Rand"},
}


def base_currency():
    """The site's own currency — everything is priced in this unless a
    manual rate converts it. Set in Admin -> Payment Config."""
    code = (get_setting("site_currency") or "NGN").upper()
    return code if code in SUPPORTED_CURRENCIES else "NGN"


def get_rates():
    """Returns {currency_code: units_of_BASE_currency per 1 unit of that
    currency}, read straight from the admin's manual rate table (no
    external API, no cache/staleness to reason about). The base currency
    itself is always 1. A currency with no rate entered yet is treated
    as 1 (i.e. shown unconverted) rather than crashing — the admin sees
    it's unset via the rates-management UI, not via a broken page."""
    base = base_currency()
    rates = {base: 1.0}
    raw = get_setting("manual_exchange_rates_json")
    if raw:
        try:
            parsed = json.loads(raw)
            for code, rate in parsed.items():
                code = code.upper()
                if code in SUPPORTED_CURRENCIES and code != base:
                    rates[code] = float(rate)
        except (ValueError, TypeError):
            pass
    return rates


def rates_are_missing_for(codes):
    """Which of these currency codes have no manual rate set yet (besides
    the base currency, which never needs one) — for warning the admin
    instead of silently showing wrong numbers."""
    base = base_currency()
    rates = get_rates()
    return [c for c in codes if c != base and c not in rates]


def convert(amount, from_currency, to_currency):
    if not amount:
        return 0.0
    from_currency = (from_currency or base_currency()).upper()
    to_currency = (to_currency or base_currency()).upper()
    if from_currency == to_currency:
        return float(amount)
    rates = get_rates()
    base_amount = float(amount) * rates.get(from_currency, 1.0)  # -> base currency
    return base_amount / rates.get(to_currency, 1.0)             # base -> target


def convert_and_sum(currency_amount_pairs, to_currency):
    """Sums a list/iterable of (currency, amount) pairs — typically from a
    `GROUP BY currency` query — converting each group into one target
    currency first. This is the correct way to answer "how much money
    have I made in total" when transactions happened in more than one
    currency: convert-then-add, never add raw amounts across currencies."""
    total = 0.0
    for currency, amount in currency_amount_pairs:
        if not amount:
            continue
        total += convert(float(amount), currency, to_currency)
    return total


def format_amount(amount, currency):
    info = SUPPORTED_CURRENCIES.get(currency, {"symbol": currency + " "})
    return f"{info['symbol']}{amount:,.2f}"


def display_price(amount, from_currency, to_currency):
    """One-stop conversion + formatting for templates."""
    converted = convert(amount, from_currency, to_currency)
    return format_amount(converted, to_currency)
