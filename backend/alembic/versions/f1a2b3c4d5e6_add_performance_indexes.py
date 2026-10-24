"""add_performance_indexes

Migration 0007: Adds composite and vector indexes for Phase 23 Performance Optimization:
1. opportunities_active_created_idx: on opportunities (is_active, created_at DESC)
2. applications_profile_updated_idx: on applications (candidate_profile_id, updated_at DESC)
3. opportunities_job_embedding_hnsw_idx:
   on opportunities USING hnsw (job_embedding vector_cosine_ops)

Revision ID: f1a2b3c4d5e6
Revises: e9f42a8b3c1d
Create Date: 2026-10-24 15:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e9f42a8b3c1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create performance indexes for opportunities and applications."""
    # 1. Composite index for active opportunity discovery ordered by recency
    op.create_index(
        "opportunities_active_created_idx",
        "opportunities",
        ["is_active", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # 2. Composite index for candidate application dashboard pipeline ordered by recency
    op.create_index(
        "applications_profile_updated_idx",
        "applications",
        ["candidate_profile_id", sa.text("updated_at DESC")],
        if_not_exists=True,
    )

    # 3. HNSW vector index for pgvector cosine distance recommendations
    op.create_index(
        "opportunities_job_embedding_hnsw_idx",
        "opportunities",
        ["job_embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"job_embedding": "vector_cosine_ops"},
        if_not_exists=True,
    )


def downgrade() -> None:
    """Safely drop the performance indexes."""
    op.drop_index(
        "opportunities_job_embedding_hnsw_idx",
        table_name="opportunities",
        postgresql_using="hnsw",
        if_exists=True,
    )
    op.drop_index(
        "applications_profile_updated_idx",
        table_name="applications",
        if_exists=True,
    )
    op.drop_index(
        "opportunities_active_created_idx",
        table_name="opportunities",
        if_exists=True,
    )
