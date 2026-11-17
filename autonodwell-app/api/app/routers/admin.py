"""Admin: prices, options, financing assumptions, sample market data, team roles.
Lets the founder change numbers without a developer or a database dashboard."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..models import AssumptionSet, HomeModel, Market, Option, User
from ..schemas import (
    AssumptionsIn, AssumptionsOut, HomeModelOut, HomeModelPatch, MarketOut, MarketPatch,
    MeOut, OptionOut, OptionPatch, UserRolePatch,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _patch(obj, body):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)


@router.get("/home-models", response_model=list[HomeModelOut])
def list_models(db: Session = Depends(get_db)):
    return db.scalars(select(HomeModel).order_by(HomeModel.sort_order)).all()


@router.patch("/home-models/{model_id}", response_model=HomeModelOut)
def patch_model(model_id: int, body: HomeModelPatch, db: Session = Depends(get_db)):
    m = db.get(HomeModel, model_id) or _404()
    _patch(m, body)
    db.commit()
    return m


@router.patch("/options/{option_id}", response_model=OptionOut)
def patch_option(option_id: int, body: OptionPatch, db: Session = Depends(get_db)):
    o = db.get(Option, option_id) or _404()
    _patch(o, body)
    db.commit()
    return o


@router.get("/assumptions", response_model=AssumptionsOut)
def get_assumptions(db: Session = Depends(get_db)):
    return db.scalar(select(AssumptionSet).where(AssumptionSet.is_active.is_(True))) or _404()


@router.post("/assumptions", response_model=AssumptionsOut, status_code=201)
def new_assumptions(body: AssumptionsIn, db: Session = Depends(get_db)):
    db.execute(update(AssumptionSet).values(is_active=False))
    a = AssumptionSet(**body.model_dump(), is_active=True)
    db.add(a)
    db.commit()
    return a


@router.get("/markets", response_model=list[MarketOut])
def list_markets(db: Session = Depends(get_db)):
    out = []
    for m in db.scalars(select(Market).order_by(Market.is_default.desc(), Market.name)):
        d = MarketOut.model_validate(m).model_dump(exclude={"zip_prefixes"})
        out.append({**d, "zip_prefixes": [z.prefix for z in m.zip_prefixes]})
    return out


@router.patch("/markets/{market_id}", response_model=MarketOut)
def patch_market(market_id: int, body: MarketPatch, db: Session = Depends(get_db)):
    m = db.get(Market, market_id) or _404()
    _patch(m, body)
    db.commit()
    d = MarketOut.model_validate(m).model_dump(exclude={"zip_prefixes"})
    return {**d, "zip_prefixes": [z.prefix for z in m.zip_prefixes]}


@router.get("/users", response_model=list[MeOut])
def list_users(q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(User).where(User.is_anonymous.is_(False))
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(User.created_at.desc()).limit(200)).all()


@router.patch("/users/{user_id}", response_model=MeOut)
def set_role(user_id: uuid.UUID, body: UserRolePatch, db: Session = Depends(get_db)):
    u = db.get(User, user_id) or _404()
    if u.is_anonymous:
        raise HTTPException(422, "User must sign in before getting a staff role")
    u.role = body.role
    db.commit()
    return u


def _404():
    raise HTTPException(404, "Not found")
