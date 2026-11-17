import hashlib
import hmac
import json

import httpx

from ...config import Settings
from .base import LeadPayload, SyncResult


class NoopCRM:
    name = "none"

    def push_lead(self, payload: LeadPayload) -> SyncResult:
        return SyncResult(ok=True, response={"skipped": "CRM_PROVIDER=none"})


class WebhookCRM:
    """Posts a signed JSON body to any URL (Zapier, Make, n8n, Google Apps Script, a GHL inbound webhook...).
    Receivers can verify the X-Autonodwell-Signature header (HMAC-SHA256 of the body)."""

    name = "webhook"

    def __init__(self, s: Settings):
        if not s.crm_webhook_url:
            raise RuntimeError("CRM_WEBHOOK_URL is required for CRM_PROVIDER=webhook")
        self.url, self.secret = s.crm_webhook_url, s.crm_webhook_secret or ""

    def push_lead(self, payload: LeadPayload) -> SyncResult:
        body = json.dumps({"event": "lead.upsert", "lead": payload.as_dict()}).encode()
        sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        try:
            r = httpx.post(
                self.url,
                content=body,
                headers={"Content-Type": "application/json", "X-Autonodwell-Signature": sig},
                timeout=10,
                follow_redirects=True,  # Google Apps Script answers POSTs with a redirect
            )
            r.raise_for_status()
            return SyncResult(ok=True, response={"status_code": r.status_code})
        except httpx.HTTPError as e:
            return SyncResult(ok=False, error=str(e))


class GoHighLevelCRM:
    """GoHighLevel (LeadConnector) API v2 with a Private Integration token.
    1. Upsert the contact (matched by email/phone per the location's duplicate rules).
    2. Add tags (separate call, because tags on upsert overwrite existing ones).
    3. Optionally create an opportunity in a pipeline, once per lead.
    Docs: https://highlevel.stoplight.io/docs/integrations
    """

    name = "ghl"

    def __init__(self, s: Settings):
        if not (s.ghl_private_token and s.ghl_location_id):
            raise RuntimeError("GHL_PRIVATE_TOKEN and GHL_LOCATION_ID are required for CRM_PROVIDER=ghl")
        self.s = s
        self.client = httpx.Client(
            base_url=s.ghl_api_base,
            timeout=15,
            headers={
                "Authorization": f"Bearer {s.ghl_private_token}",
                "Version": s.ghl_api_version,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def push_lead(self, p: LeadPayload) -> SyncResult:
        try:
            contact = {
                "locationId": self.s.ghl_location_id,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "email": p.email,
                "phone": p.phone,
                "postalCode": p.zip_code,
                "source": "Autonodwell web app",
            }
            r = self.client.post("/contacts/upsert", json={k: v for k, v in contact.items() if v})
            r.raise_for_status()
            contact_id = r.json()["contact"]["id"]

            if p.tags:
                self.client.post(f"/contacts/{contact_id}/tags", json={"tags": p.tags}).raise_for_status()

            note = (
                f"Autonodwell lead {p.lead_id} — status: {p.status}\n"
                f"Model: {p.home_model or '-'} | Style: {p.style or '-'} | Stories: {p.stories or '-'} | ZIP: {p.zip_code or '-'}\n"
                f"Estimate: {_usd(p.estimate_total_cents)} | Budget: {_usd(p.monthly_budget_cents)}/mo\n"
                f"Land status: {p.land_status or '-'} | Budget mode: {p.budget_mode or '-'}\n"
                f"Lot address: {p.site_address or '-'} | Asking price: {_usd(p.lot_price_cents)}\n"
                f"Message: {p.message or '-'}\nOpen in sales console: {p.app_url}"
            )
            self.client.post(f"/contacts/{contact_id}/notes", json={"body": note}).raise_for_status()

            opp_id = p.existing_opportunity_id
            if self.s.ghl_pipeline_id and self.s.ghl_pipeline_stage_id and not opp_id:
                o = self.client.post(
                    "/opportunities/",
                    json={
                        "locationId": self.s.ghl_location_id,
                        "pipelineId": self.s.ghl_pipeline_id,
                        "pipelineStageId": self.s.ghl_pipeline_stage_id,
                        "contactId": contact_id,
                        "name": f"{p.first_name or ''} {p.last_name or ''} — {p.home_model or 'Home'}".strip(),
                        "status": "open",
                        "monetaryValue": round((p.estimate_total_cents or 0) / 100),
                    },
                )
                o.raise_for_status()
                opp_id = o.json().get("opportunity", {}).get("id")
            return SyncResult(ok=True, contact_id=contact_id, opportunity_id=opp_id)
        except (httpx.HTTPError, KeyError, ValueError) as e:
            detail = getattr(getattr(e, "response", None), "text", "") or ""
            return SyncResult(ok=False, error=f"{e} {detail[:500]}".strip())


def _usd(cents: int | None) -> str:
    return f"${cents / 100:,.0f}" if cents else "-"
