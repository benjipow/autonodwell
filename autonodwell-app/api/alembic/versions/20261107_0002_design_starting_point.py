"""design starting point

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07 18:33:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('designs', sa.Column('land_status', sa.String(length=20), nullable=True))
    op.add_column('designs', sa.Column('budget_mode', sa.String(length=20), nullable=True))
    op.add_column('designs', sa.Column('total_budget_cents', sa.Integer(), nullable=True))
    op.add_column('designs', sa.Column('cash_available_cents', sa.Integer(), nullable=True))
    op.add_column('designs', sa.Column('site_address', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('designs', 'site_address')
    op.drop_column('designs', 'cash_available_cents')
    op.drop_column('designs', 'total_budget_cents')
    op.drop_column('designs', 'budget_mode')
    op.drop_column('designs', 'land_status')
