"""Lead alert emails through Resend.

When a customer sends their design to a consultant, the team gets an email with the
lead's details and a link to the sales console. This runs beside the CRM sync, never
instead of it, and never fails the customer's request: errors are logged and dropped.
Off unless RESEND_API_KEY and LEAD_NOTIFY_TO are set.
"""
import html
import logging

import httpx

from ..config import Settings, get_settings
from .crm.base import LeadPayload

log = logging.getLogger(__name__)
RESEND_URL = "https://api.resend.com/emails"


def _money(cents: int | None) -> str | None:
    return None if cents is None else f"${cents / 100:,.0f}"


def build_email(p: LeadPayload, is_new: bool) -> dict:
    name = " ".join(x for x in (p.first_name, p.last_name) if x) or "A customer"
    rows = [
        ("Name", name),
        ("Email", p.email),
        ("Phone", p.phone),
        ("Preferred contact", p.preferred_contact),
        ("ZIP", p.zip_code),
        ("Home model", p.home_model),
        ("Style", p.style),
        ("Stories", str(p.stories) if p.stories else None),
        ("Land", p.land_status),
        ("Site address", p.site_address),
        ("Lot price", _money(p.lot_price_cents)),
        ("Monthly budget", _money(p.monthly_budget_cents)),
        ("Total budget", _money(p.total_budget_cents)),
        ("Cash available", _money(p.cash_available_cents)),
        ("Preliminary estimate", _money(p.estimate_total_cents)),
        ("Message", p.message),
    ]
    rows = [(k, v) for k, v in rows if v]
    what = "New design review request" if is_new else "Updated design review request"
    subject = f"{what}: {name}" + (f" ({p.zip_code})" if p.zip_code else "")
    text = "\n".join([what, ""] + [f"{k}: {v}" for k, v in rows] + ["", f"Open in the sales console: {p.app_url}"])
    trs = "".join(
        f'<tr><td style="padding:6px 14px 6px 0;color:#5E4A55;vertical-align:top;white-space:nowrap">{html.escape(k)}</td>'
        f'<td style="padding:6px 0;color:#121212">{html.escape(v).replace(chr(10), "<br>")}</td></tr>'
        for k, v in rows
    )
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5">'
        f'<p style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#B23A1C;margin:0 0 6px">Autonodwell app</p>'
        f'<h2 style="font-size:20px;color:#351E28;margin:0 0 14px">{html.escape(what)}</h2>'
        f'<table style="border-collapse:collapse">{trs}</table>'
        f'<p style="margin:18px 0 0"><a href="{html.escape(p.app_url)}" style="color:#351E28">Open in the sales console</a></p>'
        '<p style="font-size:12px;color:#5E4A55;margin:14px 0 0">Estimates are preliminary examples, not quotes. Reply to this email to answer the customer directly.</p>'
        "</div>"
    )
    msg = {"subject": subject, "text": text, "html": body}
    if p.email:
        msg["reply_to"] = p.email
    return msg


def send_lead_email(payload: LeadPayload, is_new: bool, settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    to = s.lead_notify_list
    if not (s.resend_api_key and to):
        return False
    msg = {"from": s.lead_notify_from, "to": to, **build_email(payload, is_new)}
    try:
        r = httpx.post(
            RESEND_URL,
            json=msg,
            headers={"Authorization": f"Bearer {s.resend_api_key}", "Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code >= 300:
            log.warning("Lead email for %s failed: %s %s", payload.lead_id, r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:  # noqa: BLE001 — never let an email crash the request
        log.warning("Lead email for %s failed: %s", payload.lead_id, e)
        return False
