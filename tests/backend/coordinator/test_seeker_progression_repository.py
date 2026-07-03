"""Comprehensive pytest unit tests for SeekerProgressionRepository.

Tests cover: happy paths, edge cases, rank thresholds, award_resonance
accumulation + rank-up detection, affinity increment, lore unlock idempotency,
check_and_unlock_lore branch logic, summary/history shapes.

All tests use a fresh in-memory-ish SQLite DB via tmp_path — no network, no Ollama.
"""

from __future__ import annotations

import pytest

from src.coordinator.repositories.seeker_progression_repository import (
    SeekerProgressionRepository,
    RANK_THRESHOLDS,
    RESONANCE_REWARDS,
)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture()
def repo(tmp_path):
    """Fresh SeekerProgressionRepository with its own SQLite file per test."""
    db_path = str(tmp_path / "test_seeker.db")
    return SeekerProgressionRepository(db_path)


# ─────────────────────────────────────────────────────────────
# Seeker Profile: create / get / get_or_create
# ─────────────────────────────────────────────────────────────

class TestSeekerProfile:

    def test_create_seeker_profile_returns_dict(self, repo):
        profile = repo.create_seeker_profile("user_001")
        assert profile["user_id"] == "user_001"
        assert profile["rank_name"] == "Initiate"
        assert profile["total_resonance"] == 0
        assert profile["faction_primary"] is None
        assert profile["faction_secondary"] is None

    def test_create_seeker_profile_timestamps_present(self, repo):
        profile = repo.create_seeker_profile("user_001")
        assert profile["created_at"]
        assert profile["updated_at"]

    def test_get_seeker_profile_returns_none_for_missing_user(self, repo):
        result = repo.get_seeker_profile("nonexistent_user")
        assert result is None

    def test_get_seeker_profile_returns_existing(self, repo):
        repo.create_seeker_profile("user_002")
        profile = repo.get_seeker_profile("user_002")
        assert profile is not None
        assert profile["user_id"] == "user_002"
        assert profile["rank_name"] == "Initiate"

    def test_get_or_create_seeker_creates_when_absent(self, repo):
        profile = repo.get_or_create_seeker("brand_new_user")
        assert profile["user_id"] == "brand_new_user"
        assert profile["rank_name"] == "Initiate"

    def test_get_or_create_seeker_idempotent(self, repo):
        p1 = repo.get_or_create_seeker("user_idem")
        p2 = repo.get_or_create_seeker("user_idem")
        assert p1["user_id"] == p2["user_id"]
        # Second call should not throw or duplicate
        all_profiles = repo._fetchall_list("SELECT * FROM seeker_profiles WHERE user_id = ?", ("user_idem",))
        assert len(all_profiles) == 1

    def test_create_seeker_profile_duplicate_returns_existing(self, repo):
        """create_seeker_profile on an existing user falls back to get_seeker_profile."""
        repo.create_seeker_profile("dup_user")
        # Award some resonance so we can distinguish the second call's data
        repo.award_resonance("dup_user", 50, "test")
        second = repo.create_seeker_profile("dup_user")
        # Should fall back to existing profile (total_resonance should be 50)
        assert second["user_id"] == "dup_user"
        assert second["total_resonance"] == 50


# ─────────────────────────────────────────────────────────────
# Faction update
# ─────────────────────────────────────────────────────────────

class TestFactionUpdate:

    def test_update_faction_returns_true_when_updated(self, repo):
        repo.create_seeker_profile("user_f")
        result = repo.update_seeker_faction("user_f", "Void")
        assert result is True

    def test_update_faction_persisted(self, repo):
        repo.create_seeker_profile("user_f2")
        repo.update_seeker_faction("user_f2", "Celestial", "Shadow")
        profile = repo.get_seeker_profile("user_f2")
        assert profile["faction_primary"] == "Celestial"
        assert profile["faction_secondary"] == "Shadow"

    def test_update_faction_no_secondary(self, repo):
        repo.create_seeker_profile("user_f3")
        repo.update_seeker_faction("user_f3", "Void")
        profile = repo.get_seeker_profile("user_f3")
        assert profile["faction_primary"] == "Void"
        assert profile["faction_secondary"] is None

    def test_update_faction_returns_false_for_missing_user(self, repo):
        result = repo.update_seeker_faction("ghost_user", "Void")
        assert result is False


# ─────────────────────────────────────────────────────────────
# _calculate_rank — boundary tests
# ─────────────────────────────────────────────────────────────

