"""Endpoints that need no sign-in: the catalog and a stateless estimate preview."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import HomeModel, OptionCategory
from ..schemas import CatalogOut, EstimateIn, EstimateOut, LandBudgetIn, LandBudgetOut, OptionCategoryOut, OptionOut
from ..services import estimate as est
from ..services.designs import get_home_model, normalize_selections

router = APIRouter(tags=["catalog"])


@router.get("/health", include_in_schema=False)
def health():
    return {"ok": True}


@router.get("/catalog", response_model=CatalogOut)
def catalog(db: Session = Depends(get_db)):
    models = db.scalars(
        select(HomeModel).where(HomeModel.is_active.is_(True)).order_by(HomeModel.sort_order)
    ).all()
    cats = []
    for c in db.scalars(select(OptionCategory).order_by(OptionCategory.sort_order)):
        cats.append(
            OptionCategoryOut(
                id=c.id, slug=c.slug, name=c.name, description=c.description,
                selection_type=c.selection_type, display=c.display,
                options=[OptionOut.model_validate(o) for o in c.options if o.is_active],
            )
        )
    return {"home_models": models, "categories": cats, "disclaimer": est.DISCLAIMER}


@router.post("/estimate", response_model=EstimateOut)
def estimate_preview(body: EstimateIn, db: Session = Depends(get_db)):
    hm = get_home_model(db, body.home_model_id)
    opts = normalize_selections(db, body.option_ids)
    e = est.calculate(db, est.Inputs(
        hm, opts, body.zip_code, body.monthly_budget_cents, body.land_status, body.lot_price_cents, body.stories,
    ))
    return {"estimate": e, "path_home": est.path_home(db, e)}


@router.post("/land-budget", response_model=LandBudgetOut)
def land_budget(body: LandBudgetIn, db: Session = Depends(get_db)):
    return est.land_budget(
        db,
        budget_mode=body.budget_mode,
        total_budget_cents=body.total_budget_cents,
        monthly_budget_cents=body.monthly_budget_cents,
        cash_available_cents=body.cash_available_cents,
        zip_code=body.zip_code,
        stories=body.stories,
    )
