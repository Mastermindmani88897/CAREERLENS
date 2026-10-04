"""
Automated test suite for Phase 5 Authentication Module.
Validates password hashing, JWT generation, registration, login,
current-user dependency, security constraints, and error handling.
"""

import uuid
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    PasswordPolicyError,
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.db.session import async_session_factory
from app.models.user import User

# =============================================================================
# 1. PASSWORD POLICY & HASHING UNIT TESTS
# =============================================================================


def test_password_policy_validation():
    """Verify password policy enforces length, blank checks, and UTF-8 byte limits."""
    # Valid password
    validate_password_policy("StrongPassword123!")

    # Empty / whitespace
    with pytest.raises(PasswordPolicyError, match="empty or blank"):
        validate_password_policy("")
    with pytest.raises(PasswordPolicyError, match="empty or blank"):
        validate_password_policy("   ")

    # Below 8 characters
    with pytest.raises(PasswordPolicyError, match="at least 8 characters"):
        validate_password_policy("short")

    # Exceeding 72 bytes (bcrypt restriction)
    oversized = "A" * 73
    with pytest.raises(PasswordPolicyError, match="maximum allowable length"):
        validate_password_policy(oversized)


def test_password_hashing_and_verification():
    """Verify bcrypt password hashing generates valid salted hashes and verifies cleanly."""
    password = "CorrectHorseBatteryStaple99!"
    hashed = hash_password(password)

    # Hash properties
    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Verification
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False
    assert verify_password(password, "malformed_hash") is False

    # Two hashes of the same password must use distinct salts
    hashed_2 = hash_password(password)
    assert hashed != hashed_2
    assert verify_password(password, hashed_2) is True


# =============================================================================
# 2. JWT TOKEN UNIT TESTS
# =============================================================================


def test_jwt_create_and_decode_token():
    """Verify JWT access token creation and decoding with proper claims."""
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token():
    """Verify that expired JWT access tokens are rejected."""
    user_id = uuid.uuid4()
    token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_jwt_invalid_signature():
    """Verify that tokens signed with an incorrect secret are rejected."""
    user_id = uuid.uuid4()
    fake_token = jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": 9999999999, "iat": 1000},
        "wrong-secret-key-that-does-not-match-settings",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(fake_token)


def test_jwt_invalid_token_type():
    """Verify that non-access token types are rejected."""
    secret = settings.effective_jwt_secret
    invalid_type_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "refresh", "exp": 9999999999, "iat": 1000},
        secret,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError, match="Invalid token type"):
        decode_access_token(invalid_type_token)


def test_jwt_secret_loaded_from_environment():
    """Verify JWT secret is loaded from configuration and is not an empty string."""
    assert settings.effective_jwt_secret != ""
    assert len(settings.effective_jwt_secret) >= 32


# =============================================================================
# 3. REGISTRATION API ENDPOINT TESTS (POST /api/v1/auth/register)
# =============================================================================


def test_registration_success(client: TestClient):
    """Test successful user registration creates user and returns safe response without password."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"test_user_{unique_suffix}@example.com"
    password = "SecurePassword123!"

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == email
    assert data["is_active"] is True
    assert data["is_admin"] is False
    assert "created_at" in data
    assert "updated_at" in data

    # STRICT: Sensitive fields MUST NOT be present
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_registration_password_stored_as_hash():
    """Verify that user password is saved to the database as bcrypt hash, never plaintext."""
    unique_suffix = uuid.uuid4().hex[:8]

    email = f"hash_check_{unique_suffix}@example.com"
    plain_password = "MySuperSecretPassword99!"

    # Use direct test client via synchronous context
    with TestClient(client_app()) as c:
        resp = c.post(
            "/api/v1/auth/register",
            json={"email": email, "password": plain_password},
        )
        assert resp.status_code == 201
        user_id = uuid.UUID(resp.json()["id"])

    # Query database directly to verify stored hash
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()

        assert user.hashed_password != plain_password
        assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")
        assert verify_password(plain_password, user.hashed_password) is True


def test_registration_duplicate_email(client: TestClient):
    """Verify that registering with an existing email returns 409 Conflict."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"duplicate_{unique_suffix}@example.com"
    password = "Password1234!"

    # First registration
    resp1 = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp1.status_code == 201

    # Second registration with exact same email
    resp2 = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_registration_case_insensitive_duplicate_email(client: TestClient):
    """Verify duplicate email rejection is case-insensitive."""
    unique_suffix = uuid.uuid4().hex[:8]
    email_lower = f"case_{unique_suffix}@example.com"
    email_upper = f"CASE_{unique_suffix}@EXAMPLE.COM"
    password = "Password1234!"

    resp1 = client.post(
        "/api/v1/auth/register",
        json={"email": email_lower, "password": password},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        "/api/v1/auth/register",
        json={"email": email_upper, "password": password},
    )
    assert resp2.status_code == 409