class TestCalculateRank:

    def test_rank_initiate_at_zero(self, repo):
        assert repo._calculate_rank(0) == "Initiate"

    def test_rank_initiate_just_below_acolyte(self, repo):
        assert repo._calculate_rank(99) == "Initiate"

    def test_rank_acolyte_at_threshold(self, repo):
        assert repo._calculate_rank(100) == "Acolyte"

    def test_rank_acolyte_above_threshold(self, repo):
        assert repo._calculate_rank(499) == "Acolyte"

    def test_rank_adept_at_threshold(self, repo):
        assert repo._calculate_rank(500) == "Adept"

    def test_rank_adept_just_below_ascendant(self, repo):
        assert repo._calculate_rank(1999) == "Adept"

    def test_rank_ascendant_at_threshold(self, repo):
        assert repo._calculate_rank(2000) == "Ascendant"

    def test_rank_ascendant_just_below_nephilim(self, repo):
        assert repo._calculate_rank(9999) == "Ascendant"

    def test_rank_nephilim_at_threshold(self, repo):
        assert repo._calculate_rank(10000) == "Nephilim"

    def test_rank_nephilim_above_threshold(self, repo):
        assert repo._calculate_rank(99999) == "Nephilim"


# ─────────────────────────────────────────────────────────────
# award_resonance — accumulation + rank promotion
# ─────────────────────────────────────────────────────────────

class TestAwardResonance:

    def test_award_resonance_creates_profile_if_absent(self, repo):
        result = repo.award_resonance("fresh_user", 10, "test")
        assert result["new_resonance"] == 10
        assert result["new_rank"] == "Initiate"
        assert result["rank_changed"] is False

    def test_award_resonance_accumulates(self, repo):
        repo.create_seeker_profile("acc_user")
        repo.award_resonance("acc_user", 50, "first")
        result = repo.award_resonance("acc_user", 30, "second")
        assert result["new_resonance"] == 80
        profile = repo.get_seeker_profile("acc_user")
        assert profile["total_resonance"] == 80

    def test_award_resonance_no_rank_change(self, repo):
        repo.create_seeker_profile("rank_stable")
        result = repo.award_resonance("rank_stable", 50, "test")
        assert result["rank_changed"] is False
        assert result["previous_rank"] is None

    def test_award_resonance_triggers_rank_up_to_acolyte(self, repo):
        repo.create_seeker_profile("rank_up_user")
        result = repo.award_resonance("rank_up_user", 100, "test")
        assert result["rank_changed"] is True
        assert result["new_rank"] == "Acolyte"
        assert result["previous_rank"] == "Initiate"

    def test_award_resonance_rank_up_persisted(self, repo):
        repo.create_seeker_profile("persist_rank")
        repo.award_resonance("persist_rank", 500, "test")
        profile = repo.get_seeker_profile("persist_rank")
        assert profile["rank_name"] == "Adept"
        assert profile["total_resonance"] == 500

    def test_award_resonance_logs_event(self, repo):
        repo.create_seeker_profile("log_user")
        repo.award_resonance("log_user", 20, "first_conversation", persona_key="eeva", session_id="sess_1")
        history = repo.get_resonance_history("log_user")
        assert len(history) == 1
        assert history[0]["amount"] == 20
        assert history[0]["reason"] == "first_conversation"
        assert history[0]["persona_key"] == "eeva"
        assert history[0]["session_id"] == "sess_1"

    def test_award_resonance_multiple_events_in_history(self, repo):
        repo.create_seeker_profile("multi_user")
        repo.award_resonance("multi_user", 10, "a")
        repo.award_resonance("multi_user", 20, "b")
        repo.award_resonance("multi_user", 30, "c")
        history = repo.get_resonance_history("multi_user")
        assert len(history) == 3

    def test_award_resonance_multiple_events_newest_first_order(self, repo):
        """Same-second awards return newest-first (ORDER BY timestamp DESC, id DESC)."""
        repo.create_seeker_profile("multi_order_user")
        repo.award_resonance("multi_order_user", 10, "a")
        repo.award_resonance("multi_order_user", 20, "b")
        repo.award_resonance("multi_order_user", 30, "c")
        history = repo.get_resonance_history("multi_order_user")
        assert history[0]["amount"] == 30  # newest first, id DESC tie-breaker

    def test_award_resonance_rank_achieved_at_set_on_rank_up(self, repo):
        repo.create_seeker_profile("rank_ts_user")
        repo.award_resonance("rank_ts_user", 100, "test")
        profile = repo.get_seeker_profile("rank_ts_user")
        assert profile["rank_achieved_at"] is not None

    def test_award_resonance_skips_multiple_ranks(self, repo):
        """A single large award can jump multiple rank levels."""
        repo.create_seeker_profile("multi_rank")
        result = repo.award_resonance("multi_rank", 10000, "mega_award")
        assert result["new_rank"] == "Nephilim"
        assert result["rank_changed"] is True
        assert result["previous_rank"] == "Initiate"


