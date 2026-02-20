# src/coordinator/repositories/__init__.py
# Repository pattern for database access
from .base_repository import BaseRepository
from .db_adapter import DatabaseAdapter, SQLiteAdapter
from .session_repository import SessionRepository
from .message_repository import MessageRepository
from .summary_repository import SummaryRepository
from .emotional_state_repository import EmotionalStateRepository
from .seeker_progression_repository import SeekerProgressionRepository
from .user_profile_repository import UserProfileRepository
from .trade_proposal_repository import TradeProposalRepository
from .wallet_repository import WalletRepository
from .user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "DatabaseAdapter",
    "SQLiteAdapter",
    "SessionRepository",
    "MessageRepository",
    "SummaryRepository",
    "EmotionalStateRepository",
    "SeekerProgressionRepository",
    "UserProfileRepository",
    "TradeProposalRepository",
    "WalletRepository",
    "UserRepository",
]
