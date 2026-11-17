"""Customer-owned data: profile, designs, submitting to a consultant, privacy requests."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Design, DesignStatus, Lead, LeadActivity, LeadStatus, User
from ..schemas import DesignIn, DesignOut, DesignPatch, DesignSummary, MeOut, MePatch, SubmitIn
from ..services import crm
from ..services.designs import checked_style_stories, design_out, estimate_for, get_home_model, normalize_selections, resolve_home_model

router = APIRouter(tags=["customer"])


def _own_design(db: Session, user: User, design_id: uuid.UUID) -> Design:
    d = db.get(Design, design_id)
    if d is None or d.user_id != user.id or d.deleted_at is not None:
        raise HTTPException(404, "Design not found")
    return d


# ---------------------------------------------------------------- profile
@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=MeOut)
def update_me(body: MePatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    return user


@router.get("/me/export")
def export_my_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Right-to-know: everything we store about the signed-in person, as JSON."""
    designs = db.scalars(select(Design).where(Design.user_id == user.id)).all()
    leads = db.scalars(select(Lead).where(Lead.user_id == user.id)).all()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": MeOut.model_validate(user).model_dump(mode="json"),
        "designs": [
            {**DesignSummary.model_validate(d).model_dump(mode="json"), "option_ids": d.selections,
             "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None}
            for d in designs
        ],
        "consultation_requests": [
            {"id": str(l.id), "status": l.status.value, "created_at": l.created_at.isoformat(),
             "full_name": l.full_name, "email": l.email, "phone": l.phone, "zip_code": l.zip_code,
             "message": l.message, "consent_text": l.consent_text}
            for l in leads
        ],
    }


@router.delete("/me", status_code=204)
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Right-to-delete: removes designs and profile, strips personal data from leads.
    The (anonymised) lead row is kept so sales reporting totals stay correct."""
    for lead in db.scalars(select(Lead).where(Lead.user_id == user.id)):
        lead.full_name = lead.email = lead.phone = lead.message = None
        lead.status = LeadStatus.lost
        db.add(LeadActivity(lead_id=lead.id, kind="privacy", body="Customer deleted their account; personal data removed."))
    db.delete(user)  # designs cascade
    db.commit()
    from ..config import get_settings

    if get_settings().auth_mode == "firebase":
        from firebase_admin import auth as fb_auth

        try:
            fb_auth.delete_user(user.firebase_uid)
        except Exception:  # noqa: BLE001
            pass
    return Response(status_code=204)


# ---------------------------------------------------------------- designs
@router.get("/designs", response_model=list[DesignSummary])
def list_designs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Design)
        .where(Design.user_id == user.id, Design.deleted_at.is_(None))
        .order_by(Design.updated_at.desc())
    ).all()


@router.post("/designs", response_model=DesignOut, status_code=201)
def create_design(body: DesignIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    hm = resolve_home_model(db, body.home_model_id)
    opts = normalize_selections(db, body.option_ids)
    fields = body.model_dump(exclude_unset=True)
    checked_style_stories(fields)
    d = Design(
        user_id=user.id,
        name=body.name or hm.name,
        home_model=hm,
        monthly_budget_cents=body.monthly_budget_cents,
        zip_code=body.zip_code,
        land_status=body.land_status,
        budget_mode=body.budget_mode,
        total_budget_cents=body.total_budget_cents,
        cash_available_cents=body.cash_available_cents,
        site_address=body.site_address,
        lot_price_cents=body.lot_price_cents,
        style=fields.get("style"),
        stories=fields.get("stories"),
        selections=[o.id for o in opts],
        current_step=body.current_step,
    )
    db.add(d)
    db.commit()
    return design_out(db, d)


@router.get("/designs/{design_id}", response_model=DesignOut)
def get_design(design_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return design_out(db, _own_design(db, user, design_id))


@router.patch("/designs/{design_id}", response_model=DesignOut)
def update_design(design_id: uuid.UUID, body: DesignPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _own_design(db, user, design_id)
    data = body.model_dump(exclude_unset=True)
    checked_style_stories(data, current_style=d.style, current_stories=d.stories)
    if "home_model_id" in data:
        d.home_model = get_home_model(db, data.pop("home_model_id"))
    if "option_ids" in data:
        d.selections = [o.id for o in normalize_selections(db, data.pop("option_ids"))]
    for k, v in data.items():
        setattr(d, k, v)
    d.updated_at = datetime.now(timezone.utc)
    db.commit()
    return design_out(db, d)


@router.post("/designs/{design_id}/duplicate", response_model=DesignOut, status_code=201)
def duplicate_design(design_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    src = _own_design(db, user, design_id)
    d = Design(
        user_id=user.id, name=f"{src.name} (copy)"[:120], home_model_id=src.home_model_id,
        monthly_budget_cents=src.monthly_budget_cents, zip_code=src.zip_code,
        land_status=src.land_status, budget_mode=src.budget_mode,
        total_budget_cents=src.total_budget_cents, cash_available_cents=src.cash_available_cents,
        site_address=src.site_address, lot_price_cents=src.lot_price_cents,
        style=src.style, stories=src.stories,
        selections=list(src.selections), current_step=src.current_step,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return design_out(db, d)


@router.delete("/designs/{design_id}", status_code=204)
def delete_design(design_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _own_design(db, user, design_id)
    d.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.post("/designs/{design_id}/submit", response_model=DesignOut)
def submit_design(
    design_id: uuid.UUID,
    body: SubmitIn,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Step 4 → 'Review with a consultant'. Creates (or updates) the sales lead and syncs it to the CRM."""
    if user.is_anonymous:
        raise HTTPException(401, "Sign in to send your design to a consultant")
    if not body.contact_consent:
        raise HTTPException(422, "Consent to be contacted is required")
    d = _own_design(db, user, design_id)
    e = estimate_for(db, d)

    user.full_name = user.full_name or body.full_name
    user.phone = user.phone or body.phone

    lead = db.scalar(select(Lead).where(Lead.design_id == d.id))
    is_new = lead is None
    if is_new:
        lead = Lead(user_id=user.id, design_id=d.id)
        db.add(lead)
    lead.full_name, lead.email, lead.phone = body.full_name, str(body.email).lower(), body.phone
    lead.preferred_contact, lead.message = body.preferred_contact, body.message
    lead.zip_code, lead.monthly_budget_cents = d.zip_code, d.monthly_budget_cents
    lead.estimate_total_cents = e["total_cents"]
    lead.contact_consent, lead.consent_text = True, body.consent_text

    d.status, d.submitted_estimate, d.current_step = DesignStatus.submitted, e, 5
    db.flush()
    db.add(LeadActivity(lead_id=lead.id, actor_id=user.id, kind="created" if is_new else "resubmitted",
                        body="Customer requested a consultant review", data={"estimate_total_cents": e["total_cents"]}))
    ev = crm.enqueue_lead_sync(db, lead, "created" if is_new else "resubmitted")
    db.commit()
    background.add_task(crm.run_in_background, ev.id)
    return design_out(db, d)