# ─────────────────────────────────────────────────────────────
# get_resonance_to_next_rank
# ─────────────────────────────────────────────────────────────

class TestResonanceToNextRank:

    def test_no_profile_returns_defaults(self, repo):
        result = repo.get_resonance_to_next_rank("nobody")
        assert result["current_rank"] == "Initiate"
        assert result["current_resonance"] == 0
        assert result["next_rank"] == "Acolyte"
        assert result["resonance_needed"] == RANK_THRESHOLDS["Acolyte"]
        assert result["progress_percent"] == 0

    def test_initiate_progress_toward_acolyte(self, repo):
        repo.create_seeker_profile("prog_user")
        repo.award_resonance("prog_user", 50, "test")  # 50/100 = 50%
        result = repo.get_resonance_to_next_rank("prog_user")
        assert result["next_rank"] == "Acolyte"
        assert result["resonance_needed"] == 50
        assert result["progress_percent"] == 50

    def test_max_rank_nephilim_returns_no_next(self, repo):
        repo.create_seeker_profile("max_user")
        repo.award_resonance("max_user", 10000, "test")
        result = repo.get_resonance_to_next_rank("max_user")
        assert result["next_rank"] is None
        assert result["resonance_needed"] == 0
        assert result["progress_percent"] == 100

    def test_acolyte_progress_toward_adept(self, repo):
        repo.create_seeker_profile("aco_user")
        # Acolyte at 100, Adept at 500 — tier size = 400
        repo.award_resonance("aco_user", 300, "test")  # 200 into tier = 50%
        result = repo.get_resonance_to_next_rank("aco_user")
        assert result["current_rank"] == "Acolyte"
        assert result["next_rank"] == "Adept"
        assert result["progress_percent"] == 50


# ─────────────────────────────────────────────────────────────
# Persona Affinity
# ─────────────────────────────────────────────────────────────

class TestPersonaAffinity:

    def test_get_affinity_returns_none_when_absent(self, repo):
        repo.create_seeker_profile("user_a")
        result = repo.get_affinity("user_a", "eeva")
        assert result is None

    def test_create_affinity_returns_dict(self, repo):
        repo.create_seeker_profile("user_a")
        affinity = repo.create_affinity("user_a", "eeva")
        assert affinity["user_id"] == "user_a"
        assert affinity["persona_key"] == "eeva"
        assert affinity["messages_count"] == 0
        assert affinity["affinity_level"] == 0

    def test_create_affinity_auto_creates_seeker(self, repo):
        """create_affinity should call get_or_create_seeker."""
        affinity = repo.create_affinity("auto_user", "nyx")
        assert affinity["user_id"] == "auto_user"
        profile = repo.get_seeker_profile("auto_user")
        assert profile is not None

    def test_get_or_create_affinity_creates_when_absent(self, repo):
        affinity = repo.get_or_create_affinity("new_user", "cipher")
        assert affinity["persona_key"] == "cipher"
        assert affinity["messages_count"] == 0

    def test_get_or_create_affinity_idempotent(self, repo):
        a1 = repo.get_or_create_affinity("user_b", "solace")
        a2 = repo.get_or_create_affinity("user_b", "solace")
        assert a1["persona_key"] == a2["persona_key"]
        rows = repo._fetchall_list(
            "SELECT * FROM persona_affinity WHERE user_id = ? AND persona_key = ?",
            ("user_b", "solace"),
        )
        assert len(rows) == 1

    def test_create_affinity_duplicate_falls_back_to_get(self, repo):
        repo.create_seeker_profile("dup_aff_user")
        repo.create_affinity("dup_aff_user", "eeva")
        # Second create should not raise — falls back to get_affinity
        affinity = repo.create_affinity("dup_aff_user", "eeva")
        assert affinity is not None
        assert affinity["persona_key"] == "eeva"

    def test_get_affinity_returns_existing(self, repo):
        repo.create_seeker_profile("user_c")
        repo.create_affinity("user_c", "aegis")
        affinity = repo.get_affinity("user_c", "aegis")
        assert affinity is not None
        assert affinity["persona_key"] == "aegis"

    def test_increment_messages_increases_count(self, repo):
        repo.create_seeker_profile("msg_user")
        repo.create_affinity("msg_user", "aurora")
        result = repo.increment_messages("msg_user", "aurora", count=5)
        assert result["messages_count"] == 5

    def test_increment_messages_accumulates(self, repo):
        repo.create_seeker_profile("msg_acc")
        repo.increment_messages("msg_acc", "nyx", count=3)
        result = repo.increment_messages("msg_acc", "nyx", count=7)
        assert result["messages_count"] == 10

    def test_increment_messages_sets_last_conversation(self, repo):
        repo.create_seeker_profile("msg_ts")
        result = repo.increment_messages("msg_ts", "eeva")
        assert result["last_conversation"] is not None

    def test_increment_messages_first_conversation_flag(self, repo):
        repo.create_seeker_profile("msg_first")
        result = repo.increment_messages("msg_first", "eeva")
        assert result["is_first_conversation"] is True

    def test_increment_messages_not_first_after_first(self, repo):
        repo.create_seeker_profile("msg_second")
        repo.increment_messages("msg_second", "eeva")
        result = repo.increment_messages("msg_second", "eeva")
        assert result["is_first_conversation"] is False

    def test_increment_messages_auto_creates_affinity(self, repo):
        """increment_messages uses get_or_create_affinity — no pre-existing needed."""
        result = repo.increment_messages("brand_new", "eeva")
        assert result["messages_count"] == 1

    def test_get_all_affinities_empty(self, repo):
        repo.create_seeker_profile("aff_empty")
        result = repo.get_all_affinities("aff_empty")
        assert result == []

    def test_get_all_affinities_returns_all(self, repo):
        repo.create_seeker_profile("aff_multi")
        repo.create_affinity("aff_multi", "eeva")
        repo.create_affinity("aff_multi", "nyx")
        repo.create_affinity("aff_multi", "cipher")
        result = repo.get_all_affinities("aff_multi")
        assert len(result) == 3

    def test_get_all_affinities_ordered_by_messages_desc(self, repo):
        repo.create_seeker_profile("aff_order")
        repo.increment_messages("aff_order", "eeva", count=10)
        repo.increment_messages("aff_order", "nyx", count=2)
        repo.increment_messages("aff_order", "cipher", count=7)
        result = repo.get_all_affinities("aff_order")
        counts = [r["messages_count"] for r in result]
        assert counts == sorted(counts, reverse=True)

    def test_get_all_affinities_missing_user_returns_empty(self, repo):
        result = repo.get_all_affinities("nobody_here")
        assert result == []


