"""
Authentication test helpers for CareerLens.
Provides utilities for creating test users, issuing test tokens, and crafting auth headers.
Exercises actual security utilities without bypassing cryptographic verification.
"""

import uuid
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User


async def create_test_user(
    session: AsyncSession,
    email: str | None = None,
    password: str = "TestPassword123!",
    is_active: bool = True,
    is_admin: bool = False,
) -> tuple[User, str]:
    """
    Create and persist a test user in the test database.
    Returns a tuple of (User instance, plain_password).
    """
    if email is None:
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"test_auth_{unique_suffix}@example.com"

    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        is_active=is_active,
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user, password


def create_auth_token(
    user_id: uuid.UUID | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed JWT access token for a test user."""
    return create_access_token(
        subject=str(user_id),
        expires_delta=expires_delta,
        extra_claims=extra_claims,
    )


def get_auth_headers(token: str) -> dict[str, str]:
    """Return HTTP Authorization headers with the given Bearer token."""
    return {"Authorization": f"Bearer {token}"}


def create_authenticated_headers(
    user_id: uuid.UUID | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Convenience helper: generates a signed token and returns Authorization headers."""
    token = create_auth_token(
        user_id=user_id, expires_delta=expires_delta, extra_claims=extra_claims
    )
    return get_auth_headers(token)


def login_test_user(client: TestClient, email: str, password: str) -> str:
    """Execute a POST /api/v1/auth/login request and return the access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token: str = response.json()["access_token"]
    return token
