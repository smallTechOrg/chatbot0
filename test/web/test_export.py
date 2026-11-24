"""The built frontend as Flask serves it (frontend/out, built by `npm run build`; CI builds it before pytest).

These replace the tests of the old Jinja pages: the same assertions, moved to the exported HTML.
Component behaviour (industry highlighting, sign-up flow) is in frontend/src/**/*.test.ts(x).
"""

import re

import pytest

from core.config import FRONTEND_DIR

pytestmark = pytest.mark.skipif(not (FRONTEND_DIR / "index.html").is_file(), reason="frontend is not built")

PAGES = ["/", "/pricing/", "/sales/", "/support/", "/industries/", "/about/", "/signup/"]
SITE = "https://chatbot0.smalltech.in"
HOST = {"Host": "chatbot0.smalltech.in"}


def page(client, path, **kwargs):
    """The HTML of a page, without React's `<!-- -->` text separators."""
    res = client.get(path, **kwargs)
    assert res.status_code == 200
    assert res.mimetype == "text/html"
    return res.get_data(as_text=True).replace("<!-- -->", "")


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("headers", [{}, HOST], ids=["run.app", "chatbot0.smalltech.in"])
def test_public_pages_render_on_every_host(client, path, headers):
    html = page(client, path, headers=headers)
    assert 'chatbot<span class="pub-wordmark__zero">0</span>' in html
    assert 'href="/signup/"' in html
    assert "© 2026 madhyamakist pvt ltd" in html or "&copy; 2026 madhyamakist pvt ltd" in html
    assert "sales0" not in html.lower()
    for phrase in ("small business", "small-business", "smb"):
        assert phrase not in html.lower()


@pytest.mark.parametrize("path", [p.rstrip("/") for p in PAGES if p != "/"])
def test_paths_work_without_the_trailing_slash(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path,title",
    [
        ("/", "chatbot0, the AI chat agent for business websites"),
        ("/pricing/", "Pricing, chatbot0"),
        ("/sales/", "AI sales agent for your website, chatbot0"),
        ("/support/", "AI customer support agent for your website, chatbot0"),
        ("/industries/", "chatbot0 for your industry"),
        ("/about/", "About chatbot0, by smallTech"),
        ("/signup/", "Sign up free, chatbot0"),
    ],
)
def test_page_seo(client, path, title):
    html = page(client, path)
    assert f"<title>{title}</title>" in html
    assert f'<link rel="canonical" href="{SITE}{path}"/>' in html
    assert f'property="og:url" content="{SITE}{path}"' in html
    assert f'property="og:title" content="{title}"' in html
    assert 'name="description"' in html and 'name="twitter:card"' in html
    assert f'property="og:image" content="{SITE}/og-chatbot0.png"' in html
    # the current page is marked in the header nav (sign-up is the header button, not a nav link)
    if path not in ("/", "/signup/"):
        assert f'aria-current="page" href="{path}">' in html


def test_landing_has_structured_data_and_links_zer0(client):
    html = page(client, "/")
    assert '"@type":"SoftwareApplication"' in html
    assert "https://zer0.smalltech.in" in html


def test_pricing_shows_every_plan(client):
    html = page(client, "/pricing/")
    for monthly, yearly, saving in [(0, None, None), (4, 3, 25), (12, 10, 17)]:
        assert f"${monthly}<span>/month</span>" in html
        if yearly:
            assert f"or ${yearly}/month billed yearly (save {saving}%)" in html
    assert "Save up to 25% when you pay yearly" in html
    assert 'data-ga-event="plan_click" data-ga-plan="free"' in html or (
        'data-ga-plan="free"' in html and 'data-ga-event="plan_click"' in html
    )


def test_nav_footer_and_new_pages_are_linked(client):
    html = page(client, "/pricing/")
    for path in ("sales", "support", "industries", "about"):
        assert f'href="/{path}/"' in html
    assert "mailto:contact@smalltech.in" in html


def test_industries_lists_every_industry(client):
    html = page(client, "/industries/")
    for slug in ("e-commerce", "customer-service", "education", "enterprises", "healthcare", "insurance"):
        assert f'id="{slug}"' in html
    assert "pub-card--current" not in html  # nothing is highlighted without ?industry=


def test_signup_page_has_the_form(client):
    html = page(client, "/signup/")
    for field in (
        "su-name",
        "su-website",
        "su-email",
        "su-password",
        "su-phone",
        "su-prompt",
        "su-colour",
        "su-colour-picker",
    ):
        assert f'id="{field}"' in html
    assert 'type="password"' in html and "optional" in html
    assert 'id="signup-submit"' in html and "disabled" in html.split('id="signup-submit"')[1][:80]
    for colour in ("#219EBC", "#023047", "#FB8500", "#FFB703", "#E63946", "#2D6A4F", "#7209B7", "#000000"):
        assert f"Select colour {colour}" in html


def test_robots_and_sitemap(client):
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert f"Sitemap: {SITE}/sitemap.xml" in robots.get_data(as_text=True)
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "xml" in sitemap.mimetype
    body = sitemap.get_data(as_text=True)
    for path in PAGES:
        assert f"<loc>{SITE}{path}</loc>" in body


@pytest.mark.parametrize(
    "asset", ["favicon.ico", "icon.svg", "apple-icon.png", "logo-smalltech.svg", "og-chatbot0.png"]
)
def test_static_assets_are_served(client, asset):
    assert client.get(f"/{asset}").status_code == 200


