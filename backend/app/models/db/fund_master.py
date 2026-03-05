"""
models/db/fund_master.py

Fund master data — one row per Morningstar share class.
Source: JHV_MASTER feed (weekly, Monday 6AM IST).
Primary identifier: mstar_id (Morningstar SecId).
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundMaster(Base):
    __tablename__ = "fund_master"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="Morningstar SecId"
    )
    fund_id: Mapped[Optional[str]] = mapped_column(
        String(20), comment="Morningstar FundId (portfolio-level)"
    )
    amc_id: Mapped[Optional[str]] = mapped_column(
        String(20), comment="ProviderCompanyID"
    )
    legal_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="LegalName"
    )
    fund_name: Mapped[Optional[str]] = mapped_column(
        String(200), comment="FundName (short)"
    )
    amc_name: Mapped[Optional[str]] = mapped_column(
        String(300), comment="ProviderCompanyName"
    )
    category_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="FundLevelCategoryName (SEBI category)"
    )
    broad_category: Mapped[Optional[str]] = mapped_column(
        String(200), comment="BroadCategoryGroup"
    )
    inception_date: Mapped[Optional[date]] = mapped_column(
        Date, comment="InceptionDate"
    )
    managers: Mapped[Optional[str]] = mapped_column(
        String(500), comment="Manager names"
    )
    manager_education: Mapped[Optional[str]] = mapped_column(
        String(500), comment="CollegeEducationDetail"
    )
    manager_birth_year: Mapped[Optional[int]] = mapped_column(
        comment="year_of_birth"
    )
    manager_certification: Mapped[Optional[str]] = mapped_column(
        String(200), comment="certification_name"
    )
    purchase_mode: Mapped[int] = mapped_column(
        default=1, comment="1=Regular, 2=Direct"
    )
    is_index_fund: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="IndexFund"
    )
    is_fund_of_funds: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="FundOfFunds"
    )
    is_insurance_product: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="AvailableInsuranceProduct"
    )
    is_etf: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="ExchangeTradedShare"
    )
    performance_ready: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="PerformanceReady"
    )
    isin: Mapped[Optional[str]] = mapped_column(
        String(12), comment="ISIN"
    )
    amfi_code: Mapped[Optional[str]] = mapped_column(
        String(10), comment="AMFICode"
    )
    sip_available: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="SIPAvailability"
    )
    net_expense_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), comment="InterimNetExpenseRatio"
    )
    gross_expense_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), comment="GrossExpenseRatio"
    )
    turnover_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), comment="InterimTurnoverRatio"
    )
    indian_risk_level: Mapped[Optional[str]] = mapped_column(
        String(50), comment="IndianRiskLevel"
    )
    benchmark_risk_level: Mapped[Optional[str]] = mapped_column(
        String(50), comment="india_benchmark_risk_level"
    )
    fund_risk_level: Mapped[Optional[str]] = mapped_column(
        String(50), comment="india_fund_risk_level"
    )
    primary_benchmark: Mapped[Optional[str]] = mapped_column(
        String(300), comment="PrimaryProspectusBenchmarks"
    )
    investment_strategy: Mapped[Optional[str]] = mapped_column(
        Text, comment="InvestmentStrategy"
    )
    investment_philosophy: Mapped[Optional[str]] = mapped_column(
        Text, comment="InvestmentPhilosophy"
    )
    previous_fund_name: Mapped[Optional[str]] = mapped_column(
        String(300), comment="PreviousFundName"
    )
    previous_name_end_date: Mapped[Optional[date]] = mapped_column(
        Date, comment="PreviousFundNameEndDate"
    )
    pricing_frequency: Mapped[Optional[str]] = mapped_column(
        String(20), default="Daily", comment="PricingFrequency"
    )
    legal_structure: Mapped[Optional[str]] = mapped_column(
        String(100), comment="LegalStructure"
    )
    domicile_id: Mapped[Optional[str]] = mapped_column(
        String(20), comment="DomicileId"
    )
    exchange_id: Mapped[Optional[str]] = mapped_column(
        String(20), comment="ExchangeId"
    )
    closed_to_investors: Mapped[Optional[date]] = mapped_column(
        Date, comment="ClosedToInvestors"
    )
    lock_in_period: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), comment="InitialLockupPeriod in years"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Not wound up or merged"
    )
    is_eligible: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Passes universe filter"
    )
    eligibility_reason: Mapped[Optional[str]] = mapped_column(
        String(200), comment="Why ineligible"
    )
    data_source: Mapped[str] = mapped_column(
        String(20), default="morningstar"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    __table_args__ = (
        Index("idx_fund_master_category", "category_name", postgresql_where=deleted_at.is_(None)),
        Index("idx_fund_master_amfi", "amfi_code", postgresql_where=amfi_code.isnot(None)),
        Index("idx_fund_master_isin", "isin", postgresql_where=isin.isnot(None)),
        Index("idx_fund_master_eligible", "is_eligible", "category_name", postgresql_where=deleted_at.is_(None)),
        Index("idx_fund_master_purchase_mode", "purchase_mode", "category_name"),
    )
