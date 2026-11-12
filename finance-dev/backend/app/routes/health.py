from flask import Blueprint, jsonify

from .. import limiter

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
@limiter.exempt
def health():
    return jsonify(status="ok")
