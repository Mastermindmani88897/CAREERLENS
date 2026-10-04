"""
Core security utilities: password hashing (bcrypt) and JWT access tokens.
Strictly adheres to Phase 5 Authentication Module boundaries.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# Password policy constants
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # Bcrypt maximum effective password length


class PasswordPolicyError(ValueError):
    """Raised when a password violates policy constraints."""

    pass


def validate_password_policy(password: str) -> None:
    """
    Validate that password meets minimum security criteria.

    Policy:
    - Must not be empty or whitespace-only
    - Must be at least 8 characters
    - Must not exceed 72 bytes in UTF-8 encoding (to prevent silent bcrypt truncation)
    """
    if not password or not password.strip():
        raise PasswordPolicyError("Password must not be empty or blank.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )

    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise PasswordPolicyError(
            f"Password exceeds maximum allowable length of {MAX_PASSWORD_BYTES} bytes."
        )


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with random salt generation.

    Validates password against policy before hashing.
    """
    validate_password_policy(password)
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Returns False if inputs are malformed or do not match.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        plain_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception:
        return False


def _get_jwt_secret() -> str:
    """Retrieve the configured JWT secret key or raise RuntimeError."""
    secret = settings.effective_jwt_secret
    if not secret:
        raise RuntimeError("JWT secret key is not configured. Set JWT_SECRET_KEY in environment.")
    return secret


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token containing subject identity and expiration.

    Claims:
    - sub: string representation of user identity / UUID
    - exp: expiration timestamp (UTC)
    - iat: issued-at timestamp (UTC)
    - type: "access"
    """
    secret = _get_jwt_secret()
    now = datetime.now(UTC)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        secret,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode, verify signature, and validate claims of a JWT access token.

    Raises:
    - jwt.ExpiredSignatureError: Token has expired
    - jwt.InvalidTokenError: Token is malformed, invalid signature, or wrong claims
    """
    secret = _get_jwt_secret()
    payload = jwt.decode(
        token,
        secret,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )

    token_type = payload.get("type")
    if token_type and token_type != "access":
        raise jwt.InvalidTokenError(f"Invalid token type: {token_type}")

    return payload
