"""CRM adapter interface.

The app never talks to a CRM directly — it calls `get_crm().push_lead(...)`.
To switch CRMs (HubSpot, Salesforce, ...), add a class implementing `CRMAdapter`
and register it in `get_crm()`. Nothing else in the codebase changes.
"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LeadPayload:
    lead_id: str
    status: str
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    zip_code: str | None
    home_model: str | None
    estimate_total_cents: int | None
    monthly_budget_cents: int | None
    message: str | None
    app_url: str
    tags: list[str] = field(default_factory=list)
    existing_contact_id: str | None = None
    existing_opportunity_id: str | None = None
    preferred_contact: str | None = None
    land_status: str | None = None
    budget_mode: str | None = None
    total_budget_cents: int | None = None
    cash_available_cents: int | None = None
    site_address: str | None = None
    lot_price_cents: int | None = None
    style: str | None = None
    stories: int | None = None

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class SyncResult:
    ok: bool
    contact_id: str | None = None
    opportunity_id: str | None = None
    error: str | None = None
    response: dict | None = None


class CRMAdapter(Protocol):
    name: str

    def push_lead(self, payload: LeadPayload) -> SyncResult: ...
