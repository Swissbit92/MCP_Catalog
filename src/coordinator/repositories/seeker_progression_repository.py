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
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

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

    # ─────────────────────────────────────────────────────────────
    # Seeker Profile Operations
    # ─────────────────────────────────────────────────────────────

    def get_or_create_seeker(self, user_id: str) -> Dict[str, Any]:
        """Get existing seeker profile or create new one.

        Args:
            user_id: Unique user identifier

        Returns:
            Seeker profile dict with rank, resonance, faction info
        """
        profile = self.get_seeker_profile(user_id)

        if profile is None:
            profile = self.create_seeker_profile(user_id)

        return profile

    def create_seeker_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a new seeker profile.

        Args:
            user_id: Unique user identifier

        Returns:
            Newly created seeker profile
        """
        now = self._now()

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    INSERT INTO seeker_profiles
                    (user_id, rank_name, total_resonance, created_at, updated_at)
                    VALUES (?, 'Initiate', 0, ?, ?)
                """, (user_id, now, now))

                conn.commit()
                logger.info(f"[SeekerRepo] Created seeker profile: {user_id}")

                return {
                    'user_id': user_id,
                    'rank_name': 'Initiate',
                    'total_resonance': 0,
                    'faction_primary': None,
                    'faction_secondary': None,
                    'rank_achieved_at': now,
                    'created_at': now,
                    'updated_at': now,
                }

            except sqlite3.IntegrityError:
                logger.warning(f"[SeekerRepo] Profile already exists: {user_id}")
                return self.get_seeker_profile(user_id)

            finally:
                conn.close()

    def get_seeker_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get seeker profile by user ID.

        Args:
            user_id: User identifier

        Returns:
            Seeker profile dict or None
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT * FROM seeker_profiles WHERE user_id = ?
                """, (user_id,))

                row = cur.fetchone()
                return dict(row) if row else None

            finally:
                conn.close()

    def update_seeker_faction(
        self,
        user_id: str,
        faction_primary: str,
        faction_secondary: Optional[str] = None
    ) -> bool:
        """Update seeker's faction affiliation.

        Args:
            user_id: User identifier
            faction_primary: Primary house (e.g., 'lumina', 'ironclad')
            faction_secondary: Optional secondary affinity

        Returns:
            True if updated, False if profile not found
        """
        now = self._now()

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            cur = conn.cursor()

            try:
                cur.execute("""
                    UPDATE seeker_profiles
                    SET faction_primary = ?, faction_secondary = ?, updated_at = ?
                    WHERE user_id = ?
                """, (faction_primary, faction_secondary, now, user_id))

                updated = cur.rowcount > 0
                conn.commit()

                if updated:
                    logger.info(f"[SeekerRepo] Updated faction for {user_id}: {faction_primary}")

                return updated

            finally:
                conn.close()

    # ─────────────────────────────────────────────────────────────
    # Resonance Operations
    # ─────────────────────────────────────────────────────────────

    def award_resonance(
        self,
        user_id: str,
        amount: int,
        reason: str,
        persona_key: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Award resonance to a seeker.

        Automatically checks for rank advancement.

        Args:
            user_id: User identifier
            amount: Resonance points to award
            reason: Reason for the award
            persona_key: Optional associated persona
            session_id: Optional associated session

        Returns:
            Dict with new_resonance, new_rank, rank_changed
        """
        now = self._now()

        # Ensure seeker exists
        self.get_or_create_seeker(user_id)

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                # Get current state
                cur.execute("""
                    SELECT total_resonance, rank_name FROM seeker_profiles
                    WHERE user_id = ?
                """, (user_id,))
                row = cur.fetchone()
                old_resonance = row['total_resonance']
                old_rank = row['rank_name']

                # Calculate new values
                new_resonance = old_resonance + amount
                new_rank = self._calculate_rank(new_resonance)
                rank_changed = new_rank != old_rank

                # Update profile
                if rank_changed:
                    cur.execute("""
                        UPDATE seeker_profiles
                        SET total_resonance = ?, rank_name = ?, rank_achieved_at = ?, updated_at = ?
                        WHERE user_id = ?
                    """, (new_resonance, new_rank, now, now, user_id))
                    logger.info(f"[SeekerRepo] {user_id} advanced to rank: {new_rank}")
                else:
                    cur.execute("""
                        UPDATE seeker_profiles
                        SET total_resonance = ?, updated_at = ?
                        WHERE user_id = ?
                    """, (new_resonance, now, user_id))

                # Log the resonance event
                cur.execute("""
                    INSERT INTO resonance_log
                    (user_id, amount, reason, persona_key, session_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, amount, reason, persona_key, session_id, now))

                conn.commit()

                logger.debug(f"[SeekerRepo] Awarded {amount} resonance to {user_id}: {reason}")

                return {
                    'new_resonance': new_resonance,
                    'new_rank': new_rank,
                    'rank_changed': rank_changed,
                    'previous_rank': old_rank if rank_changed else None,
                }

            finally:
                conn.close()

    def get_resonance_to_next_rank(self, user_id: str) -> Dict[str, Any]:
        """Get progress toward next rank.

        Args:
            user_id: User identifier

        Returns:
            Dict with current_rank, current_resonance, next_rank,
            resonance_needed, progress_percent
        """
        profile = self.get_seeker_profile(user_id)

        if not profile:
            return {
                'current_rank': 'Initiate',
                'current_resonance': 0,
                'next_rank': 'Acolyte',
                'resonance_needed': RANK_THRESHOLDS['Acolyte'],
                'progress_percent': 0,
            }

        current_resonance = profile['total_resonance']
        current_rank = profile['rank_name']

        # Find next rank
        ranks = list(RANK_THRESHOLDS.keys())
        current_idx = ranks.index(current_rank)

        if current_idx >= len(ranks) - 1:
            # Already at max rank
            return {
                'current_rank': current_rank,
                'current_resonance': current_resonance,
                'next_rank': None,
                'resonance_needed': 0,
                'progress_percent': 100,
            }

        next_rank = ranks[current_idx + 1]
        current_threshold = RANK_THRESHOLDS[current_rank]
        next_threshold = RANK_THRESHOLDS[next_rank]

        resonance_in_tier = current_resonance - current_threshold
        tier_size = next_threshold - current_threshold
        progress_percent = min(100, int((resonance_in_tier / tier_size) * 100))

        return {
            'current_rank': current_rank,
            'current_resonance': current_resonance,
            'next_rank': next_rank,
            'resonance_needed': next_threshold - current_resonance,
            'progress_percent': progress_percent,
        }

    def _calculate_rank(self, resonance: int) -> str:
        """Calculate rank based on total resonance.

        Args:
            resonance: Total resonance points

        Returns:
            Rank name
        """
        rank = 'Initiate'
        for rank_name, threshold in RANK_THRESHOLDS.items():
            if resonance >= threshold:
                rank = rank_name
        return rank

    # ─────────────────────────────────────────────────────────────
    # Persona Affinity Operations
    # ─────────────────────────────────────────────────────────────

    def get_or_create_affinity(self, user_id: str, persona_key: str) -> Dict[str, Any]:
        """Get or create persona affinity record.

        Args:
            user_id: User identifier
            persona_key: Persona identifier

        Returns:
            Affinity record dict
        """
        affinity = self.get_affinity(user_id, persona_key)

        if affinity is None:
            affinity = self.create_affinity(user_id, persona_key)

        return affinity

    def create_affinity(self, user_id: str, persona_key: str) -> Dict[str, Any]:
        """Create new persona affinity record.

        Args:
            user_id: User identifier
            persona_key: Persona identifier

        Returns:
            Newly created affinity record
        """
        now = self._now()

        # Ensure seeker profile exists
        self.get_or_create_seeker(user_id)

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    INSERT INTO persona_affinity
                    (user_id, persona_key, messages_count, affinity_level,
                     first_conversation, created_at, updated_at)
                    VALUES (?, ?, 0, 0, ?, ?, ?)
                """, (user_id, persona_key, now, now, now))

                conn.commit()
                logger.info(f"[SeekerRepo] Created affinity: {user_id} <-> {persona_key}")

                return {
                    'user_id': user_id,
                    'persona_key': persona_key,
                    'messages_count': 0,
                    'affinity_level': 0,
                    'first_conversation': now,
                    'last_conversation': None,
                    'created_at': now,
                    'updated_at': now,
                }

            except sqlite3.IntegrityError:
                return self.get_affinity(user_id, persona_key)

            finally:
                conn.close()

    def get_affinity(self, user_id: str, persona_key: str) -> Optional[Dict[str, Any]]:
        """Get persona affinity record.

        Args:
            user_id: User identifier
            persona_key: Persona identifier

        Returns:
            Affinity record or None
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT * FROM persona_affinity
                    WHERE user_id = ? AND persona_key = ?
                """, (user_id, persona_key))

                row = cur.fetchone()
                return dict(row) if row else None

            finally:
                conn.close()

    def increment_messages(self, user_id: str, persona_key: str, count: int = 1) -> Dict[str, Any]:
        """Increment message count for persona affinity.

        Also updates last_conversation timestamp.

        Args:
            user_id: User identifier
            persona_key: Persona identifier
            count: Number of messages to add

        Returns:
            Updated affinity record with is_first flag
        """
        now = self._now()

        # Get or create affinity
        affinity = self.get_or_create_affinity(user_id, persona_key)
        is_first = affinity['messages_count'] == 0

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                new_count = affinity['messages_count'] + count

                cur.execute("""
                    UPDATE persona_affinity
                    SET messages_count = ?, last_conversation = ?, updated_at = ?
                    WHERE user_id = ? AND persona_key = ?
                """, (new_count, now, now, user_id, persona_key))

                conn.commit()

                affinity['messages_count'] = new_count
                affinity['last_conversation'] = now
                affinity['is_first_conversation'] = is_first

                return affinity

            finally:
                conn.close()

    def get_all_affinities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all persona affinities for a user.

        Args:
            user_id: User identifier

        Returns:
            List of affinity records
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT * FROM persona_affinity
                    WHERE user_id = ?
                    ORDER BY messages_count DESC
                """, (user_id,))

                rows = cur.fetchall()
                return [dict(row) for row in rows]

            finally:
                conn.close()

    # ─────────────────────────────────────────────────────────────
    # Lore Unlock Operations
    # ─────────────────────────────────────────────────────────────

    def unlock_lore(self, user_id: str, persona_key: str, fragment_id: str) -> bool:
        """Unlock a lore fragment for a user.

        Args:
            user_id: User identifier
            persona_key: Persona identifier
            fragment_id: Lore fragment identifier

        Returns:
            True if newly unlocked, False if already unlocked
        """
        now = self._now()

        # Ensure seeker profile exists
        self.get_or_create_seeker(user_id)

        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            cur = conn.cursor()

            try:
                cur.execute("""
                    INSERT INTO unlocked_lore (user_id, persona_key, fragment_id, unlocked_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, persona_key, fragment_id, now))

                conn.commit()
                logger.info(f"[SeekerRepo] Unlocked lore {fragment_id} for {user_id}")
                return True

            except sqlite3.IntegrityError:
                # Already unlocked
                return False

            finally:
                conn.close()

    def get_unlocked_lore(self, user_id: str, persona_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all unlocked lore fragments for a user.

        Args:
            user_id: User identifier
            persona_key: Optional filter by persona

        Returns:
            List of unlocked lore records
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                if persona_key:
                    cur.execute("""
                        SELECT * FROM unlocked_lore
                        WHERE user_id = ? AND persona_key = ?
                        ORDER BY unlocked_at DESC
                    """, (user_id, persona_key))
                else:
                    cur.execute("""
                        SELECT * FROM unlocked_lore
                        WHERE user_id = ?
                        ORDER BY unlocked_at DESC
                    """, (user_id,))

                rows = cur.fetchall()
                return [dict(row) for row in rows]

            finally:
                conn.close()

    def is_lore_unlocked(self, user_id: str, persona_key: str, fragment_id: str) -> bool:
        """Check if a specific lore fragment is unlocked.

        Args:
            user_id: User identifier
            persona_key: Persona identifier
            fragment_id: Lore fragment identifier

        Returns:
            True if unlocked, False otherwise
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT 1 FROM unlocked_lore
                    WHERE user_id = ? AND persona_key = ? AND fragment_id = ?
                """, (user_id, persona_key, fragment_id))

                return cur.fetchone() is not None

            finally:
                conn.close()

    def check_and_unlock_lore(
        self,
        user_id: str,
        persona_key: str,
        persona_lore_fragments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check message count and unlock any newly available lore.

        Args:
            user_id: User identifier
            persona_key: Persona identifier
            persona_lore_fragments: List of lore fragment definitions from persona JSON

        Returns:
            List of newly unlocked fragments
        """
        affinity = self.get_affinity(user_id, persona_key)
        if not affinity:
            return []

        messages_count = affinity['messages_count']
        newly_unlocked = []

        for fragment in persona_lore_fragments:
            required = fragment.get('messages_required', 0)
            fragment_id = fragment.get('fragment_id', '')

            if not fragment_id:
                continue

            # Check if eligible and not already unlocked
            if messages_count >= required and not self.is_lore_unlocked(user_id, persona_key, fragment_id):
                if self.unlock_lore(user_id, persona_key, fragment_id):
                    newly_unlocked.append(fragment)

                    # Award resonance for unlock
                    self.award_resonance(
                        user_id,
                        RESONANCE_REWARDS['lore_unlock'],
                        f'Unlocked lore: {fragment_id}',
                        persona_key=persona_key
                    )

        return newly_unlocked

    # ─────────────────────────────────────────────────────────────
    # Analytics & Reporting
    # ─────────────────────────────────────────────────────────────

    def get_seeker_summary(self, user_id: str) -> Dict[str, Any]:
        """Get complete seeker summary including all progression data.

        Args:
            user_id: User identifier

        Returns:
            Comprehensive seeker summary
        """
        profile = self.get_seeker_profile(user_id)

        if not profile:
            return {
                'exists': False,
                'user_id': user_id,
            }

        progress = self.get_resonance_to_next_rank(user_id)
        affinities = self.get_all_affinities(user_id)
        unlocked_lore = self.get_unlocked_lore(user_id)

        return {
            'exists': True,
            'user_id': user_id,
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

    def get_resonance_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent resonance events for a user.

        Args:
            user_id: User identifier
            limit: Max number of events to return

        Returns:
            List of resonance events
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT * FROM resonance_log
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit))

                rows = cur.fetchall()
                return [dict(row) for row in rows]

            finally:
                conn.close()
