# Architecture
Browser (Vercel) → Flask API (Render) → Supabase (Postgres + Auth)

- The browser signs users in with Supabase Auth and sends the access token to the API.
- The API checks the token with Supabase, validates input, then queries Supabase **as that user**, so RLS applies.
- Calculations (summary, budgets, reports, CSV) live in `backend/app/services/finance.py`.
- Tables: profiles, income_categories, expense_categories, transactions, budgets, financial_reports, audit_logs.
