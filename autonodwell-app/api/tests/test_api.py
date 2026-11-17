import httpx

from app.services.estimate import monthly_payment_cents
from tests.conftest import auth


def _catalog(client):
    return client.get("/api/v1/catalog").json()


def _model(client, slug):
    return next(m for m in _catalog(client)["home_models"] if m["slug"] == slug)


def test_catalog_has_three_models(client):
    c = _catalog(client)
    assert [(m["sq_ft"], m["bedrooms"], m["bathrooms"]) for m in c["home_models"]] == [(800, 2, 1), (1200, 3, 2), (1700, 3, 2)]
    assert {cat["slug"] for cat in c["categories"]} == {"siding", "kitchen", "flooring", "upgrades"}


def test_mortgage_math():
    # $300,000 at 7% for 30 years = $1,995.91
    assert monthly_payment_cents(30_000_000, 700, 30) == 199_591


def test_estimate_preview_and_market_fallback(client):
    m2 = _model(client, "model-two")
    r = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "zip_code": "10001", "monthly_budget_cents": 240000}).json()
    e = r["estimate"]
    assert e["market"]["slug"] == "national" and e["market"]["matched_zip"] is False
    assert sum(l["cents"] for l in e["lines"]) == e["total_cents"]
    assert e["lines"][0]["cents"] == 185_000_00  # base 175k + 10k delivery
    assert e["budget"]["fit"] in {"within", "stretch", "over"}
    assert [s["slug"] for s in r["path_home"]] == ["design", "site", "financing", "approvals", "construction", "keys"]

    sac = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "zip_code": "95816"}).json()["estimate"]
    assert sac["market"]["slug"] == "sacramento-ca" and sac["total_cents"] > e["total_cents"]


def test_land_budget_round_trip_cash_cap_and_own_lot(client):
    m2 = _model(client, "model-two")
    e = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "zip_code": "95816"}).json()["estimate"]
    land_line = next(l["cents"] for l in e["lines"] if l["key"] == "land")

    total = client.post("/api/v1/land-budget", json={
        "budget_mode": "total", "total_budget_cents": e["total_cents"], "zip_code": "95816",
    }).json()
    got = next(m["land_budget_cents"] for m in total["per_model"] if m["home_model_id"] == m2["id"])
    assert abs(got - land_line) <= 100_000  # within $1,000

    monthly = client.post("/api/v1/land-budget", json={
        "budget_mode": "monthly", "monthly_budget_cents": e["monthly"]["total_cents"], "zip_code": "95816",
    }).json()
    assert abs(monthly["affordable_total_cents"] - e["total_cents"]) <= 100_000

    cash = client.post("/api/v1/land-budget", json={
        "budget_mode": "total", "total_budget_cents": e["total_cents"], "cash_available_cents": 100_00, "zip_code": "95816",
    }).json()
    assert cash["limited_by"] == "cash"
    assert cash["per_model"] and all(m["land_budget_cents"] < 0 for m in cash["per_model"])

    assert client.post("/api/v1/land-budget", json={"budget_mode": "need_help", "zip_code": "95816"}).json()["affordable_total_cents"] is None

    own = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "zip_code": "95816", "land_status": "own_lot"}).json()["estimate"]
    own_land = next(l for l in own["lines"] if l["key"] == "land")
    assert own_land["cents"] == 0 and own_land["label"] == "Land (you own the lot)"
    assert own["total_cents"] < e["total_cents"]


def test_looking_at_lot_asking_price(client):
    m2 = _model(client, "model-two")
    asking = client.post("/api/v1/estimate", json={
        "home_model_id": m2["id"], "zip_code": "95816",
        "land_status": "looking_at_lot", "lot_price_cents": 15_000_000,
    }).json()["estimate"]
    land = next(l for l in asking["lines"] if l["key"] == "land")
    assert land["cents"] == 15_000_000 and land["label"] == "Land (asking price)"

    plain = client.post("/api/v1/estimate", json={
        "home_model_id": m2["id"], "zip_code": "95816", "land_status": "looking_at_lot",
    }).json()["estimate"]
    market = next(l["cents"] for l in client.post(
        "/api/v1/estimate", json={"home_model_id": m2["id"], "zip_code": "95816"},
    ).json()["estimate"]["lines"] if l["key"] == "land")
    assert next(l["cents"] for l in plain["lines"] if l["key"] == "land") == market

    headers = auth("lot-price-1")
    created = client.post("/api/v1/designs", json={
        "land_status": "looking_at_lot", "lot_price_cents": 15_000_000, "zip_code": "95816",
    }, headers=headers)
    assert created.status_code == 201
    saved = client.get(f"/api/v1/designs/{created.json()['id']}", headers=headers).json()
    assert saved["lot_price_cents"] == 15_000_000
    saved_land = next(l for l in saved["estimate"]["lines"] if l["key"] == "land")
    assert saved_land["cents"] == 15_000_000 and saved_land["label"] == "Land (asking price)"


