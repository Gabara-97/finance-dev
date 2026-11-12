import unittest
from unittest.mock import patch

from app import create_app
from app.services import finance
from app import validators as v

UID = "11111111-1111-1111-1111-111111111111"
CAT = "22222222-2222-2222-2222-222222222222"
AUTH = {"Authorization": "Bearer " + "x" * 30}
USER = {"id": UID, "email_confirmed_at": "2026-01-01T00:00:00Z"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SUPABASE_URL": "https://x.supabase.co", "SUPABASE_ANON_KEY": "anon"})
        self.c = self.app.test_client()

    def test_health(self):
        r = self.c.get("/api/v1/health")
        self.assertEqual((r.status_code, r.get_json()), (200, {"status": "ok"}))
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_requires_token(self):
        self.assertEqual(self.c.get("/api/v1/summary").status_code, 401)
        self.assertEqual(self.c.get("/api/v1/transactions", headers={"Authorization": "Bearer short"}).status_code, 401)

    @patch("app.auth.verify_token", return_value=None)
    def test_rejects_bad_token(self, _):
        self.assertEqual(self.c.get("/api/v1/summary", headers=AUTH).status_code, 401)

    @patch("app.auth.verify_token", return_value={"id": UID})
    def test_rejects_unverified_email(self, _):
        self.assertEqual(self.c.get("/api/v1/summary", headers=AUTH).status_code, 403)

    @patch("app.auth.verify_token", return_value=USER)
    def test_validation_rejects_bad_input(self, _):
        good = {"type": "income", "amount": 100, "tx_date": "2026-11-01"}
        bad = [
            {**good, "amount": -5}, {**good, "amount": "abc"}, {**good, "amount": "NaN"},
            {**good, "amount": True}, {**good, "type": "gift"}, {**good, "tx_date": "11/01/2026"},
            {**good, "category_id": "not-a-uuid"}, {**good, "description": "x" * 201},
        ]
        for payload in bad:
            r = self.c.post("/api/v1/transactions", json=payload, headers=AUTH)
            self.assertEqual(r.status_code, 400, payload)
        self.assertEqual(self.c.post("/api/v1/transactions", data="nope", headers=AUTH).status_code, 400)

    @patch("app.routes.api.rest", return_value=[{"id": "t1"}])
    @patch("app.auth.verify_token", return_value=USER)
    def test_create_ignores_client_user_id(self, _, rest):
        r = self.c.post("/api/v1/transactions", headers=AUTH, json={
            "type": "expense", "amount": "200", "tx_date": "2026-11-02", "category_id": CAT, "user_id": "evil"})
        self.assertEqual(r.status_code, 201)
        sent = rest.call_args.kwargs["json"]
        self.assertNotIn("user_id", sent)
        self.assertEqual(sent["expense_category_id"], CAT)
        self.assertIsNone(sent["income_category_id"])
        self.assertEqual(sent["amount"], "200.00")

    @patch("app.routes.api.rest", return_value=[])
    @patch("app.auth.verify_token", return_value=USER)
    def test_update_missing_is_404(self, _, __):
        r = self.c.put(f"/api/v1/transactions/{CAT}", headers=AUTH,
                       json={"type": "income", "amount": 1, "tx_date": "2026-11-01"})
        self.assertEqual(r.status_code, 404)

    @patch("app.auth.verify_token", return_value=USER)
    def test_bad_id_in_path(self, _):
        self.assertEqual(self.c.delete("/api/v1/transactions/1;drop", headers=AUTH).status_code, 400)


class FinanceTests(unittest.TestCase):
    ROWS = [
        {"tx_date": "2026-10-05", "type": "income", "amount": "20000.00"},
        {"tx_date": "2026-10-20", "type": "expense", "amount": 5000},
        {"tx_date": "2026-11-01", "type": "income", "amount": 1000},
        {"tx_date": "2026-11-02", "type": "expense", "amount": 200},
    ]

    def test_readme_example(self):  # matches the README: R15,000 + R1,000 - R200 = R15,800
        s = finance.summarize(self.ROWS)
        self.assertEqual((s["income"], s["expenses"], s["balance"]), (21000.0, 5200.0, 15800.0))
        self.assertEqual([m["month"] for m in s["monthly"]], ["2026-10", "2026-11"])

    def test_decimal_precision(self):
        s = finance.summarize([{"tx_date": "2026-01-01", "type": "income", "amount": "0.10"},
                               {"tx_date": "2026-01-01", "type": "income", "amount": "0.20"}])
        self.assertEqual(s["income"], 0.3)

    def test_csv_injection(self):
        self.assertEqual(finance.safe_cell("=SUM(A1)"), "'=SUM(A1)")
        self.assertEqual(finance.safe_cell("Groceries"), "Groceries")

    def test_month_range(self):
        self.assertEqual(v.month_range("2026-12"), ("2026-12-01", "2027-01-01"))
        self.assertEqual(v.month_range("2026-02"), ("2026-02-01", "2026-03-01"))
        with self.assertRaises(v.ValidationError):
            v.month_range("2026-13")

    def test_breakdown(self):
        rows = [{"type": "expense", "amount": 50, "expense_categories": {"name": "Food"}},
                {"type": "expense", "amount": 30, "expense_categories": {"name": "Food"}},
                {"type": "expense", "amount": 100, "expense_categories": None}]
        self.assertEqual(finance.breakdown(rows)[0], {"category": "Uncategorised", "total": 100.0})
        self.assertEqual(finance.breakdown(rows)[1], {"category": "Food", "total": 80.0})


if __name__ == "__main__":
    unittest.main()
