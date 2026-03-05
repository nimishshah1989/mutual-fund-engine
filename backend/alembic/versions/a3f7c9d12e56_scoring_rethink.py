"""scoring rethink — new tables and fund_recommendation

Revision ID: a3f7c9d12e56
Revises: b5cdfe28e774
Create Date: 2026-03-05 10:00:00.000000

Changes:
    1. Create signal_change_log table (audit trail for FM signal changes)
    2. Create fund_shortlist table (top N per category by QFS)
    3. Create fund_recommendation table (replaces fund_crs — no blended CRS)
    4. Drop fund_crs table (data migrated to fund_recommendation where possible)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3f7c9d12e56'
down_revision: Union[str, Sequence[str], None] = 'b5cdfe28e774'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create new scoring tables and drop fund_crs."""

    # 1. signal_change_log — audit trail for FM signal changes
    op.create_table(
        'signal_change_log',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('sector_name', sa.String(length=100), nullable=False, comment='GICS sector name'),
        sa.Column('old_signal', sa.String(length=20), nullable=True),
        sa.Column('old_confidence', sa.String(length=10), nullable=True),
        sa.Column('old_notes', sa.Text(), nullable=True),
        sa.Column('new_signal', sa.String(length=20), nullable=False),
        sa.Column('new_confidence', sa.String(length=10), nullable=False),
        sa.Column('new_notes', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(length=100), nullable=False, comment='Name of person who made the change'),
        sa.Column('change_reason', sa.String(length=500), nullable=True, comment='Optional reason for the change'),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. fund_shortlist — top N per category by QFS rank
    op.create_table(
        'fund_shortlist',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('mstar_id', sa.String(length=20), nullable=False),
        sa.Column('category_name', sa.String(length=200), nullable=False, comment='SEBI category'),
        sa.Column('qfs_score', sa.Numeric(precision=8, scale=4), nullable=False, comment='QFS at time of shortlisting'),
        sa.Column('qfs_rank', sa.Integer(), nullable=False, comment='Rank within category (1 = best)'),
        sa.Column('total_in_category', sa.Integer(), nullable=False, comment='Total eligible funds in category'),
        sa.Column('shortlist_reason', sa.String(length=200), nullable=False, server_default='top_n_by_qfs', comment='Why this fund was shortlisted'),
        sa.Column('computed_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mstar_id', 'computed_date', name='uq_shortlist_mstar_date'),
    )
    op.create_index('idx_shortlist_category_date', 'fund_shortlist', ['category_name', sa.text('computed_date DESC')])
    op.create_index('idx_shortlist_mstar_date', 'fund_shortlist', ['mstar_id', sa.text('computed_date DESC')])

    # 3. fund_recommendation — replaces fund_crs
    op.create_table(
        'fund_recommendation',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('mstar_id', sa.String(length=20), nullable=False),
        sa.Column('computed_date', sa.Date(), nullable=False),
        sa.Column('qfs', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('fsas', sa.Numeric(precision=8, scale=4), nullable=True, comment='Only populated for shortlisted funds'),
        sa.Column('qfs_rank', sa.Integer(), nullable=False, comment='Rank within category by QFS (1 = best)'),
        sa.Column('category_rank_pct', sa.Numeric(precision=5, scale=2), nullable=False, comment='Percentile rank within category (0-100, 100 = best)'),
        sa.Column('is_shortlisted', sa.Boolean(), nullable=False, server_default='false', comment='True if fund was in top N for its category'),
        sa.Column('tier', sa.String(length=10), nullable=False, comment='CORE / QUALITY / WATCH / CAUTION / EXIT — from QFS percentile'),
        sa.Column('action', sa.String(length=10), nullable=False, comment='BUY / SIP / HOLD_PLUS / HOLD / REDUCE / EXIT'),
        sa.Column('override_applied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('override_reason', sa.String(length=200), nullable=True),
        sa.Column('original_tier', sa.String(length=10), nullable=True),
        sa.Column('action_rationale', sa.Text(), nullable=True),
        sa.Column('qfs_id', sa.UUID(), nullable=True),
        sa.Column('fsas_id', sa.UUID(), nullable=True),
        sa.Column('engine_version', sa.String(length=20), nullable=False, server_default='2.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mstar_id', 'computed_date', name='uq_recommendation_mstar_date'),
    )
    op.create_index('idx_recommendation_mstar_date', 'fund_recommendation', ['mstar_id', sa.text('computed_date DESC')])
    op.create_index('idx_recommendation_tier', 'fund_recommendation', ['tier', sa.text('qfs DESC')])
    op.create_index('idx_recommendation_shortlisted', 'fund_recommendation', ['is_shortlisted', 'tier'])

    # 4. Drop the legacy fund_crs table
    op.drop_table('fund_crs')


def downgrade() -> None:
    """Reverse: recreate fund_crs, drop new tables."""

    # Recreate fund_crs
    op.create_table(
        'fund_crs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('mstar_id', sa.String(length=20), nullable=False),
        sa.Column('computed_date', sa.Date(), nullable=False),
        sa.Column('qfs', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('fsas', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('qfs_weight', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('fsas_weight', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('crs', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('tier', sa.String(length=10), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('override_applied', sa.Boolean()),
        sa.Column('override_reason', sa.String(length=200)),
        sa.Column('original_tier', sa.String(length=10)),
        sa.Column('action_rationale', sa.Text()),
        sa.Column('qfs_id', sa.UUID()),
        sa.Column('fsas_id', sa.UUID()),
        sa.Column('engine_version', sa.String(length=20)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mstar_id', 'computed_date', name='uq_crs_mstar_date'),
    )
    op.create_index('idx_crs_mstar_date', 'fund_crs', ['mstar_id', sa.text('computed_date DESC')])
    op.create_index('idx_crs_tier', 'fund_crs', ['tier', sa.text('crs DESC')])

    # Drop new tables
    op.drop_table('fund_recommendation')
    op.drop_table('fund_shortlist')
    op.drop_table('signal_change_log')
