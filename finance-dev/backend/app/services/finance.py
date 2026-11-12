"""Pure calculation helpers (no I/O) so they are easy to test."""
import csv
import io
from collections import defaultdict
from decimal import Decimal


def D(x):
    return Decimal(str(x))


def summarize(rows):
    income = sum((D(r["amount"]) for r in rows if r["type"] == "income"), Decimal(0))
    expenses = sum((D(r["amount"]) for r in rows if r["type"] == "expense"), Decimal(0))
    monthly = defaultdict(lambda: {"income": Decimal(0), "expenses": Decimal(0)})
    for r in rows:
        key = "income" if r["type"] == "income" else "expenses"
        monthly[r["tx_date"][:7]][key] += D(r["amount"])
    return {
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(income - expenses),
        "monthly": [
            {"month": m, "income": float(v["income"]), "expenses": float(v["expenses"])}
            for m, v in sorted(monthly.items())
        ][-6:],
    }


def category_name(row):
    return (row.get("income_categories") or row.get("expense_categories") or {}).get("name") or "Uncategorised"


def breakdown(rows):
    out = defaultdict(lambda: Decimal(0))
    for r in rows:
        if r["type"] == "expense":
            out[category_name(r)] += D(r["amount"])
    return sorted(({"category": k, "total": float(v)} for k, v in out.items()), key=lambda x: -x["total"])


def spent_by_category(rows):
    out = defaultdict(lambda: Decimal(0))
    for r in rows:
        out[r["expense_category_id"]] += D(r["amount"])
    return out


def safe_cell(value):
    """Stop spreadsheet formula injection when a CSV is opened in Excel/Sheets."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Type", "Category", "Description", "Amount (ZAR)"])
    for r in rows:
        w.writerow([r["tx_date"], r["type"], safe_cell(category_name(r)), safe_cell(r.get("description")), r["amount"]])
    return buf.getvalue()
