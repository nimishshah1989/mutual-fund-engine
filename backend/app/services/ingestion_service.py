"""
services/ingestion_service.py

Orchestrates Morningstar data ingestion: fetches all API endpoints for
each fund, calls mapper functions to translate and upsert into the database.
Tracks progress via IngestionLog entries.

One fund's failure never stops the batch — errors are captured and
reported in the final summary. Each fund's upserts run inside a
savepoint (nested transaction), so a failure rolls back only that fund.

Field mapping functions live in ingestion_mappers.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fund_master_repo import FundMasterRepository
from app.repositories.fund_performance_repo import FundPerformanceRepository
from app.repositories.fund_ranks_repo import FundRanksRepository
from app.repositories.fund_risk_stats_repo import FundRiskStatsRepository
from app.repositories.fund_sector_exposure_repo import FundSectorExposureRepository
from app.repositories.ingestion_log_repo import IngestionLogRepository
from app.services.ingestion_mappers import (
    upsert_fund_master,
    upsert_performance,
    upsert_ranks,
    upsert_risk_stats,
    upsert_sector_exposure,
)
from app.services.morningstar_fetcher import MorningstarFetcher

logger = structlog.get_logger(__name__)


class IngestionService:
    """Coordinates Morningstar API fetching and DB upserting for fund data."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.master_repo = FundMasterRepository(session)
        self.perf_repo = FundPerformanceRepository(session)
        self.risk_repo = FundRiskStatsRepository(session)
        self.ranks_repo = FundRanksRepository(session)
        self.sector_repo = FundSectorExposureRepository(session)
        self.log_repo = IngestionLogRepository(session)
        self.fetcher = MorningstarFetcher()

    async def ingest_fund(self, mstar_id: str) -> dict:
        """
        Fetch all Morningstar data for a single fund, parse, and upsert.
        All upserts run inside a savepoint so failures roll back only this fund.
        """
        result = {"mstar_id": mstar_id, "status": "success", "tables_updated": [], "error": None}

        try:
            api_data = await self.fetcher.fetch_all_for_fund(mstar_id)

            async with self.session.begin_nested():
                dp_data = api_data.get("DP", {})
                cyr_data = api_data.get("CYR", {})
                rm_data = api_data.get("RM", {})
                rmp_data = api_data.get("RMP", {})
                ttrr_data = api_data.get("TTRR", {})
                gssb_data = api_data.get("GSSB", {})

                if dp_data:
                    await upsert_fund_master(self.master_repo, mstar_id, dp_data)
                    result["tables_updated"].append("fund_master")

                if dp_data:
                    await upsert_performance(self.perf_repo, mstar_id, dp_data, cyr_data)
                    result["tables_updated"].append("fund_performance")

                if rm_data or rmp_data:
                    await upsert_risk_stats(self.risk_repo, mstar_id, rm_data, rmp_data)
                    result["tables_updated"].append("fund_risk_stats")

                if ttrr_data:
                    await upsert_ranks(self.ranks_repo, mstar_id, ttrr_data)
                    result["tables_updated"].append("fund_ranks")

                if gssb_data:
                    await upsert_sector_exposure(self.sector_repo, mstar_id, gssb_data)
                    result["tables_updated"].append("fund_sector_exposure")

            await self.session.flush()
            logger.info("ingestion_fund_complete", mstar_id=mstar_id, tables=result["tables_updated"])

        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            result["tables_updated"] = []
            logger.error("ingestion_fund_failed", mstar_id=mstar_id, error=str(exc))

        return result

    async def ingest_all_funds(self, mstar_ids: list[str]) -> dict:
        """
        Run ingestion for a batch of funds sequentially.
        Creates an IngestionLog entry tracking the overall run.
        """
        started_at = datetime.now(timezone.utc)

        log = await self.log_repo.create_log({
            "feed_name": "MORNINGSTAR_API", "file_name": None,
            "records_total": len(mstar_ids), "records_inserted": 0,
            "records_updated": 0, "records_failed": 0,
            "status": "RUNNING", "started_at": started_at,
        })
        log_id = log.id

        succeeded = 0
        failed = 0
        errors: list[dict[str, str]] = []

        async with self.fetcher:
            for index, mstar_id in enumerate(mstar_ids, 1):
                logger.info("ingestion_progress", current=index, total=len(mstar_ids), mstar_id=mstar_id)
                fund_result = await self.ingest_fund(mstar_id)

                if fund_result["status"] == "success":
                    succeeded += 1
                else:
                    failed += 1
                    errors.append({"mstar_id": mstar_id, "error": fund_result["error"] or "Unknown error"})

        status = "SUCCESS" if failed == 0 else ("FAILED" if succeeded == 0 else "PARTIAL")
        completed_at = datetime.now(timezone.utc)

        await self.log_repo.update_log(log_id, {
            "records_inserted": succeeded, "records_updated": succeeded,
            "records_failed": failed,
            "errors": {"fund_errors": errors} if errors else None,
            "status": status, "completed_at": completed_at,
        })

        summary = {
            "total": len(mstar_ids), "succeeded": succeeded, "failed": failed,
            "errors": errors, "log_id": str(log_id),
            "duration_seconds": (completed_at - started_at).total_seconds(),
        }
        logger.info("ingestion_batch_complete", **summary)
        return summary
