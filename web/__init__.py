"""Serves the Next.js static export (frontend/) from Flask.

Everything a person sees on chatbot0 is that export; Flask answers only the JSON APIs
and, for any GET/HEAD request that no route matched, looks the path up in
``FRONTEND_DIR`` in this order: ``<path>``, ``<path>/index.html``, ``<path>.html``.
Nothing found: ``404.html`` with status 404.

API routes always win, because this runs as the 404 handler. A 404 that an API route
raised itself, a non-GET request, and anything under ``/api/`` keep the JSON error the
API gives everywhere else. The old ``/chatbot0/<page>`` URLs redirect to ``/<page>``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from flask import Flask, Response, redirect, request, send_file
from werkzeug.exceptions import NotFound
from werkzeug.security import safe_join

from core.config import FRONTEND_DIR

logger = logging.getLogger(__name__)

IMMUTABLE_PREFIX = "_next/static/"
NOT_FOUND_PAGE = "404.html"
# `next build` also writes 404/index.html next to 404.html; neither is a page to link to.
_NOT_PAGES = frozenset({"404", NOT_FOUND_PAGE})

ErrorHandler = Callable[[Any], Any]


def find_file(root: Path, url_path: str) -> Path | None:
    """The file that answers ``url_path`` inside ``root``, or None. Never leaves ``root``."""
    rel = url_path.strip("/")
    if rel in _NOT_PAGES:
        return None
    candidates = [rel, f"{rel}/index.html" if rel else "index.html"]
    if rel:
        candidates.append(f"{rel}.html")
    for candidate in candidates:
        joined = safe_join(str(root), candidate)
        if joined and Path(joined).is_file():
            return Path(joined)
    return None


def _file_response(path: Path, rel: str) -> Response:
    response = send_file(path, conditional=True)
    if rel.startswith(IMMUTABLE_PREFIX):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.suffix == ".html":
        response.headers["Cache-Control"] = "no-cache"
    return response


def _serves_frontend() -> bool:
    """Only an unmatched GET/HEAD outside /api/ is a page request; a 404 an API route raised is its own."""
    return request.url_rule is None and request.method in ("GET", "HEAD") and not request.path.startswith("/api/")


def register_frontend(app: Flask, root: Path = FRONTEND_DIR, api_error: ErrorHandler | None = None) -> None:
    """Serve ``root`` for requests no route matched. ``api_error`` shapes the 404s that are not pages."""
    if not (root / "index.html").is_file():
        logger.warning("[WEB] no frontend export at %s; run `npm run build` in frontend/", root)

    def serve(url_path: str) -> Response | None:
        found = find_file(root, url_path)
        return _file_response(found, url_path.strip("/")) if found else None

    def _not_found_page() -> Response:
        page = root / NOT_FOUND_PAGE
        if not page.is_file():
            raise NotFound()
        response = _file_response(page, NOT_FOUND_PAGE)
        response.status_code = 404
        return response

    @app.get("/")
    def home() -> Response:
        return serve("/") or _not_found_page()

    @app.get("/chatbot0/", defaults={"page": ""}, strict_slashes=False)
    @app.get("/chatbot0/<path:page>")
    def legacy_prefix(page: str) -> Response:
        """The pages used to live under /chatbot0/ on the run.app URL; the old admin pages are the login now."""
        target = "/login/" if page == "admin" or page.startswith("admin/") else "/" + page
        return redirect(f"{target}?{request.query_string.decode()}" if request.query_string else target, code=301)

    @app.errorhandler(404)
    def not_found(error: NotFound) -> Any:
        if _serves_frontend():
            try:
                return serve(request.path) or _not_found_page()
            except NotFound:
                pass
        return api_error(error) if api_error else error
