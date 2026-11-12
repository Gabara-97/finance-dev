import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # The API never needs the service-role key: it forwards the user's own
    # token to Supabase, so Row Level Security applies to every query.
    SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or ""
    ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
    MAX_CONTENT_LENGTH = 16 * 1024
