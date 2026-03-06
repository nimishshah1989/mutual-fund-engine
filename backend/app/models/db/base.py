"""
models/db/base.py

Imports all ORM models so Alembic can detect them for auto-generation.
Import this module in alembic/env.py to ensure all models are registered
with SQLAlchemy's metadata.
"""

from app.core.database import Base  # noqa: F401

# Import all models here so Alembic discovers them
from app.models.db.fund_master import FundMaster  # noqa: F401
from app.models.db.fund_performance import FundPerformance  # noqa: F401
from app.models.db.fund_risk_stats import FundRiskStats  # noqa: F401
from app.models.db.fund_ranks import FundRanks  # noqa: F401
from app.models.db.category_returns import CategoryReturns  # noqa: F401
from app.models.db.sector_signals import SectorSignal  # noqa: F401
from app.models.db.fund_sector_exposure import FundSectorExposure  # noqa: F401
from app.models.db.sector_mapping import SectorMapping  # noqa: F401
from app.models.db.fund_qfs import FundQFS  # noqa: F401
from app.models.db.fund_fsas import FundFSAS  # noqa: F401
from app.models.db.fund_crs import FundCRS  # noqa: F401 — legacy, kept for migration
from app.models.db.fund_recommendation import FundRecommendation  # noqa: F401
from app.models.db.fund_shortlist import FundShortlist  # noqa: F401
from app.models.db.signal_change_log import SignalChangeLog  # noqa: F401
from app.models.db.engine_config import EngineConfig  # noqa: F401
from app.models.db.alert_events import AlertEvent  # noqa: F401
from app.models.db.ingestion_log import IngestionLog  # noqa: F401
from app.models.db.score_audit_log import ScoreAuditLog  # noqa: F401
from app.models.db.benchmark_sector_weights import BenchmarkSectorWeight  # noqa: F401
from app.models.db.nav_history import NavHistory  # noqa: F401
from app.models.db.benchmark_history import BenchmarkHistory  # noqa: F401
from app.models.db.mf_pulse_snapshot import MFPulseSnapshot  # noqa: F401
