"""construction cost factor and area type by ZIP

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-14 08:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('zip_land_values', sa.Column('construction_index_bps', sa.Integer(), nullable=True))
    op.add_column('zip_land_values', sa.Column('factor_basis', sa.String(length=10), nullable=True))
    op.add_column('zip_land_values', sa.Column('area_type', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('zip_land_values', 'area_type')
    op.drop_column('zip_land_values', 'factor_basis')
    op.drop_column('zip_land_values', 'construction_index_bps')
