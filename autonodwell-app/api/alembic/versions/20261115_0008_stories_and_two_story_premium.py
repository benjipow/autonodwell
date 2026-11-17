"""stories on a design, and the two-story premium

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-15 15:10:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('designs', sa.Column('stories', sa.Integer(), nullable=True))
    op.add_column(
        'assumption_sets',
        sa.Column('two_story_premium_cents', sa.Integer(), nullable=False, server_default='8500000'),
    )
    op.alter_column('assumption_sets', 'two_story_premium_cents', server_default=None)


def downgrade() -> None:
    op.drop_column('assumption_sets', 'two_story_premium_cents')
    op.drop_column('designs', 'stories')
