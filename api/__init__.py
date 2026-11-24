"""HTTP blueprints. Each module parses a request, calls the code behind it and shapes the response; no SQL here."""

from .admin import admin_api_bp
from .auth import auth_bp
from .chat import chat_bp
from .health import health_bp
from .jobs import jobs_bp
from .leads import leads_bp
from .prompts import prompt_bp
from .signup import signup_bp
from .sites import sites_bp
from .slack_settings import slack_bp
from .swagger import swaggerui_blueprint
from .whatsapp import whatsapp_bp
from .whatsapp_connections import connections_bp


def register_blueprints(app):
    app.register_blueprint(health_bp)
    app.register_blueprint(swaggerui_blueprint)
    app.register_blueprint(chat_bp)
    app.register_blueprint(prompt_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(signup_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(slack_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(connections_bp)