def test_registration_invalid_inputs(client: TestClient):
    """Verify validation errors on invalid registration inputs."""
    # Invalid email format
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!"},
    )
    assert resp.status_code == 422

    # Password too short (< 8 chars)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "123"},
    )
    assert resp.status_code == 422

    # Empty password
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": ""},
    )
    assert resp.status_code == 422


# =============================================================================
# 4. LOGIN API ENDPOINT TESTS (POST /api/v1/auth/login)
# =============================================================================


def test_login_success(client: TestClient):
    """Test successful login returns valid JWT token and token_type bearer."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"login_user_{unique_suffix}@example.com"
    password = "ValidPassword123!"

    # Register first
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Decode and verify the token maps to the registered user
    payload = decode_access_token(token_data["access_token"])
    assert payload["sub"] == user_id


def test_login_case_insensitive_email(client: TestClient):
    """Test login allows mixed/uppercase email matching."""
    unique_suffix = uuid.uuid4().hex[:8]
    email_registered = f"case_login_{unique_suffix}@example.com"
    email_login = f"CASE_LOGIN_{unique_suffix}@EXAMPLE.COM"
    password = "ValidPassword123!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email_registered, "password": password},
    )
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email_login, "password": password},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_login_invalid_password(client: TestClient):
    """Verify login with incorrect password returns 401 without specific enumeration details."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"wrong_pwd_{unique_suffix}@example.com"
    password = "CorrectPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword123!"},
    )
    assert login_resp.status_code == 401
    assert "Invalid email or password" in login_resp.json()["detail"]


def test_login_unknown_email(client: TestClient):
    """Verify login with non-existent email returns 401 with generic error."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_email_123456@example.com", "password": "SomePassword123!"},
    )
    assert login_resp.status_code == 401
    assert "Invalid email or password" in login_resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user_rejected():
    """Verify inactive user cannot log in and receives 403 Forbidden."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"inactive_{unique_suffix}@example.com"
    password = "InactivePassword123!"

    async with async_session_factory() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=False,
            is_admin=False,
        )
        session.add(user)
        await session.commit()

    with TestClient(client_app()) as c:
        resp = c.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"].lower()


# =============================================================================
# 5. PROTECTED CURRENT USER ENDPOINT TESTS (GET /api/v1/auth/me)
# =============================================================================


def test_get_current_user_me_success(client: TestClient):
    """Verify GET /api/v1/auth/me returns user profile with valid Bearer token."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"me_test_{unique_suffix}@example.com"
    password = "ValidPassword123!"

    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_resp.json()["access_token"]

    # Call /auth/me
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["id"] == user_id
    assert user_data["email"] == email
    assert user_data["is_active"] is True
    assert "hashed_password" not in user_data


def test_get_current_user_missing_token(client: TestClient):
    """Verify GET /api/v1/auth/me without Authorization header returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_get_current_user_invalid_token(client: TestClient):
    """Verify GET /api/v1/auth/me with garbage token returns 401."""
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert resp.status_code == 401


def test_get_current_user_expired_token(client: TestClient):
    """Verify GET /api/v1/auth/me with expired token returns 401."""
    expired_token = create_access_token(
        subject=uuid.uuid4(),
        expires_delta=timedelta(seconds=-1),
    )
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_get_current_user_invalid_scheme(client: TestClient):
    """Verify GET /api/v1/auth/me with non-Bearer scheme returns 401."""
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert resp.status_code == 401


def test_get_current_user_nonexistent_user_id(client: TestClient):
    """Verify GET /api/v1/auth/me with valid token for deleted/nonexistent user returns 401."""
    random_uuid = uuid.uuid4()
    token = create_access_token(subject=random_uuid)
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "User not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_inactive_account():
    """Verify GET /api/v1/auth/me with active token but deactivated user returns 401."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"deactivated_{unique_suffix}@example.com"
    password = "DeactivatedPassword123!"

    async with async_session_factory() as session:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=False,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    token = create_access_token(subject=user_id)

    with TestClient(client_app()) as c:
        resp = c.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "inactive" in resp.json()["detail"].lower()


def test_openapi_contains_auth_endpoints(client: TestClient):
    """Verify OpenAPI specification documents all Phase 5 auth endpoints."""
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    paths = spec.get("paths", {})

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths

    # Verify POST /auth/register schemas
    register_post = paths["/api/v1/auth/register"]["post"]
    assert "201" in register_post["responses"]

    # Verify POST /auth/login schemas
    login_post = paths["/api/v1/auth/login"]["post"]
    assert "200" in login_post["responses"]

    # Verify GET /auth/me
    me_get = paths["/api/v1/auth/me"]["get"]
    assert "200" in me_get["responses"]


# Helper function to get FastAPI app instance
def client_app():
    from app.main import app

    return app
