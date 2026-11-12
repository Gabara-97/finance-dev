import re
from datetime import date
from decimal import Decimal, InvalidOperation

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ValidationError(Exception):
    pass


def uuid(x, label="id"):
    if not isinstance(x, str) or not UUID_RE.match(x):
        raise ValidationError(f"Invalid {label}")
    return x


def tx_type(x):
    if x not in ("income", "expense"):
        raise ValidationError("Type must be income or expense")
    return x


def amount(x):
    if isinstance(x, bool):
        raise ValidationError("Amount must be a number")
    try:
        d = Decimal(str(x))
    except InvalidOperation:
        raise ValidationError("Amount must be a number")
    if not d.is_finite() or d <= 0 or d > Decimal("1000000000"):
        raise ValidationError("Amount must be greater than 0 and at most 1,000,000,000")
    return str(d.quantize(Decimal("0.01")))


def iso_date(x):
    try:
        return date.fromisoformat(x).isoformat()
    except (TypeError, ValueError):
        raise ValidationError("Date must be YYYY-MM-DD")


def text(x, max_len, label="Text"):
    if x is None:
        return None
    if not isinstance(x, str) or len(x.strip()) > max_len:
        raise ValidationError(f"{label} must be text of at most {max_len} characters")
    return x.strip() or None


def month(x):
    if not isinstance(x, str) or not MONTH_RE.match(x):
        raise ValidationError("Month must be YYYY-MM")
    return x


def month_range(x):
    """'2026-11' -> ('2026-11-01', '2026-12-01')"""
    y, m = map(int, month(x).split("-"))
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01", f"{ny:04d}-{nm:02d}-01"


def limit(x, default=100, max_=500):
    if x in (None, ""):
        return default
    try:
        return max(1, min(int(x), max_))
    except ValueError:
        raise ValidationError("Invalid limit")


def body(data):
    if not isinstance(data, dict):
        raise ValidationError("Expected a JSON object")
    return data


def transaction(data):
    d = body(data)
    t = tx_type(d.get("type"))
    cat = d.get("category_id")
    cat = uuid(cat, "category") if cat else None
    return {
        "type": t,
        "amount": amount(d.get("amount")),
        "tx_date": iso_date(d.get("tx_date")),
        "description": text(d.get("description"), 200, "Description"),
        # the other column is always sent as null so switching type clears it
        "income_category_id": cat if t == "income" else None,
        "expense_category_id": cat if t == "expense" else None,
    }


def budget(data):
    d = body(data)
    start, _ = month_range(month(d.get("month")))
    return {
        "expense_category_id": uuid(d.get("category_id"), "category"),
        "month": start,
        "amount_limit": amount(d.get("amount_limit")),
    }
