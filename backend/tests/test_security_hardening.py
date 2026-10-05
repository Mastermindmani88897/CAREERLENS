"""
Automated test suite for Phase 8 Security & Development Tooling Hardening.
Verifies security headers, CORS baseline, logging redaction, error masking,
secret management, and production configuration safeguards.
"""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import SensitiveDataFilter
from app.main import app

# =============================================================================
# 1. SECURITY RESPONSE HEADERS TESTS
# =============================================================================


def test_security_headers_present_on_root_endpoint(client: TestClient):
    """Verify standard security headers are present on all HTTP responses."""
    response = client.get("/")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in headers.get("permissions-policy", "")
    assert "geolocation=()" in headers.get("permissions-policy", "")


def test_security_headers_present_on_health_endpoint(client: TestClient):
    """Verify security headers are attached to API v1 responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"


# =============================================================================
# 2. CORS SECURITY BASELINE TESTS
# =============================================================================


def test_cors_preflight_allowed_origin(client: TestClient):
    """Verify CORS preflight request allows configured localhost origins."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }
    response = client.options("/api/v1/auth/login", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_disallows_unapproved_origin(client: TestClient):
    """Verify unapproved third-party origins do not receive CORS allow header."""
    headers = {
        "Origin": "http://malicious-site.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/v1/auth/login", headers=headers)
    # When origin is not permitted, CORS middleware does not set access-control-allow-origin
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_settings_comma_separated_parsing():
    """Verify ALLOWED_ORIGINS string is properly split into clean origins."""
    s = Settings(
        ENVIRONMENT="development",
        ALLOWED_ORIGINS="http://localhost:3000, http://127.0.0.1:3000/",
    )
    assert "http://localhost:3000" in s.CORS_ORIGINS
    assert "http://127.0.0.1:3000" in s.CORS_ORIGINS


# =============================================================================
# 3. LOGGING REDACTION & SECURITY FOUNDATION TESTS
# =============================================================================


def test_logging_filter_redacts_passwords():
    """Verify SensitiveDataFilter sanitizes plain passwords in log messages."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg=(
            "User authentication failed: password='SecretSuperPassword123!' "
            "for user test@example.com"
        ),
        args=(),
        exc_info=None,
    )
    filtr = SensitiveDataFilter()
    filtr.filter(record)

    assert "SecretSuperPassword123!" not in record.msg
    assert "password='***'" in record.msg


def test_logging_filter_redacts_bearer_tokens():
    """Verify SensitiveDataFilter sanitizes bearer tokens in log records."""
    token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature"
    )
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg=f"Incoming request with Authorization: Bearer {token}",
        args=(),
        exc_info=None,
    )
    filtr = SensitiveDataFilter()
    filtr.filter(record)

    assert token not in record.msg
    assert "[REDACTED" in record.msg


def test_logging_filter_redacts_database_urls():
    """Verify SensitiveDataFilter sanitizes database passwords in connection URIs."""
    uri = "postgresql+asyncpg://careerlens_user:SuperSecretDBPass99@localhost:5432/careerlens_db"
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg=f"Connecting to database at {uri}",
        args=(),
        exc_info=None,
    )
    filtr = SensitiveDataFilter()
    filtr.filter(record)

    assert "SuperSecretDBPass99" not in record.msg
    assert "careerlens_user:***@" in record.msg


def test_logging_filter_redacts_arguments():
    """Verify SensitiveDataFilter redacts sensitive arguments passed to logger."""
    filtr = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=40,
        msg="Login attempt for %s with token %s",
        args=(
            "user@example.com",
            "Bearer secret_token_xyz_12345",
        ),
        exc_info=None,
    )
    filtr.filter(record)

    assert "secret_token_xyz_12345" not in str(record.args)
    assert "[REDACTED_TOKEN]" in str(record.args)


# =============================================================================
# 4. UNHANDLED EXCEPTION MASKING TESTS
# =============================================================================


def test_unhandled_exception_masked_in_responses():
    """Verify unhandled application exceptions return generic 500 without leaking stack traces."""

    # Register a temporary route that raises an unhandled exception with sensitive text
    @app.get("/api/v1/test-error-leak", include_in_schema=False)
    def crash_endpoint():
        raise RuntimeError("Internal DB crashed: postgresql://admin:leaked_pass@internal:5432/db")

    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get("/api/v1/test-error-leak")
        assert response.status_code == 500
        data = response.json()
        assert data == {"detail": "Internal server error"}
        assert "leaked_pass" not in response.text
        assert "RuntimeError" not in response.text


# =============================================================================
# 5. PRODUCTION CONFIGURATION SAFEGUARDS TESTS
# =============================================================================


def test_production_settings_enforces_debug_false():
    """Verify Settings rejects DEBUG=True when ENVIRONMENT=production."""
    with pytest.raises(ValidationError, match="DEBUG must be set to False"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET_KEY="A" * 32,
            DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/prod",
            TEST_DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/test",
            CORS_ORIGINS=["https://app.careerlens.com"],
        )


def test_production_settings_enforces_strong_jwt_secret():
    """Verify Settings rejects empty or short JWT secrets in production."""
    with pytest.raises(ValidationError, match="JWT secret key must be at least 32 characters"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="too-short",
            DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/prod",
            TEST_DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/test",
            CORS_ORIGINS=["https://app.careerlens.com"],
        )


def test_production_settings_rejects_placeholder_credentials():
    """Verify Settings rejects default placeholder PASSWORD in production DATABASE_URL."""
    with pytest.raises(ValidationError, match="placeholder credentials"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="A" * 32,
            DATABASE_URL="postgresql+asyncpg://careerlens_user:PASSWORD@localhost:5432/careerlens_db",
            TEST_DATABASE_URL="postgresql+asyncpg://careerlens_user:PASSWORD@localhost:5432/careerlens_test",
            CORS_ORIGINS=["https://app.careerlens.com"],
        )


def test_production_settings_rejects_wildcard_cors():
    """Verify Settings rejects wildcard CORS origins in production."""
    with pytest.raises(ValidationError, match="Wildcard CORS origin is forbidden"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="A" * 32,
            DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/prod",
            TEST_DATABASE_URL="postgresql+asyncpg://user:realpassword@db:5432/test",
            CORS_ORIGINS=["*"],
        )


# =============================================================================
# 6. REPOSITORY HYGIENE & SECRET TRACKING TESTS
# =============================================================================


def test_env_example_contains_no_real_secrets():
    """Verify .env.example contains only placeholders and no real passwords or keys."""
    env_example_path = Path(__file__).resolve().parent.parent.parent / ".env.example"
    assert env_example_path.exists(), ".env.example must exist at repository root"

    content = env_example_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()

            # Ensure keys that require secrets have empty or placeholder values
            if key in (
                "APP_SECRET_KEY",
                "JWT_SECRET_KEY",
                "GEMINI_API_KEY",
                "OPENAI_API_KEY",
                "ADZUNA_APP_KEY",
            ):
                assert val == "", f".env.example has non-empty secret for {key}"
            if "PASSWORD" in val:
                assert val == "PASSWORD" or "PASSWORD@" in val, f"Suspicious password in {line}"
