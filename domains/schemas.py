"""
Marshmallow schemas for the Domains resource.

These schemas serve three purposes simultaneously:
  1. Input validation  – marshmallow enforces types, required fields, and custom rules.
  2. Output serialisation – flask-smorest calls Schema.dump() on every response.
  3. OpenAPI documentation – flask-smorest reflects the schema into the generated spec.
"""
import re

from marshmallow import EXCLUDE, Schema, ValidationError, fields, pre_load, validate, validates


class CreateDomainRequest(Schema):
    """Request body for POST /domains/."""

    class Meta:
        # Silently drop any fields the client sends that are not declared here
        # (e.g. legacy callers still sending 'key' or 'parent_id').
        unknown = EXCLUDE

    website_url = fields.Str(
        required=True,
        metadata={
            "description": (
                "Full or partial website address to register. "
                "The canonical hostname is extracted automatically – scheme, path, "
                "query-string and a leading 'www.' are all stripped. "
                "The domain key is auto-generated from the hostname."
            ),
            "example": "https://www.example.com/about",
        },
    )

    # Who is signing up, from the chatbot0 sign-up form. All optional, stored
    # on the domain and never returned by the API (GET /domains/ is public).
    contact_name = fields.Str(
        load_default=None,
        validate=validate.Length(max=200),
        metadata={"description": "Name of the person signing up.", "example": "Anjali"},
    )
    email = fields.Email(
        load_default=None,
        validate=validate.Length(max=254),
        metadata={"description": "Contact email.", "example": "anjali@example.com"},
    )
    mobile = fields.Str(
        load_default=None,
        validate=validate.Regexp(r"^\+?[0-9 ()-]{6,20}$", error="Not a valid phone number."),
        metadata={"description": "Contact phone number.", "example": "+91 98765 43210"},
    )

    @pre_load
    def blank_contact_is_none(self, data, **kwargs):
        """The form sends "" for a field left empty. Treat it as not given."""
        if isinstance(data, dict):
            data = dict(data)
            for name in ("contact_name", "email", "mobile"):
                value = data.get(name)
                if isinstance(value, str):
                    data[name] = value.strip() or None
        return data

    @validates("website_url")
    def validate_website_url(self, value: str) -> None:
        """Reject blank or obviously non-URL values early."""
        stripped = value.strip()
        if not stripped:
            raise ValidationError("website_url must not be blank.")
        # A naive guard – detailed parsing happens in the service layer.
        candidate = re.sub(r"^https?://", "", stripped, flags=re.IGNORECASE)
        host_part = candidate.split("/")[0].split("?")[0]
        if "." not in host_part:
            raise ValidationError(
                "website_url does not appear to contain a valid hostname."
            )


class DomainResponse(Schema):
    """Serialisation schema for a Domain record."""

    id = fields.Int(
        dump_only=True,
        metadata={"description": "Auto-assigned primary key.", "example": 42},
    )
    key = fields.Str(
        dump_only=True,
        metadata={"description": "Domain key identifier.", "example": "EXAMPLE_COM"},
    )
    address = fields.Str(
        dump_only=True,
        metadata={
            "description": "Canonical hostname extracted from the submitted URL.",
            "example": "example.com",
        },
    )
    parent_id = fields.Int(
        dump_only=True,
        allow_none=True,
        metadata={"description": "ID of the parent domain; null for root domains.", "example": None},
    )
    created_at = fields.DateTime(
        dump_only=True,
        metadata={"description": "ISO-8601 timestamp of when the domain was created."},
    )
