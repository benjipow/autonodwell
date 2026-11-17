"""Database schema. Any change here must ship with an Alembic migration
(`alembic revision --autogenerate -m "..."`) — never edit the database by hand.

Conventions
- Money is stored as integer cents (`*_cents`) to avoid floating-point errors.
- Percentages/rates are stored as basis points (`*_bps`, 1% = 100 bps).
- Primary keys for customer-facing records are UUIDs so they can be exposed in URLs
  and created offline by a future native app.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


# --------------------------------------------------------------------------- people
class Role(str, enum.Enum):
    customer = "customer"
    sales = "sales"
    admin = "admin"


class User(Timestamped, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), default=Role.customer)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    designs: Mapped[list["Design"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


# --------------------------------------------------------------------------- catalog
class HomeModel(Timestamped, Base):
    """A base home template (Model 1/2/3). Editable by admins, versioned by updated_at."""

    __tablename__ = "home_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    tagline: Mapped[str | None] = mapped_column(String(240))
    sq_ft: Mapped[int] = mapped_column(Integer)
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[float] = mapped_column()
    base_price_cents: Mapped[int] = mapped_column(Integer)
    floor_plan_key: Mapped[str] = mapped_column(String(60))  # which plan drawing / asset to show
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class SelectionType(str, enum.Enum):
    single = "single"
    multi = "multi"


class PricingMode(str, enum.Enum):
    flat = "flat"  # fixed amount
    per_sq_ft = "per_sq_ft"  # amount × home square footage


class OptionCategory(Timestamped, Base):
    __tablename__ = "option_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    selection_type: Mapped[SelectionType] = mapped_column(_enum(SelectionType, "selection_type"))
    display: Mapped[str] = mapped_column(String(20), default="chips")  # chips | swatches | cards
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    options: Mapped[list["Option"]] = relationship(
        back_populates="category", order_by="Option.sort_order"
    )


class Option(Timestamped, Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("option_categories.id"))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    pricing_mode: Mapped[PricingMode] = mapped_column(_enum(PricingMode, "pricing_mode"))
    price_cents: Mapped[int] = mapped_column(Integer, default=0)  # flat amount, or per sq ft
    swatch_hex: Mapped[str | None] = mapped_column(String(9))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[OptionCategory] = relationship(back_populates="options")


class AssumptionSet(Timestamped, Base):
    """Financing and soft-cost assumptions used by the estimator. Exactly one is active.
    Every saved estimate records which set produced it, so numbers can be audited later."""

    __tablename__ = "assumption_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    interest_rate_bps: Mapped[int] = mapped_column(Integer)
    term_years: Mapped[int] = mapped_column(Integer)
    down_payment_bps: Mapped[int] = mapped_column(Integer)
    closing_cost_bps: Mapped[int] = mapped_column(Integer)
    soft_cost_bps: Mapped[int] = mapped_column(Integer)  # design, engineering, permits mgmt
    contingency_bps: Mapped[int] = mapped_column(Integer)
    delivery_cents: Mapped[int] = mapped_column(Integer)
    two_story_premium_cents: Mapped[int] = mapped_column(Integer, default=8_500_000)
    notes: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- location data
class Market(Timestamped, Base):
    """Regional cost data. MVP rows are labeled samples (is_sample=True). The planned
    Autonodwell location database (MLS, zoning, permits by ZIP) will populate/replace these."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    state: Mapped[str | None] = mapped_column(String(2))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # fallback for unknown ZIPs
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
    construction_cost_index_bps: Mapped[int] = mapped_column(Integer, default=10000)  # 100% = national
    site_install_cents: Mapped[int] = mapped_column(Integer)
    land_allocation_cents: Mapped[int] = mapped_column(Integer)
    permit_fees_cents: Mapped[int] = mapped_column(Integer)
    permit_weeks_low: Mapped[int] = mapped_column(Integer)
    permit_weeks_high: Mapped[int] = mapped_column(Integer)
    property_tax_bps: Mapped[int] = mapped_column(Integer)  # annual, of total cost
    insurance_annual_cents: Mapped[int] = mapped_column(Integer)
    data_source: Mapped[str] = mapped_column(String(300), default="Placeholder sample data")
    notes: Mapped[str | None] = mapped_column(Text)

    zip_prefixes: Mapped[list["ZipPrefix"]] = relationship(back_populates="market")


