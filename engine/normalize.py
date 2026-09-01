"""Normalization utilities: amounts to integer paise, dates to ISO, strings cleaned."""
import re
from datetime import date, datetime


def normalize_amount_paise(value) -> int:
    """Accepts an integer/float/str amount already in paise and returns a clean int.

    All CSVs in this project store amounts in paise already (see data/generate_data.py),
    so this is a light validation pass, not a unit conversion.
    """
    if isinstance(value, str):
        value = value.strip()
    return int(round(float(value)))


def normalize_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    return datetime.strptime(s, "%Y-%m-%d").date()


def normalize_reference(value: str) -> str:
    s = "" if value is None else str(value)
    s = s.upper()
    s = re.sub(r"[\s\-_]+", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def normalize_text(value: str) -> str:
    s = "" if value is None else str(value)
    return s.strip().lower()
