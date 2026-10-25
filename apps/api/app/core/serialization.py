from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def jsonable(value):
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value