class ZipPrefix(Base):
    """Maps the first 3 digits of a ZIP to a market. Will be superseded by a full ZIP table."""

    __tablename__ = "zip_prefixes"

    prefix: Mapped[str] = mapped_column(String(3), primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"))
    market: Mapped[Market] = relationship(back_populates="zip_prefixes")


class ZipLandValue(Base):
    """Quarter-acre land price and construction cost factor, by 3-digit ZIP area."""

    __tablename__ = "zip_land_values"

    prefix: Mapped[str] = mapped_column(String(3), primary_key=True)
    state: Mapped[str] = mapped_column(String(2))
    land_cents: Mapped[int] = mapped_column(Integer)
    basis: Mapped[str] = mapped_column(String(10))  # "zip" or "state"
    source: Mapped[str] = mapped_column(String(200))
    construction_index_bps: Mapped[int | None] = mapped_column(Integer)  # 10000 = national average
    factor_basis: Mapped[str | None] = mapped_column(String(10))  # "zip", "state", or "national"
    area_type: Mapped[str | None] = mapped_column(String(20))


class PathStage(Timestamped, Base):
    """The 'path home' timeline shown in step 3 (Design → Site → Financing → ...)."""

    __tablename__ = "path_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    who: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(Text)
    weeks_low: Mapped[int] = mapped_column(Integer)
    weeks_high: Mapped[int] = mapped_column(Integer)
    cost_key: Mapped[str | None] = mapped_column(String(40))  # links to an estimate line
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# --------------------------------------------------------------------------- customer work
class DesignStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"  # sent to a consultant (a lead exists)


class Design(Timestamped, Base):
    __tablename__ = "designs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="My home")
    home_model_id: Mapped[int] = mapped_column(ForeignKey("home_models.id"))
    monthly_budget_cents: Mapped[int | None] = mapped_column(Integer)
    zip_code: Mapped[str | None] = mapped_column(String(10))
    # Starting point, answered before a home is chosen.
    land_status: Mapped[str | None] = mapped_column(String(20))  # own_lot | looking_at_lot | need_land
    budget_mode: Mapped[str | None] = mapped_column(String(20))  # total | monthly | need_help
    total_budget_cents: Mapped[int | None] = mapped_column(Integer)
    cash_available_cents: Mapped[int | None] = mapped_column(Integer)
    site_address: Mapped[str | None] = mapped_column(String(200))
    lot_price_cents: Mapped[int | None] = mapped_column(Integer)
    style: Mapped[str | None] = mapped_column(String(20))  # pop | mcm | craftsman
    stories: Mapped[int | None] = mapped_column(Integer)  # 1, or 2 for Mid-Century Modern
    selections: Mapped[list[int]] = mapped_column(JsonType, default=list)  # option ids
    status: Mapped[DesignStatus] = mapped_column(_enum(DesignStatus, "design_status"), default=DesignStatus.draft)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    # Frozen copy of the estimate at the moment the customer submitted it to sales.
    submitted_estimate: Mapped[dict | None] = mapped_column(JsonType)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="designs")
    home_model: Mapped[HomeModel] = relationship()


# --------------------------------------------------------------------------- sales
class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    consultation_scheduled = "consultation_scheduled"
    qualified = "qualified"
    financing = "financing"
    won = "won"
    lost = "lost"


class Lead(Timestamped, Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    design_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))
    status: Mapped[LeadStatus] = mapped_column(_enum(LeadStatus, "lead_status"), default=LeadStatus.new, index=True)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(60), default="web_app")

    # Contact snapshot (customer may later edit their profile; the lead keeps what they sent)
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    preferred_contact: Mapped[str | None] = mapped_column(String(20))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    message: Mapped[str | None] = mapped_column(Text)
    estimate_total_cents: Mapped[int | None] = mapped_column(Integer)
    monthly_budget_cents: Mapped[int | None] = mapped_column(Integer)

    contact_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text: Mapped[str | None] = mapped_column(Text)  # exact wording the customer agreed to

    crm_provider: Mapped[str | None] = mapped_column(String(30))
    crm_contact_id: Mapped[str | None] = mapped_column(String(120))
    crm_opportunity_id: Mapped[str | None] = mapped_column(String(120))
    crm_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crm_sync_error: Mapped[str | None] = mapped_column(Text)

    design: Mapped[Design | None] = relationship(foreign_keys=[design_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_id])
    activities: Mapped[list["LeadActivity"]] = relationship(
        back_populates="lead", order_by="LeadActivity.created_at.desc()", cascade="all, delete-orphan"
    )


class LeadActivity(Base):
    """Append-only history: notes, status changes, assignments, CRM sync results."""

    __tablename__ = "lead_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(30))  # note | status | assignment | crm_sync | created
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="activities")
    actor: Mapped[User | None] = relationship()


class IntegrationEvent(Base):
    """Outbox for outbound integrations (CRM today; email/SMS/lender APIs later).
    Every push is recorded here so failures can be retried and audited."""

    __tablename__ = "integration_events"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    event_type: Mapped[str] = mapped_column(String(60))
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    response: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
