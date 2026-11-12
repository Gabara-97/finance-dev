# Local setup

## 1. Supabase (free tier is fine)
1. Create a project at supabase.com.
2. SQL Editor: run `database/migrations/001_schema.sql`, then `002_rls.sql`.
3. Authentication → Providers → Email: keep **Confirm email** ON. Authentication → Multi-Factor: enable **TOTP**.
4. Authentication → URL Configuration: add `http://localhost:5500` (and later your Vercel URL) as Site URL / redirect URLs.
5. Project Settings → API: copy the **Project URL** and the **anon public** key. (Never use or share the `service_role` key — this project doesn't need it.)

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env        # then edit .env with your URL + anon key
python run.py                  # http://localhost:5000/api/v1/health -> {"status":"ok"}
pytest -q                      # unit tests
```

## 3. Frontend
Edit `frontend/js/config.js` (Supabase URL, anon key, API URL), then:
```bash
cd frontend
python -m http.server 5500     # open http://localhost:5500
```
Register, click the verification link in your email, sign in.
