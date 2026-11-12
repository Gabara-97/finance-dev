"""Thin PostgREST client. Every call carries the *user's* JWT, so Postgres
Row Level Security decides what rows are visible or writable."""
import logging

import requests
from flask import current_app, g

log = logging.getLogger("finance-dev")


class DBError(Exception):
    def __init__(self, status, public_message):
        super().__init__(public_message)
        self.status = status
        self.public_message = public_message


def rest(method, path, *, params=None, json=None, prefer=None):
    cfg = current_app.config
    headers = {"apikey": cfg["SUPABASE_ANON_KEY"], "Authorization": f"Bearer {g.token}"}
    if prefer:
        headers["Prefer"] = prefer
    try:
        r = requests.request(
            method, f"{cfg['SUPABASE_URL']}/rest/v1/{path}",
            headers=headers, params=params, json=json, timeout=10,
        )
    except requests.RequestException:
        log.exception("Supabase unreachable")
        raise DBError(502, "Database unavailable")
    if r.status_code >= 400:
        log.warning("Supabase %s %s -> %s %s", method, path, r.status_code, r.text[:300])
        if r.status_code in (401, 403):
            raise DBError(403, "Not allowed")
        if r.status_code == 409:
            raise DBError(409, "That record already exists or conflicts with another")
        raise DBError(400, "Request could not be completed")
    return r.json() if r.content else None
