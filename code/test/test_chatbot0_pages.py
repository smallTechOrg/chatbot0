"""chatbot0 public pages (SMA-8): they render, carry the right links and SEO,
and leave the existing routes ("/" Swagger UI, /health, the API) alone."""

import pytest

from chatbot0 import content


PAGES = ["/", "/pricing", "/sales", "/support", "/industries", "/about", "/signup"]


@pytest.mark.parametrize("path", ["/chatbot0" + p for p in PAGES])
def test_public_pages_render(client, path):
    res = client.get(path)
    assert res.status_code == 200
    assert res.mimetype == "text/html"
    html = res.get_data(as_text=True)
    assert 'chatbot<span class="pub-wordmark__zero">0</span>' in html
    assert content.SIGNUP_URL in html
    assert 'href="static/css/chatbot0.css"' in html
    assert "© 2026 madhyamakist pvt ltd" in html or "&copy; 2026 madhyamakist pvt ltd" in html
    assert "sales0" not in html.lower()


def test_landing_seo(client):
    html = client.get("/chatbot0/").get_data(as_text=True)
    assert "<title>chatbot0, the AI chat agent for business websites</title>" in html
    assert '<link rel="canonical" href="https://chatbot0.smalltech.in/">' in html
    assert 'property="og:url" content="https://chatbot0.smalltech.in/"' in html
    assert content.ZER0_URL in html


def test_pricing_shows_every_plan(client):
    html = client.get("/chatbot0/pricing").get_data(as_text=True)
    assert '<link rel="canonical" href="https://chatbot0.smalltech.in/pricing">' in html
    for plan in content.PLANS:
        assert f"${plan.monthly}<span>/month</span>" in html
        if plan.yearly:
            assert f"or ${plan.yearly}/month billed yearly (save {plan.yearly_saving_pct}%)" in html


def test_yearly_savings_are_computed_from_prices():
    by_key = {p.key: p for p in content.PLANS}
    assert by_key["free"].yearly_saving_pct is None
    assert by_key["basic"].yearly_saving_pct == 25  # $4 -> $3
    assert by_key["pro"].yearly_saving_pct == 17  # $12 -> $10