def test_zip_land_replaces_market_allocation(client):
    from app.db import SessionLocal
    from app.models import ZipLandValue

    source = "FHFA residential land prices v4.0 (June 2024), 2022 values, quarter-acre lot"
    construction = "DoD area cost factors, 2026"
    with SessionLocal() as db:
        db.merge(ZipLandValue(
            prefix="941", state="CA", land_cents=2_956_900_00, basis="zip", source=source,
            construction_index_bps=13200, factor_basis="zip", area_type="urban",
        ))
        db.merge(ZipLandValue(
            prefix="787", state="TX", land_cents=289_000_00, basis="zip", source=source,
            construction_index_bps=8200, factor_basis="zip", area_type="urban",
        ))
        db.merge(ZipLandValue(
            prefix="396", state="MS", land_cents=12_400_00, basis="zip", source=source,
            construction_index_bps=None, factor_basis=None, area_type=None,
        ))
        # Phoenix market index, but no ZIP construction factor: home cost stays on the market.
        db.merge(ZipLandValue(
            prefix="850", state="AZ", land_cents=70_000_00, basis="zip", source=source,
            construction_index_bps=None, factor_basis=None, area_type=None,
        ))
        db.commit()

    m2 = _model(client, "model-two")

    def land_of(body):
        e = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], **body}).json()["estimate"]
        line = next(l for l in e["lines"] if l["key"] == "land")
        return e, line

    def home_cents(e):
        return next(l["cents"] for l in e["lines"] if l["key"] == "home_delivery")

    austin, austin_land = land_of({"zip_code": "78704"})
    assert austin_land["cents"] == 289_000_00
    assert austin["market"]["area_label"] == "ZIP area 787, TX"
    assert austin["market"]["land_source"] == source
    assert austin["market"]["area_type"] == "urban"
    assert austin["market"]["construction_source"] == construction

    bay, bay_land = land_of({"zip_code": "94110"})
    delta, delta_land = land_of({"zip_code": "39601"})
    assert bay_land["cents"] > delta_land["cents"]
    assert home_cents(bay) > home_cents(austin)  # 13200 vs 8200, before land
    assert bay["market"]["construction_source"] == construction

    phoenix_gap, _ = land_of({"zip_code": "85001"})
    phoenix_open, _ = land_of({"zip_code": "85201"})
    assert home_cents(phoenix_gap) == home_cents(phoenix_open)
    assert phoenix_gap["market"]["slug"] == "phoenix-az"
    assert phoenix_gap["market"]["construction_source"] is None

    owned, owned_land = land_of({"zip_code": "78704", "land_status": "own_lot"})
    assert owned_land["cents"] == 0 and owned_land["label"] == "Land (you own the lot)"
    assert owned["market"]["land_source"] is None and owned["market"]["area_label"] is None
    assert home_cents(owned) == home_cents(austin)

    asking, asking_land = land_of({
        "zip_code": "78704", "land_status": "looking_at_lot", "lot_price_cents": 15_000_000,
    })
    assert asking_land["cents"] == 15_000_000 and asking_land["label"] == "Land (asking price)"
    assert asking["market"]["land_source"] is None

    sac, sac_land = land_of({"zip_code": "95816"})
    assert sac_land["cents"] == 95_000_00  # Sacramento sample allocation; no ZIP-area row
    assert sac["market"]["area_label"] is None and sac["market"]["land_source"] is None

    nowhere, nowhere_land = land_of({})
    assert nowhere_land["cents"] == 60_000_00  # national sample allocation
    assert nowhere["market"]["area_label"] is None
    assert nowhere["market"]["area_type"] is None and nowhere["market"]["construction_source"] is None
    assert delta["market"]["construction_source"] is None
    assert home_cents(delta) == home_cents(nowhere)  # null ZIP index keeps the national market index

    budget = client.post("/api/v1/land-budget", json={
        "budget_mode": "total", "total_budget_cents": austin["total_cents"], "zip_code": "78704",
    }).json()
    got = next(m["land_budget_cents"] for m in budget["per_model"] if m["home_model_id"] == m2["id"])
    assert abs(got - 289_000_00) <= 100_000
    assert abs(got - 85_000_00) > 100_000  # not the Austin sample allocation
    assert budget["market"]["area_label"] == "ZIP area 787, TX"
    assert budget["market"]["land_source"] == source
    assert budget["market"]["construction_source"] == construction
    assert budget["market"]["area_type"] == "urban"