# ─────────────────────────────────────────────────────────────
# Lore Unlock
# ─────────────────────────────────────────────────────────────

class TestLoreUnlock:

    def test_unlock_lore_returns_true_on_first_unlock(self, repo):
        repo.create_seeker_profile("lore_user")
        result = repo.unlock_lore("lore_user", "eeva", "fragment_001")
        assert result is True

    def test_unlock_lore_returns_false_on_duplicate(self, repo):
        repo.create_seeker_profile("lore_dup")
        repo.unlock_lore("lore_dup", "eeva", "fragment_001")
        result = repo.unlock_lore("lore_dup", "eeva", "fragment_001")
        assert result is False

    def test_unlock_lore_auto_creates_seeker(self, repo):
        repo.unlock_lore("auto_lore_user", "nyx", "frag_x")
        profile = repo.get_seeker_profile("auto_lore_user")
        assert profile is not None

    def test_is_lore_unlocked_false_when_not_unlocked(self, repo):
        repo.create_seeker_profile("lore_check")
        result = repo.is_lore_unlocked("lore_check", "eeva", "frag_missing")
        assert result is False

    def test_is_lore_unlocked_true_after_unlock(self, repo):
        repo.create_seeker_profile("lore_check2")
        repo.unlock_lore("lore_check2", "eeva", "frag_found")
        result = repo.is_lore_unlocked("lore_check2", "eeva", "frag_found")
        assert result is True

    def test_is_lore_unlocked_different_persona_false(self, repo):
        """fragment_id unlocked for one persona should not appear unlocked for another."""
        repo.create_seeker_profile("lore_persona_check")
        repo.unlock_lore("lore_persona_check", "eeva", "shared_frag")
        result = repo.is_lore_unlocked("lore_persona_check", "nyx", "shared_frag")
        assert result is False

    def test_get_unlocked_lore_empty_initially(self, repo):
        repo.create_seeker_profile("lore_empty")
        result = repo.get_unlocked_lore("lore_empty")
        assert result == []

    def test_get_unlocked_lore_all_personas(self, repo):
        repo.create_seeker_profile("lore_all")
        repo.unlock_lore("lore_all", "eeva", "frag_e1")
        repo.unlock_lore("lore_all", "nyx", "frag_n1")
        result = repo.get_unlocked_lore("lore_all")
        assert len(result) == 2

    def test_get_unlocked_lore_filter_by_persona(self, repo):
        repo.create_seeker_profile("lore_filter")
        repo.unlock_lore("lore_filter", "eeva", "frag_e1")
        repo.unlock_lore("lore_filter", "eeva", "frag_e2")
        repo.unlock_lore("lore_filter", "nyx", "frag_n1")
        result = repo.get_unlocked_lore("lore_filter", persona_key="eeva")
        assert len(result) == 2
        assert all(r["persona_key"] == "eeva" for r in result)

    def test_get_unlocked_lore_contains_fragment_id(self, repo):
        repo.create_seeker_profile("lore_shape")
        repo.unlock_lore("lore_shape", "eeva", "frag_abc")
        result = repo.get_unlocked_lore("lore_shape")
        assert result[0]["fragment_id"] == "frag_abc"
        assert result[0]["persona_key"] == "eeva"
        assert result[0]["unlocked_at"] is not None


