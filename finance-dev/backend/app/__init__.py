import logging

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .db import DBError
from .validators import ValidationError

limiter = Limiter(key_func=get_remote_address, default_limits=[Config.RATE_LIMIT_DEFAULT])
log = logging.getLogger("finance-dev")


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)  # real client IP behind Render's proxy

    CORS(
        app,
        origins=app.config["ALLOWED_ORIGINS"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    limiter.init_app(app)

    from .routes.api import api_bp
    from .routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return resp

    @app.errorhandler(ValidationError)
    def bad_input(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(DBError)
    def db_error(e):
        return jsonify(error=e.public_message), e.status

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found"), 404

    @app.errorhandler(413)
    def too_big(_):
        return jsonify(error="Request too large"), 413

    @app.errorhandler(429)
    def too_many(_):
        return jsonify(error="Too many requests, slow down"), 429

    @app.errorhandler(Exception)
    def unexpected(e):
        log.exception("Unhandled error")
        return jsonify(error="Server error"), 500

    return app