def test_load_land_reports_912():
    import subprocess
    import sys
    from pathlib import Path

    from app.db import SessionLocal
    from app.models import ZipLandValue

    api = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "app.load_land"],
        cwd=api,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "912"
    with SessionLocal() as db:
        row = db.get(ZipLandValue, "005")
    assert row is not None
    assert row.land_cents == 496_900_00 and row.basis == "state"
    assert row.construction_index_bps == 10_300 and row.factor_basis == "state" and row.area_type == "urban"


def test_options_change_price_and_validate(client):
    c = _catalog(client)
    m2 = _model(client, "model-two")
    floor_oak = next(o for cat in c["categories"] for o in cat["options"] if o["slug"] == "floor-oak")
    base = client.post("/api/v1/estimate", json={"home_model_id": m2["id"]}).json()["estimate"]
    oak = client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "option_ids": [floor_oak["id"]]}).json()["estimate"]
    assert oak["options_total_cents"] - base["options_total_cents"] == 3_00 * 1200  # $3/sq ft
    sidings = [o["id"] for cat in c["categories"] if cat["slug"] == "siding" for o in cat["options"]][:2]
    assert client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "option_ids": sidings}).status_code == 422
    assert client.post("/api/v1/estimate", json={"home_model_id": m2["id"], "option_ids": [99999]}).status_code == 422


def test_design_lifecycle_anonymous_then_signed_in(client):
    m1 = _model(client, "model-one")
    anon = auth("visitor-1")
    r = client.post("/api/v1/designs", json={"home_model_id": m1["id"], "monthly_budget_cents": 200000}, headers=anon)
    assert r.status_code == 201
    did = r.json()["id"]
    assert len(r.json()["option_ids"]) == 3  # defaults for the 3 single-choice categories

    assert client.patch(f"/api/v1/designs/{did}", json={"zip_code": "78704", "current_step": 3}, headers=anon).json()["estimate"]["market"]["slug"] == "austin-tx"

    submit = {"full_name": "Ana Ruiz", "email": "ana@example.com", "contact_consent": True, "consent_text": "OK to contact me"}
    assert client.post(f"/api/v1/designs/{did}/submit", json=submit, headers=anon).status_code == 401

    # Same Firebase UID after account linking -> same designs
    signed = auth("visitor-1", "ana@example.com")
    assert [d["id"] for d in client.get("/api/v1/designs", headers=signed).json()] == [did]
    r = client.post(f"/api/v1/designs/{did}/submit", json=submit, headers=signed)
    assert r.status_code == 200 and r.json()["status"] == "submitted" and r.json()["lead_status"] == "new"
    assert r.json()["current_step"] == 5

    dup = client.post(f"/api/v1/designs/{did}/duplicate", headers=signed).json()
    assert dup["status"] == "draft"
    assert client.delete(f"/api/v1/designs/{dup['id']}", headers=signed).status_code == 204
    # other people can't see it
    assert client.get(f"/api/v1/designs/{did}", headers=auth("someone-else")).status_code == 404


