from decimal import Decimal
from app.core.algorithms import academic_cgpas


def test_cgpa():
    assert academic_cgpas([(v, 22) for v in ["8.2", "8.3", "8.4", "8.5", "8.1", "8.6", "8.7", "8.56"]])[-1] == Decimal(
        "8.42"
    )
