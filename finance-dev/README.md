# Finance DEv
Personal and small-business finance manager. Default currency: South African Rand (ZAR).

**Stack:** HTML/CSS/JS frontend (Vercel) · Flask REST API (Render) · Supabase (PostgreSQL, Auth, RLS)

## What works
Registration with email verification, login, password reset, optional TOTP two-factor auth, income/expense CRUD with delete confirmation, categories, search and filters, monthly budgets with progress, dashboard with chart, monthly reports, CSV export, audit log, light/dark mode, mobile layout.

## How it is secured
- Passwords and sessions are handled by Supabase Auth; the app stores no passwords.
- The API forwards the user's own token to Supabase, so **Row Level Security** decides what each user can see. No service-role key is used anywhere.
- Input validation, parameterised PostgREST calls, CORS allow-list, rate limiting, security headers, XSS-safe rendering (`textContent` only), CSV formula-injection protection.
- Audit logs are written by database triggers and cannot be forged by clients.

## Structure
`frontend/` static app · `backend/` Flask API + tests · `database/migrations/` SQL (run 001 then 002) · `docs/` setup, deployment, security, testing

## Get started
See [docs/SETUP.md](docs/SETUP.md), then [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
