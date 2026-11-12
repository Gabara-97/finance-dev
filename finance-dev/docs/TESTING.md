# Testing
**Automated** (`cd backend && pytest -q`): auth rejection (missing/invalid token, unverified email), input validation, client-supplied `user_id` ignored, income/expense/balance maths, month ranges, CSV injection guard, health endpoint.

**Manual checklist** (needs a live Supabase project):
- Register → verify email → login → logout → password reset
- Enrol 2FA, log out, log in with a code
- Add, edit, delete (with confirm) an income and an expense; check totals
- Create a budget and confirm the progress bar
- Export a CSV
- **Isolation:** create two users; confirm user B cannot see user A's rows (UI, and `GET /transactions/<A's id>` via API)
- Resize to phone width; toggle dark mode
