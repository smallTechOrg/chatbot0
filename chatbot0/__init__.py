"""chatbot0 public pages (Linear SMA-8), rendered server-side by Flask.

chatbot0 is the AI chat agent this backend powers. Its marketing pages live
here, under the /chatbot0/ prefix, because "/" already serves the legacy
Swagger UI (api/swagger.py) and must keep doing so.

    /chatbot0/             landing page
    /chatbot0/pricing      pricing
    /chatbot0/sales        AI sales agent use case
    /chatbot0/support      AI support agent use case
    /chatbot0/industries   industries (?industry=<name> highlights one; old zer0 links use it)
    /chatbot0/about        about chatbot0 and smallTech
    /chatbot0/signup       sign-up form (static/chatbot0/js/signup.js calls the API on this service)
    /chatbot0/robots.txt   for when chatbot0.smalltech.in maps onto this prefix
    /chatbot0/sitemap.xml
    /chatbot0/static/...   CSS, favicons, logo (files in static/chatbot0/)

Links and asset paths in the templates are relative ("pricing", "./",
"static/..."), so the same HTML works at /chatbot0/ on this service and at the
root of chatbot0.smalltech.in. On that host (Cloud Run domain mapping, see
register_host_routing) GET/HEAD on "/", the page paths above, "/robots.txt",
"/sitemap.xml" and "/static/..." serve these pages; every other path and method,
and every other host, is untouched, so the API and the Swagger UI behave exactly
as before. That is how the sign-up page reaches the API: signup.js calls
root-absolute paths (POST /domains/, POST /prompt),
which are API routes on this service whether the page was served at /chatbot0/
or at the root of chatbot0.smalltech.in. Canonical, Open Graph and sitemap URLs always point at
https://chatbot0.smalltech.in.

The pages read nothing from the database and call no LLM; the only input is
?industry= on /industries, matched against a fixed list.
"""

from __future__ import annotations

import os

from flask import Blueprint, Flask, Response, render_template, request, send_from_directory

from . import content

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "chatbot0")

chatbot0_bp = Blueprint(
    "chatbot0",
    __name__,
    url_prefix="/chatbot0",
    static_folder=_STATIC_DIR,
    static_url_path="/static",
)

LANDING_TITLE = "chatbot0, the AI chat agent for business websites"
LANDING_DESCRIPTION = (
    "chatbot0 sits on your website, answers visitors, captures leads and hands you the warm conversation. "
    "Free plan with 200 conversations a month. No code. By smallTech."
)
PRICING_TITLE = "Pricing, chatbot0"
PRICING_DESCRIPTION = (
    f"Simple pricing for chatbot0. Start free with {content.FREE_CONVERSATIONS} conversations a month, "
    f"upgrade from ${content.LOWEST_PAID_MONTHLY} a month. No hidden fees."
)

SALES_TITLE = "AI sales agent for your website, chatbot0"
SALES_DESCRIPTION = (
    "chatbot0 talks to every visitor, answers questions about what you sell, asks the qualifying questions "
    "and sends warm leads to your dashboard. Free to start."
)
SUPPORT_TITLE = "AI customer support agent for your website, chatbot0"
SUPPORT_DESCRIPTION = (
    "chatbot0 answers customers' questions instantly, day and night, from what you tell it about your business, "
    "and passes the rest to your team. Free to start."
)
INDUSTRIES_TITLE = "chatbot0 for your industry"
INDUSTRIES_DESCRIPTION = (
    "How businesses in e-commerce, education, healthcare, insurance, real estate, recruitment and more use "
    "chatbot0 to answer visitors and capture leads."
)
ABOUT_TITLE = "About chatbot0, by smallTech"
ABOUT_DESCRIPTION = (
    "chatbot0 is the AI chat agent from smallTech, the company behind Zer0. AI for Everyone: the tools large "
    "companies use, simple and affordable for any business."
)
SIGNUP_TITLE = "Sign up free, chatbot0"
SIGNUP_DESCRIPTION = (
    f"Create your free chatbot0 agent and get the one-line embed script for your website. "
    f"{content.FREE_CONVERSATIONS} conversations a month free, no card needed."
)

# Public pages, in sitemap order: path -> view name. register_host_routing serves the same paths at the host root.
PAGE_PATHS = ("/", "/pricing", "/sales", "/support", "/industries", "/about", "/signup")


