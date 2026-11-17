"""national land prices by 3-digit ZIP

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14 08:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'zip_land_values',
        sa.Column('prefix', sa.String(length=3), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('land_cents', sa.Integer(), nullable=False),
        sa.Column('basis', sa.String(length=10), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('prefix'),
    )


def downgrade() -> None:
    op.drop_table('zip_land_values')
