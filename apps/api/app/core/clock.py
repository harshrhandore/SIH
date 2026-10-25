"""UTC wall clock and the canonical six-digit event timestamp format."""

from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def utc_stamp(value=None):
    return (value or utc_now()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
