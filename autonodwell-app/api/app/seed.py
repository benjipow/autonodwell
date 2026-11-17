"""Idempotent seed: reference data the app needs to run (catalog, assumptions, sample
markets, path stages). Safe to re-run — rows are matched by slug and only created if
missing, so prices edited in the admin screen are never overwritten.

    python -m app.seed            # reference data
    python -m app.seed --demo     # + demo staff accounts and sample leads (local only)

ALL PRICES AND MARKET NUMBERS BELOW ARE PLACEHOLDERS, not sourced data.
"""
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import (
    AssumptionSet, Design, DesignStatus, HomeModel, Lead, LeadActivity, LeadStatus, Market,
    Option, OptionCategory, PathStage, PricingMode, Role, SelectionType, User, ZipPrefix,
)

K = 100  # cents per dollar

HOME_MODELS = [
    dict(slug="model-one", name="Model One", tagline="Compact two-bedroom starter home", sq_ft=800,
         bedrooms=2, bathrooms=1, base_price_cents=135_000 * K, floor_plan_key="m1", sort_order=1),
    dict(slug="model-two", name="Model Two", tagline="The three-bedroom family starter home", sq_ft=1200,
         bedrooms=3, bathrooms=2, base_price_cents=175_000 * K, floor_plan_key="m2", sort_order=2),
    dict(slug="model-three", name="Model Three", tagline="Three bedrooms with room to grow", sq_ft=1700,
         bedrooms=3, bathrooms=2, base_price_cents=255_000 * K, floor_plan_key="m3", sort_order=3),
]

CATEGORIES = [
    dict(slug="siding", name="Exterior siding", selection_type=SelectionType.single, display="swatches", sort_order=1,
         description="Each finish maps to a real cladding assembly.", options=[
             dict(slug="siding-cedar", name="Natural cedar", swatch_hex="#c9a77c", price=0, default=True),
             dict(slug="siding-charcoal", name="Charcoal board & batten", swatch_hex="#3a3d3c", price=1_200),
             dict(slug="siding-bone", name="Bone fiber cement", swatch_hex="#d8d4cb", price=0),
             dict(slug="siding-sage", name="Sage lap siding", swatch_hex="#7c8a7a", price=800),
         ]),
    dict(slug="kitchen", name="Kitchen finish", selection_type=SelectionType.single, display="swatches", sort_order=2,
         description="Cabinet and counter package.", options=[
             dict(slug="kitchen-light", name="Light oak & quartz", swatch_hex="#efece6", price=0, default=True),
             dict(slug="kitchen-walnut", name="Walnut & stone", swatch_hex="#a9825a", price=2_400),
             dict(slug="kitchen-black", name="Matte black & concrete", swatch_hex="#2a2b2b", price=1_800),
         ]),
    dict(slug="flooring", name="Flooring", selection_type=SelectionType.single, display="chips", sort_order=3,
         description="Priced per square foot of the home.", options=[
             dict(slug="floor-lvp", name="Luxury vinyl", price=0, default=True, per_sq_ft=True),
             dict(slug="floor-oak", name="Oak", price=3, per_sq_ft=True),
             dict(slug="floor-tile", name="Tile", price=2, per_sq_ft=True),
             dict(slug="floor-concrete", name="Concrete", price=1, per_sq_ft=True),
         ]),
    dict(slug="upgrades", name="Upgrades", selection_type=SelectionType.multi, display="cards", sort_order=4,
         description="Optional. Pick any.", options=[
             dict(slug="up-porch", name="Covered front porch", price=9_500, description="Adds ~120 sq ft of covered outdoor space."),
             dict(slug="up-solar", name="Solar-ready roof", price=4_200, description="Conduit, structure and panel layout prepared."),
             dict(slug="up-heatpump", name="High-efficiency heat pump", price=6_800, description="Upgraded heating, cooling and water heating."),
             dict(slug="up-smart", name="Smart home package", price=2_100, description="Thermostat, locks, leak sensors."),
         ]),
]

ASSUMPTIONS = dict(name="MVP placeholder v1", is_active=True, interest_rate_bps=700, term_years=30,
                   down_payment_bps=500, closing_cost_bps=300, soft_cost_bps=700, contingency_bps=600,
                   delivery_cents=10_000 * K, two_story_premium_cents=85_000 * K,
                   notes="Placeholder assumptions for the MVP. Replace with lender-reviewed figures.")

# (slug, name, state, cost index bps, site $, land $, permit $, permit weeks, tax bps, insurance $/yr, zip prefixes)
MARKETS = [
    ("national", "National average (sample)", None, 10000, 65_000, 60_000, 4_000, (12, 26), 100, 1_800, [], True),
    ("sacramento-ca", "Sacramento, CA (sample)", "CA", 11200, 78_000, 95_000, 9_000, (16, 30), 110, 1_800, ["956", "957", "958"], False),
    ("austin-tx", "Austin, TX (sample)", "TX", 9800, 62_000, 85_000, 6_000, (12, 24), 190, 2_600, ["786", "787"], False),
    ("phoenix-az", "Phoenix, AZ (sample)", "AZ", 9600, 58_000, 70_000, 5_000, (10, 20), 60, 1_700, ["850", "852", "853"], False),
    ("raleigh-nc", "Raleigh, NC (sample)", "NC", 9500, 60_000, 65_000, 5_500, (10, 22), 85, 1_500, ["275", "276"], False),
    ("boise-id", "Boise, ID (sample)", "ID", 10000, 64_000, 80_000, 6_000, (12, 24), 70, 1_300, ["836", "837"], False),
]

