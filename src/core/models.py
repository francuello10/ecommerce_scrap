"""
SQLAlchemy 2.0 ORM Models — Competitive Intelligence Engine
============================================================

All tables are Directus-friendly:
  - snake_case names
  - BIGINT PKs (auto-increment)
  - Explicit FKs
  - created_at / updated_at on most tables

Tables are grouped by functional area:
  0. SaaS / Multi-Tenant
  1. Configuration
  2. Raw / Operational
  3. Tech Fingerprinting
  4. Catalog (Phase 2 ready)
  5. Results / Processed
  6. Delivery / Briefs
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# ══════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════

class BillingStatus(str, PyEnum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"


class MonitoringFrequency(str, PyEnum):
    LOW = "LOW"        # 1x/day
    MEDIUM = "MEDIUM"  # 3x/day
    HIGH = "HIGH"      # 6x/day


class CompetitorStatus(str, PyEnum):
    PENDING_ONBOARDING = "PENDING_ONBOARDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class Priority(str, PyEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PageType(str, PyEnum):
    HOMEPAGE = "HOMEPAGE"
    PROMO_PAGE = "PROMO_PAGE"
    FINANCING_PAGE = "FINANCING_PAGE"
    SHIPPING_PAGE = "SHIPPING_PAGE"
    CATEGORY = "CATEGORY"
    OTHER = "OTHER"


class DiscoveryMethod(str, PyEnum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class NewsletterStatus(str, PyEnum):
    PENDING_AUTO = "PENDING_AUTO"
    PENDING_OPTIN = "PENDING_OPTIN"
    PENDING_MANUAL = "PENDING_MANUAL"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


class SnapshotStatus(str, PyEnum):
    PENDING_EXTRACTION = "PENDING_EXTRACTION"
    EXTRACTED = "EXTRACTED"
    ERROR = "ERROR"


class SignalSource(str, PyEnum):
    WEB = "WEB"
    EMAIL = "EMAIL"


class SignalType(str, PyEnum):
    PROMO = "PROMO"
    FINANCIACION = "FINANCIACION"
    ENVIO = "ENVIO"
    URGENCIA = "URGENCIA"
    CTA = "CTA"
    BRAND_HIGHLIGHT = "BRAND_HIGHLIGHT"


class EventType(str, PyEnum):
    NEW_PROMO = "NEW_PROMO"
    REMOVED_PROMO = "REMOVED_PROMO"
    CHANGED_HERO = "CHANGED_HERO"
    CHANGED_FINANCING = "CHANGED_FINANCING"
    FLASH_SALE = "FLASH_SALE"


class Severity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UpsellEventType(str, PyEnum):
    HISTORICAL_DATA_AVAILABLE = "HISTORICAL_DATA_AVAILABLE"
    TIER_UPGRADE_SUGGESTED = "TIER_UPGRADE_SUGGESTED"


class UpsellStatus(str, PyEnum):
    PENDING = "PENDING"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class TechChangeType(str, PyEnum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"


class JobStatus(str, PyEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED_PARTIAL = "FAILED_PARTIAL"
    FAILED = "FAILED"


class BriefStatus(str, PyEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class CompetitorLevel(str, PyEnum):
    """Reach level for the Competitor Suggestion Engine."""
    GLOBAL_BENCHMARK = "GLOBAL_BENCHMARK"   # World-class / international
    REGIONAL_RIVAL = "REGIONAL_RIVAL"       # LATAM / regional
    DIRECT_RIVAL = "DIRECT_RIVAL"           # National / local


# ══════════════════════════════════════════════════════════════════════
# 0. SAAS / MULTI-TENANT
# ══════════════════════════════════════════════════════════════════════

class SubscriptionTier(Base):
    """
    Defines subscription plans with feature flags.
    Managed by admins directly in Directus.
    """
    __tablename__ = "subscription_tier"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # BASIC, PROFESSIONAL, ENTERPRISE

    # Limits
    max_competitors: Mapped[int] = mapped_column(Integer, default=3)
    max_monitored_pages: Mapped[int] = mapped_column(Integer, default=5)
    monitoring_frequency: Mapped[MonitoringFrequency] = mapped_column(
        Enum(MonitoringFrequency), default=MonitoringFrequency.LOW
    )
    history_retention_days: Mapped[int] = mapped_column(Integer, default=30)  # -1 = unlimited

    # Feature Flags
    can_track_newsletters: Mapped[bool] = mapped_column(Boolean, default=False)
    can_track_tech_stack: Mapped[bool] = mapped_column(Boolean, default=False)
    can_track_catalog: Mapped[bool] = mapped_column(Boolean, default=False)
    can_use_realtime_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    can_access_api: Mapped[bool] = mapped_column(Boolean, default=False)
    can_generate_weekly_brief: Mapped[bool] = mapped_column(Boolean, default=False)
    can_use_baseline_comparison: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_competitor_suggestions: Mapped[bool] = mapped_column(Boolean, default=True)  # Suggestion Engine

    # Pricing
    price_monthly_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    clients: Mapped[list["Client"]] = relationship("Client", back_populates="tier")


class Client(Base):
    """
    A SaaS customer (agency or brand).
    """
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tier_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_tier.id"), nullable=True)
    industry_id: Mapped[int | None] = mapped_column(ForeignKey("industry.id"), nullable=True)
    billing_status: Mapped[BillingStatus] = mapped_column(
        Enum(BillingStatus), default=BillingStatus.TRIAL
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tier: Mapped["SubscriptionTier | None"] = relationship("SubscriptionTier", back_populates="clients")
    industry: Mapped["Industry | None"] = relationship("Industry", back_populates="clients")
    competitor_links: Mapped[list["ClientCompetitor"]] = relationship("ClientCompetitor", back_populates="client")
    upsell_events: Mapped[list["UpsellEvent"]] = relationship("UpsellEvent", back_populates="client")


class ClientCompetitor(Base):
    """
    N:N join between Client and Competitor.
    is_baseline = True means "this is MY company" → enables comparison reports.
    history_access_start_date = controls access to historical data (upsell key).
    """
    __tablename__ = "client_competitor"
    __table_args__ = (UniqueConstraint("client_id", "competitor_id", name="uq_client_competitor"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM)
    history_access_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="competitor_links")
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="client_links")


class UpsellEvent(Base):
    """
    Tracks upsell opportunities when a client adds an already-known competitor.
    """
    __tablename__ = "upsell_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    event_type: Mapped[UpsellEventType] = mapped_column(Enum(UpsellEventType))
    data_available_since: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    snapshots_count: Mapped[int] = mapped_column(Integer, default=0)
    signals_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[UpsellStatus] = mapped_column(Enum(UpsellStatus), default=UpsellStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="upsell_events")
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="upsell_events")


# ══════════════════════════════════════════════════════════════════════
# 0B. SUGGESTION ENGINE (Competitor Discovery by Industry)
# ══════════════════════════════════════════════════════════════════════

class Industry(Base):
    """
    Business vertical / industry. Used by the Suggestion Engine
    to recommend competitors during client onboarding.
    Examples: DEPORTES, ELECTRONICA, MODA, HOGAR, etc.
    Managed in Directus — clients can request new industries.
    """
    __tablename__ = "industry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 🏀, 📱, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    clients: Mapped[list["Client"]] = relationship("Client", back_populates="industry")
    competitor_industries: Mapped[list["CompetitorIndustry"]] = relationship(
        "CompetitorIndustry", back_populates="industry"
    )


class CompetitorIndustry(Base):
    """
    N:N junction between Competitor and Industry, with a CompetitorLevel.
    One competitor can appear in multiple industries at different levels.

    Levels:
    - GLOBAL_BENCHMARK: World-class / international (ej: Nike, Amazon)
    - REGIONAL_RIVAL: LATAM / regional (ej: Dafiti, MercadoLibre)
    - DIRECT_RIVAL: Nacional / local (ej: Newsport, Dexter)
    """
    __tablename__ = "competitor_industry"
    __table_args__ = (
        UniqueConstraint("competitor_id", "industry_id", name="uq_competitor_industry"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industry.id"), nullable=False)
    level: Mapped[CompetitorLevel] = mapped_column(
        Enum(CompetitorLevel), default=CompetitorLevel.DIRECT_RIVAL
    )
    is_suggested: Mapped[bool] = mapped_column(Boolean, default=True)  # False = manual add
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="industry_links")
    industry: Mapped["Industry"] = relationship("Industry", back_populates="competitor_industries")


# ══════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION (Editable in Directus)
# ══════════════════════════════════════════════════════════════════════

class Competitor(Base):
    """
    Global competitor registry. Not owned by any single client.
    Clients link to competitors via ClientCompetitor.
    """
    __tablename__ = "competitor"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    vertical: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[CompetitorStatus] = mapped_column(
        Enum(CompetitorStatus), default=CompetitorStatus.PENDING_ONBOARDING
    )
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    client_links: Mapped[list["ClientCompetitor"]] = relationship("ClientCompetitor", back_populates="competitor")
    industry_links: Mapped[list["CompetitorIndustry"]] = relationship("CompetitorIndustry", back_populates="competitor")
    monitored_pages: Mapped[list["MonitoredPage"]] = relationship("MonitoredPage", back_populates="competitor")
    newsletter_subscriptions: Mapped[list["NewsletterSubscription"]] = relationship(
        "NewsletterSubscription", back_populates="competitor"
    )
    tech_profile: Mapped["CompetitorTechProfile | None"] = relationship(
        "CompetitorTechProfile", back_populates="competitor", uselist=False
    )
    tech_history: Mapped[list["TechProfileHistory"]] = relationship(
        "TechProfileHistory", back_populates="competitor"
    )
    tech_changes: Mapped[list["TechProfileChange"]] = relationship(
        "TechProfileChange", back_populates="competitor"
    )
    change_events: Mapped[list["ChangeEvent"]] = relationship("ChangeEvent", back_populates="competitor")
    upsell_events: Mapped[list["UpsellEvent"]] = relationship("UpsellEvent", back_populates="competitor")


class MonitoredPage(Base):
    """
    A specific URL to be scraped for a competitor.
    Auto-discovered (header/footer scan) or manually added.
    """
    __tablename__ = "monitored_page"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_type: Mapped[PageType] = mapped_column(Enum(PageType), default=PageType.OTHER)
    discovery_method: Mapped[DiscoveryMethod] = mapped_column(Enum(DiscoveryMethod), default=DiscoveryMethod.AUTO)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="monitored_pages")
    snapshots: Mapped[list["PageSnapshot"]] = relationship("PageSnapshot", back_populates="page")


class NewsletterAccount(Base):
    """
    Email inbox used to subscribe to competitor newsletters.
    """
    __tablename__ = "newsletter_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email_address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), default="imap.gmail.com")
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    mailbox_config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    subscriptions: Mapped[list["NewsletterSubscription"]] = relationship(
        "NewsletterSubscription", back_populates="account"
    )


class NewsletterSubscription(Base):
    """
    Tracks the status of subscribing a competitor's newsletter
    to our monitoring inbox.
    """
    __tablename__ = "newsletter_subscription"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    newsletter_account_id: Mapped[int] = mapped_column(ForeignKey("newsletter_account.id"), nullable=False)
    status: Mapped[NewsletterStatus] = mapped_column(Enum(NewsletterStatus), default=NewsletterStatus.PENDING_AUTO)
    auto_sub_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="newsletter_subscriptions")
    account: Mapped["NewsletterAccount"] = relationship("NewsletterAccount", back_populates="subscriptions")


class SignalTaxonomy(Base):
    """
    Classification system for signals extracted from web and email.
    """
    __tablename__ = "signal_taxonomy"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[SignalType] = mapped_column(Enum(SignalType))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ══════════════════════════════════════════════════════════════════════
# 2. RAW / OPERATIONAL (Read-only / Audit in Directus)
# ══════════════════════════════════════════════════════════════════════

class CrawlRun(Base):
    """
    A single execution of the scraping cron job.
    """
    __tablename__ = "crawl_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.RUNNING)

    # Relationships
    snapshots: Mapped[list["PageSnapshot"]] = relationship("PageSnapshot", back_populates="run")


class PageSnapshot(Base):
    """
    A raw HTML capture of a monitored page at a point in time.
    Append-only. Signal extraction happens after this is saved.
    """
    __tablename__ = "page_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    monitored_page_id: Mapped[int] = mapped_column(ForeignKey("monitored_page.id"), nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_run.id"), nullable=True)
    raw_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    screenshot_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[SnapshotStatus] = mapped_column(Enum(SnapshotStatus), default=SnapshotStatus.PENDING_EXTRACTION)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    page: Mapped["MonitoredPage"] = relationship("MonitoredPage", back_populates="snapshots")
    run: Mapped["CrawlRun | None"] = relationship("CrawlRun", back_populates="snapshots")
    signals: Mapped[list["DetectedSignal"]] = relationship("DetectedSignal", back_populates="snapshot")


class NewsletterMessage(Base):
    """
    A received email from a competitor's newsletter.
    """
    __tablename__ = "newsletter_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    newsletter_account_id: Mapped[int] = mapped_column(ForeignKey("newsletter_account.id"), nullable=False)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_optin_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)


class JobExecutionLog(Base):
    """
    Audit log for background job executions.
    """
    __tablename__ = "job_execution_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.RUNNING)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


# ══════════════════════════════════════════════════════════════════════
# 3. TECH FINGERPRINTING
# ══════════════════════════════════════════════════════════════════════

class CompetitorTechProfile(Base):
    """
    Current (active) technology stack for a competitor. 1:1 with Competitor.
    is_valid = False signals that the extractor failed and needs recalibration.
    """
    __tablename__ = "competitor_tech_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), unique=True, nullable=False)
    ecommerce_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analytics_tools: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    marketing_automation: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tag_managers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    payment_gateways: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    live_chat: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    cdn_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    js_frameworks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    full_fingerprint_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fingerprinted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="tech_profile")


class TechProfileHistory(Base):
    """
    Append-only log of tech stack snapshots. Inserted only when a change is detected.
    """
    __tablename__ = "tech_profile_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    ecommerce_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_fingerprint_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="tech_history")


class TechProfileChange(Base):
    """
    A specific tool/technology that was added, removed, or changed.
    """
    __tablename__ = "tech_profile_change"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    change_type: Mapped[TechChangeType] = mapped_column(Enum(TechChangeType))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="tech_changes")


# ══════════════════════════════════════════════════════════════════════
# 4. CATALOG — Phase 2 Ready (tables exist, populated later)
# ══════════════════════════════════════════════════════════════════════

class Product(Base):
    """
    A product SKU from a competitor's catalog (Phase 2).
    """
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    category_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    category_tree: Mapped[list | None] = mapped_column(JSONB, nullable=True) # Full hierarchy
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list | None] = mapped_column(JSONB, nullable=True) # Multiple URLs
    financing_options: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # 12 cuotas, etc.
    discovered_from: Mapped[str | None] = mapped_column(String(2048), nullable=True) # URL where found (grid/list)
    rating_avg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    badges: Mapped[list | None] = mapped_column(JSONB, nullable=True) # ["NUEVO", "BEST SELLER"]
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Generic catch-all
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    variants: Mapped[list["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    price_history: Mapped[list["PriceHistory"]] = relationship("PriceHistory", back_populates="product")


class ProductVariant(Base):
    """
    A specific variation of a product (e.g., Size: 42, Color: Red).
    """
    __tablename__ = "product_variant"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True) # e.g. "42", "XL", "Rojo"
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    list_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")


class PriceHistory(Base):
    """
    Price snapshots for a product over time (Phase 2).
    """
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("page_snapshot.id"), nullable=True)
    list_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="ARS")
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="price_history")


# ══════════════════════════════════════════════════════════════════════
# 5. RESULTS / PROCESSED
# ══════════════════════════════════════════════════════════════════════

class DetectedSignal(Base):
    """
    A commercial signal extracted from a web snapshot or email.
    """
    __tablename__ = "detected_signal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_type: Mapped[SignalSource] = mapped_column(Enum(SignalSource))
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("page_snapshot.id"), nullable=True)
    taxonomy_id: Mapped[int | None] = mapped_column(ForeignKey("signal_taxonomy.id"), nullable=True)
    raw_text_found: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    snapshot: Mapped["PageSnapshot | None"] = relationship("PageSnapshot", back_populates="signals")


class ChangeEvent(Base):
    """
    A meaningful change detected between two consecutive snapshots.
    HIGH/CRITICAL severity triggers real-time Slack alerts.
    """
    __tablename__ = "change_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitor.id"), nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType))
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.MEDIUM)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="change_events")


# ══════════════════════════════════════════════════════════════════════
# 6. DELIVERY / BRIEFS
# ══════════════════════════════════════════════════════════════════════

class DailyBrief(Base):
    """
    Generated daily briefing summarizing all changes from the past 24h.
    """
    __tablename__ = "daily_brief"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    brief_date: Mapped[datetime] = mapped_column(Date, nullable=False, unique=True)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[BriefStatus] = mapped_column(Enum(BriefStatus), default=BriefStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeeklyBrief(Base):
    """
    Generated weekly briefing aggregating daily insights and trends.
    """
    __tablename__ = "weekly_brief"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIGeneratorSettings(Base):
    """
    Configuration for the Briefing AI Engine.
    Allows editing the system prompt and model choice from Directus.
    """
    __tablename__ = "ai_generator_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # e.g. "DEFAULT_DAILY_BRIEF"
    model_name: Mapped[str] = mapped_column(String(100), default="gemini-1.5-pro")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
