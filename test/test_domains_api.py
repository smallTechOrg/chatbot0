"""
Controller-level tests for the Domains API (POST/GET /domains).

Isolation strategy
------------------
These tests import ``app`` (which requires a live database connection for the
initial ``db.py`` setup – same requirement as all other tests in this project).
Once the app is instantiated, every call to the route functions is intercepted
at the service boundary by patching ``api.domains._get_domain_service``.
This means **no SQL is executed during the test run itself**.

Complementary pure-unit tests (no DB required at all) live in
``test_domains_service.py``.
"""

import os
import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app as flask_app
from domains.service import (
    DomainAlreadyExistsError,
    DomainService,
    InvalidWebsiteURLError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DOMAIN = {
    "id": 1,
    "key": "EXAMPLE_COM",
    "address": "example.com",
    "parent_id": None,
    "created_at": datetime(2024, 1, 1, tzinfo=UTC),
}


@pytest.fixture(scope="module")
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def notify():
    """Never post to Slack from a test. Yields the mock to check the call."""
    with patch("api.domains.notify_signup") as fake:
        yield fake


@pytest.fixture
def mock_service():
    """
    Patch the service factory so that no database queries reach the DB.
    Yields a MagicMock pre-configured with sensible defaults.
    """
    with patch("api.domains._get_domain_service") as factory:
        svc = MagicMock(spec=DomainService)
        svc.add_domain.return_value = SAMPLE_DOMAIN
        svc.get_domain.return_value = SAMPLE_DOMAIN
        svc.list_domains.return_value = [SAMPLE_DOMAIN]
        factory.return_value = svc
        yield svc


# ---------------------------------------------------------------------------
# POST /domains/ – success
# ---------------------------------------------------------------------------


class TestCreateDomain:
    def test_returns_201_on_success(self, client, mock_service):
        response = client.post(
            "/domains/",
            json={"website_url": "https://www.example.com/about"},
        )
        assert response.status_code == 201

    def test_response_contains_expected_fields(self, client, mock_service):
        response = client.post(
            "/domains/",
            json={"website_url": "https://www.example.com/about"},
        )
        data = response.get_json()
        assert data["address"] == "example.com"
        assert data["key"] == "EXAMPLE_COM"
        assert data["id"] == 1
        assert data["parent_id"] is None

    def test_service_receives_correct_arguments(self, client, mock_service):
        client.post(
            "/domains/",
            json={"website_url": "https://example.com"},
        )
        mock_service.add_domain.assert_called_once_with(
            website_url="https://example.com",
            parent_id=1,
            contact={"contact_name": None, "email": None, "mobile": None},
        )

    def test_extra_fields_are_ignored(self, client, mock_service):
        """key and parent_id sent by the client should be silently ignored."""
        response = client.post(
            "/domains/",
            json={"website_url": "https://example.com", "key": "CUSTOM", "parent_id": 99},
        )
        # still succeeds – unknown fields are stripped by marshmallow
        assert response.status_code == 201
        _, kwargs = mock_service.add_domain.call_args
        assert "key" not in kwargs
        assert kwargs["parent_id"] == 1


class TestCreateDomainContact:
    """The chatbot0 sign-up sends who is signing up along with the website."""

    def test_contact_reaches_the_service(self, client, mock_service):
        response = client.post(
            "/domains/",
            json={
                "website_url": "acme.com",
                "contact_name": "  Anjali ",
                "email": "anjali@acme.com",
            },
        )
        assert response.status_code == 201
        _, kwargs = mock_service.add_domain.call_args
        assert kwargs["contact"] == {"contact_name": "Anjali", "email": "anjali@acme.com", "mobile": None}

    def test_blank_fields_are_not_given(self, client, mock_service):
        response = client.post(
            "/domains/",
            json={
                "website_url": "acme.com",
                "contact_name": "",
                "email": "  ",
                "mobile": "+91 98765 43210",
            },
        )
        assert response.status_code == 201
        _, kwargs = mock_service.add_domain.call_args
        assert kwargs["contact"] == {"contact_name": None, "email": None, "mobile": "+91 98765 43210"}

    @pytest.mark.parametrize(
        "field,value", [("email", "not-an-email"), ("mobile", "call me"), ("contact_name", "x" * 201)]
    )
    def test_bad_contact_returns_422(self, client, mock_service, field, value):
        response = client.post("/domains/", json={"website_url": "acme.com", field: value})
        assert response.status_code == 422
        mock_service.add_domain.assert_not_called()

    def test_contact_is_never_returned(self, client, mock_service):
        mock_service.add_domain.return_value = {**SAMPLE_DOMAIN, "email": "anjali@acme.com"}
        mock_service.list_domains.return_value = [{**SAMPLE_DOMAIN, "email": "anjali@acme.com"}]
        created = client.post("/domains/", json={"website_url": "acme.com", "email": "anjali@acme.com"})
        listed = client.get("/domains/")
        assert "anjali@acme.com" not in created.get_data(as_text=True)
        assert "anjali@acme.com" not in listed.get_data(as_text=True)

    def test_sign_up_is_posted_to_slack(self, client, mock_service, notify):
        client.post("/domains/", json={"website_url": "acme.com", "contact_name": "Anjali", "mobile": "9876543210"})
        notify.assert_called_once_with("example.com", {"contact_name": "Anjali", "email": None, "mobile": "9876543210"})

    def test_failed_sign_up_is_not_posted(self, client, mock_service, notify):
        mock_service.add_domain.side_effect = DomainAlreadyExistsError("exists")
        assert client.post("/domains/", json={"website_url": "acme.com"}).status_code == 409
        notify.assert_not_called()


# ---------------------------------------------------------------------------
# POST /domains/ – validation errors (handled by marshmallow schema, no DB)
# ---------------------------------------------------------------------------


class TestCreateDomainValidation:
    def test_missing_website_url_returns_422(self, client, mock_service):
        response = client.post("/domains/", json={})
        assert response.status_code == 422

    def test_blank_website_url_returns_422(self, client, mock_service):
        response = client.post("/domains/", json={"website_url": "  "})
        assert response.status_code == 422

    def test_url_without_tld_returns_422(self, client, mock_service):
        response = client.post("/domains/", json={"website_url": "https://nodomain"})
        assert response.status_code == 422

    def test_no_json_body_returns_422(self, client, mock_service):
        response = client.post("/domains/", content_type="application/json", data="")
        assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# POST /domains/ – service-layer errors
# ---------------------------------------------------------------------------


class TestCreateDomainServiceErrors:
    def test_duplicate_domain_returns_409(self, client, mock_service):
        mock_service.add_domain.side_effect = DomainAlreadyExistsError("A domain for 'example.com' already exists.")
        response = client.post("/domains/", json={"website_url": "https://example.com"})
        assert response.status_code == 409

    def test_invalid_url_from_service_returns_422(self, client, mock_service):
        mock_service.add_domain.side_effect = InvalidWebsiteURLError("Bad URL.")
        response = client.post("/domains/", json={"website_url": "example.com"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /domains/
# ---------------------------------------------------------------------------


class TestListDomains:
    def test_returns_200(self, client, mock_service):
        response = client.get("/domains/")
        assert response.status_code == 200

    def test_returns_list(self, client, mock_service):
        response = client.get("/domains/")
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["address"] == "example.com"

    def test_empty_list_when_no_domains(self, client, mock_service):
        mock_service.list_domains.return_value = []
        response = client.get("/domains/")
        assert response.get_json() == []


# ---------------------------------------------------------------------------
# GET /domains/<int:domain_id>
# ---------------------------------------------------------------------------


class TestGetDomain:
    def test_returns_200_when_found(self, client, mock_service):
        response = client.get("/domains/1")
        assert response.status_code == 200

    def test_response_matches_domain(self, client, mock_service):
        response = client.get("/domains/1")
        data = response.get_json()
        assert data["id"] == 1
        assert data["address"] == "example.com"

    def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.get_domain.return_value = None
        response = client.get("/domains/999")
        assert response.status_code == 404
