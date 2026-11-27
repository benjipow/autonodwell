"""The estimator. This is the ONLY place prices and payments are calculated —
the web app and any future native app just display what this returns.

All math is in integer cents. Output is a plain dict (JSON-serialisable) so it can be
frozen onto a design when the customer submits it.
"""
import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AssumptionSet, HomeModel, Market, Option, PathStage, PricingMode, ZipLandValue, ZipPrefix

DISCLAIMER = (
    "Estimate, not a quote. A preliminary affordability estimate is not mortgage preapproval or a loan offer. "
    "Rates, terms and payments shown are examples only; your actual rate, APR, fees and eligibility come from your lender. "
    "Prices, land, permits and financing shown are planning assumptions and will change."
)
CONSTRUCTION_SOURCE = "DoD area cost factors, 2026"


@dataclass
class Inputs:
    home_model: HomeModel
    options: list[Option]
    zip_code: str | None
    monthly_budget_cents: int | None
    land_status: str | None = None
    lot_price_cents: int | None = None
    stories: int | None = None


def resolve_market(db: Session, zip_code: str | None) -> tuple[Market, bool]:
    """Returns (market, matched). Falls back to the default market for unknown ZIPs.
    Swap this function for the real location-data service when it exists."""
    if zip_code and len(zip_code) >= 3:
        zp = db.get(ZipPrefix, zip_code[:3])
        if zp:
            return zp.market, True
    default = db.scalar(select(Market).where(Market.is_default.is_(True)))
    if default is None:
        raise RuntimeError("No default market configured")
    return default, False


def land_for_zip(db: Session, zip_code: str | None) -> ZipLandValue | None:
    """Quarter-acre land price for the first 3 digits of a ZIP, if we have one."""
    if not zip_code or len(zip_code) < 3:
        return None
    return db.get(ZipLandValue, zip_code[:3])


def construction_index_bps(market: Market, zip_row: ZipLandValue | None) -> int:
    """ZIP-area construction factor when the row has one, otherwise the market index."""
    if zip_row is not None and zip_row.construction_index_bps is not None:
        return zip_row.construction_index_bps
    return market.construction_cost_index_bps


def active_assumptions(db: Session) -> AssumptionSet:
    a = db.scalar(select(AssumptionSet).where(AssumptionSet.is_active.is_(True)))
    if a is None:
        raise RuntimeError("No active assumption set")
    return a


def monthly_payment_cents(principal_cents: int, rate_bps: int, years: int) -> int:
    n = years * 12
    r = rate_bps / 10000 / 12
    if r == 0:
        return round(principal_cents / n)
    return round(principal_cents * r / (1 - (1 + r) ** -n))


def _pct(amount: int, bps: int) -> int:
    return round(amount * bps / 10000)


def option_price_cents(opt: Option, sq_ft: int) -> int:
    return opt.price_cents * sq_ft if opt.pricing_mode == PricingMode.per_sq_ft else opt.price_cents


def calculate(db: Session, inp: Inputs) -> dict:
    a = active_assumptions(db)
    market, matched = resolve_market(db, inp.zip_code)
    hm = inp.home_model

    options_total = sum(option_price_cents(o, hm.sq_ft) for o in inp.options)
    zip_row = land_for_zip(db, inp.zip_code)
    index = construction_index_bps(market, zip_row)
    home = _pct(hm.base_price_cents + options_total, index)
    home_and_delivery = home + a.delivery_cents
    two_story = _pct(a.two_story_premium_cents, index) if inp.stories == 2 else 0
    site = market.site_install_cents
    owns_lot = inp.land_status == "own_lot"
    asking = inp.land_status == "looking_at_lot" and inp.lot_price_cents is not None
    zip_land = None
    if owns_lot:
        land, land_label = 0, "Land (you own the lot)"
    elif asking:
        land, land_label = inp.lot_price_cents, "Land (asking price)"
    else:
        zip_land = zip_row
        if zip_land is not None:
            land, land_label = zip_land.land_cents, "Land allocation"
        else:
            land, land_label = market.land_allocation_cents, "Land allocation"
    hard = home_and_delivery + two_story + site + land
    soft = _pct(hard, a.soft_cost_bps) + _pct(hard, a.contingency_bps) + market.permit_fees_cents
    total = hard + soft

    down = _pct(total, a.down_payment_bps)
    loan = total - down
    p_and_i = monthly_payment_cents(loan, a.interest_rate_bps, a.term_years)
    taxes = round(_pct(total, market.property_tax_bps) / 12)
    insurance = round(market.insurance_annual_cents / 12)
    monthly_all_in = p_and_i + taxes + insurance
    cash_needed = down + _pct(loan, a.closing_cost_bps)

    budget = inp.monthly_budget_cents
    if budget:
        ratio = monthly_all_in / budget
        fit = "within" if ratio <= 1 else "stretch" if ratio <= 1.1 else "over"
    else:
        fit = None

    lines = [
        {"key": "home_delivery", "label": "Home + delivery", "cents": home_and_delivery},
        {"key": "site_install", "label": "Site + installation", "cents": site},
        {"key": "land", "label": land_label, "cents": land},
        {"key": "soft_contingency", "label": "Soft costs + contingency", "cents": soft},
    ]
    if two_story:
        lines.insert(1, {"key": "two_story", "label": "Two-story option", "cents": two_story})
    return {
        "lines": lines,
        "options_total_cents": options_total,
        "total_cents": total,
        "down_payment_cents": down,
        "loan_cents": loan,
        "cash_needed_cents": cash_needed,
        "monthly": {
            "principal_interest_cents": p_and_i,
            "taxes_cents": taxes,
            "insurance_cents": insurance,
            "total_cents": monthly_all_in,
        },
        "budget": {"monthly_budget_cents": budget, "fit": fit},
        "assumptions": {
            "id": a.id,
            "name": a.name,
            "interest_rate_pct": a.interest_rate_bps / 100,
            "term_years": a.term_years,
            "down_payment_pct": a.down_payment_bps / 100,
            "closing_cost_pct": a.closing_cost_bps / 100,
            "soft_cost_pct": a.soft_cost_bps / 100,
            "contingency_pct": a.contingency_bps / 100,
        },
        "market": _market_out(market, matched, zip_land, zip_row),
        "disclaimer": DISCLAIMER,
    }


