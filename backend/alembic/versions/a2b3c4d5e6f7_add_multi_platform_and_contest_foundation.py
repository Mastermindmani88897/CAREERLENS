"""add_multi_platform_and_contest_foundation

Migration 0008: Implements Phase 26.2 Database Migration & Ingestion Foundation:
1. Adds 'coding_contest' to opportunity_type_enum.
2. Adds multi-platform sources to opportunity_source_enum:
   'remotive', 'arbeitnow', 'codeforces', 'greenhouse', 'lever',
   'adzuna', 'usajobs', 'remoteok', 'devpost'.
3. Adds event & synchronization metadata columns to opportunities table:
   event_start_time, event_end_time, registration_deadline, duration_seconds,
   prize_summary, first_seen_at, last_seen_at, external_metadata.
4. Adds relational indexes on opportunities(last_seen_at) and opportunities(event_start_time).
5. Creates connector_sync_status table for operational telemetry without storing secrets.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-25 14:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_OPPORTUNITY_SOURCES = [
    "remotive",
    "arbeitnow",
    "codeforces",
    "greenhouse",
    "lever",
    "adzuna",
    "usajobs",
    "remoteok",
    "devpost",
]


def upgrade() -> None:
    """Safely apply backward-compatible Phase 26.2 schema additions."""
    # 1. Extend opportunity_type_enum with coding_contest
    op.execute("ALTER TYPE opportunity_type_enum ADD VALUE IF NOT EXISTS 'coding_contest';")

    # 2. Extend opportunity_source_enum with multi-platform sources
    for source_val in NEW_OPPORTUNITY_SOURCES:
        op.execute(f"ALTER TYPE opportunity_source_enum ADD VALUE IF NOT EXISTS '{source_val}';")

    # 3. Add event and sync metadata columns to opportunities
    op.add_column(
        "opportunities",
        sa.Column("event_start_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("event_end_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("registration_deadline", sa.Date(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("prize_summary", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "external_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    # 4. Create indexes on event and freshness columns
    op.create_index(
        "opportunities_last_seen_idx",
        "opportunities",
        ["last_seen_at"],
        if_not_exists=True,
    )
    op.create_index(
        "opportunities_event_start_idx",
        "opportunities",
        ["event_start_time"],
        if_not_exists=True,
    )

    # 5. Create connector_sync_status table for operational telemetry
    op.create_table(
        "connector_sync_status",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "refresh_interval_minutes",
            sa.Integer(),
            server_default=sa.text("60"),
            nullable=False,
        ),
        sa.Column("last_sync_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_fetched", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_skipped", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("last_error_summary", sa.Text(), nullable=True),
        sa.Column(
            "sync_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
    )
    op.create_index(
        "connector_sync_source_idx",
        "connector_sync_status",
        ["source"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Downgrade schema modifications safely."""
    # 1. Drop connector_sync_status table and its index
    op.drop_index(
        "connector_sync_source_idx",
        table_name="connector_sync_status",
        if_exists=True,
    )
    op.drop_table("connector_sync_status")

    # 2. Drop opportunity event/freshness indexes
    op.drop_index(
        "opportunities_event_start_idx",
        table_name="opportunities",
        if_exists=True,
    )
    op.drop_index(
        "opportunities_last_seen_idx",
        table_name="opportunities",
        if_exists=True,
    )

    # 3. Drop opportunity columns
    op.drop_column("opportunities", "external_metadata")
    op.drop_column("opportunities", "last_seen_at")
    op.drop_column("opportunities", "first_seen_at")
    op.drop_column("opportunities", "prize_summary")
    op.drop_column("opportunities", "duration_seconds")
    op.drop_column("opportunities", "registration_deadline")
    op.drop_column("opportunities", "event_end_time")
    op.drop_column("opportunities", "event_start_time")

    # Note: PostgreSQL does not provide an 'ALTER TYPE ... DROP VALUE' statement.
    # The enum values added ('coding_contest' in opportunity_type_enum and the platform
    # sources in opportunity_source_enum) remain harmlessly in the enum definition.
