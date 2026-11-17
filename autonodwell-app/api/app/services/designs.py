from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Design, HomeModel, Lead, Option, OptionCategory, SelectionType
from . import estimate as est


def get_home_model(db: Session, model_id: int) -> HomeModel:
    hm = db.get(HomeModel, model_id)
    if hm is None or not hm.is_active:
        raise HTTPException(422, "Unknown home model")
    return hm


def resolve_home_model(db: Session, model_id: int | None) -> HomeModel:
    """The chosen model, or Model Two when the customer has not picked one yet."""
    if model_id is not None:
        return get_home_model(db, model_id)
    hm = db.scalar(select(HomeModel).where(HomeModel.slug == "model-two", HomeModel.is_active.is_(True)))
    if hm is None:
        hm = db.scalar(
            select(HomeModel).where(HomeModel.is_active.is_(True)).order_by(HomeModel.sort_order, HomeModel.id)
        )
    if hm is None:
        raise HTTPException(422, "Unknown home model")
    return hm


def checked_style_stories(data: dict, *, current_style: str | None = None, current_stories: int | None = None) -> None:
    """stories=2 is only valid with Mid-Century Modern. Leaving that style resets stories to 1."""
    if "style" not in data and "stories" not in data:
        return
    style = data["style"] if "style" in data else current_style
    stories = data["stories"] if "stories" in data else current_stories
    if "style" in data and style != "mcm" and "stories" not in data:
        stories = 1
    if stories == 2 and style != "mcm":
        raise HTTPException(422, "Two stories are only available for Mid-Century Modern")
    if "style" in data:
        data["style"] = style
    data["stories"] = stories


def normalize_selections(db: Session, option_ids: list[int] | None) -> list[Option]:
    """Validates option ids and fills in defaults, so every single-choice category
    has exactly one selection. Unknown or inactive ids are rejected."""
    categories = db.scalars(select(OptionCategory).order_by(OptionCategory.sort_order)).all()
    chosen = set(option_ids or [])
    by_id = {o.id: o for c in categories for o in c.options if o.is_active}
    unknown = chosen - set(by_id)
    if unknown:
        raise HTTPException(422, f"Unknown options: {sorted(unknown)}")

    result: list[Option] = []
    for c in categories:
        active = [o for o in c.options if o.is_active]
        picked = [o for o in active if o.id in chosen]
        if c.selection_type == SelectionType.single:
            if len(picked) > 1:
                raise HTTPException(422, f"Choose only one option for {c.name}")
            if not picked:
                picked = [o for o in active if o.is_default][:1] or active[:1]
        result.extend(picked)
    return result


def estimate_for(db: Session, design: Design) -> dict:
    options = normalize_selections(db, design.selections)
    return est.calculate(
        db, est.Inputs(
            design.home_model, options, design.zip_code, design.monthly_budget_cents,
            design.land_status, design.lot_price_cents, design.stories,
        )
    )


def design_out(db: Session, design: Design) -> dict:
    e = estimate_for(db, design)
    lead = db.scalar(select(Lead).where(Lead.design_id == design.id).order_by(Lead.created_at.desc()))
    return {
        "id": design.id,
        "name": design.name,
        "home_model": design.home_model,
        "monthly_budget_cents": design.monthly_budget_cents,
        "zip_code": design.zip_code,
        "land_status": design.land_status,
        "budget_mode": design.budget_mode,
        "total_budget_cents": design.total_budget_cents,
        "cash_available_cents": design.cash_available_cents,
        "site_address": design.site_address,
        "lot_price_cents": design.lot_price_cents,
        "style": design.style,
        "stories": design.stories,
        "status": design.status,
        "current_step": design.current_step,
        "created_at": design.created_at,
        "updated_at": design.updated_at,
        "option_ids": design.selections,
        "estimate": e,
        "path_home": est.path_home(db, e),
        "lead_status": lead.status if lead else None,
    }
