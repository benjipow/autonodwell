"""Sales console: lead pipeline, assignment, notes, CRM sync, CSV export."""
import csv
import io
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth import require_staff
from ..db import get_db
from ..models import Lead, LeadActivity, LeadStatus, Role, User
from ..schemas import LeadDetail, LeadPage, LeadPatch, NoteIn, StaffOut
from ..services import crm

router = APIRouter(prefix="/sales", tags=["sales"])


def _filtered(status: LeadStatus | None, assigned: str | None, q: str | None, staff: User):
    stmt = select(Lead)
    if status:
        stmt = stmt.where(Lead.status == status)
    if assigned == "me":
        stmt = stmt.where(Lead.assigned_to_id == staff.id)
    elif assigned == "none":
        stmt = stmt.where(Lead.assigned_to_id.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Lead.full_name.ilike(like), Lead.email.ilike(like), Lead.phone.ilike(like), Lead.zip_code.ilike(like)))
    return stmt


def _detail(db: Session, lead: Lead) -> dict:
    d = LeadDetail.model_validate(lead, from_attributes=True).model_dump()
    if lead.design:
        d.update(design_name=lead.design.name, home_model_name=lead.design.home_model.name,
                 submitted_estimate=lead.design.submitted_estimate)
    return d


def _get(db: Session, lead_id: uuid.UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return lead


@router.get("/team", response_model=list[StaffOut])
def team(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return db.scalars(select(User).where(User.role.in_([Role.sales, Role.admin])).order_by(User.full_name)).all()


@router.get("/leads", response_model=LeadPage)
def list_leads(
    status: LeadStatus | None = None,
    assigned: str | None = Query(default=None, pattern="^(me|none)$"),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
):
    stmt = _filtered(status, assigned, q, staff)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    counts = dict(db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "counts_by_status": {s.value: counts.get(s, 0) for s in LeadStatus}}


@router.get("/leads.csv")
def export_leads(
    status: LeadStatus | None = None, assigned: str | None = None, q: str | None = None,
    db: Session = Depends(get_db), staff: User = Depends(require_staff),
):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "created_at", "status", "name", "email", "phone", "zip", "estimate_usd", "budget_usd_mo", "assigned_to", "crm_contact_id"])
    for l in db.scalars(_filtered(status, assigned, q, staff).order_by(Lead.created_at.desc())):
        w.writerow([l.id, l.created_at.isoformat(), l.status.value, l.full_name, l.email, l.phone, l.zip_code,
                    (l.estimate_total_cents or 0) // 100, (l.monthly_budget_cents or 0) // 100,
                    l.assigned_to.email if l.assigned_to else "", l.crm_contact_id or ""])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=autonodwell-leads.csv"})


@router.get("/leads/{lead_id}", response_model=LeadDetail)
def get_lead(lead_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return _detail(db, _get(db, lead_id))


@router.patch("/leads/{lead_id}", response_model=LeadDetail)
def update_lead(
    lead_id: uuid.UUID, body: LeadPatch, background: BackgroundTasks,
    db: Session = Depends(get_db), staff: User = Depends(require_staff),
):
    lead = _get(db, lead_id)
    sync = False
    if body.status and body.status != lead.status:
        db.add(LeadActivity(lead_id=lead.id, actor_id=staff.id, kind="status",
                            body=f"Status: {lead.status.value} → {body.status.value}",
                            data={"from": lead.status.value, "to": body.status.value}))
        lead.status, sync = body.status, True
    if body.unassign and lead.assigned_to_id:
        lead.assigned_to_id = None
        db.add(LeadActivity(lead_id=lead.id, actor_id=staff.id, kind="assignment", body="Unassigned"))
    elif body.assigned_to_id and body.assigned_to_id != lead.assigned_to_id:
        rep = db.get(User, body.assigned_to_id)
        if rep is None or rep.role not in (Role.sales, Role.admin):
            raise HTTPException(422, "Can only assign to sales team members")
        lead.assigned_to_id = rep.id
        db.add(LeadActivity(lead_id=lead.id, actor_id=staff.id, kind="assignment",
                            body=f"Assigned to {rep.full_name or rep.email}"))
    ev = crm.enqueue_lead_sync(db, lead, "status_changed") if sync else None
    db.commit()
    if ev:
        background.add_task(crm.run_in_background, ev.id)
    db.refresh(lead)
    return _detail(db, lead)


@router.post("/leads/{lead_id}/notes", response_model=LeadDetail)
def add_note(lead_id: uuid.UUID, body: NoteIn, db: Session = Depends(get_db), staff: User = Depends(require_staff)):
    lead = _get(db, lead_id)
    db.add(LeadActivity(lead_id=lead.id, actor_id=staff.id, kind="note", body=body.body))
    db.commit()
    db.refresh(lead)
    return _detail(db, lead)


@router.post("/leads/{lead_id}/crm-sync", response_model=LeadDetail)
def resync(lead_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Manual retry — runs synchronously so the rep sees the result immediately."""
    lead = _get(db, lead_id)
    ev = crm.enqueue_lead_sync(db, lead, "manual_resync")
    db.commit()
    crm.process_event(db, ev.id)
    db.refresh(lead)
    return _detail(db, lead)
