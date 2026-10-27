"""create_autofill_sessions

Migration 0009: Implements Phase 27.2 Application Preparation Engine & Field-Mapping Foundation:
Creates autofill_sessions table to track application preparation state,
normalized candidate data payload, unmapped/missing fields, diagnostic telemetry,
and session expiration without storing passwords or raw credentials.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-27 14:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create autofill_sessions table, foreign keys, and indexes."""
    op.create_table(
        "autofill_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("resume_id", sa.UUID(), nullable=True),
        sa.Column("ats_provider", sa.String(length=50), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="preparation_pending",
            nullable=False,
        ),
        sa.Column(
            "normalized_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "missing_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "diagnostic_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name="fk_autofill_sessions_candidate_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_autofill_sessions_opportunity_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="fk_autofill_sessions_resume_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_autofill_sessions"),
    )

    op.create_index(
        "ix_autofill_sessions_candidate_profile_id",
        "autofill_sessions",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_autofill_sessions_opportunity_id",
        "autofill_sessions",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_autofill_sessions_status",
        "autofill_sessions",
        ["status"],
    )
    op.create_index(
        "ix_autofill_sessions_expires_at",
        "autofill_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_autofill_sessions_candidate_opp_status",
        "autofill_sessions",
        ["candidate_profile_id", "opportunity_id", "status"],
    )


def downgrade() -> None:
    """Drop indexes and autofill_sessions table cleanly."""
    op.drop_index("ix_autofill_sessions_candidate_opp_status", table_name="autofill_sessions")
    op.drop_index("ix_autofill_sessions_expires_at", table_name="autofill_sessions")
    op.drop_index("ix_autofill_sessions_status", table_name="autofill_sessions")
    op.drop_index("ix_autofill_sessions_opportunity_id", table_name="autofill_sessions")
    op.drop_index("ix_autofill_sessions_candidate_profile_id", table_name="autofill_sessions")
    op.drop_table("autofill_sessions")