# ─────────────────────────────────────────────────────────────
# check_and_unlock_lore — trigger logic
# ─────────────────────────────────────────────────────────────

class TestCheckAndUnlockLore:

    def _make_fragments(self, *specs):
        """Helper: build fragment list from (fragment_id, **kwargs) specs."""
        result = []
        for spec in specs:
            fid, kwargs = spec[0], spec[1]
            result.append({"fragment_id": fid, **kwargs})
        return result

    def test_returns_empty_when_no_affinity(self, repo):
        """No affinity record → no unlocks possible."""
        repo.create_seeker_profile("ck_user_noaff")
        fragments = [{"fragment_id": "f1", "messages_required": 0}]
        result = repo.check_and_unlock_lore("ck_user_noaff", "eeva", fragments)
        assert result == []

    def test_messages_required_met_unlocks_fragment(self, repo):
        repo.increment_messages("ck_user1", "eeva", count=10)
        fragments = [{"fragment_id": "f1", "messages_required": 5}]
        result = repo.check_and_unlock_lore("ck_user1", "eeva", fragments)
        assert len(result) == 1
        assert result[0]["fragment_id"] == "f1"

    def test_messages_required_not_met_no_unlock(self, repo):
        repo.increment_messages("ck_user2", "eeva", count=3)
        fragments = [{"fragment_id": "f2", "messages_required": 10}]
        result = repo.check_and_unlock_lore("ck_user2", "eeva", fragments)
        assert result == []

    def test_already_unlocked_fragment_skipped(self, repo):
        repo.increment_messages("ck_skip", "eeva", count=10)
        repo.unlock_lore("ck_skip", "eeva", "already_done")
        fragments = [{"fragment_id": "already_done", "messages_required": 1}]
        result = repo.check_and_unlock_lore("ck_skip", "eeva", fragments)
        assert result == []

    def test_fragment_without_fragment_id_skipped(self, repo):
        repo.increment_messages("ck_noid", "eeva", count=5)
        fragments = [{"messages_required": 1}]  # no fragment_id key
        result = repo.check_and_unlock_lore("ck_noid", "eeva", fragments)
        assert result == []

    def test_fragment_with_empty_fragment_id_skipped(self, repo):
        repo.increment_messages("ck_emptyid", "eeva", count=5)
        fragments = [{"fragment_id": "", "messages_required": 1}]
        result = repo.check_and_unlock_lore("ck_emptyid", "eeva", fragments)
        assert result == []

    def test_malformed_fragment_no_conditions_skipped(self, repo):
        """Fragment with no recognised trigger fields should be skipped."""
        repo.increment_messages("ck_malformed", "eeva", count=5)
        fragments = [{"fragment_id": "no_trigger_keys"}]
        result = repo.check_and_unlock_lore("ck_malformed", "eeva", fragments)
        assert result == []

    def test_check_and_unlock_awards_resonance(self, repo):
        repo.increment_messages("ck_reward", "eeva", count=5)
        fragments = [{"fragment_id": "reward_frag", "messages_required": 1}]
        repo.check_and_unlock_lore("ck_reward", "eeva", fragments)
        profile = repo.get_seeker_profile("ck_reward")
        assert profile["total_resonance"] == RESONANCE_REWARDS["lore_unlock"]

    def test_rank_required_met(self, repo):
        repo.award_resonance("ck_rank", 500, "test")  # Adept
        repo.get_or_create_affinity("ck_rank", "cipher")
        fragments = [{"fragment_id": "rank_frag", "rank_required": "Adept"}]
        result = repo.check_and_unlock_lore("ck_rank", "cipher", fragments)
        assert len(result) == 1

    def test_rank_required_not_met(self, repo):
        repo.award_resonance("ck_lowrank", 10, "test")  # still Initiate
        repo.get_or_create_affinity("ck_lowrank", "cipher")
        fragments = [{"fragment_id": "high_rank_frag", "rank_required": "Adept"}]
        result = repo.check_and_unlock_lore("ck_lowrank", "cipher", fragments)
        assert result == []

    def test_affinity_required_met(self, repo):
        repo.create_seeker_profile("ck_aff_met")
        # Manually set affinity_level to 5
        repo.get_or_create_affinity("ck_aff_met", "nyx")
        repo._execute(
            "UPDATE persona_affinity SET affinity_level = 5 WHERE user_id = ? AND persona_key = ?",
            ("ck_aff_met", "nyx"),
        )
        fragments = [{"fragment_id": "aff_frag", "affinity_required": 5}]
        result = repo.check_and_unlock_lore("ck_aff_met", "nyx", fragments)
        assert len(result) == 1

    def test_affinity_required_not_met(self, repo):
        repo.get_or_create_affinity("ck_aff_low", "nyx")
        fragments = [{"fragment_id": "high_aff_frag", "affinity_required": 10}]
        result = repo.check_and_unlock_lore("ck_aff_low", "nyx", fragments)
        assert result == []

    def test_cross_persona_required_string_met(self, repo):
        repo.unlock_lore("ck_cross", "eeva", "prereq_frag")
        repo.get_or_create_affinity("ck_cross", "nyx")
        fragments = [{"fragment_id": "cross_frag", "cross_persona_required": "prereq_frag"}]
        result = repo.check_and_unlock_lore("ck_cross", "nyx", fragments)
        assert len(result) == 1

    def test_cross_persona_required_list_met(self, repo):
        repo.unlock_lore("ck_cross_list", "eeva", "p1")
        repo.unlock_lore("ck_cross_list", "cipher", "p2")
        repo.get_or_create_affinity("ck_cross_list", "nyx")
        fragments = [{"fragment_id": "cross_list_frag", "cross_persona_required": ["p1", "p2"]}]
        result = repo.check_and_unlock_lore("ck_cross_list", "nyx", fragments)
        assert len(result) == 1

    def test_cross_persona_required_partial_not_met(self, repo):
        repo.unlock_lore("ck_cross_partial", "eeva", "p1")
        # p2 not unlocked
        repo.get_or_create_affinity("ck_cross_partial", "nyx")
        fragments = [{"fragment_id": "cp_frag", "cross_persona_required": ["p1", "p2"]}]
        result = repo.check_and_unlock_lore("ck_cross_partial", "nyx", fragments)
        assert result == []

    def test_trigger_logic_any_or_passes(self, repo):
        """trigger_logic='any': only one condition needs to pass."""
        repo.increment_messages("ck_any", "eeva", count=10)  # messages_count=10
        repo.get_or_create_affinity("ck_any", "eeva")
        fragments = [{
            "fragment_id": "any_frag",
            "messages_required": 100,   # NOT met (10 < 100)
            "affinity_required": 0,     # met (0 >= 0)
            "trigger_logic": "any",
        }]
        result = repo.check_and_unlock_lore("ck_any", "eeva", fragments)
        assert len(result) == 1

    def test_trigger_logic_all_default_requires_all(self, repo):
        """trigger_logic='all' (default): all conditions must pass."""
        repo.increment_messages("ck_all", "eeva", count=10)
        repo.get_or_create_affinity("ck_all", "eeva")
        fragments = [{
            "fragment_id": "all_frag",
            "messages_required": 100,  # NOT met
            "affinity_required": 0,    # met
            # trigger_logic defaults to 'all'
        }]
        result = repo.check_and_unlock_lore("ck_all", "eeva", fragments)
        assert result == []

    def test_multiple_fragments_partial_unlock(self, repo):
        repo.increment_messages("ck_partial", "eeva", count=5)
        fragments = [
            {"fragment_id": "f_easy", "messages_required": 1},
            {"fragment_id": "f_hard", "messages_required": 100},
        ]
        result = repo.check_and_unlock_lore("ck_partial", "eeva", fragments)
        assert len(result) == 1
        assert result[0]["fragment_id"] == "f_easy"

    def test_unlocked_cache_updated_within_single_call(self, repo):
        """A fragment unlocked earlier in the same check_and_unlock_lore call
        should be visible to subsequent cross_persona_required checks in the same call."""
        repo.get_or_create_affinity("ck_cache", "eeva")
        fragments = [
            # First fragment: unlocked by affinity=0
            {"fragment_id": "first_frag", "affinity_required": 0},
            # Second fragment: requires first_frag to be unlocked
            {"fragment_id": "second_frag", "cross_persona_required": "first_frag"},
        ]
        result = repo.check_and_unlock_lore("ck_cache", "eeva", fragments)
        # Both should unlock: first_frag is added to cached set after first unlock
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────
# get_seeker_summary
# ─────────────────────────────────────────────────────────────

