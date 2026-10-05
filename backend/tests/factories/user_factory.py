"""
User factory for generating deterministic test User instances.
"""

import uuid
from typing import Any

from app.core.security import hash_password
from app.models.user import User
from tests.factories.base import BaseFactory


class UserFactory(BaseFactory[User]):
    """Factory for User entity."""

    model_class = User

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "email": f"test_user_{unique_suffix}@example.com",
            "hashed_password": hash_password("TestPassword123!"),
            "is_active": True,
            "is_admin": False,
        }
