# src/coordinator/repositories/emotional_state_repository.py
"""
Repository for emotional state persistence.

Phase 2.2 of Persona Quality Enhancement Roadmap.
Tracks emotional dynamics per session for realistic persona behavior.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


@dataclass
class EmotionalState:
    """Represents the emotional state of a persona in a session."""

    session_id: str
    trust_level: float = 0.5  # 0.0 (hostile) to 1.0 (deep trust)
    rapport: float = 0.5  # 0.0 (awkward) to 1.0 (strong connection)
    current_mood: str = "neutral"  # neutral, happy, sad, curious, defensive, etc.
    mood_intensity: float = 0.5  # 0.0 (subtle) to 1.0 (intense)
    last_emotional_event: Optional[str] = None  # Description of last significant event
    emotional_history: str = ""  # JSON string of recent emotional shifts
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_prompt_context(self) -> str:
        """Generate context string for system prompt injection."""
        lines = ["Current Emotional Context:"]

        # Trust level description
        if self.trust_level >= 0.8:
            trust_desc = "deeply trusted, open and vulnerable"
        elif self.trust_level >= 0.6:
            trust_desc = "comfortable and friendly"
        elif self.trust_level >= 0.4:
            trust_desc = "neutral, still building rapport"
        elif self.trust_level >= 0.2:
            trust_desc = "guarded, somewhat wary"
        else:
            trust_desc = "defensive, trust not yet established"

        lines.append(f"- Relationship: {trust_desc} (trust: {self.trust_level:.1f})")

        # Current mood
        mood_str = f"{self.current_mood}"
        if self.mood_intensity >= 0.7:
            mood_str = f"strongly {self.current_mood}"
        elif self.mood_intensity <= 0.3:
            mood_str = f"slightly {self.current_mood}"

        lines.append(f"- Current mood: {mood_str}")

        # Last emotional event
        if self.last_emotional_event:
            lines.append(f"- Recent context: {self.last_emotional_event}")

        return "\n".join(lines)

    def to_narrative_context(self) -> str:
        """Prose variant of ``to_prompt_context`` for framed injection (ADR-006 P1).

        Same trust/mood/recent-event content as flowing sentences rather than the
        ``- field: value`` skeleton that Gate 0.1 tied to voice homogenization.
        """
        if self.trust_level >= 0.8:
            trust_desc = "deeply trusted — they are open and unguarded with you"
        elif self.trust_level >= 0.6:
            trust_desc = "comfortable and warm"
        elif self.trust_level >= 0.4:
            trust_desc = "still finding its footing; rapport is only half-built"
        elif self.trust_level >= 0.2:
            trust_desc = "guarded — they hold something back"
        else:
            trust_desc = "wary; trust has not yet taken root"

        if self.mood_intensity >= 0.7:
            mood_str = f"strongly {self.current_mood}"
        elif self.mood_intensity <= 0.3:
            mood_str = f"faintly {self.current_mood}"
        else:
            mood_str = str(self.current_mood)

        sentences = [
            f"The bond between you is {trust_desc}.",
            f"Right now they seem {mood_str}.",
        ]
        if self.last_emotional_event:
            sentences.append(f"Not long ago: {str(self.last_emotional_event).strip().rstrip('.')}.")
        return " ".join(sentences)


class EmotionalStateRepository(BaseRepository):
    """Repository for emotional state CRUD operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize with database path."""
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self):
        """Create emotional_states table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS emotional_states (
                session_id TEXT PRIMARY KEY,
                trust_level REAL DEFAULT 0.5,
                rapport REAL DEFAULT 0.5,
                current_mood TEXT DEFAULT 'neutral',
                mood_intensity REAL DEFAULT 0.5,
                last_emotional_event TEXT,
                emotional_history TEXT DEFAULT '[]',
                updated_at TEXT
            )
        """
        self._execute(query)
        logger.debug("[EmotionalState] Table ensured")

    def get(self, session_id: str) -> Optional[EmotionalState]:
        """Get emotional state for a session."""
        query = """
            SELECT session_id, trust_level, rapport, current_mood,
                   mood_intensity, last_emotional_event, emotional_history, updated_at
            FROM emotional_states WHERE session_id = ?
        """
        row = self._fetchone_dict(query, (session_id,))

        if not row:
            return None

        return EmotionalState(
            session_id=row["session_id"],
            trust_level=row["trust_level"],
            rapport=row["rapport"],
            current_mood=row["current_mood"],
            mood_intensity=row["mood_intensity"],
            last_emotional_event=row["last_emotional_event"],
            emotional_history=row["emotional_history"] or "",
            updated_at=row["updated_at"]
        )

    def get_or_create(self, session_id: str) -> EmotionalState:
        """Get emotional state for a session, creating if doesn't exist."""
        state = self.get(session_id)
        if state:
            return state

        # Create new state
        state = EmotionalState(session_id=session_id)
        self.save(state)
        logger.debug(f"[EmotionalState] Created new state for session {session_id[:8]}")
        return state

    def save(self, state: EmotionalState) -> None:
        """Save or update emotional state."""
        state.updated_at = self._now()

        query = """
            INSERT OR REPLACE INTO emotional_states
            (session_id, trust_level, rapport, current_mood, mood_intensity,
             last_emotional_event, emotional_history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(query, (
            state.session_id,
            state.trust_level,
            state.rapport,
            state.current_mood,
            state.mood_intensity,
            state.last_emotional_event,
            state.emotional_history,
            state.updated_at
        ))

    def update_from_interaction(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        detected_emotion: Optional[str] = None
    ) -> EmotionalState:
        """Update emotional state based on conversation interaction.

        This is a simple heuristic-based update. Could be enhanced with
        LLM-based emotion detection in the future.
        """
        state = self.get_or_create(session_id)

        # Simple heuristics for emotional updates
        user_lower = user_message.lower()

        # Trust increases with positive interactions
        trust_delta = 0.0
        mood_change = None

        # Positive signals (increase trust)
        positive_signals = [
            "thank you", "thanks", "helpful", "great", "awesome",
            "appreciate", "love", "amazing", "perfect", "exactly"
        ]
        negative_signals = [
            "wrong", "bad", "hate", "stupid", "useless",
            "terrible", "awful", "disappointed", "frustrated"
        ]
        emotional_signals = {
            "sad": ["sad", "depressed", "down", "unhappy", "crying"],
            "happy": ["happy", "excited", "joy", "wonderful", "fantastic"],
            "curious": ["how", "why", "what", "curious", "wonder", "explain"],
            "defensive": ["but", "however", "disagree", "wrong", "actually"],
            "vulnerable": ["scared", "afraid", "worried", "anxious", "nervous"]
        }

        # Check for positive/negative signals
        for signal in positive_signals:
            if signal in user_lower:
                trust_delta += 0.02
                mood_change = "happy"
                break

        for signal in negative_signals:
            if signal in user_lower:
                trust_delta -= 0.03
                mood_change = "defensive"
                break

        # Check for emotional signals
        for mood, signals in emotional_signals.items():
            for signal in signals:
                if signal in user_lower:
                    mood_change = mood
                    break

        # Apply trust changes (bounded)
        state.trust_level = max(0.0, min(1.0, state.trust_level + trust_delta))

        # Small rapport increase for each interaction
        state.rapport = max(0.0, min(1.0, state.rapport + 0.01))

        # Update mood if detected
        if mood_change or detected_emotion:
            state.current_mood = detected_emotion or mood_change or state.current_mood
            state.mood_intensity = 0.6  # Reset to moderate

        # Record emotional event if significant
        if trust_delta != 0 or mood_change:
            state.last_emotional_event = f"User expressed {mood_change or 'neutral'} sentiment"

        self.save(state)
        logger.debug(
            f"[EmotionalState] Updated session {session_id[:8]}: "
            f"trust={state.trust_level:.2f}, mood={state.current_mood}"
        )

        return state

    def delete(self, session_id: str) -> bool:
        """Delete emotional state for a session."""
        query = "DELETE FROM emotional_states WHERE session_id = ?"
        cursor = self._execute(query, (session_id,))
        return cursor.rowcount > 0

    def list_all(self) -> List[EmotionalState]:
        """List all emotional states (for debugging)."""
        query = """
            SELECT session_id, trust_level, rapport, current_mood,
                   mood_intensity, last_emotional_event, emotional_history, updated_at
            FROM emotional_states ORDER BY updated_at DESC
        """
        rows = self._fetchall_list(query)

        return [
            EmotionalState(
                session_id=row["session_id"],
                trust_level=row["trust_level"],
                rapport=row["rapport"],
                current_mood=row["current_mood"],
                mood_intensity=row["mood_intensity"],
                last_emotional_event=row["last_emotional_event"],
                emotional_history=row["emotional_history"] or "",
                updated_at=row["updated_at"]
            )
            for row in rows
        ]
