# Deployment

## Backend → Render
1. Push this repo to GitHub.
2. Render → New → Blueprint (uses `backend/render.yaml`), or New Web Service with root `backend`, build `pip install -r requirements.txt`, start `gunicorn run:app`, health check `/api/v1/health`.
3. Set environment variables in the Render dashboard: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `ALLOWED_ORIGINS` (your Vercel URL).
4. Check the deploy logs and open `https://<service>.onrender.com/api/v1/health`.

## Frontend → Vercel
1. Vercel → New Project → import the repo, **Root Directory = `frontend`**, framework preset "Other".
2. Before deploying, set `API_BASE_URL` in `frontend/js/config.js` to `https://<service>.onrender.com/api/v1` and commit.
3. Add the Vercel URL to Supabase redirect URLs and to Render's `ALLOWED_ORIGINS`.

## Notes
Render's free tier sleeps when idle (first request can take ~30 s). Rate-limit counters are per instance (in memory); use Redis if you scale to multiple instances.