def _market_out(
    market: Market,
    matched: bool,
    zip_land: ZipLandValue | None = None,
    zip_row: ZipLandValue | None = None,
) -> dict:
    """zip_land is set only when that row's land price is the land line.
    zip_row is the area record, used for the construction factor even when land is not."""
    used_index = zip_row is not None and zip_row.construction_index_bps is not None
    return {
        "slug": market.slug,
        "name": market.name,
        "matched_zip": matched,
        "is_sample": market.is_sample,
        "data_source": market.data_source,
        "permit_weeks": [market.permit_weeks_low, market.permit_weeks_high],
        "land_source": zip_land.source if zip_land else None,
        "area_label": f"ZIP area {zip_land.prefix}, {zip_land.state}" if zip_land else None,
        "area_type": zip_row.area_type if zip_row else None,
        "construction_source": CONSTRUCTION_SOURCE if used_index else None,
    }


def land_budget(
    db: Session,
    *,
    budget_mode: str | None,
    total_budget_cents: int | None,
    monthly_budget_cents: int | None,
    cash_available_cents: int | None,
    zip_code: str | None,
    stories: int | None = None,
) -> dict:
    """How much land each active home leaves inside a total, monthly, or cash budget.

    The affordable project cost is the inverse of calculate(): a total budget is itself,
    a monthly budget solves back to the project cost that payment would support, and cash
    on hand caps the project at the down payment plus closing costs. Land is whatever is
    left after the home, delivery, site work, permits, and soft costs.
    """
    a = active_assumptions(db)
    market, matched = resolve_market(db, zip_code)
    # No owned lot and no asking price here. When a ZIP-area price exists it is
    # what calculate() uses instead of market.land_allocation_cents, so a budget
    # equal to that estimate solves back to the ZIP land price.
    zip_land = land_for_zip(db, zip_code)
    index_bps = construction_index_bps(market, zip_land)
    out_market = _market_out(market, matched, zip_land, zip_land)

    def unknown() -> dict:
        return {
            "affordable_total_cents": None,
            "limited_by": None,
            "per_model": [],
            "market": out_market,
            "disclaimer": DISCLAIMER,
        }

    amount = total_budget_cents if budget_mode == "total" else monthly_budget_cents
    if budget_mode == "need_help" or budget_mode not in ("total", "monthly") or amount is None:
        return unknown()

    d = a.down_payment_bps / 10000
    k = a.closing_cost_bps / 10000
    s = a.soft_cost_bps / 10000
    c = a.contingency_bps / 10000
    r = a.interest_rate_bps / 10000 / 12
    n = a.term_years * 12
    f = (1 / n) if r == 0 else r / (1 - (1 + r) ** -n)
    tax = market.property_tax_bps / 10000

    if budget_mode == "total":
        t_budget = float(amount)
    else:
        t_budget = (amount - market.insurance_annual_cents / 12) / ((1 - d) * f + tax / 12)

    if cash_available_cents is not None:
        t_cash = cash_available_cents / (d + k * (1 - d))
        if t_cash < t_budget:
            t, limited_by = t_cash, "cash"
        else:
            t, limited_by = t_budget, budget_mode
    else:
        t, limited_by = t_budget, budget_mode

    # Imported here: designs.normalize_selections is how a new design picks defaults,
    # and designs.py imports this module.
    from .designs import normalize_selections

    defaults = normalize_selections(db, None)
    per_model = []
    models = db.scalars(
        select(HomeModel).where(HomeModel.is_active.is_(True)).order_by(HomeModel.sort_order, HomeModel.id)
    )
    for hm in models:
        options_total = sum(option_price_cents(o, hm.sq_ft) for o in defaults)
        home = _pct(hm.base_price_cents + options_total, index_bps)
        home_and_delivery = home + a.delivery_cents
        two_story = _pct(a.two_story_premium_cents, index_bps) if stories == 2 else 0
        h = home_and_delivery + market.site_install_cents + two_story
        raw = (t - market.permit_fees_cents) / (1 + s + c) - h
        per_model.append(
            {
                "home_model_id": hm.id,
                "name": hm.name,
                "land_budget_cents": math.floor(raw / 100_000) * 100_000,
            }
        )

    return {
        "affordable_total_cents": round(t),
        "limited_by": limited_by,
        "per_model": per_model,
        "market": out_market,
        "disclaimer": DISCLAIMER,
    }


def path_home(db: Session, estimate: dict) -> list[dict]:
    costs = {line["key"]: line["cents"] for line in estimate["lines"]}
    permit_weeks = estimate["market"]["permit_weeks"]
    out = []
    for s in db.scalars(select(PathStage).order_by(PathStage.sort_order)):
        weeks = permit_weeks if s.slug == "approvals" else [s.weeks_low, s.weeks_high]
        out.append(
            {
                "slug": s.slug,
                "name": s.name,
                "who": s.who,
                "description": s.description,
                "next_action": s.next_action,
                "weeks": weeks,
                "cost_cents": costs.get(s.cost_key) if s.cost_key else None,
            }
        )
    return out
