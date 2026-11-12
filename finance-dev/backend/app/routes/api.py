import re
from datetime import date

from flask import Blueprint, Response, g, jsonify, request

from .. import limiter
from .. import validators as v
from ..auth import require_auth
from ..db import rest
from ..services import finance

api_bp = Blueprint("api", __name__)
TX_SELECT = "*,income_categories(name),expense_categories(name)"
WRITE_LIMIT = "30/minute"


def _json():
    return v.body(request.get_json(silent=True))


def _month_tx(month, select):
    start, end = v.month_range(month)
    return rest("GET", "transactions", params={
        "select": select, "and": f"(tx_date.gte.{start},tx_date.lt.{end})", "order": "tx_date.asc", "limit": "5000",
    })


# ---------- categories ----------
@api_bp.get("/categories")
@require_auth
def categories():
    p = {"select": "id,name", "order": "name"}
    return jsonify(income=rest("GET", "income_categories", params=p), expense=rest("GET", "expense_categories", params=p))


# ---------- transactions ----------
@api_bp.get("/transactions")
@require_auth
def list_transactions():
    p = {"select": TX_SELECT, "order": "tx_date.desc,created_at.desc",
         "limit": str(v.limit(request.args.get("limit")))}
    if request.args.get("type"):
        p["type"] = "eq." + v.tx_type(request.args["type"])
    q = re.sub(r"[^\w\s.\-]", "", request.args.get("q", ""))[:50].strip()
    if q:
        p["description"] = f"ilike.*{q}*"
    if request.args.get("month"):
        start, end = v.month_range(request.args["month"])
        p["and"] = f"(tx_date.gte.{start},tx_date.lt.{end})"
    return jsonify(rest("GET", "transactions", params=p))


@api_bp.post("/transactions")
@require_auth
@limiter.limit(WRITE_LIMIT)
def create_transaction():
    row = v.transaction(_json())
    out = rest("POST", "transactions", json=row, prefer="return=representation", params={"select": TX_SELECT})
    return jsonify(out[0]), 201


@api_bp.put("/transactions/<tx_id>")
@require_auth
@limiter.limit(WRITE_LIMIT)
def update_transaction(tx_id):
    row = v.transaction(_json())
    out = rest("PATCH", "transactions", json=row, prefer="return=representation",
               params={"id": "eq." + v.uuid(tx_id), "select": TX_SELECT})
    if not out:
        return jsonify(error="Transaction not found"), 404
    return jsonify(out[0])


@api_bp.delete("/transactions/<tx_id>")
@require_auth
@limiter.limit(WRITE_LIMIT)
def delete_transaction(tx_id):
    rest("DELETE", "transactions", params={"id": "eq." + v.uuid(tx_id)})
    return "", 204


# ---------- summary ----------
@api_bp.get("/summary")
@require_auth
def summary():
    rows = rest("GET", "transactions", params={"select": "tx_date,type,amount", "limit": "10000"})
    return jsonify(finance.summarize(rows))


# ---------- budgets ----------
@api_bp.get("/budgets")
@require_auth
def list_budgets():
    month = v.month(request.args.get("month") or date.today().strftime("%Y-%m"))
    start, _ = v.month_range(month)
    budgets = rest("GET", "budgets", params={
        "select": "id,amount_limit,expense_category_id,expense_categories(name)", "month": "eq." + start})
    spent = finance.spent_by_category(
        [r for r in _month_tx(month, "type,amount,expense_category_id") if r["type"] == "expense"])
    return jsonify([{
        "id": b["id"], "category": b["expense_categories"]["name"],
        "limit": float(b["amount_limit"]), "spent": float(spent.get(b["expense_category_id"], 0)),
    } for b in budgets])


@api_bp.post("/budgets")
@require_auth
@limiter.limit(WRITE_LIMIT)
def save_budget():
    row = v.budget(_json())
    out = rest("POST", "budgets", json=row, prefer="resolution=merge-duplicates,return=representation",
               params={"on_conflict": "user_id,expense_category_id,month"})
    return jsonify(out[0]), 201


@api_bp.delete("/budgets/<budget_id>")
@require_auth
@limiter.limit(WRITE_LIMIT)
def delete_budget(budget_id):
    rest("DELETE", "budgets", params={"id": "eq." + v.uuid(budget_id)})
    return "", 204


# ---------- reports ----------
@api_bp.get("/reports/monthly")
@require_auth
def monthly_report():
    month = v.month(request.args.get("month") or date.today().strftime("%Y-%m"))
    rows = _month_tx(month, TX_SELECT)
    s = finance.summarize(rows)
    start, _ = v.month_range(month)
    rest("POST", "financial_reports", prefer="resolution=merge-duplicates",
         params={"on_conflict": "user_id,month"},
         json={"month": start, "total_income": s["income"], "total_expenses": s["expenses"], "balance": s["balance"]})
    return jsonify(month=month, income=s["income"], expenses=s["expenses"], balance=s["balance"],
                   count=len(rows), by_category=finance.breakdown(rows))


@api_bp.get("/reports/export")
@require_auth
@limiter.limit("10/minute")
def export_report():
    month = v.month(request.args.get("month") or date.today().strftime("%Y-%m"))
    return Response(finance.to_csv(_month_tx(month, TX_SELECT)), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="finance-dev-{month}.csv"'})


# ---------- profile ----------
@api_bp.get("/profile")
@require_auth
def get_profile():
    rows = rest("GET", "profiles", params={"select": "full_name,currency,role", "id": "eq." + g.user_id})
    return jsonify(rows[0] if rows else {})


@api_bp.put("/profile")
@require_auth
@limiter.limit(WRITE_LIMIT)
def update_profile():
    name = v.text(_json().get("full_name"), 100, "Name")
    out = rest("PATCH", "profiles", json={"full_name": name}, prefer="return=representation",
               params={"select": "full_name,currency,role", "id": "eq." + g.user_id})
    return jsonify(out[0] if out else {})
