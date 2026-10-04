"""create_tracking_models

Migration 0004: Creates matches, applications, application_status_history,
and interview_prep tables along with eligibility_status_enum and
application_status_enum.

Revision ID: c7e23d4f5a6b
Revises: b4f81c9a1d2e
Create Date: 2026-10-04 19:36:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e23d4f5a6b"
down_revision: str | Sequence[str] | None = "b4f81c9a1d2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types
eligibility_status_enum = postgresql.ENUM(
    "eligible",
    "partial",
    "review_required",
    name="eligibility_status_enum",
    create_type=False,
)
application_status_enum = postgresql.ENUM(
    "saved",
    "applied",
    "oa",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    name="application_status_enum",
    create_type=False,
)


def upgrade() -> None:
    """Create tracking enums, matches, applications, status history, and interview prep tables."""
    bind = op.get_bind()

    # 1. Create enums
    eligibility_status_enum.create(bind, checkfirst=True)
    application_status_enum.create(bind, checkfirst=True)

    # 2. Create matches table
    op.create_table(
        "matches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("deterministic_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column(
            "eligibility_status",
            eligibility_status_enum,
            nullable=False,
        ),
        sa.Column("eligibility_warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation_text", sa.Text(), nullable=True),
        sa.Column("skill_gap", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_matches_candidate_opportunity",
        ),
    )
    op.create_index(
        "matches_profile_score_idx",
        "matches",
        ["candidate_profile_id", sa.text("final_score DESC")],
    )

    # 3. Create applications table
    op.create_table(
        "applications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            application_status_enum,
            server_default="saved",
            nullable=False,
        ),
        sa.Column("applied_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_applications_candidate_opportunity",
        ),
    )
    op.create_index(
        "applications_profile_status_idx",
        "applications",
        ["candidate_profile_id", "status"],
    )

    # 4. Create application_status_history table
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            application_status_enum,
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "status_history_app_id_idx",
        "application_status_history",
        ["application_id"],
    )

    # 5. Create interview_prep table
    op.create_table(
        "interview_prep",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation_method", sa.String(length=20), nullable=False),
        sa.Column(
            "generated_at",
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
        sa.Column("candidate_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_interview_prep_candidate_opportunity",
        ),
    )


def downgrade() -> None:
    """Drop tracking tables and tracking enums."""
    op.drop_table("interview_prep")

    op.drop_index("status_history_app_id_idx", table_name="application_status_history")
    op.drop_table("application_status_history")

    op.drop_index("applications_profile_status_idx", table_name="applications")
    op.drop_table("applications")

    op.drop_index("matches_profile_score_idx", table_name="matches")
    op.drop_table("matches")

    bind = op.get_bind()
    application_status_enum.drop(bind, checkfirst=True)
    eligibility_status_enum.drop(bind, checkfirst=True)
