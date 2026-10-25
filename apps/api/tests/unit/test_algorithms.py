from datetime import date
from decimal import Decimal
import pytest
from app.core.algorithms import (
    synthetic_id,
    valid_id,
    clean,
    normalized_name,
    name_match,
    academic_cgpas,
    certificate_confidence,
    trust,
    career,
    CATALOGUE,
    possible_match,
)
from app.core.audit import canonical


def test_id_boundaries():
    assert synthetic_id(1) == "SYN-0000000000018"
    for counter in [1, 2, 9, 10, 100001]:
        assert valid_id(synthetic_id(counter))
        assert not valid_id(synthetic_id(counter)[:-1] + "x")
    assert not valid_id("SYN-000000 000018")


def test_normalization_and_subset():
    assert clean("N/A") is None
    assert clean("0") == "0"
    assert normalized_name(" Dr. Riya  Sharma ") == "riya sharma"
    assert name_match("Riya", "Riya Sharma") == (100.0, False)
    assert name_match("Riya Sharma", "Sharma Riya")[1]


def test_cgpa():
    assert academic_cgpas([(v, 22) for v in ["8.2", "8.3", "8.4", "8.5", "8.1", "8.6", "8.7", "8.56"]])[-1] == Decimal(
        "8.42"
    )


def test_confidence():
    fields = dict(name="Riya Sharma", issuer="Shiksham Demo Academy", date="2026-06-20", credential_id="SYNDS-0018")
    value, _, guard = certificate_confidence(fields, dict(full_name="Riya Sharma", dob=date(2004, 6, 15)), "2026-10-25")
    assert value == 95 and guard
    fields["name"] = None
    assert certificate_confidence(fields, dict(full_name="Riya Sharma", dob=date(2004, 6, 15)), "2026-10-25")[0] < 85


def test_trust_and_career():
    inputs = dict(complete_fields=10, certificates=2, approved=True)
    assert trust(inputs)["score"] == 91
    assert trust({**inputs, "risk": 83})["score"] == 76
    assert career("DATA_SCIENTIST", {k: [{}] for k in list(CATALOGUE["DATA_SCIENTIST"])[:5]})["readiness_percent"] == 74
    assert all(sum(v.values()) == 100 for v in CATALOGUE.values())


def test_canonical():
    assert canonical({"z": "e\u0301", "a": None}) == '{"a":null,"z":"é"}'
    with pytest.raises(ValueError):
        canonical({"bad": 1.5})


def test_corroboration():
    assert not possible_match(dict(full_name="Riya Sharma"), dict(full_name="Riya Sharma"))[1]
    assert possible_match(
        dict(full_name="Riya Sharma", dob="2004-06-15"), dict(full_name="Riya Sharma", dob="2004-06-15")
    )[1]
