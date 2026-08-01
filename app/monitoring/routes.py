"""
monitoring feature (Hao Jun) — you OWN this folder.

/health is used by:
  - Ashish's Docker healthcheck (container orchestration needs to know
    if the app is actually working, not just that a process is running)
  - Server/uptime monitoring (pings this instead of "/", since "/" only
    proves a page rendered — it doesn't prove the database is reachable)

Deliberately has NO @login_required and NO template rendering — it must
stay fast and dependency-free so it can be polled frequently without
adding load, and so it still responds even if something else in the
app (e.g. templates, auth) is broken.
"""
from flask import Blueprint, jsonify
from sqlalchemy import text
from ..extensions import db

monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.route("/health")
def health():
    try:
        # Cheapest possible query — just proves the DB connection works,
        # not that any particular table/row exists.
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception:
        return jsonify({"status": "error", "database": "disconnected"}), 503