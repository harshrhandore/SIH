from decimal import Decimal, ROUND_HALF_UP


def money_round(value, places="0.01"):
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)
