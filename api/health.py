"""GET /health: the app and the database, for Cloud Run and the deploy smoke test."""

import contextlib

from flask import Blueprint, jsonify

from core import config
from core.db_pool import get_connection, get_pool

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """
    Report the state of the app and the database. The probe borrows from the
    same pool as every other endpoint, so a green check means the API can
    reach the database. One attempt and a short timeout keep it fast.

    Schema state is not reported here. Creating and migrating tables is the
    deployment's job, not something a liveness probe should discover.
    """
    status = {
        "message": "Hello World",
        "database": "disconnected",
    }

    try:
        with get_connection(attempts=1, timeout=config.DB_HEALTH_TIMEOUT) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        status["database"] = "connected"
        code = 200
    except Exception as e:
        status["database_error"] = str(e)
        code = 503

    with contextlib.suppress(Exception):  # the pool could not even be built
        status["pool"] = get_pool().get_stats()

    return jsonify(status), code