PATH_STAGES = [
    dict(slug="design", name="Design", who="Autonodwell architect · engineer", weeks_low=4, weeks_high=8, cost_key="soft_contingency",
         description="Your selections become a permit-ready plan set, engineered for your site.",
         next_action="Review your design with an Autonodwell consultant."),
    dict(slug="site", name="Site", who="Land · zoning · utilities", weeks_low=4, weeks_high=12, cost_key="land",
         description="Confirm a buildable lot: zoning, setbacks, access, water, power and sewer.",
         next_action="Tell us whether you own land or need help finding it."),
    dict(slug="financing", name="Financing", who="Participating lender", weeks_low=4, weeks_high=8, cost_key=None,
         description="A construction-to-permanent loan or other financing from a qualified lender.",
         next_action="Connect with a participating lender. Lenders make their own credit decisions."),
    dict(slug="approvals", name="Approvals", who="Local permitting office", weeks_low=12, weeks_high=26, cost_key=None,
         description="Building permits and inspections. Timelines vary widely by city and county.",
         next_action="We prepare and track the permit package for your jurisdiction."),
    dict(slug="construction", name="Construction", who="Builder · suppliers", weeks_low=16, weeks_high=24, cost_key="home_delivery",
         description="Site work, foundation, home delivery and installation, then finishes and inspections.",
         next_action="Schedule is set once permits and financing are in place."),
    dict(slug="keys", name="Keys", who="You", weeks_low=0, weeks_high=1, cost_key=None,
         description="Final inspection, closing on permanent financing, and move-in.",
         next_action="Your home records and maintenance plan continue after closing."),
]


def _get_or_create(db: Session, model, slug: str, **values):
    obj = db.scalar(select(model).where(model.slug == slug))
    if obj is None:
        obj = model(slug=slug, **values)
        db.add(obj)
        db.flush()
    return obj


def seed_reference(db: Session) -> None:
    for m in HOME_MODELS:
        _get_or_create(db, HomeModel, m["slug"], **{k: v for k, v in m.items() if k != "slug"})
    for c in CATEGORIES:
        opts = c["options"]
        cat = _get_or_create(db, OptionCategory, c["slug"], **{k: v for k, v in c.items() if k not in ("slug", "options")})
        for i, o in enumerate(opts):
            _get_or_create(
                db, Option, o["slug"], category_id=cat.id, name=o["name"], description=o.get("description"),
                pricing_mode=PricingMode.per_sq_ft if o.get("per_sq_ft") else PricingMode.flat,
                price_cents=o["price"] * K, swatch_hex=o.get("swatch_hex"), is_default=o.get("default", False),
                sort_order=i,
            )
    if db.scalar(select(AssumptionSet).limit(1)) is None:
        db.add(AssumptionSet(**ASSUMPTIONS))
    for slug, name, st, idx, site, land, permit, (wl, wh), tax, ins, prefixes, default in MARKETS:
        m = _get_or_create(
            db, Market, slug, name=name, state=st, is_default=default, is_sample=True,
            construction_cost_index_bps=idx, site_install_cents=site * K, land_allocation_cents=land * K,
            permit_fees_cents=permit * K, permit_weeks_low=wl, permit_weeks_high=wh, property_tax_bps=tax,
            insurance_annual_cents=ins * K, data_source="Placeholder sample data — not sourced. Replace before launch.",
        )
        for p in prefixes:
            if db.get(ZipPrefix, p) is None:
                db.add(ZipPrefix(prefix=p, market_id=m.id))
    for i, s in enumerate(PATH_STAGES):
        _get_or_create(db, PathStage, s["slug"], sort_order=i, **{k: v for k, v in s.items() if k != "slug"})
    db.commit()


def seed_demo(db: Session) -> None:
    """Local development only: dev-token accounts and a few leads to click through."""

    def user(uid, email, name, role):
        u = db.scalar(select(User).where(User.firebase_uid == uid))
        if u is None:
            u = User(firebase_uid=uid, email=email, full_name=name, role=role, is_anonymous=False)
            db.add(u)
            db.flush()
        return u

    user("demo-admin", "admin@example.com", "Demo Admin", Role.admin)
    rep = user("demo-sales", "sales@example.com", "Demo Sales Rep", Role.sales)
    if db.scalar(select(Lead).limit(1)):
        db.commit()
        return
    models = {m.slug: m for m in db.scalars(select(HomeModel))}
    from .services.designs import estimate_for

    samples = [
        ("Jordan Lee", "jordan@example.com", "95816", "model-two", 2_400, LeadStatus.new, None),
        ("Priya Shah", "priya@example.com", "78704", "model-three", 3_100, LeadStatus.contacted, rep),
        ("Marcus Hill", "marcus@example.com", "27601", "model-one", 1_800, LeadStatus.consultation_scheduled, rep),
    ]
    for i, (name, email, zip_, slug, budget, status, assignee) in enumerate(samples):
        cust = user(f"demo-customer-{i}", email, name, Role.customer)
        d = Design(user_id=cust.id, name=models[slug].name, home_model=models[slug], zip_code=zip_,
                   monthly_budget_cents=budget * K, selections=[], status=DesignStatus.submitted, current_step=5)
        db.add(d)
        db.flush()
        e = estimate_for(db, d)
        d.submitted_estimate = e
        lead = Lead(user_id=cust.id, design_id=d.id, status=status, assigned_to_id=assignee.id if assignee else None,
                    full_name=name, email=email, zip_code=zip_, preferred_contact="email",
                    estimate_total_cents=e["total_cents"], monthly_budget_cents=budget * K,
                    contact_consent=True, consent_text="(demo data)", message="Demo lead for local development.")
        db.add(lead)
        db.flush()
        db.add(LeadActivity(lead_id=lead.id, kind="created", body="Customer requested a consultant review"))
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_reference(session)
        if "--demo" in sys.argv:
            seed_demo(session)
    print("Seed complete")
