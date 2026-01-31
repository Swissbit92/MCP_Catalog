"""nephilim_progression_system

Revision ID: 3nephilim_progression
Revises: 2dba9f1a6b1e
Create Date: 2026-01-31

NEPHILIM Phase 3: Gamification System

Adds tables for:
- seeker_profiles: User progression (rank, resonance, faction)
- persona_affinity: Per-persona relationship tracking
- resonance_log: Event history for resonance changes
- unlocked_lore: Tracks which lore fragments have been unlocked
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3nephilim_progression'
down_revision: Union[str, None] = '2dba9f1a6b1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create NEPHILIM progression tables."""

    # Create seeker_profiles table
    # Tracks overall user progression in the NEPHILIM system
    op.create_table(
        'seeker_profiles',
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('rank_name', sa.Text(), server_default='Initiate'),
        sa.Column('total_resonance', sa.Integer(), server_default='0'),
        sa.Column('faction_primary', sa.Text(), nullable=True),
        sa.Column('faction_secondary', sa.Text(), nullable=True),
        sa.Column('rank_achieved_at', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create persona_affinity table
    # Tracks relationship with each individual Nephilim
    op.create_table(
        'persona_affinity',
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('persona_key', sa.Text(), nullable=False),
        sa.Column('messages_count', sa.Integer(), server_default='0'),
        sa.Column('affinity_level', sa.Integer(), server_default='0'),
        sa.Column('last_conversation', sa.Text(), nullable=True),
        sa.Column('first_conversation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['seeker_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'persona_key')
    )

    # Create resonance_log table
    # Audit trail of resonance gains for analytics and debugging
    op.create_table(
        'resonance_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('persona_key', sa.Text(), nullable=True),
        sa.Column('session_id', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['seeker_profiles.user_id'], ondelete='CASCADE')
    )

    # Create unlocked_lore table
    # Tracks which lore fragments have been unlocked by each user
    op.create_table(
        'unlocked_lore',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('persona_key', sa.Text(), nullable=False),
        sa.Column('fragment_id', sa.Text(), nullable=False),
        sa.Column('unlocked_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['seeker_profiles.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'persona_key', 'fragment_id', name='uq_user_persona_fragment')
    )

    # Create indexes for efficient queries
    op.create_index('idx_seeker_profiles_rank', 'seeker_profiles', ['rank_name'])
    op.create_index('idx_seeker_profiles_faction', 'seeker_profiles', ['faction_primary'])
    op.create_index('idx_persona_affinity_user', 'persona_affinity', ['user_id'])
    op.create_index('idx_persona_affinity_persona', 'persona_affinity', ['persona_key'])
    op.create_index('idx_resonance_log_user', 'resonance_log', ['user_id'])
    op.create_index('idx_resonance_log_timestamp', 'resonance_log', ['timestamp'])
    op.create_index('idx_unlocked_lore_user', 'unlocked_lore', ['user_id'])
    op.create_index('idx_unlocked_lore_persona', 'unlocked_lore', ['persona_key'])


def downgrade() -> None:
    """Drop NEPHILIM progression tables."""

    # Drop indexes
    op.drop_index('idx_unlocked_lore_persona', table_name='unlocked_lore')
    op.drop_index('idx_unlocked_lore_user', table_name='unlocked_lore')
    op.drop_index('idx_resonance_log_timestamp', table_name='resonance_log')
    op.drop_index('idx_resonance_log_user', table_name='resonance_log')
    op.drop_index('idx_persona_affinity_persona', table_name='persona_affinity')
    op.drop_index('idx_persona_affinity_user', table_name='persona_affinity')
    op.drop_index('idx_seeker_profiles_faction', table_name='seeker_profiles')
    op.drop_index('idx_seeker_profiles_rank', table_name='seeker_profiles')

    # Drop tables (in reverse order)
    op.drop_table('unlocked_lore')
    op.drop_table('resonance_log')
    op.drop_table('persona_affinity')
    op.drop_table('seeker_profiles')
