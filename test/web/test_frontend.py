"""web/: serving the frontend export. A fixture directory stands in for frontend/out."""

import pytest
from flask import Flask, abort, jsonify

from web import find_file, register_frontend


@pytest.fixture
def export(tmp_path):
    """A tiny export: landing, a page with an index.html, a flat .html page, hashed assets, a 404 page."""
    root = tmp_path / "out"
    (root / "pricing").mkdir(parents=True)
    (root / "404").mkdir()
    (root / "_next" / "static" / "chunks").mkdir(parents=True)
    (root / "index.html").write_text("<title>home</title>")
    (root / "pricing" / "index.html").write_text("<title>pricing</title>")
    (root / "about.html").write_text("<title>about</title>")
    (root / "404.html").write_text("<title>missing</title>")
    (root / "404" / "index.html").write_text("<title>missing</title>")
    (root / "robots.txt").write_text("User-agent: *\n")
    (root / "_next" / "static" / "chunks" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("outside the export")
    return root


@pytest.fixture
def client(export):
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/domains/<int:domain_id>")
    def domain(domain_id):
        abort(404)

    @app.post("/chat")
    def chat():
        return jsonify(success=True)

    register_frontend(app, root=export, api_error=lambda e: ({"code": e.code, "status": e.name}, e.code))
    return app.test_client()


def test_root_serves_the_landing_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<title>home</title>" in res.data


def test_file_is_found_by_its_path(client):
    res = client.get("/robots.txt")
    assert res.status_code == 200
    assert res.data == b"User-agent: *\n"


@pytest.mark.parametrize("path", ["/pricing", "/pricing/"])
def test_directory_falls_back_to_its_index_html(client, path):
    res = client.get(path)
    assert res.status_code == 200
    assert b"<title>pricing</title>" in res.data


def test_flat_html_file_is_found_without_its_extension(client):
    assert b"<title>about</title>" in client.get("/about").data


def test_unknown_path_serves_the_404_page_with_status_404(client):
    res = client.get("/nope/")
    assert res.status_code == 404
    assert res.mimetype == "text/html"
    assert b"<title>missing</title>" in res.data


@pytest.mark.parametrize("path", ["/404", "/404/", "/404.html"])
def test_the_404_page_itself_is_not_a_page(client, path):
    assert client.get(path).status_code == 404


def test_head_request_is_served_too(client):
    assert client.head("/pricing/").status_code == 200
    assert client.head("/nope/").status_code == 404


@pytest.mark.parametrize(
    "path", ["/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "/pricing/../../secret.txt"]
)
def test_paths_cannot_leave_the_export(client, path):
    res = client.get(path)
    assert b"outside" not in res.data


def test_find_file_refuses_to_leave_the_root(export):
    assert find_file(export, "../secret.txt") is None
    assert find_file(export, "/pricing/../../secret.txt") is None


def test_api_routes_win_over_the_frontend(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    assert client.post("/chat").get_json() == {"success": True}


def test_a_404_raised_by_an_api_route_stays_json(client):
    res = client.get("/domains/7")
    assert res.status_code == 404
    assert res.get_json() == {"code": 404, "status": "Not Found"}


def test_unknown_api_paths_get_a_json_404(client):
    res = client.get("/api/nothing-here")
    assert res.status_code == 404
    assert res.get_json() == {"code": 404, "status": "Not Found"}


def test_non_get_requests_to_unknown_paths_get_the_api_error(client):
    res = client.post("/pricing/")
    assert res.status_code in (404, 405)
    assert res.mimetype != "text/html"


def test_html_is_not_cached(client):
    assert client.get("/").headers["Cache-Control"] == "no-cache"
    assert client.get("/nope/").headers["Cache-Control"] == "no-cache"


def test_next_static_assets_are_cached_forever(client):
    res = client.get("/_next/static/chunks/app.js")
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_other_files_are_revalidated(client):
    assert "immutable" not in client.get("/robots.txt").headers.get("Cache-Control", "")


@pytest.mark.parametrize(
    "old,new",
    [
        ("/chatbot0", "/"),
        ("/chatbot0/", "/"),
        ("/chatbot0/pricing", "/pricing"),
        ("/chatbot0/industries?industry=Education", "/industries?industry=Education"),
    ],
)
def test_old_chatbot0_urls_redirect_permanently(client, old, new):
    res = client.get(old)
    assert res.status_code == 301
    assert res.headers["Location"].endswith(new)


def test_missing_export_still_answers_with_the_api_error(tmp_path):
    app = Flask(__name__)
    register_frontend(app, root=tmp_path / "missing", api_error=lambda e: ({"code": e.code}, e.code))
    res = app.test_client().get("/anything/")
    assert res.status_code == 404
    assert res.get_json() == {"code": 404}
