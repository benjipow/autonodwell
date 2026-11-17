"""Request/response shapes. These generate the OpenAPI spec at /openapi.json, which the
web app (and a future native app) turn into a typed client — the API contract lives here."""
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import DesignStatus, LeadStatus, PricingMode, Role, SelectionType


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- catalog
class HomeModelOut(ORM):
    id: int
    slug: str
    name: str
    tagline: str | None
    sq_ft: int
    bedrooms: int
    bathrooms: float
    base_price_cents: int
    floor_plan_key: str
    image_url: str | None


class OptionOut(ORM):
    id: int
    slug: str
    name: str
    description: str | None
    pricing_mode: PricingMode
    price_cents: int
    swatch_hex: str | None
    is_default: bool


class OptionCategoryOut(ORM):
    id: int
    slug: str
    name: str
    description: str | None
    selection_type: SelectionType
    display: str
    options: list[OptionOut]


class CatalogOut(BaseModel):
    home_models: list[HomeModelOut]
    categories: list[OptionCategoryOut]
    disclaimer: str


# ---------------------------------------------------------------- estimate
class EstimateIn(BaseModel):
    home_model_id: int
    option_ids: list[int] = []
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    monthly_budget_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    land_status: Literal["own_lot", "looking_at_lot", "need_land"] | None = None
    lot_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    stories: Literal[1, 2] | None = None


class EstimateLine(BaseModel):
    key: str
    label: str
    cents: int


class Monthly(BaseModel):
    principal_interest_cents: int
    taxes_cents: int
    insurance_cents: int
    total_cents: int


class BudgetFit(BaseModel):
    monthly_budget_cents: int | None
    fit: Literal["within", "stretch", "over"] | None


class MarketInfo(BaseModel):
    slug: str
    name: str
    matched_zip: bool
    is_sample: bool
    data_source: str
    permit_weeks: list[int]
    land_source: str | None = None  # set when a ZIP-area land price was used
    area_label: str | None = None  # e.g. "ZIP area 787, TX"
    area_type: str | None = None
    construction_source: str | None = None  # set when a ZIP-area construction factor was used


class Estimate(BaseModel):
    lines: list[EstimateLine]
    options_total_cents: int
    total_cents: int
    down_payment_cents: int
    loan_cents: int
    cash_needed_cents: int
    monthly: Monthly
    budget: BudgetFit
    assumptions: dict[str, Any]
    market: MarketInfo
    disclaimer: str


class PathStageOut(BaseModel):
    slug: str
    name: str
    who: str
    description: str
    next_action: str
    weeks: list[int]
    cost_cents: int | None


class EstimateOut(BaseModel):
    estimate: Estimate
    path_home: list[PathStageOut]


class LandBudgetIn(BaseModel):
    budget_mode: Literal["total", "monthly", "need_help"]
    total_budget_cents: int | None = Field(default=None, ge=0)
    monthly_budget_cents: int | None = Field(default=None, ge=0)
    cash_available_cents: int | None = Field(default=None, ge=0)
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    stories: Literal[1, 2] | None = None


class LandBudgetModel(BaseModel):
    home_model_id: int
    name: str
    land_budget_cents: int


class LandBudgetOut(BaseModel):
    affordable_total_cents: int | None
    limited_by: str | None
    per_model: list[LandBudgetModel]
    market: MarketInfo
    disclaimer: str


# ---------------------------------------------------------------- me
class MeOut(ORM):
    id: uuid.UUID
    email: str | None
    full_name: str | None
    phone: str | None
    role: Role
    is_anonymous: bool
    marketing_opt_in: bool