class TestSeekerSummary:

    def test_summary_nonexistent_user_returns_exists_false(self, repo):
        result = repo.get_seeker_summary("ghost")
        assert result["exists"] is False
        assert result["user_id"] == "ghost"

    def test_summary_existing_user_exists_true(self, repo):
        repo.create_seeker_profile("sum_user")
        result = repo.get_seeker_summary("sum_user")
        assert result["exists"] is True

    def test_summary_contains_expected_keys(self, repo):
        repo.create_seeker_profile("sum_keys")
        result = repo.get_seeker_summary("sum_keys")
        for key in ("exists", "user_id", "rank", "total_resonance", "faction_primary",
                    "faction_secondary", "rank_progress", "persona_affinities",
                    "unlocked_lore_count", "unlocked_lore", "created_at", "updated_at"):
            assert key in result, f"Missing key: {key}"

    def test_summary_rank_and_resonance_correct(self, repo):
        repo.create_seeker_profile("sum_rank")
        repo.award_resonance("sum_rank", 500, "test")
        result = repo.get_seeker_summary("sum_rank")
        assert result["rank"] == "Adept"
        assert result["total_resonance"] == 500

    def test_summary_persona_affinities_populated(self, repo):
        repo.create_seeker_profile("sum_aff")
        repo.create_affinity("sum_aff", "eeva")
        repo.create_affinity("sum_aff", "nyx")
        result = repo.get_seeker_summary("sum_aff")
        assert len(result["persona_affinities"]) == 2

    def test_summary_unlocked_lore_count(self, repo):
        repo.create_seeker_profile("sum_lore")
        repo.unlock_lore("sum_lore", "eeva", "f1")
        repo.unlock_lore("sum_lore", "eeva", "f2")
        result = repo.get_seeker_summary("sum_lore")
        assert result["unlocked_lore_count"] == 2
        assert len(result["unlocked_lore"]) == 2

    def test_summary_faction_populated(self, repo):
        repo.create_seeker_profile("sum_faction")
        repo.update_seeker_faction("sum_faction", "Void", "Celestial")
        result = repo.get_seeker_summary("sum_faction")
        assert result["faction_primary"] == "Void"
        assert result["faction_secondary"] == "Celestial"

    def test_summary_rank_progress_is_dict(self, repo):
        repo.create_seeker_profile("sum_prog")
        result = repo.get_seeker_summary("sum_prog")
        assert isinstance(result["rank_progress"], dict)
        assert "current_rank" in result["rank_progress"]