def test_design_starting_point_round_trip(client):
    headers = auth("starter-1")
    r = client.post(
        "/api/v1/designs",
        json={"land_status": "need_land", "budget_mode": "need_help"},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["land_status"] == "need_land"
    assert body["budget_mode"] == "need_help"
    assert body["home_model"]["slug"] == "model-two"

    patched = client.patch(
        f"/api/v1/designs/{body['id']}",
        json={"site_address": "1200 Lot Line Rd", "total_budget_cents": 45_000_000},
        headers=headers,
    )
    assert patched.status_code == 200
    saved = client.get(f"/api/v1/designs/{body['id']}", headers=headers).json()
    assert saved["site_address"] == "1200 Lot Line Rd"
    assert saved["total_budget_cents"] == 45_000_000
    assert saved["land_status"] == "need_land"
    assert saved["budget_mode"] == "need_help"


def test_design_style_round_trip(client):
    headers = auth("style-1")
    created = client.post("/api/v1/designs", json={"style": "craftsman"}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["style"] == "craftsman"
    did = body["id"]
    assert client.get(f"/api/v1/designs/{did}", headers=headers).json()["style"] == "craftsman"

    patched = client.patch(f"/api/v1/designs/{did}", json={"style": "mcm", "stories": 2}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["style"] == "mcm" and patched.json()["stories"] == 2
    assert client.get(f"/api/v1/designs/{did}", headers=headers).json()["stories"] == 2

    rejected = client.post("/api/v1/designs", json={"style": "pop", "stories": 2}, headers=headers)
    assert rejected.status_code == 422
    reset = client.patch(f"/api/v1/designs/{did}", json={"style": "pop"}, headers=headers)
    assert reset.status_code == 200
    assert reset.json()["style"] == "pop" and reset.json()["stories"] == 1

    assert client.post("/api/v1/designs", json={"style": "colonial"}, headers=headers).status_code == 422
    assert client.patch(f"/api/v1/designs/{did}", json={"style": "barn"}, headers=headers).status_code == 422


def test_two_story_option_scales_with_zip(client):
    from app.db import SessionLocal
    from app.models import ZipLandValue

    source = "FHFA residential land prices v4.0 (June 2024), 2022 values, quarter-acre lot"
    with SessionLocal() as db:
        db.merge(ZipLandValue(
            prefix="941", state="CA", land_cents=2_956_900_00, basis="zip", source=source,
            construction_index_bps=13200, factor_basis="zip", area_type="urban",
        ))
        db.merge(ZipLandValue(
            prefix="787", state="TX", land_cents=289_000_00, basis="zip", source=source,
            construction_index_bps=8200, factor_basis="zip", area_type="urban",
        ))
        db.commit()

    m2 = _model(client, "model-two")

    def estimate(zip_code, stories):
        return client.post("/api/v1/estimate", json={
            "home_model_id": m2["id"], "zip_code": zip_code, "stories": stories,
        }).json()["estimate"]

    one = estimate("94110", 1)
    two = estimate("94110", 2)
    assert all(line["key"] != "two_story" for line in one["lines"])
    line = next(item for item in two["lines"] if item["key"] == "two_story")
    assert line["label"] == "Two-story option"
    assert two["total_cents"] > one["total_cents"]
    assert two["total_cents"] - one["total_cents"] > line["cents"]
    austin = next(item["cents"] for item in estimate("78704", 2)["lines"] if item["key"] == "two_story")
    assert line["cents"] > austin


def test_sales_console_permissions_and_pipeline(client):
    assert client.get("/api/v1/sales/leads", headers=auth("customer-x", "x@example.com")).status_code == 403

    boss = auth("boss", "boss@example.com")  # ADMIN_EMAILS bootstrap
    assert client.get("/api/v1/me", headers=boss).json()["role"] == "admin"
    rep_id = client.get("/api/v1/me", headers=auth("rep-1", "rep@example.com")).json()["id"]
    assert client.patch(f"/api/v1/admin/users/{rep_id}", json={"role": "sales"}, headers=boss).status_code == 200
    rep = auth("rep-1", "rep@example.com")

    page = client.get("/api/v1/sales/leads", headers=rep).json()
    assert page["total"] >= 1
    lead_id = page["items"][0]["id"]
    d = client.patch(f"/api/v1/sales/leads/{lead_id}", json={"status": "contacted", "assigned_to_id": rep_id}, headers=rep).json()
    assert d["status"] == "contacted" and d["assigned_to"]["id"] == rep_id
    d = client.post(f"/api/v1/sales/leads/{lead_id}/notes", json={"body": "Left a voicemail"}, headers=rep).json()
    assert [a["kind"] for a in d["activities"]][:3] == ["note", "assignment", "status"] or "note" in [a["kind"] for a in d["activities"]]
    assert d["submitted_estimate"]["total_cents"] == d["estimate_total_cents"]
    assert client.get("/api/v1/sales/leads?assigned=me", headers=rep).json()["total"] >= 1
    csv = client.get("/api/v1/sales/leads.csv", headers=rep)
    assert csv.status_code == 200 and "ana@example.com" in csv.text
    # sales can't change prices
    assert client.patch("/api/v1/admin/home-models/1", json={"base_price_cents": 1}, headers=rep).status_code == 403


def test_admin_price_change_flows_into_estimates(client):
    boss = auth("boss", "boss@example.com")
    m1 = _model(client, "model-one")
    before = client.post("/api/v1/estimate", json={"home_model_id": m1["id"]}).json()["estimate"]["lines"][0]["cents"]
    client.patch(f"/api/v1/admin/home-models/{m1['id']}", json={"base_price_cents": m1["base_price_cents"] + 1_000_00}, headers=boss)
    after = client.post("/api/v1/estimate", json={"home_model_id": m1["id"]}).json()["estimate"]["lines"][0]["cents"]
    assert after - before == 1_000_00
    a = client.get("/api/v1/admin/assumptions", headers=boss).json()
    new = client.post("/api/v1/admin/assumptions", json={**{k: v for k, v in a.items() if k != "id"}, "name": "v2", "interest_rate_bps": 650}, headers=boss).json()
    assert new["id"] != a["id"]
    assert client.post("/api/v1/estimate", json={"home_model_id": m1["id"]}).json()["estimate"]["assumptions"]["interest_rate_pct"] == 6.5


def test_privacy_export_and_delete(client):
    me = auth("privacy-1", "privacy.person@example.com")
    m1 = _model(client, "model-one")
    did = client.post("/api/v1/designs", json={"home_model_id": m1["id"]}, headers=me).json()["id"]
    client.post(f"/api/v1/designs/{did}/submit", headers=me, json={"full_name": "P Q", "email": "privacy.person@example.com", "contact_consent": True, "consent_text": "ok"})
    ex = client.get("/api/v1/me/export", headers=me).json()
    assert ex["profile"]["email"] == "privacy.person@example.com" and len(ex["designs"]) == 1 and len(ex["consultation_requests"]) == 1
    assert client.delete("/api/v1/me", headers=me).status_code == 204
    boss = auth("boss", "boss@example.com")
    assert "privacy.person@example.com" not in client.get("/api/v1/sales/leads.csv", headers=boss).text


def test_build_payload_includes_starting_point(client):
    import uuid

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Lead
    from app.services.crm import build_payload

    headers = auth("starting-crm", "starting-crm@example.com")
    created = client.post(
        "/api/v1/designs",
        json={"land_status": "need_land", "budget_mode": "total"},
        headers=headers,
    )
    assert created.status_code == 201
    did = created.json()["id"]
    submitted = client.post(
        f"/api/v1/designs/{did}/submit",
        headers=headers,
        json={
            "full_name": "Casey Lot",
            "email": "starting-crm@example.com",
            "contact_consent": True,
            "consent_text": "ok",
        },
    )
    assert submitted.status_code == 200

    with SessionLocal() as db:
        lead = db.scalar(select(Lead).where(Lead.design_id == uuid.UUID(did)))
        payload = build_payload(lead)
    assert payload.land_status == "need_land"
    assert payload.budget_mode == "total"
    assert payload.style is None
    assert payload.stories is None


def test_ghl_adapter_calls(monkeypatch):
    import json

    from app.config import Settings
    from app.services.crm.adapters import GoHighLevelCRM
    from app.services.crm.base import LeadPayload

    calls = []
    notes = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path, req.headers.get("Version")))
        if req.url.path.endswith("/notes"):
            notes.append(json.loads(req.content))
        if req.url.path == "/contacts/upsert":
            return httpx.Response(200, json={"contact": {"id": "c123"}})
        if req.url.path == "/opportunities/":
            return httpx.Response(201, json={"opportunity": {"id": "o456"}})
        return httpx.Response(200, json={})

    s = Settings(crm_provider="ghl", ghl_private_token="t", ghl_location_id="loc", ghl_pipeline_id="p", ghl_pipeline_stage_id="st")
    crm = GoHighLevelCRM(s)
    crm.client = httpx.Client(base_url=s.ghl_api_base, transport=httpx.MockTransport(handler), headers=crm.client.headers)
    res = crm.push_lead(LeadPayload("L1", "new", "Ana", "Ruiz", "a@x.com", None, "78704", "Model Two", 35_000_000, 240_000, None, "http://x", ["autonodwell"], style="mcm", stories=2))
    assert res.ok and res.contact_id == "c123" and res.opportunity_id == "o456"
    assert [c[1] for c in calls] == ["/contacts/upsert", "/contacts/c123/tags", "/contacts/c123/notes", "/opportunities/"]
    assert all(c[2] == "2021-07-28" for c in calls)
    assert "Style: mcm" in notes[0]["body"] and "Stories: 2" in notes[0]["body"]
