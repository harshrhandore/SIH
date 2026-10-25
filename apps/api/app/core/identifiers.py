"""Synthetic identifier format and Luhn check; no official verification."""

import re


def luhn(digits):
    return (
        sum(
            (int(c) * 2 - 9 if int(c) * 2 > 9 else int(c) * 2) if i % 2 else int(c)
            for i, c in enumerate(reversed(digits))
        )
        % 10
    )


def synthetic_id(counter):
    base = f"{counter:012d}"
    return "SYN-" + base + str((10 - luhn(base + "0")) % 10)


def valid_id(value):
    return bool(value and re.fullmatch(r"SYN-[0-9]{13}", value) and luhn(value[4:]) == 0)