# ─────────────────────────────────────────────────────────────
# get_resonance_history
# ─────────────────────────────────────────────────────────────

class TestResonanceHistory:

    def test_history_empty_for_new_user(self, repo):
        repo.create_seeker_profile("hist_user")
        result = repo.get_resonance_history("hist_user")
        assert result == []

    def test_history_empty_for_nonexistent_user(self, repo):
        result = repo.get_resonance_history("nobody")
        assert result == []

    def test_history_ordered_newest_first(self, repo):
        repo.create_seeker_profile("hist_order")
        repo.award_resonance("hist_order", 10, "first")
        repo.award_resonance("hist_order", 20, "second")
        history = repo.get_resonance_history("hist_order")
        assert history[0]["amount"] == 20
        assert history[1]["amount"] == 10

    def test_history_limit_respected(self, repo):
        repo.create_seeker_profile("hist_limit")
        for i in range(60):
            repo.award_resonance("hist_limit", 1, f"event_{i}")
        result = repo.get_resonance_history("hist_limit", limit=10)
        assert len(result) == 10

    def test_history_default_limit_50(self, repo):
        repo.create_seeker_profile("hist_default")
        for i in range(55):
            repo.award_resonance("hist_default", 1, f"e_{i}")
        result = repo.get_resonance_history("hist_default")
        assert len(result) == 50

    def test_history_event_fields(self, repo):
        repo.create_seeker_profile("hist_fields")
        repo.award_resonance("hist_fields", 15, "daily_return", persona_key="aurora", session_id="s42")
        event = repo.get_resonance_history("hist_fields")[0]
        assert event["user_id"] == "hist_fields"
        assert event["amount"] == 15
        assert event["reason"] == "daily_return"
        assert event["persona_key"] == "aurora"
        assert event["session_id"] == "s42"
        assert event["timestamp"]

    def test_history_without_optional_fields(self, repo):
        """persona_key and session_id should be None when not provided."""
        repo.create_seeker_profile("hist_opt")
        repo.award_resonance("hist_opt", 5, "test")
        event = repo.get_resonance_history("hist_opt")[0]
        assert event["persona_key"] is None
        assert event["session_id"] is None


