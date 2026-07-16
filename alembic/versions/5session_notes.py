"""session_notes table (ADR-011 per-session author's note)

Revision ID: 5session_notes
Revises: 4memory_facts
Create Date: 2026-07-16

Additive: one sticky author's note per session (the /note director directive).
Dual-covered by SessionNoteRepository._ensure_table for Docker/test envs that
skip alembic.
"""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = '5session_notes'
down_revision: Union[str, None] = '4memory_facts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'session_notes',
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id'),
    )


def downgrade() -> None:
    op.drop_table('session_notes')
