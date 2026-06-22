"""Repository for NEPHILIM Seeker progression system.

Handles all database operations for:
- Seeker profiles (rank, resonance, faction)
- Persona affinity tracking
- Lore fragment unlocks
- Resonance event logging

Phase 3: NEPHILIM Gamification System
"""

from __future__ import annotations

import sqlite3
import logging
from typing import Optional, List, Dict, Any

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


# Rank thresholds (resonance required)
RANK_THRESHOLDS = {
    'Initiate': 0,
    'Acolyte': 100,
    'Adept': 500,
    'Ascendant': 2000,
    'Nephilim': 10000,
}

# Resonance rewards
RESONANCE_REWARDS = {
    'first_conversation': 20,      # First time chatting with a Nephilim
    'meaningful_conversation': 10,  # 5+ exchanges
    'extended_session': 25,         # 20+ exchanges
    'daily_return': 5,              # Returning after 24+ hours
    'lore_unlock': 50,              # Unlocking a lore fragment
    'affinity_milestone': 30,       # Reaching affinity milestones
    'new_persona': 10,              # Engaging with a new Nephilim
}


class SeekerProgressionRepository(BaseRepository):
    """Database repository for NEPHILIM Seeker progression.

    Manages the gamification layer including ranks, resonance,
    persona affinities, and lore unlocks.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize with database path and ensure tables exist."""
        super().__init__(db_path)
        self._ensure_tables()

    def _ensure_tables(self):
        """Create NEPHILIM progression tables if they don't exist."""
        self._execute("""
            CREATE TABLE IF NOT EXISTS seeker_profiles (
                user_id TEXT NOT NULL PRIMARY KEY,
                rank_name TEXT DEFAULT 'Initiate',
                total_resonance INTEGER DEFAULT 0,
                faction_primary TEXT,
                faction_secondary TEXT,
                rank_achieved_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS persona_affinity (
                user_id TEXT NOT NULL,
                persona_key TEXT NOT NULL,
                messages_count INTEGER DEFAULT 0,
                affinity_level INTEGER DEFAULT 0,
                last_conversation TEXT,
                first_conversation TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, persona_key),
                FOREIGN KEY (user_id) REFERENCES seeker_profiles(user_id) ON DELETE CASCADE
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS resonance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                persona_key TEXT,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES seeker_profiles(user_id) ON DELETE CASCADE
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS unlocked_lore (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                persona_key TEXT NOT NULL,
                fragment_id TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES seeker_profiles(user_id) ON DELETE CASCADE,
                UNIQUE (user_id, persona_key, fragment_id)
            )
        """)

        self._execute("CREATE INDEX IF NOT EXISTS idx_seeker_profiles_rank ON seeker_profiles(rank_name)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_seeker_profiles_faction ON seeker_profiles(faction_primary)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_persona_affinity_user ON persona_affinity(user_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_persona_affinity_persona ON persona_affinity(persona_key)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_resonance_log_user ON resonance_log(user_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_resonance_log_timestamp ON resonance_log(timestamp)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_unlocked_lore_user ON unlocked_lore(user_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_unlocked_lore_persona ON unlocked_lore(persona_key)")

        logger.debug("[SeekerProgression] Tables ensured")

    # ─────────────────────────────────────────────────────────────
    # Seeker Profile Operations
    # ─────────────────────────────────────────────────────────────

    def get_or_create_seeker(self, user_id: str) -> Dict[str, Any]:
        """Get existing seeker profile or create new one."""
        profile = self.get_seeker_profile(user_id)
        if profile is None:
            profile = self.create_seeker_profile(user_id)
        return profile

    def create_seeker_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a new seeker profile."""
        now = self._now()
        try:
            self._execute(
                "INSERT INTO seeker_profiles (user_id, rank_name, total_resonance, created_at, updated_at) VALUES (?, 'Initiate', 0, ?, ?)",
                (user_id, now, now),
            )
            logger.info(f"[SeekerRepo] Created seeker profile: {user_id}")
            return {
                'user_id': user_id, 'rank_name': 'Initiate', 'total_resonance': 0,
                'faction_primary': None, 'faction_secondary': None,
                'rank_achieved_at': now, 'created_at': now, 'updated_at': now,
            }
        except sqlite3.IntegrityError:
            logger.warning(f"[SeekerRepo] Profile already exists: {user_id}")
            return self.get_seeker_profile(user_id)

    def get_seeker_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get seeker profile by user ID."""
        return self._fetchone_dict("SELECT * FROM seeker_profiles WHERE user_id = ?", (user_id,))

    def update_seeker_faction(self, user_id: str, faction_primary: str, faction_secondary: Optional[str] = None) -> bool:
        """Update seeker's faction affiliation. Returns True if updated."""
        now = self._now()
        cur = self._execute(
            "UPDATE seeker_profiles SET faction_primary = ?, faction_secondary = ?, updated_at = ? WHERE user_id = ?",
            (faction_primary, faction_secondary, now, user_id),
        )
        updated = cur.rowcount > 0
        if updated:
            logger.info(f"[SeekerRepo] Updated faction for {user_id}: {faction_primary}")
        return updated

    # ─────────────────────────────────────────────────────────────
    # Resonance Operations
    # ─────────────────────────────────────────────────────────────

    def award_resonance(
        self, user_id: str, amount: int, reason: str,
        persona_key: Optional[str] = None, session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Award resonance to a seeker. Automatically checks for rank advancement."""
        now = self._now()
        self.get_or_create_seeker(user_id)

        row = self._fetchone_dict(
            "SELECT total_resonance, rank_name FROM seeker_profiles WHERE user_id = ?",
            (user_id,),
        )
        old_resonance = row['total_resonance']
        old_rank = row['rank_name']
        new_resonance = old_resonance + amount
        new_rank = self._calculate_rank(new_resonance)
        rank_changed = new_rank != old_rank

        if rank_changed:
            self._execute(
                "UPDATE seeker_profiles SET total_resonance = ?, rank_name = ?, rank_achieved_at = ?, updated_at = ? WHERE user_id = ?",
                (new_resonance, new_rank, now, now, user_id),
            )
            logger.info(f"[SeekerRepo] {user_id} advanced to rank: {new_rank}")
        else:
            self._execute(
                "UPDATE seeker_profiles SET total_resonance = ?, updated_at = ? WHERE user_id = ?",
                (new_resonance, now, user_id),
            )

        self._execute(
            "INSERT INTO resonance_log (user_id, amount, reason, persona_key, session_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, amount, reason, persona_key, session_id, now),
        )

        logger.debug(f"[SeekerRepo] Awarded {amount} resonance to {user_id}: {reason}")
        return {
            'new_resonance': new_resonance, 'new_rank': new_rank,
            'rank_changed': rank_changed,
            'previous_rank': old_rank if rank_changed else None,
        }

    def get_resonance_to_next_rank(self, user_id: str) -> Dict[str, Any]:
        """Get progress toward next rank."""
        profile = self.get_seeker_profile(user_id)

        if not profile:
            return {
                'current_rank': 'Initiate', 'current_resonance': 0,
                'next_rank': 'Acolyte',
                'resonance_needed': RANK_THRESHOLDS['Acolyte'],
                'progress_percent': 0,
            }

        current_resonance = profile['total_resonance']
        current_rank = profile['rank_name']
        ranks = list(RANK_THRESHOLDS.keys())
        current_idx = ranks.index(current_rank)

        if current_idx >= len(ranks) - 1:
            return {
                'current_rank': current_rank, 'current_resonance': current_resonance,
                'next_rank': None, 'resonance_needed': 0, 'progress_percent': 100,
            }

        next_rank = ranks[current_idx + 1]
        current_threshold = RANK_THRESHOLDS[current_rank]
        next_threshold = RANK_THRESHOLDS[next_rank]
        resonance_in_tier = current_resonance - current_threshold
        tier_size = next_threshold - current_threshold
        progress_percent = min(100, int((resonance_in_tier / tier_size) * 100))

        return {
            'current_rank': current_rank, 'current_resonance': current_resonance,
            'next_rank': next_rank,
            'resonance_needed': next_threshold - current_resonance,
            'progress_percent': progress_percent,
        }

    def _calculate_rank(self, resonance: int) -> str:
        """Calculate rank based on total resonance."""
        rank = 'Initiate'
        for rank_name, threshold in RANK_THRESHOLDS.items():
            if resonance >= threshold:
                rank = rank_name
        return rank

    # ─────────────────────────────────────────────────────────────
    # Persona Affinity Operations
    # ─────────────────────────────────────────────────────────────

    def get_or_create_affinity(self, user_id: str, persona_key: str) -> Dict[str, Any]:
        """Get or create persona affinity record."""
        affinity = self.get_affinity(user_id, persona_key)
        if affinity is None:
            affinity = self.create_affinity(user_id, persona_key)
        return affinity

    def create_affinity(self, user_id: str, persona_key: str) -> Dict[str, Any]:
        """Create new persona affinity record."""
        now = self._now()
        self.get_or_create_seeker(user_id)

        try:
            self._execute(
                "INSERT INTO persona_affinity (user_id, persona_key, messages_count, affinity_level, first_conversation, created_at, updated_at) VALUES (?, ?, 0, 0, ?, ?, ?)",
                (user_id, persona_key, now, now, now),
            )
            logger.info(f"[SeekerRepo] Created affinity: {user_id} <-> {persona_key}")
            return {
                'user_id': user_id, 'persona_key': persona_key,
                'messages_count': 0, 'affinity_level': 0,
                'first_conversation': now, 'last_conversation': None,
                'created_at': now, 'updated_at': now,
            }
        except sqlite3.IntegrityError:
            return self.get_affinity(user_id, persona_key)

    def get_affinity(self, user_id: str, persona_key: str) -> Optional[Dict[str, Any]]:
        """Get persona affinity record."""
        return self._fetchone_dict(
            "SELECT * FROM persona_affinity WHERE user_id = ? AND persona_key = ?",
            (user_id, persona_key),
        )

    def increment_messages(self, user_id: str, persona_key: str, count: int = 1) -> Dict[str, Any]:
        """Increment message count for persona affinity."""
        now = self._now()
        affinity = self.get_or_create_affinity(user_id, persona_key)
        is_first = affinity['messages_count'] == 0
        new_count = affinity['messages_count'] + count

        self._execute(
            "UPDATE persona_affinity SET messages_count = ?, last_conversation = ?, updated_at = ? WHERE user_id = ? AND persona_key = ?",
            (new_count, now, now, user_id, persona_key),
        )
        affinity['messages_count'] = new_count
        affinity['last_conversation'] = now
        affinity['is_first_conversation'] = is_first
        return affinity

    def get_all_affinities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all persona affinities for a user."""
        return self._fetchall_list(
            "SELECT * FROM persona_affinity WHERE user_id = ? ORDER BY messages_count DESC",
            (user_id,),
        )

    # ─────────────────────────────────────────────────────────────
    # Lore Unlock Operations
    # ─────────────────────────────────────────────────────────────

    def unlock_lore(self, user_id: str, persona_key: str, fragment_id: str) -> bool:
        """Unlock a lore fragment. Returns True if newly unlocked."""
        now = self._now()
        self.get_or_create_seeker(user_id)
        try:
            self._execute(
                "INSERT INTO unlocked_lore (user_id, persona_key, fragment_id, unlocked_at) VALUES (?, ?, ?, ?)",
                (user_id, persona_key, fragment_id, now),
            )
            logger.info(f"[SeekerRepo] Unlocked lore {fragment_id} for {user_id}")
            return True
        except sqlite3.IntegrityError:
            return False

    def get_unlocked_lore(self, user_id: str, persona_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all unlocked lore fragments for a user."""
        if persona_key:
            return self._fetchall_list(
                "SELECT * FROM unlocked_lore WHERE user_id = ? AND persona_key = ? ORDER BY unlocked_at DESC",
                (user_id, persona_key),
            )
        return self._fetchall_list(
            "SELECT * FROM unlocked_lore WHERE user_id = ? ORDER BY unlocked_at DESC",
            (user_id,),
        )

    def is_lore_unlocked(self, user_id: str, persona_key: str, fragment_id: str) -> bool:
        """Check if a specific lore fragment is unlocked."""
        row = self._fetchone_dict(
            "SELECT 1 AS found FROM unlocked_lore WHERE user_id = ? AND persona_key = ? AND fragment_id = ?",
            (user_id, persona_key, fragment_id),
        )
        return row is not None

    def check_and_unlock_lore(
        self, user_id: str, persona_key: str,
        fragments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check triggers and unlock any newly available lore fragments.

        Supports multiple trigger types per fragment:
        - messages_required (int): message count threshold (original)
        - rank_required (str): seeker must have reached this rank (e.g. "Adept")
        - affinity_required (int): persona affinity level threshold
        - cross_persona_required (str|list): fragment_ids from other personas that must be unlocked
        - trigger_logic ("all"|"any"): how to combine conditions (default "all" = AND)

        Backward compatible: fragments with only messages_required work as before.
        """
        affinity = self.get_affinity(user_id, persona_key)
        if not affinity:
            return []

        messages_count = affinity['messages_count']
        affinity_level = affinity.get('affinity_level', 0)

        # Lazy-loaded state — only fetched when needed by specific trigger types
        _seeker_profile = None
        _all_unlocked_ids = None

        newly_unlocked = []

        for fragment in fragments:
            fragment_id = fragment.get('fragment_id', '')
            if not fragment_id:
                continue

            # Skip already-unlocked fragments
            if self.is_lore_unlocked(user_id, persona_key, fragment_id):
                continue

            # Collect conditions based on which trigger fields are present
            conditions = []
            trigger_logic = fragment.get('trigger_logic', 'all')

            # messages_required (original trigger)
            msg_req = fragment.get('messages_required')
            if msg_req is not None:
                conditions.append(messages_count >= msg_req)

            # rank_required — compare seeker rank against RANK_THRESHOLDS ordering
            rank_req = fragment.get('rank_required')
            if rank_req:
                if _seeker_profile is None:
                    _seeker_profile = self.get_seeker_profile(user_id) or {}
                seeker_rank = _seeker_profile.get('rank_name', 'Initiate')
                rank_order = list(RANK_THRESHOLDS.keys())
                seeker_idx = rank_order.index(seeker_rank) if seeker_rank in rank_order else 0
                req_idx = rank_order.index(rank_req) if rank_req in rank_order else len(rank_order)
                conditions.append(seeker_idx >= req_idx)

            # affinity_required — compare persona affinity level
            aff_req = fragment.get('affinity_required')
            if aff_req is not None:
                conditions.append(affinity_level >= aff_req)

            # cross_persona_required — check fragment_ids from other personas are unlocked
            cross_req = fragment.get('cross_persona_required')
            if cross_req:
                if _all_unlocked_ids is None:
                    all_unlocked = self.get_unlocked_lore(user_id)  # all personas
                    _all_unlocked_ids = {row['fragment_id'] for row in all_unlocked}
                if isinstance(cross_req, str):
                    cross_req = [cross_req]
                conditions.append(all(fid in _all_unlocked_ids for fid in cross_req))

            # If no conditions were collected, skip (malformed fragment)
            if not conditions:
                continue

            # Evaluate: AND (all) or OR (any)
            if trigger_logic == 'any':
                passes = any(conditions)
            else:
                passes = all(conditions)

            if passes:
                if self.unlock_lore(user_id, persona_key, fragment_id):
                    newly_unlocked.append(fragment)
                    # Update cached set so later cross_persona checks see this unlock
                    if _all_unlocked_ids is not None:
                        _all_unlocked_ids.add(fragment_id)
                    self.award_resonance(
                        user_id, RESONANCE_REWARDS['lore_unlock'],
                        f'Unlocked lore: {fragment_id}', persona_key=persona_key,
                    )

        return newly_unlocked

    # ─────────────────────────────────────────────────────────────
    # Analytics & Reporting
    # ─────────────────────────────────────────────────────────────

    def get_seeker_summary(self, user_id: str) -> Dict[str, Any]:
        """Get complete seeker summary including all progression data."""
        profile = self.get_seeker_profile(user_id)

        if not profile:
            return {'exists': False, 'user_id': user_id}

        progress = self.get_resonance_to_next_rank(user_id)
        affinities = self.get_all_affinities(user_id)
        unlocked_lore = self.get_unlocked_lore(user_id)

        return {
            'exists': True, 'user_id': user_id,
            'rank': profile['rank_name'],
            'total_resonance': profile['total_resonance'],
            'faction_primary': profile['faction_primary'],
            'faction_secondary': profile['faction_secondary'],
            'rank_progress': progress,
            'persona_affinities': affinities,
            'unlocked_lore_count': len(unlocked_lore),
            'unlocked_lore': unlocked_lore,
            'created_at': profile['created_at'],
            'updated_at': profile['updated_at'],
        }

    def get_resonance_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent resonance events for a user."""
        # Tie-break by id DESC: timestamp has 1-second resolution, so events logged
        # in the same second would otherwise come back in insertion order (ROWID asc),
        # not newest-first. id is the AUTOINCREMENT PK, so id DESC == insertion-desc.
        return self._fetchall_list(
            "SELECT * FROM resonance_log WHERE user_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (user_id, limit),
        )
