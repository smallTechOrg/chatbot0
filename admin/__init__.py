"""
chatbot0 admin pages, under /chatbot0/admin/. The first piece of the tenant UI
that moves into this app (from zero-frontend-web).

    /chatbot0/admin/login                       password sign-in
    /chatbot0/admin/whatsapp                    WhatsApp connections; add one
    /chatbot0/admin/whatsapp/<id>               webhook URL + verify token, status,
                                                replace credentials, check, test message

Sign-in is one shared password (CHATBOT0_ADMIN_PASSWORD) until tenant accounts
exist. The session cookie is signed with a key derived from
CHATBOT0_SECRET_KEY; every POST carries a CSRF token. Credentials entered here
are encrypted before they are stored and are never shown again.
"""

from __future__ import annotations

import functools
import hmac
import re
import secrets
import unicodedata

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

import config
from db_pool import with_connection
from whatsapp import repository
from whatsapp.client import OUTSIDE_SERVICE_WINDOW, check_number, send_text

admin_bp = Blueprint("admin", __name__, url_prefix="/chatbot0/admin")

_DIGITS = re.compile(r"^\d{5,20}$")
_RECIPIENT = re.compile(r"^\+?\d{7,15}$")

# Graph API codes with a known fix, shown next to a failed test message.
_SEND_HINTS = {
    OUTSIDE_SERVICE_WINDOW: "The recipient has not messaged this number in the last 24 hours. "
    "Send any message to the business number from that phone first, then retry.",
    131030: "On a Meta test number, only recipients added under API Setup > 'To' can receive messages.",
    190: "The access token is invalid or expired. Replace it below.",
}


def _clean(value: str) -> str:
    """
    A pasted value without the invisible characters web pages copy along:
    any Unicode space (non-breaking, thin, ...) and format characters such as
    left-to-right marks and zero-width spaces, which the Meta dashboard adds.
    """
    return "".join(ch for ch in value if not (ch.isspace() or unicodedata.category(ch) in ("Cf", "Zs")))


def _clean_id(value: str) -> str:
    """A pasted numeric ID: invisible characters dropped, a leading "ID:" label too."""
    value = _clean(value)
    value = re.sub(r"^(phone ?number ?)?id:?", "", value, flags=re.I)
    # Unicode digits (e.g. full-width) to ASCII.
    return "".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in value)


def admin_enabled() -> bool:
    return bool(config.CHATBOT0_SECRET_KEY and config.CHATBOT0_ADMIN_PASSWORD)


@admin_bp.before_request
def _guard():
    if not admin_enabled():
        return render_template("admin/disabled.html"), 503
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
            abort(400, "The form expired. Go back, reload the page and try again.")


