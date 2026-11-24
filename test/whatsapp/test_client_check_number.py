from whatsapp import client


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, ""

    def json(self):
        return self._body


def test_check_number_asks_for_the_name_status_fields_and_parses_them(monkeypatch):
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(kwargs)
        return FakeResponse(
            200, {"display_phone_number": "+1 555 0100", "name_status": "APPROVED", "status": "CONNECTED"}
        )

    monkeypatch.setattr(client.requests, "request", fake_request)
    result = client.check_number("123456", "tok")
    assert seen["params"]["fields"] == (
        "display_phone_number,verified_name,name_status,new_name_status,status,quality_rating,code_verification_status"
    )
    assert result.ok and result.data["name_status"] == "APPROVED" and result.data["status"] == "CONNECTED"
    assert result.data.get("verified_name") is None  # a missing field is harmless


def test_a_graph_error_keeps_its_code_in_the_message(monkeypatch):
    body = {"error": {"code": 131037, "message": "display name needs approval"}}
    monkeypatch.setattr(client.requests, "request", lambda *a, **k: FakeResponse(400, body))
    result = client.send_text("1", "tok", "2", "hi")
    assert not result.ok and "131037" in result.error
