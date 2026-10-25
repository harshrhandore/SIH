"""Version-one deterministic algorithms for synthetic records only."""

from app.core.identifiers import luhn as luhn, synthetic_id as synthetic_id, valid_id as valid_id
from app.core.numbers import money_round as money_round
from app.modules.trust.service import trust as trust
from app.modules.career.service import career as career
from app.modules.career.catalogue import CATALOGUE as CATALOGUE
from app.modules.verification.matching import (
    normalized_name as normalized_name,
    name_match as name_match,
    possible_match as possible_match,
)


import re
import json
import unicodedata
from datetime import date
from decimal import Decimal
from app.settings import ROOT

MISSING = {"", "na", "n/a", "null", "none", "-"}


def clean(value):
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value)).strip()
    return None if text.casefold() in MISSING else text


def academic_cgpas(terms):
    weighted, credits = Decimal(0), Decimal(0)
    out = []
    for sgpa, credit in terms:
        weighted += Decimal(str(sgpa)) * Decimal(str(credit))
        credits += Decimal(str(credit))
        out.append(money_round(weighted / credits))
    return out


def certificate_confidence(extracted, student, as_of):
    n, guard = name_match(extracted.get("name"), student.get("full_name"))
    issuer = normalized_name(extracted.get("issuer"))
    providers = {
        normalized_name(name): entry["pattern"]
        for name, entry in json.loads((ROOT / "db/seed/certificate_providers.json").read_text(encoding="utf-8")).items()
    }
    i = Decimal(1) if issuer in providers else Decimal(".5") if issuer else Decimal(0)
    d = Decimal(0)
    try:
        issued = date.fromisoformat(extracted.get("date") or "")
        dob = date.fromisoformat(str(student["dob"]))
        d = Decimal(int(date(dob.year + 14, dob.month, min(dob.day, 28)) <= issued <= date.fromisoformat(as_of)))
    except (ValueError, TypeError, KeyError):
        pass
    credential = (extracted.get("credential_id") or "").upper()
    c = (
        Decimal(1)
        if issuer in providers and re.fullmatch(providers[issuer], credential)
        else Decimal(2) / Decimal(3)
        if re.fullmatch(r"[A-Z0-9-]{6,40}", credential)
        else Decimal(0)
    )
    confidence = money_round(
        100 * (Decimal(".5") * Decimal(str(n / 100)) + Decimal(".2") * i + Decimal(".15") * d + Decimal(".15") * c)
    )
    return float(confidence), dict(name=n / 100, issuer=float(i), date=float(d), credential_id=float(c)), guard
