"""Lead alert email (Resend): pure tests, no database needed."""
import httpx

from app.config import Settings
from app.services import notify
from app.services.crm.base import LeadPayload


def _payload(**kw) -> LeadPayload:
    base = dict(lead_id="L1", status="new", first_name="Ana", last_name="Ruiz", email="ana@example.com", phone="555-0100",
                zip_code="94110", home_model="Redwood", estimate_total_cents=31250000, monthly_budget_cents=210000,
                message="Corner lot <b>bold</b>", app_url="https://app.autonodwell.com/sales/leads/L1")
    base.update(kw)
    return LeadPayload(**base)


def test_email_content_escapes_and_links():
    m = notify.build_email(_payload(), is_new=True)
    assert m["subject"] == "New design review request: Ana Ruiz (94110)"
    assert m["reply_to"] == "ana@example.com"
    assert "$312,500" in m["text"] and "$2,100" in m["text"]
    assert "&lt;b&gt;bold&lt;/b&gt;" in m["html"] and "<b>bold</b>" not in m["html"]
    assert "https://app.autonodwell.com/sales/leads/L1" in m["html"]


def test_off_without_settings(monkeypatch):
    called = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: called.append(1))
    assert notify.send_lead_email(_payload(), True, Settings(resend_api_key=None, lead_notify_to="a@b.co")) is False
    assert notify.send_lead_email(_payload(), True, Settings(resend_api_key="re_x", lead_notify_to="")) is False
    assert called == []


def test_sends_through_resend(monkeypatch):
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, json=json, auth=headers["Authorization"])
        return httpx.Response(200, json={"id": "e1"})

    monkeypatch.setattr(httpx, "post", fake_post)
    s = Settings(resend_api_key="re_test", lead_notify_to="team@example.com, b@example.com")
    assert notify.send_lead_email(_payload(), False, s) is True
    assert sent["url"] == "https://api.resend.com/emails" and sent["auth"] == "Bearer re_test"
    assert sent["json"]["to"] == ["team@example.com", "b@example.com"]
    assert sent["json"]["from"] == "Autonodwell <inquiries@autonodwell.com>"
    assert sent["json"]["subject"].startswith("Updated design review request")


def test_failure_never_raises(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    assert notify.send_lead_email(_payload(), True, Settings(resend_api_key="re_x", lead_notify_to="t@example.com")) is False
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(403, text="domain not verified"))
    assert notify.send_lead_email(_payload(), True, Settings(resend_api_key="re_x", lead_notify_to="t@example.com")) is False