def _render(template: str, *, path: str, title: str, description: str, **extra) -> str:
    return render_template(
        template,
        page_path=path,
        page_title=title,
        page_description=description,
        canonical=content.SITE_URL + path,
        site_url=content.SITE_URL,
        signup_url=content.SIGNUP_URL,
        zer0_url=content.ZER0_URL,
        contact_email=content.CONTACT_EMAIL,
        github_url=content.GITHUB_URL,
        linkedin_url=content.LINKEDIN_URL,
        plans=content.PLANS,
        free_conversations=content.FREE_CONVERSATIONS,
        max_yearly_saving_pct=content.MAX_YEARLY_SAVING_PCT,
        # The chat widget needs a `domains` row for the page's origin, so it is only rendered on the chatbot0 host.
        chat_widget=(request.host or "").split(":")[0].lower() in _chat_hosts(),
        widget_url=content.WIDGET_URL,
        **extra,
    )


@chatbot0_bp.route("/", methods=["GET"])
def landing():
    return _render("chatbot0/landing.html", path="/", title=LANDING_TITLE, description=LANDING_DESCRIPTION)


@chatbot0_bp.route("/pricing", methods=["GET"])
def pricing():
    return _render("chatbot0/pricing.html", path="/pricing", title=PRICING_TITLE, description=PRICING_DESCRIPTION)


@chatbot0_bp.route("/sales", methods=["GET"])
def sales():
    return _render("chatbot0/sales.html", path="/sales", title=SALES_TITLE, description=SALES_DESCRIPTION)


@chatbot0_bp.route("/support", methods=["GET"])
def support():
    return _render("chatbot0/support.html", path="/support", title=SUPPORT_TITLE, description=SUPPORT_DESCRIPTION)


@chatbot0_bp.route("/industries", methods=["GET"])
def industries():
    # Old zer0 links carry ?industry=<name>; that entry is highlighted and named at the top of the page.
    # The canonical URL stays /industries.
    return _render(
        "chatbot0/industries.html", path="/industries", title=INDUSTRIES_TITLE, description=INDUSTRIES_DESCRIPTION,
        industries=content.INDUSTRIES, selected=content.find_industry(request.args.get("industry")),
    )


@chatbot0_bp.route("/about", methods=["GET"])
def about():
    return _render("chatbot0/about.html", path="/about", title=ABOUT_TITLE, description=ABOUT_DESCRIPTION)


@chatbot0_bp.route("/signup", methods=["GET"])
def signup():
    return _render(
        "chatbot0/signup.html", path="/signup", title=SIGNUP_TITLE, description=SIGNUP_DESCRIPTION,
        default_colour=content.DEFAULT_WIDGET_COLOUR, widget_colours=content.WIDGET_COLOURS,
    )


@chatbot0_bp.route("/robots.txt", methods=["GET"])
def robots():
    body = f"User-agent: *\nAllow: /\nSitemap: {content.SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@chatbot0_bp.route("/sitemap.xml", methods=["GET"])
def sitemap():
    urls = "".join(f"<url><loc>{content.SITE_URL}{p}</loc></url>" for p in PAGE_PATHS)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    )
    return Response(body, mimetype="application/xml")


# Hosts that serve the chatbot0 pages at their root. Override with CHATBOT0_HOSTS (comma-separated).
DEFAULT_HOSTS = "chatbot0.smalltech.in"


def _chat_hosts() -> set[str]:
    return {h.strip().lower() for h in os.environ.get("CHATBOT0_HOSTS", DEFAULT_HOSTS).split(",") if h.strip()}


def register_host_routing(app: Flask) -> None:
    """Serve the chatbot0 pages at the root of the chatbot0 host(s).

    Only GET/HEAD on a handful of exact paths is intercepted, and only for those hosts; anything else falls
    through to the normal routes (API, health, Swagger). The sign-up page relies on that: its POST /domains/
    and POST /prompt reach the API on this host unchanged."""
    hosts = _chat_hosts()
    pages = {
        "/": landing, "/pricing": pricing, "/sales": sales, "/support": support, "/industries": industries,
        "/about": about, "/signup": signup, "/robots.txt": robots, "/sitemap.xml": sitemap,
    }

    @app.before_request
    def _chatbot0_host_root():
        if request.method not in ("GET", "HEAD"):
            return None
        host = (request.host or "").split(":")[0].lower()
        if host not in hosts:
            return None
        path = request.path
        if path in pages:
            return pages[path]()
        if path.startswith("/static/"):
            return send_from_directory(_STATIC_DIR, path[len("/static/"):])
        return None
