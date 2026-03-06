"""add pulse tables — nav_history, benchmark_history, mf_pulse_snapshot

Revision ID: d4e5f6a7b8c9
Revises: c8d2f4a91b73
Create Date: 2026-03-06 18:00:00.000000

Changes:
    1. Create nav_history table (daily NAV for all funds, ~404K rows)
    2. Create benchmark_history table (daily Nifty 50 prices, ~756 rows)
    3. Create mf_pulse_snapshot table (ratio return snapshots per fund × period)
    4. Seed engine_config with pulse_signal_thresholds
"""

revision = "d4e5f6a7b8c9"
down_revision = "c8d2f4a91b73"
branch_labels = None
depends_on = None

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # 1. nav_history — daily NAV for all mutual funds
    op.create_table(
        "nav_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mstar_id", sa.String(20), nullable=False, comment="Morningstar SecId"),
        sa.Column("nav_date", sa.Date, nullable=False, comment="NAV publication date"),
        sa.Column("nav", sa.Numeric(14, 4), nullable=False, comment="Net Asset Value"),
        sa.Column("source", sa.String(30), server_default="amfi", comment="Data source"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("mstar_id", "nav_date", name="uq_nav_history_fund_date"),
    )
    op.create_index("idx_nav_history_fund_date_desc", "nav_history", ["mstar_id", sa.text("nav_date DESC")])
    op.create_index("idx_nav_history_date_desc", "nav_history", [sa.text("nav_date DESC")])

    # 2. benchmark_history — daily Nifty 50 closing prices
    op.create_table(
        "benchmark_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("benchmark_name", sa.String(50), nullable=False, server_default="NIFTY_50", comment="Benchmark identifier"),
        sa.Column("price_date", sa.Date, nullable=False, comment="Trading date"),
        sa.Column("close_price", sa.Numeric(14, 4), nullable=False, comment="Closing price"),
        sa.Column("source", sa.String(30), server_default="yfinance", comment="Data source"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("benchmark_name", "price_date", name="uq_benchmark_history_name_date"),
    )
    op.create_index("idx_benchmark_history_name_date_desc", "benchmark_history", ["benchmark_name", sa.text("price_date DESC")])

    # 3. mf_pulse_snapshot — ratio return snapshots
    op.create_table(
        "mf_pulse_snapshot",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mstar_id", sa.String(20), nullable=False, comment="Morningstar SecId"),
        sa.Column("snapshot_date", sa.Date, nullable=False, comment="Computation date"),
        sa.Column("period", sa.String(5), nullable=False, comment="1m, 3m, 6m, 1y, 2y, 3y"),
        sa.Column("nav_current", sa.Numeric(14, 4), comment="Fund NAV current"),
        sa.Column("nav_old", sa.Numeric(14, 4), comment="Fund NAV at period start"),
        sa.Column("fund_return", sa.Numeric(10, 4), comment="Fund return %"),
        sa.Column("nifty_current", sa.Numeric(14, 4), comment="Nifty close current"),
        sa.Column("nifty_old", sa.Numeric(14, 4), comment="Nifty close at period start"),
        sa.Column("nifty_return", sa.Numeric(10, 4), comment="Nifty return %"),
        sa.Column("ratio_current", sa.Numeric(14, 6), comment="fund/nifty ratio current"),
        sa.Column("ratio_old", sa.Numeric(14, 6), comment="fund/nifty ratio old"),
        sa.Column("ratio_return", sa.Numeric(10, 4), comment="Ratio return %"),
        sa.Column("signal", sa.String(15), comment="STRONG_OW/OVERWEIGHT/NEUTRAL/UNDERWEIGHT/STRONG_UW"),
        sa.Column("excess_return", sa.Numeric(10, 4), comment="fund_return - nifty_return"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("mstar_id", "snapshot_date", "period", name="uq_pulse_snapshot_fund_date_period"),
    )
    op.create_index("idx_pulse_snapshot_period_signal", "mf_pulse_snapshot", ["period", "signal"])
    op.create_index("idx_pulse_snapshot_fund_date", "mf_pulse_snapshot", ["mstar_id", sa.text("snapshot_date DESC")])

    # 4. Seed engine_config with pulse signal thresholds
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text(
            """
            INSERT INTO engine_config (id, config_key, config_value, description, created_at, updated_at)
            VALUES (
                :id, 'pulse_signal_thresholds',
                '{"strong_ow": 1.05, "strong_uw": 0.95}'::jsonb,
                'MF Pulse signal thresholds: ratio_period > strong_ow = STRONG_OW, < strong_uw = STRONG_UW',
                :now, :now
            )
            ON CONFLICT (config_key) DO NOTHING
            """
        ).bindparams(id=str(uuid.uuid4()), now=now)
    )


def downgrade() -> None:
    op.drop_table("mf_pulse_snapshot")
    op.drop_table("benchmark_history")
    op.drop_table("nav_history")
    op.execute(sa.text("DELETE FROM engine_config WHERE config_key = 'pulse_signal_thresholds'"))
