"""add_opportunity_type

Migration 0005: Adds opportunity_type_enum and opportunity_type column to
opportunities table with server default 'job' and index opportunities_type_idx.

Revision ID: d8e31a7f4b9c
Revises: c7e23d4f5a6b
Create Date: 2026-10-08 11:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e31a7f4b9c"
down_revision: str | Sequence[str] | None = "c7e23d4f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum type
opportunity_type_enum = postgresql.ENUM(
    "job",
    "internship",
    "hackathon",
    name="opportunity_type_enum",
    create_type=False,
)


def upgrade() -> None:
    """Add opportunity_type_enum, opportunity_type column, and index."""
    bind = op.get_bind()

    # 1. Create opportunity_type_enum
    opportunity_type_enum.create(bind, checkfirst=True)

    # 2. Add opportunity_type column with server default 'job'
    op.add_column(
        "opportunities",
        sa.Column(
            "opportunity_type",
            opportunity_type_enum,
            server_default="job",
            nullable=False,
        ),
    )

    # 3. Create index on opportunity_type
    op.create_index(
        "opportunities_type_idx",
        "opportunities",
        ["opportunity_type"],
    )


def downgrade() -> None:
    """Drop opportunities_type_idx, opportunity_type column, and opportunity_type_enum."""
    op.drop_index("opportunities_type_idx", table_name="opportunities")
    op.drop_column("opportunities", "opportunity_type")

    bind = op.get_bind()
    opportunity_type_enum.drop(bind, checkfirst=True)