class MePatch(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    marketing_opt_in: bool | None = None


# ---------------------------------------------------------------- designs
LandStatus = Literal["own_lot", "looking_at_lot", "need_land"]
BudgetMode = Literal["total", "monthly", "need_help"]
HouseStyle = Literal["pop", "mcm", "craftsman"]
Stories = Literal[1, 2]


class DesignIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    home_model_id: int | None = None
    monthly_budget_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    option_ids: list[int] | None = None  # omitted -> category defaults
    current_step: int = Field(default=1, ge=1, le=5)
    land_status: LandStatus | None = None
    budget_mode: BudgetMode | None = None
    total_budget_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    cash_available_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    site_address: str | None = Field(default=None, max_length=200)
    lot_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    style: HouseStyle | None = None
    stories: Stories | None = None


class DesignPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    home_model_id: int | None = None
    monthly_budget_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    option_ids: list[int] | None = None
    current_step: int | None = Field(default=None, ge=1, le=5)
    land_status: LandStatus | None = None
    budget_mode: BudgetMode | None = None
    total_budget_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    cash_available_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    site_address: str | None = Field(default=None, max_length=200)
    lot_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    style: HouseStyle | None = None
    stories: Stories | None = None


class DesignSummary(ORM):
    id: uuid.UUID
    name: str
    home_model: HomeModelOut
    monthly_budget_cents: int | None
    zip_code: str | None
    land_status: LandStatus | None = None
    budget_mode: BudgetMode | None = None
    total_budget_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    cash_available_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    site_address: str | None = None
    lot_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    style: HouseStyle | None = None
    stories: Stories | None = None
    status: DesignStatus
    current_step: int
    created_at: datetime
    updated_at: datetime


class DesignOut(DesignSummary):
    option_ids: list[int]
    estimate: Estimate
    path_home: list[PathStageOut]
    lead_status: LeadStatus | None = None


class SubmitIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    preferred_contact: Literal["email", "phone", "text"] = "email"
    message: str | None = Field(default=None, max_length=4000)
    contact_consent: bool
    consent_text: str = Field(max_length=2000)


# ---------------------------------------------------------------- sales
class StaffOut(ORM):
    id: uuid.UUID
    email: str | None
    full_name: str | None
    role: Role


class LeadSummary(ORM):
    id: uuid.UUID
    status: LeadStatus
    full_name: str | None
    email: str | None
    phone: str | None
    zip_code: str | None
    estimate_total_cents: int | None
    monthly_budget_cents: int | None
    assigned_to: StaffOut | None
    crm_synced_at: datetime | None
    crm_sync_error: str | None
    created_at: datetime
    updated_at: datetime


class ActivityOut(ORM):
    id: int
    kind: str
    body: str | None
    data: dict | None
    actor: StaffOut | None
    created_at: datetime


class LeadDetail(LeadSummary):
    preferred_contact: str | None
    message: str | None
    contact_consent: bool
    consent_text: str | None
    source: str
    crm_provider: str | None
    crm_contact_id: str | None
    design_id: uuid.UUID | None
    design_name: str | None = None
    home_model_name: str | None = None
    submitted_estimate: dict | None = None
    activities: list[ActivityOut]


class LeadPage(BaseModel):
    items: list[LeadSummary]
    total: int
    page: int
    page_size: int
    counts_by_status: dict[str, int]


class LeadPatch(BaseModel):
    status: LeadStatus | None = None
    assigned_to_id: uuid.UUID | None = None
    unassign: bool = False


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


# ---------------------------------------------------------------- admin
class HomeModelPatch(BaseModel):
    name: str | None = None
    tagline: str | None = None
    base_price_cents: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    image_url: str | None = None


class OptionPatch(BaseModel):
    name: str | None = None
    price_cents: int | None = None
    is_active: bool | None = None
    is_default: bool | None = None


class AssumptionsOut(ORM):
    id: int
    name: str
    interest_rate_bps: int
    term_years: int
    down_payment_bps: int
    closing_cost_bps: int
    soft_cost_bps: int
    contingency_bps: int
    delivery_cents: int
    two_story_premium_cents: int
    notes: str | None


class AssumptionsIn(BaseModel):
    """Saving creates a NEW assumption set and activates it (old estimates stay traceable)."""

    name: str
    interest_rate_bps: int = Field(ge=0, le=3000)
    term_years: int = Field(ge=5, le=40)
    down_payment_bps: int = Field(ge=0, le=10000)
    closing_cost_bps: int = Field(ge=0, le=1500)
    soft_cost_bps: int = Field(ge=0, le=5000)
    contingency_bps: int = Field(ge=0, le=5000)
    delivery_cents: int = Field(ge=0)
    two_story_premium_cents: int = Field(default=8_500_000, ge=0)
    notes: str | None = None


class MarketOut(ORM):
    id: int
    slug: str
    name: str
    state: str | None
    is_default: bool
    is_sample: bool
    construction_cost_index_bps: int
    site_install_cents: int
    land_allocation_cents: int
    permit_fees_cents: int
    permit_weeks_low: int
    permit_weeks_high: int
    property_tax_bps: int
    insurance_annual_cents: int
    data_source: str
    zip_prefixes: list[str] = []


class MarketPatch(BaseModel):
    construction_cost_index_bps: int | None = None
    site_install_cents: int | None = None
    land_allocation_cents: int | None = None
    permit_fees_cents: int | None = None
    permit_weeks_low: int | None = None
    permit_weeks_high: int | None = None
    property_tax_bps: int | None = None
    insurance_annual_cents: int | None = None
    data_source: str | None = None
    is_sample: bool | None = None


class UserRolePatch(BaseModel):
    role: Role
