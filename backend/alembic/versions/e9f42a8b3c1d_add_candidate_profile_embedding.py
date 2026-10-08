"""add_candidate_profile_embedding

Migration 0006: Adds profile_embedding Vector(384) and embedding_updated_at
to candidate_profiles table for Phase 16 Local Embedding Foundation.

Revision ID: e9f42a8b3c1d
Revises: d8e31a7f4b9c
Create Date: 2026-10-08 12:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f42a8b3c1d"
down_revision: str | Sequence[str] | None = "d8e31a7f4b9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add profile_embedding Vector(384) and embedding_updated_at to candidate_profiles."""
    op.add_column(
        "candidate_profiles",
        sa.Column("profile_embedding", Vector(384), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Safely drop profile_embedding and embedding_updated_at from candidate_profiles."""
    op.drop_column("candidate_profiles", "embedding_updated_at")
    op.drop_column("candidate_profiles", "profile_embedding")
