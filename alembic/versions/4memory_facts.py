"""ADR-006 Phase 1 (M2) — memory_entities + memory_facts (ontology-lite fact store)

Revision ID: 4memory_facts
Revises: 3nephilim_progression
Create Date: 2026-07-04

Two-table temporal fact store for companion memory. Dual-covered with
MemoryFactRepository._ensure_table() (which self-creates in Docker/test envs that
skip alembic). See ADR-006 Phase 1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4memory_facts'
down_revision: Union[str, None] = '3nephilim_progression'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the ontology-lite fact store."""
    op.create_table(
        'memory_entities',
        sa.Column('entity_id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('entity_type', sa.Text(), server_default='person', nullable=False),
        sa.Column('properties', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('entity_id'),
    )
    op.create_index(
        'idx_memory_entities_user', 'memory_entities',
        ['user_id', 'entity_type', 'name'],
    )

    op.create_table(
        'memory_facts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('subject_id', sa.Text(), nullable=False),
        sa.Column('predicate', sa.Text(), nullable=False),
        sa.Column('object', sa.Text(), nullable=False),
        sa.Column('object_type', sa.Text(), server_default='literal', nullable=False),
        sa.Column('valid_from', sa.Text(), nullable=False),
        sa.Column('valid_to', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('source_session_id', sa.Text(), nullable=True),
        sa.Column('source_message_id', sa.Text(), nullable=True),
        sa.Column('superseded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['subject_id'], ['memory_entities.entity_id']),
        sa.ForeignKeyConstraint(['superseded_by'], ['memory_facts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_memory_facts_subject_pred', 'memory_facts',
        ['user_id', 'subject_id', 'predicate'],
    )
    op.create_index('idx_memory_facts_valid', 'memory_facts', ['valid_to'])


def downgrade() -> None:
    op.drop_index('idx_memory_facts_valid', table_name='memory_facts')
    op.drop_index('idx_memory_facts_subject_pred', table_name='memory_facts')
    op.drop_table('memory_facts')
    op.drop_index('idx_memory_entities_user', table_name='memory_entities')
    op.drop_table('memory_entities')
