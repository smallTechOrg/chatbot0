"""The legacy Swagger UI moved from / (now the frontend) to /api/legacy-docs."""


def test_legacy_swagger_ui_is_at_api_legacy_docs(client):
    res = client.get("/api/legacy-docs/")
    assert res.status_code == 200
    assert "swagger" in res.get_data(as_text=True).lower()


def test_legacy_swagger_ui_still_reads_the_static_spec(client):
    assert client.get("/static/swagger.yaml").status_code == 200


def test_smorest_docs_are_unchanged(client):
    assert client.get("/api/openapi.json").status_code == 200
    assert client.get("/api/docs").status_code == 200


def test_root_is_no_longer_the_swagger_ui(client):
    res = client.get("/", headers={"Host": "zero-sales-agent-a23rjysfbq-uc.a.run.app"})
    assert "swagger" not in res.get_data(as_text=True).lower()
