"""house style on a design

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-14 15:20:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('designs', sa.Column('style', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('designs', 'style')
