"""Normalized, corroborated matching; similarity alone never merges records."""

from collections import defaultdict


import unicodedata
from rapidfuzz import fuzz
from unidecode import unidecode


def normalized_name(value):
    text = unicodedata.normalize("NFC", value or "").casefold()
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    tokens = text.split()
    while tokens and tokens[0] in {"mr", "mrs", "ms", "dr"}:
        tokens.pop(0)
    return " ".join(tokens)


def name_match(a, b):
    x, y = normalized_name(a), normalized_name(b)
    if not x or not y:
        return 0.0, False
    score = max(fuzz.token_set_ratio(x, y), fuzz.token_set_ratio(unidecode(x), unidecode(y)))
    guard = min(len(x.split()), len(y.split())) / max(len(x.split()), len(y.split())) >= 0.67
    guard = guard and (
        x == y or max(fuzz.token_sort_ratio(x, y), fuzz.token_sort_ratio(unidecode(x), unidecode(y))) >= 85
    )
    return score, guard


def possible_match(a, b):
    n, guard = name_match(a.get("full_name"), b.get("full_name"))
    p = (
        name_match(a.get("parent_name"), b.get("parent_name"))[0]
        if a.get("parent_name") and b.get("parent_name")
        else 0
    )
    same_dob = bool(a.get("dob") and str(a["dob"]) == str(b.get("dob")))
    score = 0.75 * n + 0.20 * (100 if same_dob else 0) + 0.05 * p
    return score, n >= 90 and guard and score >= 87 and (same_dob or p >= 90)


def make_indexes(rows, claims=None):
    by_id = {}
    by_enrollment = {}
    by_dob = defaultdict(list)
    for row in rows:
        if row.get("submitted_apaar_id"):
            by_id[row["submitted_apaar_id"]] = row
        if row.get("submitted_enrollment_no"):
            by_enrollment[row["submitted_enrollment_no"]] = row
        if row.get("dob"):
            by_dob[str(row["dob"])].append(row)
    for identifier, sid in (claims or {}).items():
        by_id.setdefault(identifier, dict(id=sid))
    return by_id, by_enrollment, by_dob
