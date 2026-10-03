from fastapi.testclient import TestClient


def test_health_check_v1(client: TestClient):
    """Verify GET /api/v1/health returns 200 and expected machine-readable payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CareerLens"
    assert "version" in data


def test_health_check_root_alias(client: TestClient):
    """Verify GET /health alias returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_endpoint(client: TestClient):
    """Verify GET / returns 200 with service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "CareerLens"
    assert data["health"] == "/api/v1/health"


def test_openapi_spec(client: TestClient):
    """Verify OpenAPI JSON specification is available."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "CareerLens"


def test_health_requires_no_auth(client: TestClient):
    """Verify health endpoint does not require any credentials, tokens, or auth headers."""
    response = client.get("/api/v1/health", headers={})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
