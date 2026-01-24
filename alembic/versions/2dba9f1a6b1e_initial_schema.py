"""initial_schema

Revision ID: 2dba9f1a6b1e
Revises:
Create Date: 2026-01-17 14:06:14.240755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dba9f1a6b1e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('persona_key', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.Text(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.Text(), server_default='llm'),
        sa.Column('multi_message_id', sa.Text(), nullable=True),
        sa.Column('multi_message_index', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create conversation_summaries table
    op.create_table(
        'conversation_summaries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('message_range', sa.Text(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('emotional_developments', sa.Text(), nullable=True),
        sa.Column('topics_discussed', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE')
    )

    # Create emotional_states table
    op.create_table(
        'emotional_states',
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('trust_level', sa.Float(), server_default='0.5'),
        sa.Column('rapport', sa.Float(), server_default='0.5'),
        sa.Column('current_mood', sa.Text(), server_default='neutral'),
        sa.Column('mood_intensity', sa.Float(), server_default='0.5'),
        sa.Column('last_emotional_event', sa.Text(), nullable=True),
        sa.Column('emotional_history', sa.Text(), server_default='[]'),
        sa.Column('updated_at', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id')
    )

    # Create user_profiles table (Phase 3: Cross-session memory)
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.Column('profile_data', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create user_sessions table (links users to their chat sessions)
    op.create_table(
        'user_sessions',
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'session_id')
    )

    # Create indexes
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])
    op.create_index('idx_sessions_persona', 'chat_sessions', ['persona_key'])
    op.create_index('idx_sessions_created_at', 'chat_sessions', ['created_at'])
    op.create_index('idx_summaries_session_id', 'conversation_summaries', ['session_id'])
    op.create_index('idx_emotional_states_session', 'emotional_states', ['session_id'])
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_session_id', 'user_sessions', ['session_id'])


def downgrade() -> None:
    """Drop all tables."""

    # Drop indexes first
    op.drop_index('idx_user_sessions_session_id', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_id', table_name='user_sessions')
    op.drop_index('idx_emotional_states_session', table_name='emotional_states')
    op.drop_index('idx_summaries_session_id', table_name='conversation_summaries')
    op.drop_index('idx_sessions_created_at', table_name='chat_sessions')
    op.drop_index('idx_sessions_persona', table_name='chat_sessions')
    op.drop_index('idx_messages_session_id', table_name='messages')

    # Drop tables (in reverse order of creation, respecting foreign keys)
    op.drop_table('user_sessions')
    op.drop_table('user_profiles')
    op.drop_table('emotional_states')
    op.drop_table('conversation_summaries')
    op.drop_table('messages')
    op.drop_table('chat_sessions')
