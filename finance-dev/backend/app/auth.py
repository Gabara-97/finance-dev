import logging
from functools import wraps

import requests
from flask import current_app, g, jsonify, request

log = logging.getLogger("finance-dev")


def verify_token(token):
    """Ask Supabase Auth who this token belongs to. Returns the user dict or None."""
    cfg = current_app.config
    try:
        r = requests.get(
            f"{cfg['SUPABASE_URL']}/auth/v1/user",
            headers={"apikey": cfg["SUPABASE_ANON_KEY"], "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException:
        log.exception("Supabase Auth unreachable")
        return None
    return r.json() if r.status_code == 200 else None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or len(header) < 20:
            return jsonify(error="Missing token"), 401
        token = header[7:].strip()
        user = verify_token(token)
        if not user or not user.get("id"):
            return jsonify(error="Invalid or expired session"), 401
        if not (user.get("email_confirmed_at") or user.get("confirmed_at")):
            return jsonify(error="Verify your email address first"), 403
        g.token, g.user_id = token, user["id"]
        return fn(*args, **kwargs)

    return wrapper