@admin_bp.app_context_processor
def _csrf():
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    return {"csrf_token": csrf_token}


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), config.CHATBOT0_ADMIN_PASSWORD):
            session.clear()
            session["admin"] = True
            session.permanent = True
            nxt = request.args.get("next", "")
            # Only paths inside the admin area: no open redirect.
            return redirect(nxt if nxt.startswith("/chatbot0/admin/") else url_for("admin.whatsapp_list"))
        flash("Wrong password.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def home():
    return redirect(url_for("admin.whatsapp_list"))


def _webhook_url(connection_id: str) -> str:
    base = config.PUBLIC_BASE_URL
    if not base:
        proto = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()
        base = f"{proto}://{request.host}"
    return f"{base}/whatsapp/webhook/{connection_id}"


@with_connection
def _domain_keys(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT key FROM domains ORDER BY key;")
        return [r[0] for r in cur.fetchall()]


def _check(connection_id: str, phone_number_id: str, token: str) -> bool:
    result = check_number(phone_number_id, token)
    if result.ok:
        data = result.data or {}
        repository.mark_checked(connection_id, data.get("display_phone_number"), data.get("verified_name"))
        flash(
            f"Token works for {data.get('display_phone_number') or phone_number_id}"
            f"{' (' + data['verified_name'] + ')' if data.get('verified_name') else ''}.",
            "ok",
        )
        return True
    repository.mark_error(connection_id, result.error or "check failed", needs_attention=True)
    flash(f"Graph API check failed: {result.error}", "error")
    return False


@admin_bp.route("/whatsapp", methods=["GET", "POST"])
@login_required
def whatsapp_list():
    if request.method == "POST":
        raw_id = request.form.get("phone_number_id") or ""
        f = {k: _clean(request.form.get(k) or "") for k in ("domain_key", "access_token", "app_secret")}
        f["phone_number_id"] = _clean_id(raw_id)
        if not _DIGITS.match(f["phone_number_id"]):
            flash(
                f"Phone number ID must be the long numeric ID from WhatsApp > API Setup (not the phone "
                f"number). Received {len(raw_id)} characters: {raw_id.encode('unicode_escape').decode()[:80]}",
                "error",
            )
        elif not all(f.values()):
            flash("All four fields are required.", "error")
        else:
            try:
                created = repository.create_connection(**f)
            except repository.DomainNotFound:
                flash(f"No domain with key {f['domain_key']}.", "error")
            except repository.NumberAlreadyConnected:
                flash("That number is already connected. Open it below to replace its credentials.", "error")
            else:
                _check(created["id"], f["phone_number_id"], f["access_token"])
                return redirect(url_for("admin.whatsapp_detail", connection_id=created["id"]))
    return render_template(
        "admin/whatsapp_list.html",
        connections=repository.list_connections(),
        domain_keys=_domain_keys(),
        form=request.form,
    )


@admin_bp.route("/whatsapp/<connection_id>")
@login_required
def whatsapp_detail(connection_id):
    connection = repository.get_connection(connection_id) or abort(404)
    return render_template(
        "admin/whatsapp_detail.html", c=connection, webhook_url=_webhook_url(connection_id), domain_keys=_domain_keys()
    )


@admin_bp.route("/whatsapp/<connection_id>/credentials", methods=["POST"])
@login_required
def whatsapp_credentials(connection_id):
    repository.get_connection(connection_id) or abort(404)
    token = _clean(request.form.get("access_token") or "") or None
    app_secret = _clean(request.form.get("app_secret") or "") or None
    domain_key = _clean(request.form.get("domain_key") or "") or None
    if not (token or app_secret or domain_key):
        flash("Nothing to change.", "error")
    else:
        try:
            repository.update_credentials(connection_id, token, app_secret, domain_key)
            flash("Saved.", "ok")
        except repository.DomainNotFound:
            flash(f"No domain with key {domain_key}.", "error")
        if token:
            full = repository.get_connection_with_credentials(connection_id)
            _check(connection_id, full["phone_number_id"], full["access_token"])
    return redirect(url_for("admin.whatsapp_detail", connection_id=connection_id))


@admin_bp.route("/whatsapp/<connection_id>/check", methods=["POST"])
@login_required
def whatsapp_check(connection_id):
    full = repository.get_connection_with_credentials(connection_id) or abort(404)
    _check(connection_id, full["phone_number_id"], full["access_token"])
    return redirect(url_for("admin.whatsapp_detail", connection_id=connection_id))


@admin_bp.route("/whatsapp/<connection_id>/test", methods=["POST"])
@login_required
def whatsapp_test(connection_id):
    full = repository.get_connection_with_credentials(connection_id) or abort(404)
    to = (request.form.get("to") or "").replace(" ", "").replace("-", "")
    body = (request.form.get("body") or "").strip() or "Test message from chatbot0. Reply to chat with the bot."
    if not _RECIPIENT.match(to):
        flash("Enter the recipient with country code, digits only, e.g. 919876543210.", "error")
    else:
        result = send_text(full["phone_number_id"], full["access_token"], to.lstrip("+"), body)
        if result.ok:
            flash(f"Sent to +{to.lstrip('+')}.", "ok")
        else:
            hint = _SEND_HINTS.get(result.code, "")
            flash(f"Not sent: {result.error}. {hint}".strip(), "error")
            if result.token_problem:
                repository.mark_error(connection_id, result.error or "send failed", needs_attention=True)
    return redirect(url_for("admin.whatsapp_detail", connection_id=connection_id))
