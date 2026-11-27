"""financing step wording: no "participating lender" claim, lender-chosen terms

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-27 10:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = dict(
    who="Your chosen lender",
    description="A construction-to-permanent loan or other financing from a licensed lender you choose.",
    next_action="Talk with a licensed lender. Autonodwell is not a lender or mortgage broker; lenders make their own credit decisions.",
)
OLD = dict(
    who="Participating lender",
    description="A construction-to-permanent loan or other financing from a qualified lender.",
    next_action="Connect with a participating lender. Lenders make their own credit decisions.",
)


def _set(values: dict) -> None:
    op.execute(
        sa.text("UPDATE path_stages SET who = :who, description = :description, next_action = :next_action WHERE slug = 'financing'")
        .bindparams(**values)
    )


def upgrade() -> None:
    _set(NEW)


def downgrade() -> None:
    _set(OLD)