# ─────────────────────────────────────────────────────────────
# Integration: full progression flow
# ─────────────────────────────────────────────────────────────

class TestIntegrationFlow:

    def test_full_progression_journey(self, repo):
        """Simulate a realistic user journey: chat, rank up, lore unlock."""
        user_id = "journey_user"

        # First contact: seeker created
        profile = repo.get_or_create_seeker(user_id)
        assert profile["rank_name"] == "Initiate"

        # Chat with eeva
        affinity = repo.get_or_create_affinity(user_id, "eeva")
        repo.increment_messages(user_id, "eeva", count=5)

        # Award first-conversation resonance
        result = repo.award_resonance(user_id, RESONANCE_REWARDS["first_conversation"], "first_conversation", persona_key="eeva")
        assert result["new_resonance"] == 20
        assert result["rank_changed"] is False

        # More resonance — cross Acolyte threshold
        result = repo.award_resonance(user_id, 80, "extended_session")
        assert result["new_rank"] == "Acolyte"
        assert result["rank_changed"] is True

        # Unlock a lore fragment
        unlocked = repo.unlock_lore(user_id, "eeva", "lore_origin_story")
        assert unlocked is True

        # Check summary
        summary = repo.get_seeker_summary(user_id)
        assert summary["exists"] is True
        assert summary["rank"] == "Acolyte"
        assert summary["unlocked_lore_count"] == 1

        # History should have all events
        history = repo.get_resonance_history(user_id)
        assert len(history) == 2

    def test_multi_user_isolation(self, repo):
        """Two users in the same db should not bleed into each other."""
        repo.award_resonance("user_alpha", 500, "test")
        repo.award_resonance("user_beta", 50, "test")

        alpha = repo.get_seeker_profile("user_alpha")
        beta = repo.get_seeker_profile("user_beta")

        assert alpha["rank_name"] == "Adept"
        assert beta["rank_name"] == "Initiate"
        assert alpha["total_resonance"] == 500
        assert beta["total_resonance"] == 50


# ─────────────────────────────────────────────────────────────
# increment_affinity (Phase-2 fix: affinity_level was never incremented)
# ─────────────────────────────────────────────────────────────

class TestIncrementAffinity:
    def test_gated_below_start_messages(self, repo):
        # messages_count starts at 0 (< AFFINITY_START_MESSAGES) → no deepening
        r = repo.increment_affinity("aff_u1", "eeva", 1)
        assert r["affinity_level"] == 0
        assert r["milestone_reached"] is None

    def test_increments_after_threshold_with_emerging_milestone(self, repo):
        repo.increment_messages("aff_u2", "eeva", count=5)  # reach the gate
        r = repo.increment_affinity("aff_u2", "eeva", 1)
        assert r["affinity_level"] == 1
        assert r["milestone_reached"] == "emerging"

    def test_milestones_awarded_once_in_order(self, repo):
        repo.increment_messages("aff_u3", "eeva", count=5)
        milestones = []
        for _ in range(6):  # climb affinity 1..6
            r = repo.increment_affinity("aff_u3", "eeva", 1)
            if r["milestone_reached"]:
                milestones.append(r["milestone_reached"])
        assert milestones == ["emerging", "established"]  # at 1 and 5, each once
        assert repo.get_or_create_affinity("aff_u3", "eeva")["affinity_level"] == 6

    def test_affinity_required_lore_fires_after_fix(self, repo):
        repo.increment_messages("aff_u4", "eeva", count=5)
        frags = [{"fragment_id": "deep1", "affinity_required": 5}]
        for _ in range(4):  # affinity_level → 4, below requirement
            repo.increment_affinity("aff_u4", "eeva", 1)
        repo.check_and_unlock_lore("aff_u4", "eeva", frags)
        assert all(u["fragment_id"] != "deep1" for u in repo.get_unlocked_lore("aff_u4", "eeva"))
        repo.increment_affinity("aff_u4", "eeva", 1)  # cross to 5
        repo.check_and_unlock_lore("aff_u4", "eeva", frags)
        assert any(u["fragment_id"] == "deep1" for u in repo.get_unlocked_lore("aff_u4", "eeva"))
