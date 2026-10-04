"""create_opportunity_models

Migration 0003: Creates opportunities and opportunity_skills tables
along with opportunity_source_enum and approved relational indexes.

Revision ID: b4f81c9a1d2e
Revises: 0a859f9b9f2c
Create Date: 2026-10-04 19:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4f81c9a1d2e"
down_revision: str | Sequence[str] | None = "0a859f9b9f2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types
opportunity_source_enum = postgresql.ENUM(
    "synthetic",
    "manual",
    "api",
    name="opportunity_source_enum",
    create_type=False,
)
education_level_enum = postgresql.ENUM(
    "none",
    "diploma",
    "bachelor",
    "master",
    "phd",
    "any",
    name="education_level_enum",
    create_type=False,
)
work_mode_enum = postgresql.ENUM(
    "remote",
    "hybrid",
    "onsite",
    "any",
    name="work_mode_enum",
    create_type=False,
)
employment_type_enum = postgresql.ENUM(
    "fulltime",
    "parttime",
    "internship",
    "contract",
    "any",
    name="employment_type_enum",
    create_type=False,
)


def upgrade() -> None:
    """Create opportunity_source_enum, opportunities table, and opportunity_skills table."""
    # 1. Create opportunity_source_enum
    opportunity_source_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create opportunities table
    op.create_table(
        "opportunities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_skills", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("min_experience_years", sa.Integer(), nullable=True),
        sa.Column("max_experience_years", sa.Integer(), nullable=True),
        sa.Column(
            "required_education_level",
            education_level_enum,
            server_default="any",
            nullable=False,
        ),
        sa.Column("location_city", sa.String(length=100), nullable=True),
        sa.Column("location_state", sa.String(length=100), nullable=True),
        sa.Column("location_country", sa.String(length=100), nullable=True),
        sa.Column(
            "work_mode",
            work_mode_enum,
            server_default="any",
            nullable=False,
        ),
        sa.Column("employment_type", employment_type_enum, nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=10), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("source", opportunity_source_enum, nullable=False),
        sa.Column("source_id", sa.String(length=512), nullable=True),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("job_embedding", Vector(384), nullable=True),
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create opportunities indexes
    op.create_index(
        "opportunities_source_dedup_idx",
        "opportunities",
        ["source", "source_id"],
        unique=True,
        postgresql_where=sa.text("source_id IS NOT NULL"),
    )
    op.create_index("opportunities_active_idx", "opportunities", ["is_active"])
    op.create_index(
        "opportunities_employment_type_idx",
        "opportunities",
        ["employment_type"],
    )
    op.create_index("opportunities_work_mode_idx", "opportunities", ["work_mode"])

    # 4. Create opportunity_skills table
    op.create_table(
        "opportunity_skills",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id",
            "skill_name",
            name="uq_opportunity_skills_opp_skill",
        ),
    )
    op.create_index(
        "opp_skills_opp_id_idx",
        "opportunity_skills",
        ["opportunity_id"],
    )
    op.create_index(
        "opp_skills_name_idx",
        "opportunity_skills",
        ["skill_name"],
    )


def downgrade() -> None:
    """Drop opportunity_skills, opportunities, and opportunity_source_enum."""
    op.drop_index("opp_skills_name_idx", table_name="opportunity_skills")
    op.drop_index("opp_skills_opp_id_idx", table_name="opportunity_skills")
    op.drop_table("opportunity_skills")

    op.drop_index("opportunities_work_mode_idx", table_name="opportunities")
    op.drop_index("opportunities_employment_type_idx", table_name="opportunities")
    op.drop_index("opportunities_active_idx", table_name="opportunities")
    op.drop_index("opportunities_source_dedup_idx", table_name="opportunities")
    op.drop_table("opportunities")

    opportunity_source_enum.drop(op.get_bind(), checkfirst=True)
