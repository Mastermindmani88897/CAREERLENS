"""
Authentication schemas for request validation and safe responses.
Strictly excludes sensitive fields such as hashed_password.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="User password (8-72 characters, must not exceed 72 bytes)",
    )

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase and trimmed."""
        return v.strip().lower()

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_bytes(cls, v: str) -> str:
        """Ensure password is not blank and does not exceed 72 UTF-8 bytes."""
        if not v or not v.strip():
            raise ValueError("Password must not be empty or whitespace-only.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes.")
        return v


class UserLoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase and trimmed."""
        return v.strip().lower()


class Token(BaseModel):
    """Authentication token response schema."""

    access_token: str = Field(..., description="Signed JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")


class UserResponse(BaseModel):
    """Safe user profile response strictly omitting sensitive data (hashed_password)."""

    id: uuid.UUID
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
