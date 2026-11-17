"""model two is 1,200 sq ft

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-13 17:40:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE home_models SET sq_ft = 1200 WHERE slug = 'model-two'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE home_models SET sq_ft = 1100 WHERE slug = 'model-two'"))
