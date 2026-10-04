"""
Authentication endpoints: registration, login, and current-user identity.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import authenticate_user, register_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new user account with email and password.",
)
async def register(
    user_in: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Register a new user, storing a hashed password and returning public user profile."""
    user = await register_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user with email and password, returning a signed JWT access token.",
)
async def login(
    login_data: UserLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate credentials and issue a signed Bearer JWT access token."""
    user = await authenticate_user(db, login_data)
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve the authenticated user's safe identity profile.",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return the profile of the currently authenticated user without sensitive credentials."""
    return UserResponse.model_validate(current_user)
