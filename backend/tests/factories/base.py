"""
Base test factory module for CareerLens models.
Provides standardized build (in-memory) and async create (persisted) capabilities.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseFactory[T]:
    """Abstract base factory pattern providing build and create abstractions."""

    model_class: type[T]

    @classmethod
    def build(cls, **kwargs: Any) -> T:
        """Instantiate model in-memory with deterministic defaults and overrides."""
        defaults = cls.default_attributes()
        defaults.update(kwargs)
        return cls.model_class(**defaults)

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs: Any) -> T:
        """Instantiate model, persist to database via session, flush, and return instance."""
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        """Subclasses must define deterministic default attributes for model creation."""
        raise NotImplementedError("Subclasses must implement default_attributes")
