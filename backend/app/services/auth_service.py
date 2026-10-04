"""
Authentication and user service logic.
Handles user registration, authentication verification, and secure password handling.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Retrieve a user by primary key ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieve a user by case-insensitive email address."""
    normalized_email = email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, user_in: UserRegisterRequest) -> User:
    """
    Register a new user account.

    Validates:
    - Email uniqueness (case-insensitive)
    - Hashes password using bcrypt
    - Persists user to database

    Raises:
    - HTTPException 409 Conflict if email is already registered.
    """
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    hashed_pw = hash_password(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        is_active=True,
        is_admin=False,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def authenticate_user(db: AsyncSession, login_data: UserLoginRequest) -> User:
    """
    Authenticate a user by email and password.

    Returns:
    - Authenticated User entity on success.

    Raises:
    - HTTPException 401 Unauthorized for invalid email or password (constant error message).
    - HTTPException 403 Forbidden if user account is deactivated.
    """
    user = await get_user_by_email(db, login_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user