def test_robots_and_sitemap(client):
    robots = client.get("/chatbot0/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://chatbot0.smalltech.in/sitemap.xml" in robots.get_data(as_text=True)
    sitemap = client.get("/chatbot0/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.mimetype == "application/xml"
    body = sitemap.get_data(as_text=True)
    assert "<loc>https://chatbot0.smalltech.in/</loc>" in body
    for path in PAGES:
        assert f"<loc>https://chatbot0.smalltech.in{path}</loc>" in body


@pytest.mark.parametrize(
    "asset",
    ["css/chatbot0.css", "img/icon.svg", "img/favicon.ico", "img/apple-icon.png",
     "img/logo-smalltech.svg", "img/og-chatbot0.png"],
)
def test_static_assets_served(client, asset):
    assert client.get(f"/chatbot0/static/{asset}").status_code == 200


def test_prefix_without_slash_redirects_to_landing(client):
    res = client.get("/chatbot0")
    assert res.status_code in (301, 308)
    assert res.headers["Location"].endswith("/chatbot0/")


def test_root_is_still_the_swagger_ui(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "swagger" in html.lower()
    assert "chatbot0" not in html


HOST = {"Host": "chatbot0.smalltech.in"}


@pytest.mark.parametrize("path", PAGES)
def test_chatbot0_host_serves_pages_at_root(client, path):
    res = client.get(path, headers=HOST)
    assert res.status_code == 200 and res.mimetype == "text/html"
    assert 'chatbot<span class="pub-wordmark__zero">0</span>' in res.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/static/css/chatbot0.css", "/static/img/icon.svg", "/robots.txt", "/sitemap.xml"])
def test_chatbot0_host_serves_assets_at_root(client, path):
    assert client.get(path, headers=HOST).status_code == 200


def test_chatbot0_host_leaves_api_paths_alone(client):
    assert client.get("/health", headers=HOST).status_code == client.get("/health").status_code


def test_other_hosts_keep_swagger_at_root(client):
    html = client.get("/", headers={"Host": "zero-sales-agent-a23rjysfbq-uc.a.run.app"}).get_data(as_text=True)
    assert "chatbot<span" not in html


def test_chat_widget_is_on_the_chatbot0_host_only(client):
    on_host = client.get("/", headers=HOST).get_data(as_text=True)
    assert f'src="{content.WIDGET_URL}/embed.js"' in on_host
    assert f'data-chat-url="{content.WIDGET_URL}/embed"' in on_host
    assert "embed.js" in client.get("/pricing", headers=HOST).get_data(as_text=True)
    # other hosts (the Cloud Run URL, localhost) have no domains row, so no widget
    assert "embed.js" not in client.get("/chatbot0/").get_data(as_text=True)


def test_pages_load_the_shared_analytics_script(client):
    """One GA4 property for every smallTech site; the script decides by hostname whether to run."""
    for path in PAGES:
        assert 'src="static/js/st-analytics.js"' in client.get(path, headers=HOST).get_data(as_text=True)
    script = client.get("/static/js/st-analytics.js", headers=HOST)
    assert script.status_code == 200
    body = script.get_data(as_text=True)
    assert "G-YTYS0G2P7L" in body and '"chatbot0.smalltech.in": "chatbot0"' in body
    # Plan buttons say which plan was picked.
    assert 'data-ga-event="plan_click" data-ga-plan="free"' in client.get("/pricing", headers=HOST).get_data(as_text=True)


# ---------------------------------------------------------------- pages ported from zer0.smalltech.in

@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("host", [None, "chatbot0.smalltech.in"])
def test_no_small_business_wording(client, path, host):
    """smallTech is "AI for Everyone": chatbot0 is for businesses, never pitched as small-business software."""
    url = path if host else "/chatbot0" + path
    html = client.get(url, headers={"Host": host} if host else {}).get_data(as_text=True).lower()
    for phrase in ("small business", "small-business", "smb"):
        assert phrase not in html, f"{phrase!r} on {url}"


@pytest.mark.parametrize(
    "path,title",
    [("/sales", "AI sales agent for your website, chatbot0"),
     ("/support", "AI customer support agent for your website, chatbot0"),
     ("/industries", "chatbot0 for your industry"),
     ("/about", "About chatbot0, by smallTech"),
     ("/signup", "Sign up free, chatbot0")],
)
def test_new_pages_seo(client, path, title):
    html = client.get("/chatbot0" + path).get_data(as_text=True)
    assert f"<title>{title}</title>" in html
    assert f'<link rel="canonical" href="https://chatbot0.smalltech.in{path}">' in html
    assert f'property="og:url" content="https://chatbot0.smalltech.in{path}"' in html
    assert 'property="og:title"' in html and 'name="description"' in html
    # current page is marked in the header nav (sign-up is the header button, not a nav link)
    if path != "/signup":
        assert f'href="{path[1:]}" class="pub-nav__link" aria-current="page"' in html


def test_signup_buttons_go_to_chatbot0_signup(client):
    assert content.SIGNUP_URL == "signup"
    html = client.get("/chatbot0/").get_data(as_text=True)
    assert 'class="pub-btn pub-btn--primary pub-header__cta" href="signup"' in html
    assert "zer0.smalltech.in/signup" not in html


def test_signup_page_has_the_form_and_loads_its_script(client):
    for res in (client.get("/chatbot0/signup"), client.get("/signup", headers=HOST)):
        html = res.get_data(as_text=True)
        assert res.status_code == 200
        assert '<form class="pub-form" id="signup-form">' in html
        for field in ("su-name", "su-website", "su-email", "su-phone", "su-prompt", "su-colour", "su-colour-picker"):
            assert f'id="{field}"' in html
        assert 'data-contact-method="email"' in html and 'data-contact-method="phone"' in html
        for colour in content.WIDGET_COLOURS:
            assert f'data-colour="{colour}"' in html
        assert 'id="signup-submit" disabled' in html
        assert 'src="static/js/signup.js"' in html
        # no input carries a name, so nothing personal can end up in a URL without the script
        assert " name=" not in html.split('id="signup-form"')[1].split("</form>")[0]


def test_signup_script_calls_the_api_like_the_old_sign_up_page(client):
    for url, headers in (("/chatbot0/static/js/signup.js", {}), ("/static/js/signup.js", HOST)):
        res = client.get(url, headers=headers)
        assert res.status_code == 200
        js = res.get_data(as_text=True)
        # same three calls, in order, root-absolute so they reach the API from /chatbot0/ and the chatbot0 host
        order = [js.index('jsonPost("/domains/", "POST"'), js.index('jsonPost("/prompt", "POST"'),
                 js.index('jsonPost("/chat-info/contact", "PATCH"')]
        assert order == sorted(order)
        assert 'agent_type: "sales"' in js and 'type: "company"' in js
        assert 'var WIDGET_ORIGIN = "https://zer0.smalltech.in";' in js
        assert 'track("sign_up", { method: "chatbot0" })' in js


@pytest.mark.parametrize("path", ["/domains/", "/prompt", "/chat-info/contact"])
def test_chatbot0_host_passes_signup_api_calls_through(client, path):
    """Host routing only serves pages on GET/HEAD; the sign-up's API calls reach the API on the chatbot0 host."""
    method = client.patch if path == "/chat-info/contact" else client.post
    on_host = method(path, json={}, headers=HOST)
    elsewhere = method(path, json={})
    assert on_host.status_code == elsewhere.status_code
    assert on_host.mimetype != "text/html"


@pytest.mark.parametrize("value,slug", [("E-Commerce", "e-commerce"), ("IT Support", "it-support"),
                                        ("real estate", "real-estate"), ("enterprises", "enterprises")])
def test_old_industry_links_land_on_their_entry(client, value, slug):
    for url, headers in (("/chatbot0/industries", {}), ("/industries", HOST)):
        html = client.get(url, query_string={"industry": value}, headers=headers).get_data(as_text=True)
        industry = content.find_industry(value)
        assert f'<span class="pub-accent">{industry.name}.</span>' in html
        assert f'class="pub-card pub-card--current" id="{slug}" aria-current="true"' in html
        assert '<link rel="canonical" href="https://chatbot0.smalltech.in/industries">' in html


def test_industries_lists_every_industry_and_drops_small_business(client):
    html = client.get("/chatbot0/industries").get_data(as_text=True)
    for industry in content.INDUSTRIES:
        assert f'id="{industry.slug}"' in html and industry.feature in html
    assert "pub-card--current" not in html
    assert content.find_industry("Small Business") is None
    assert "pub-card--current" not in client.get("/chatbot0/industries?industry=Small%20Business").get_data(as_text=True)


def test_about_links_to_smalltech_and_zer0(client):
    html = client.get("/chatbot0/about").get_data(as_text=True)
    assert 'href="https://smalltech.in"' in html and f'href="{content.ZER0_URL}"' in html
    assert "AI for Everyone" in html


def test_new_pages_are_in_header_and_footer_nav(client):
    html = client.get("/chatbot0/pricing").get_data(as_text=True)
    for path in ("sales", "support", "industries", "about"):
        assert f'href="{path}" class="pub-nav__link"' in html
        assert f'<a href="{path}">' in html
