"""Lead → CRM sync via an outbox table (IntegrationEvent).

Flow: an API action calls `enqueue_lead_sync()` inside the same DB transaction as the
lead change, then `process_event()` runs as a background task. Failures stay in the
outbox with the error and can be retried from the sales console (or a Cloud Scheduler job).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...config import get_settings
from ...models import IntegrationEvent, Lead, LeadActivity
from .adapters import GoHighLevelCRM, NoopCRM, WebhookCRM
from .base import CRMAdapter, LeadPayload, SyncResult


def get_crm() -> CRMAdapter:
    s = get_settings()
    if s.crm_provider == "ghl":
        return GoHighLevelCRM(s)
    if s.crm_provider == "webhook":
        return WebhookCRM(s)
    return NoopCRM()


def build_payload(lead: Lead) -> LeadPayload:
    first, _, last = (lead.full_name or "").partition(" ")
    design = lead.design
    model = design.home_model.name if design and design.home_model else None
    return LeadPayload(
        lead_id=str(lead.id),
        status=lead.status.value,
        first_name=first or None,
        last_name=last or None,
        email=lead.email,
        phone=lead.phone,
        zip_code=lead.zip_code,
        home_model=model,
        estimate_total_cents=lead.estimate_total_cents,
        monthly_budget_cents=lead.monthly_budget_cents,
        message=lead.message,
        app_url=f"{get_settings().app_base_url}/sales/leads/{lead.id}",
        tags=["autonodwell", f"autonodwell-{lead.status.value}"] + ([f"model-{model.lower().replace(' ', '-')}"] if model else []),
        existing_contact_id=lead.crm_contact_id,
        existing_opportunity_id=lead.crm_opportunity_id,
        preferred_contact=lead.preferred_contact,
        land_status=design.land_status if design else None,
        budget_mode=design.budget_mode if design else None,
        total_budget_cents=design.total_budget_cents if design else None,
        cash_available_cents=design.cash_available_cents if design else None,
        site_address=design.site_address if design else None,
        lot_price_cents=design.lot_price_cents if design else None,
        style=design.style if design else None,
        stories=design.stories if design else None,
    )


def enqueue_lead_sync(db: Session, lead: Lead, reason: str) -> IntegrationEvent:
    provider = get_settings().crm_provider
    ev = IntegrationEvent(
        provider=provider,
        event_type=f"lead.{reason}",
        lead_id=lead.id,
        idempotency_key=f"{provider}:{lead.id}:{reason}:{datetime.now(timezone.utc).isoformat()}",
        payload=build_payload(lead).as_dict(),
    )
    db.add(ev)
    return ev


def process_event(db: Session, event_id: int) -> IntegrationEvent:
    ev = db.get(IntegrationEvent, event_id)
    if ev is None or ev.status == "sent":
        return ev
    lead = db.get(Lead, ev.lead_id) if ev.lead_id else None
    payload = build_payload(lead) if lead else LeadPayload(**ev.payload)  # use freshest data
    ev.attempts += 1
    try:
        result = get_crm().push_lead(payload)
    except Exception as e:  # noqa: BLE001 — never let an integration crash the request
        result = SyncResult(ok=False, error=str(e))
    now = datetime.now(timezone.utc)
    if result.ok:
        ev.status, ev.sent_at, ev.last_error, ev.response = "sent", now, None, result.response
    else:
        ev.status, ev.last_error = "failed", result.error
    if lead and ev.provider != "none":
        lead.crm_provider = ev.provider
        if result.ok:
            lead.crm_contact_id = result.contact_id or lead.crm_contact_id
            lead.crm_opportunity_id = result.opportunity_id or lead.crm_opportunity_id
            lead.crm_synced_at, lead.crm_sync_error = now, None
        else:
            lead.crm_sync_error = result.error
        if ev.provider != "none":
            db.add(
                LeadActivity(
                    lead_id=lead.id,
                    kind="crm_sync",
                    body=f"Synced to {ev.provider}" if result.ok else f"CRM sync failed: {result.error}",
                    data={"event_id": ev.id, "ok": result.ok},
                )
            )
    db.commit()
    return ev


def run_in_background(event_id: int) -> None:
    from ...db import SessionLocal

    with SessionLocal() as db:
        process_event(db, event_id)
