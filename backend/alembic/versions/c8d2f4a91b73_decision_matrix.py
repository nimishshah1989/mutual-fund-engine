"""decision matrix — benchmark weights table + recommendation matrix fields

Revision ID: c8d2f4a91b73
Revises: a3f7c9d12e56
Create Date: 2026-03-06 12:00:00.000000

Changes:
    1. Create benchmark_sector_weights table (NIFTY 50 sector allocations for FMS)
    2. Add matrix columns to fund_recommendation (fm_score, percentiles, matrix position)
    3. Add matrix and action indices to fund_recommendation
    4. Seed engine_config with benchmark_mstar_id and matrix_thresholds
"""

revision = "c8d2f4a91b73"
down_revision = "a3f7c9d12e56"
branch_labels = None
depends_on = None

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # 1. Create benchmark_sector_weights table
    op.create_table(
        "benchmark_sector_weights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("benchmark_name", sa.String(100), nullable=False),
        sa.Column("benchmark_mstar_id", sa.String(20), nullable=False),
        sa.Column("sector_name", sa.String(100), nullable=False),
        sa.Column("weight_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="morningstar_gssb"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "benchmark_mstar_id", "sector_name", "effective_date",
            name="uq_benchmark_sector_date",
        ),
    )
    op.create_index(
        "idx_benchmark_name_date",
        "benchmark_sector_weights",
        ["benchmark_name", sa.text("effective_date DESC")],
    )
    op.create_index(
        "idx_benchmark_mstar_id",
        "benchmark_sector_weights",
        ["benchmark_mstar_id"],
    )

    # 2. Add matrix columns to fund_recommendation
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "fm_score", sa.Numeric(8, 4), nullable=True,
            comment="FM Alignment Score (0-100) — alias for fsas in matrix context",
        ),
    )
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "fm_score_percentile", sa.Numeric(5, 2), nullable=True,
            comment="FMS percentile rank within category (0-100, 100 = best)",
        ),
    )
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "qfs_percentile", sa.Numeric(5, 2), nullable=True,
            comment="QFS percentile rank within category (alias of category_rank_pct)",
        ),
    )
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "matrix_row", sa.String(10), nullable=True,
            comment="QFS band: HIGH / MID / LOW",
        ),
    )
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "matrix_col", sa.String(10), nullable=True,
            comment="FMS band: HIGH / MID / LOW",
        ),
    )
    op.add_column(
        "fund_recommendation",
        sa.Column(
            "matrix_position", sa.String(20), nullable=True,
            comment="Combined: HIGH_HIGH, HIGH_MID, etc.",
        ),
    )

    # 3. Add matrix indices
    op.create_index(
        "idx_recommendation_matrix",
        "fund_recommendation",
        ["matrix_position", "computed_date"],
    )
    op.create_index(
        "idx_recommendation_action",
        "fund_recommendation",
        ["action", sa.text("qfs DESC")],
    )

    # 4. Seed engine_config with benchmark and matrix config
    engine_config = sa.table(
        "engine_config",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("config_key", sa.String),
        sa.column("config_value", JSONB),
        sa.column("description", sa.Text),
        sa.column("updated_by", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)

    op.bulk_insert(engine_config, [
        {
            "id": uuid.uuid4(),
            "config_key": "benchmark_mstar_id",
            "config_value": {"value": "F00000VBPN"},
            "description": (
                "Morningstar ID for NIFTY 50 benchmark index fund/ETF. "
                "Used in FMS active weight calculation. "
                "Default: UTI Nifty 50 Index Fund Direct Growth (F00000VBPN). "
                "Change to any NIFTY 50 tracking fund."
            ),
            "updated_by": "migration",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid.uuid4(),
            "config_key": "benchmark_name",
            "config_value": {"value": "NIFTY 50"},
            "description": "Human-readable name for the benchmark used in FMS.",
            "updated_by": "migration",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid.uuid4(),
            "config_key": "matrix_thresholds",
            "config_value": {"low_upper": 33.33, "high_lower": 66.67},
            "description": (
                "Percentile thresholds for 3x3 decision matrix tercile bands. "
                "low_upper = boundary between LOW and MID. "
                "high_lower = boundary between MID and HIGH."
            ),
            "updated_by": "migration",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid.uuid4(),
            "config_key": "benchmark_stale_days",
            "config_value": {"value": 45},
            "description": (
                "Max age in days for cached benchmark weights before auto-refresh. "
                "Pipeline checks this before computing FMS."
            ),
            "updated_by": "migration",
            "created_at": now,
            "updated_at": now,
        },
    ])


def downgrade() -> None:
    # Remove seeded config
    op.execute(
        "DELETE FROM engine_config WHERE config_key IN "
        "('benchmark_mstar_id', 'benchmark_name', 'matrix_thresholds', 'benchmark_stale_days')"
    )

    # Remove matrix indices
    op.drop_index("idx_recommendation_action", table_name="fund_recommendation")
    op.drop_index("idx_recommendation_matrix", table_name="fund_recommendation")

    # Remove matrix columns
    op.drop_column("fund_recommendation", "matrix_position")
    op.drop_column("fund_recommendation", "matrix_col")
    op.drop_column("fund_recommendation", "matrix_row")
    op.drop_column("fund_recommendation", "qfs_percentile")
    op.drop_column("fund_recommendation", "fm_score_percentile")
    op.drop_column("fund_recommendation", "fm_score")

    # Drop benchmark table
    op.drop_index("idx_benchmark_mstar_id", table_name="benchmark_sector_weights")
    op.drop_index("idx_benchmark_name_date", table_name="benchmark_sector_weights")
    op.drop_table("benchmark_sector_weights")
