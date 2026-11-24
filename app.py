"""The Flask app: wires logging, the database bootstrap, blueprints, CORS and the scheduler."""

import logging
from datetime import timedelta

from flask import Flask, render_template
from flask_cors import CORS
from flask_smorest import Api

from api import register_blueprints
from api.domains import domains_bp
from auth.legacy import register_legacy_lock
from core import crypto
from core.config import APP_ENV, CHATBOT0_SECRET_KEY, DEBUG, PORT, SCHEDULER_ENABLED, WERKZEUG_RUN_MAIN
from core.logging import configure_logging
from core.schema import init_db
from summary.scheduler import start_scheduler, stop_scheduler
from web import register_frontend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> Flask:
    configure_logging()
    flask_app = Flask(__name__)

    # -- Database ------------------------------------------------------------
    # init_db never raises: if PostgreSQL is down the app still starts, /health
    # reports it, and a background thread creates the schema once the database
    # comes back. Previously an unreachable database at import time killed the
    # process, so even the health check was unreachable.
    init_db()

    # -- flask-smorest / OpenAPI configuration ---------------------------------
    # Auto-generated spec is served at /api/openapi.json.
    # Interactive Swagger UI is served at /api/docs.
    # The legacy static swagger.yaml UI is served at /api/legacy-docs.
    flask_app.config.update(
        API_TITLE="Chat API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/api",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    )

    # -- Existing blueprints (health, chat, prompts, legacy swagger UI) --------
    register_blueprints(flask_app)

    # -- Sessions ---------------------------------------------------------------
    # The login cookie is signed with a key derived from CHATBOT0_SECRET_KEY.
    # Without it nobody can sign in (the auth endpoints answer 503).
    if CHATBOT0_SECRET_KEY:
        flask_app.secret_key = crypto.session_signing_key()
    flask_app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=APP_ENV != "local",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )

    # The cutover lock for the old public endpoints (off unless LOCK_LEGACY_API=true).
    register_legacy_lock(flask_app)

    # -- Smorest-managed blueprints (auto-documented) --------------------------
    smorest_api = Api(flask_app)
    smorest_api.register_blueprint(domains_bp)

    CORS(flask_app)

    # -- Frontend (the Next.js export) ------------------------------------------
    # Last: it answers only what no route above matched, so the APIs always win.
    register_frontend(flask_app, api_error=smorest_api.handle_http_exception)

    # -- Background jobs -------------------------------------------------------
    # Locally the periodic summary runs in a thread of this process. On Cloud Run
    # SCHEDULER_ENABLED is false and Cloud Scheduler calls POST /jobs/periodic-summary
    # instead (see api/jobs.py).
    if SCHEDULER_ENABLED:
        start_scheduler()
    else:
        logger.info("[SCHEDULER] disabled (SCHEDULER_ENABLED=false); jobs run via /jobs/*")

    return flask_app


app = create_app()


@app.route("/chat-ui")
def chat_ui():
    return render_template("chat.html")


if __name__ == "__main__":
    # In debug, Werkzeug's reloader runs this file in a parent and a child process.
    # Stop the parent's scheduler so Slack doesn't get every summary twice.
    if DEBUG and not WERKZEUG_RUN_MAIN:
        stop_scheduler()
    app.run(debug=DEBUG, port=PORT)