def test_pages_load_the_shared_analytics_script(client):
    """One GA4 property for every smallTech site; the script decides by hostname whether to run."""
    for path in PAGES:
        assert "/st-analytics.js" in page(client, path)
    script = client.get("/st-analytics.js")
    assert script.status_code == 200
    body = script.get_data(as_text=True)
    assert "G-YTYS0G2P7L" in body and '"chatbot0.smalltech.in": "chatbot0"' in body


def test_built_assets_are_cached_forever(client):
    html = page(client, "/")
    asset = re.search(r'/_next/static/[^"]+\.js', html)
    assert asset
    res = client.get(asset.group(0))
    assert res.status_code == 200
    assert "immutable" in res.headers["Cache-Control"]


def test_root_on_the_run_app_host_is_the_landing_page_not_swagger(client):
    html = page(client, "/", headers={"Host": "zero-sales-agent-a23rjysfbq-uc.a.run.app"})
    assert "chatbot0, the AI chat agent" in html
    assert "swagger" not in html.lower()


def test_unknown_page_is_the_404_page(client):
    res = client.get("/no-such-page/")
    assert res.status_code == 404
    assert "Page not found, chatbot0" in res.get_data(as_text=True)


def test_old_prefix_redirects(client):
    res = client.get("/chatbot0/pricing")
    assert res.status_code == 301 and res.headers["Location"].endswith("/pricing")
    res = client.get("/chatbot0/industries?industry=Education")
    assert res.headers["Location"].endswith("/industries?industry=Education")


@pytest.mark.parametrize("path", ["/domains/", "/prompt", "/chat-info/contact"])
def test_signup_api_calls_reach_the_api_on_the_chatbot0_host(client, path):
    """The sign-up page's calls are API routes on every host, never the frontend."""
    method = client.patch if path == "/chat-info/contact" else client.post
    on_host = method(path, json={}, headers=HOST)
    assert on_host.status_code == method(path, json={}).status_code
    assert on_host.mimetype != "text/html"


def test_health_is_unchanged_on_the_chatbot0_host(client):
    assert client.get("/health", headers=HOST).status_code == client.get("/health").status_code


# ---------------------------------------------------------------- the chat widget


def test_embed_frame_is_served(client):
    res = client.get("/embed/?host=https%3A%2F%2Fexample.com&color=%23219EBC")
    assert res.status_code == 200 and res.mimetype == "text/html"
    html = res.get_data(as_text=True)
    assert "<title>chatbot0 chat</title>" in html
    assert 'content="noindex' in html  # the frame is not a page to index


def test_embed_frame_works_without_the_trailing_slash(client):
    assert client.get("/embed").status_code == 200


def test_embed_js_is_served_as_javascript_with_chatbot0_as_the_default_frame(client):
    res = client.get("/embed.js")
    assert res.status_code == 200
    assert "javascript" in res.mimetype
    js = res.get_data(as_text=True)
    assert '"https://chatbot0.smalltech.in/embed/"' in js
    # snippets installed before the widget moved still name zer0's frame; they are followed to the new one
    assert "zer0\\.smalltech\\.in\\/embed" in js
    # the contract with the frame: host origin and colour in the query, close and analytics messages back
    assert "?host=" in js and "&color=" in js
    assert "CLOSE_CHAT" in js and "ANALYTICS_EVENT" in js and "SEND_MESSAGE" in js


def test_signup_snippet_points_at_chatbot0s_widget(client):
    chunks = "".join(p.read_text(errors="ignore") for p in (FRONTEND_DIR / "_next" / "static" / "chunks").rglob("*.js"))
    assert "https://chatbot0.smalltech.in" in chunks and "/embed.js" in chunks


def test_widget_chat_contract_origin_selects_the_domain(client, monkeypatch):
    """The widget calls POST /chat?origin=<host site> and GET /history?origin=...: the API keeps taking both."""
    from api import chat as chat_api

    seen = {}

    def fake_reply(text, session_id, request_type, domain):
        seen["domain"] = domain
        return "stubbed"

    monkeypatch.setattr(chat_api, "get_groq_response", fake_reply)
    res = client.post(
        "/chat?origin=https%3A%2F%2Fexample.com",
        json={"input": "hi", "session_id": "0b8a6c0e-7a3c-4a5e-9d8f-111111111111", "request_type": "sales"},
    )
    assert res.status_code == 200
    assert res.get_json()["success"] is True
    assert seen["domain"]


def test_old_admin_urls_lead_to_the_login_page(client):
    for path in ("/chatbot0/admin/", "/chatbot0/admin/login", "/chatbot0/admin/whatsapp/abc"):
        res = client.get(path)
        assert res.status_code == 301 and res.headers["Location"].endswith("/login/")


# ---------------------------------------------------------------- the signed-in app (client-rendered pages)


@pytest.mark.parametrize(
    "path,title",
    [
        ("/login/", "Sign in, chatbot0"),
        ("/accept/", "Choose your password, chatbot0"),
        ("/dashboard/", "Leads, chatbot0"),
    ],
)
def test_app_pages_are_served_and_not_indexed(client, path, title):
    html = page(client, path)
    assert f"<title>{title}</title>" in html
    assert 'name="robots" content="noindex' in html


def test_the_accept_page_never_leaks_its_token_through_the_referrer(client):
    assert 'name="referrer" content="no-referrer"' in page(client, "/accept/")


def test_analytics_skips_the_private_app_paths(client):
    js = client.get("/st-analytics.js").get_data(as_text=True)
    assert "login|accept" in js and "dashboard" in js
