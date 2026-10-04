"""
FastAPI dependency injection utilities for authentication and database sessions.
"""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id

# HTTPBearer security scheme for OpenAPI documentation and header extraction
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Authenticate request via Bearer JWT and retrieve corresponding User entity.

    Steps:
    1. Read Bearer token from Authorization header.
    2. Validate token structure, signature, and expiration.
    3. Extract user UUID subject claim.
    4. Fetch user from database.
    5. Verify user existence and active status.

    Raises:
    - HTTPException 401 Unauthorized for missing, invalid, expired tokens, or inactive users.
    """
    if auth is None or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if auth.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials.strip()

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject claim is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity in token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency verifying that the authenticated user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
