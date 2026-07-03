# tests/backend/coordinator/test_strategy_service.py
"""
Unit tests for StrategyService — comprehensive deterministic coverage.

Covers:
- list_strategies: valid dir, empty dir, filtered by user_id, missing strategy_id, malformed JSON
- get_strategy: found, not found, malformed JSON
- activate_strategy: happy path (guardrail mutation, status, timestamps, logging)
- pause_strategy: success, not found
- resume_strategy: success, not found
- cancel_strategy: success, not found
- check_guardrails: daily limit, per-trade limit, both passing, edge values
- has_open_position: always False
- _log_approval_decision: invoked without raising

All file I/O goes through tmp_path — no network, no Mongo, no Ollama.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest

from src.coordinator.services.strategy_service import StrategyService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_strategy(directory: Path, strategy: dict) -> Path:
    """Write a strategy dict as JSON into directory/{strategy_id}.json."""
    sid = strategy["strategy_id"]
    fp = directory / f"{sid}.json"
    fp.write_text(json.dumps(strategy), encoding="utf-8")
    return fp


def _make_strategy(
    strategy_id: str = "strat-001",
    user_id: str = "user-1",
    status: str = "active",
    daily_limit: float = 100.0,
    max_trade: float = 50.0,
    spent_today: float = 0.0,
) -> dict:
    """Return a minimal valid strategy dict."""
    return {
        "strategy_id": strategy_id,
        "user_id": user_id,
        "status": status,
        "guardrails": {
            "daily_limit_usdc": daily_limit,
            "max_trade_size_usdc": max_trade,
            "spent_today_usdc": spent_today,
            "daily_reset_date": "2026-06-22",
        },
    }


# ---------------------------------------------------------------------------
# list_strategies
# ---------------------------------------------------------------------------

class TestListStrategies:
    """Tests for StrategyService.list_strategies."""

    def test_returns_empty_list_for_missing_dir(self, tmp_path):
        """Non-existent directory returns empty list without raising."""
        svc = StrategyService(strategies_dir=str(tmp_path / "does_not_exist"))
        result = svc.list_strategies()
        assert result == []

    def test_returns_empty_list_for_empty_dir(self, tmp_path):
        """Directory with no JSON files returns empty list."""
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert result == []

    def test_loads_single_strategy(self, tmp_path):
        strategy = _make_strategy("strat-a", user_id="user-1")
        _write_strategy(tmp_path, strategy)
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert len(result) == 1
        assert result[0]["strategy_id"] == "strat-a"

    def test_loads_multiple_strategies(self, tmp_path):
        for sid in ["strat-1", "strat-2", "strat-3"]:
            _write_strategy(tmp_path, _make_strategy(sid))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert len(result) == 3

    def test_skips_file_missing_strategy_id(self, tmp_path):
        """Files without strategy_id key are silently skipped."""
        (tmp_path / "bad.json").write_text(json.dumps({"name": "no id"}))
        _write_strategy(tmp_path, _make_strategy("strat-ok"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        # Only the valid strategy should be returned
        assert len(result) == 1
        assert result[0]["strategy_id"] == "strat-ok"

    def test_skips_malformed_json(self, tmp_path):
        """Malformed JSON files are skipped without crashing."""
        (tmp_path / "broken.json").write_text("{not valid json!!!")
        _write_strategy(tmp_path, _make_strategy("strat-valid"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert len(result) == 1

    def test_ignores_non_json_files(self, tmp_path):
        """Non-.json files are ignored."""
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "data.yaml").write_text("key: value")
        _write_strategy(tmp_path, _make_strategy("strat-json"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert len(result) == 1

    def test_filter_by_user_id_matches(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("strat-u1", user_id="user-1"))
        _write_strategy(tmp_path, _make_strategy("strat-u2", user_id="user-2"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies(user_id="user-1")
        assert len(result) == 1
        assert result[0]["strategy_id"] == "strat-u1"

    def test_filter_by_user_id_no_match(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("strat-u1", user_id="user-1"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies(user_id="nonexistent-user")
        assert result == []

    def test_filter_by_user_id_multiple_matches(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("strat-a", user_id="user-X"))
        _write_strategy(tmp_path, _make_strategy("strat-b", user_id="user-X"))
        _write_strategy(tmp_path, _make_strategy("strat-c", user_id="user-Y"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies(user_id="user-X")
        assert len(result) == 2

    def test_no_user_id_filter_returns_all(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("strat-a", user_id="user-1"))
        _write_strategy(tmp_path, _make_strategy("strat-b", user_id="user-2"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies()
        assert len(result) == 2

    def test_strategies_without_user_id_field_not_matched_in_filter(self, tmp_path):
        """Strategies with no user_id key are not returned when filtering."""
        s = _make_strategy("strat-no-uid")
        del s["user_id"]
        _write_strategy(tmp_path, s)
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies(user_id="user-1")
        assert result == []

    def test_returns_all_strategies_when_user_id_is_none(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("strat-x"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.list_strategies(user_id=None)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_strategy
# ---------------------------------------------------------------------------

class TestGetStrategy:
    """Tests for StrategyService.get_strategy."""

    def test_returns_strategy_when_found(self, tmp_path):
        strategy = _make_strategy("my-strat")
        _write_strategy(tmp_path, strategy)
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.get_strategy("my-strat")
        assert result is not None
        assert result["strategy_id"] == "my-strat"

    def test_returns_none_when_not_found(self, tmp_path):
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.get_strategy("nonexistent")
        assert result is None

    def test_returns_none_for_malformed_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("{bad json!")
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.get_strategy("bad")
        assert result is None

    def test_returns_full_strategy_data(self, tmp_path):
        strategy = _make_strategy("full-strat", user_id="user-99", daily_limit=500.0)
        _write_strategy(tmp_path, strategy)
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.get_strategy("full-strat")
        assert result["guardrails"]["daily_limit_usdc"] == 500.0
        assert result["user_id"] == "user-99"


# ---------------------------------------------------------------------------
# activate_strategy
# ---------------------------------------------------------------------------

class TestActivateStrategy:
    """Tests for StrategyService.activate_strategy."""

    def _base_config(self, tmp_path: Path, strategy_id: str = "act-strat") -> dict:
        return {
            "strategy_id": strategy_id,
            "status": "pending",
            "user_id": None,
            "approved_at": None,
            "guardrails": {
                "daily_limit_usdc": 100.0,
                "max_trade_size_usdc": 50.0,
                "spent_today_usdc": 99.0,  # should be reset to 0
                "daily_reset_date": "2020-01-01",
            },
        }

    def test_sets_status_to_active(self, tmp_path):
        config = self._base_config(tmp_path)
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-1")
        assert config["status"] == "active"

    def test_sets_user_id(self, tmp_path):
        config = self._base_config(tmp_path)
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-42")
        assert config["user_id"] == "user-42"

    def test_sets_approved_at_to_iso_string(self, tmp_path):
        config = self._base_config(tmp_path)
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-1")
        assert config["approved_at"] is not None
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(config["approved_at"])
        assert dt.tzinfo is not None  # UTC-aware

    def test_resets_spent_today_to_zero(self, tmp_path):
        config = self._base_config(tmp_path)
        config["guardrails"]["spent_today_usdc"] = 99.0
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-1")
        assert config["guardrails"]["spent_today_usdc"] == 0.0

    def test_sets_daily_reset_date_to_today(self, tmp_path):
        config = self._base_config(tmp_path)
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-1")
        today_str = date.today().isoformat()
        assert config["guardrails"]["daily_reset_date"] == today_str

    def test_returns_strategy_id(self, tmp_path):
        config = self._base_config(tmp_path, strategy_id="return-me")
        svc = StrategyService(strategies_dir=str(tmp_path))
        result = svc.activate_strategy(config, user_id="user-1")
        assert result == "return-me"

    def test_writes_strategy_to_disk(self, tmp_path):
        config = self._base_config(tmp_path, strategy_id="disk-check")
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.activate_strategy(config, user_id="user-1")
        # File should exist on disk
        written_fp = tmp_path / "disk-check.json"
        assert written_fp.exists()
        data = json.loads(written_fp.read_text())
        assert data["status"] == "active"

    def test_logs_approval_decision(self, tmp_path, caplog):
        config = self._base_config(tmp_path)
        svc = StrategyService(strategies_dir=str(tmp_path))
        with caplog.at_level(logging.INFO):
            svc.activate_strategy(config, user_id="user-log")
        # _log_approval_decision logs via logger.info
        assert any("act-strat" in r.message or "strategy_approved" in r.message or "user-log" in r.message
                   for r in caplog.records)


# ---------------------------------------------------------------------------
# pause_strategy
# ---------------------------------------------------------------------------

class TestPauseStrategy:
    """Tests for StrategyService.pause_strategy."""

    def test_returns_true_when_strategy_exists(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("pause-me", status="active"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.pause_strategy("pause-me", "user-1") is True

    def test_sets_status_to_paused_on_disk(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("pause-disk", status="active"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.pause_strategy("pause-disk", "user-1")
        data = json.loads((tmp_path / "pause-disk.json").read_text())
        assert data["status"] == "paused"

    def test_returns_false_when_strategy_not_found(self, tmp_path):
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.pause_strategy("ghost", "user-1") is False

    def test_logs_pause_event(self, tmp_path, caplog):
        _write_strategy(tmp_path, _make_strategy("log-pause"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        with caplog.at_level(logging.INFO):
            svc.pause_strategy("log-pause", "user-1")
        assert any("log-pause" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# resume_strategy
# ---------------------------------------------------------------------------

class TestResumeStrategy:
    """Tests for StrategyService.resume_strategy."""

    def test_returns_true_when_strategy_exists(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("resume-me", status="paused"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.resume_strategy("resume-me", "user-1") is True

    def test_sets_status_to_active_on_disk(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("resume-disk", status="paused"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.resume_strategy("resume-disk", "user-1")
        data = json.loads((tmp_path / "resume-disk.json").read_text())
        assert data["status"] == "active"

    def test_returns_false_when_strategy_not_found(self, tmp_path):
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.resume_strategy("ghost", "user-1") is False

    def test_logs_resume_event(self, tmp_path, caplog):
        _write_strategy(tmp_path, _make_strategy("log-resume", status="paused"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        with caplog.at_level(logging.INFO):
            svc.resume_strategy("log-resume", "user-1")
        assert any("log-resume" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# cancel_strategy
# ---------------------------------------------------------------------------

class TestCancelStrategy:
    """Tests for StrategyService.cancel_strategy."""

    def test_returns_true_when_strategy_exists(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("cancel-me"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.cancel_strategy("cancel-me", "user-1") is True

    def test_sets_status_to_cancelled_on_disk(self, tmp_path):
        _write_strategy(tmp_path, _make_strategy("cancel-disk"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        svc.cancel_strategy("cancel-disk", "user-1")
        data = json.loads((tmp_path / "cancel-disk.json").read_text())
        assert data["status"] == "cancelled"

    def test_returns_false_when_strategy_not_found(self, tmp_path):
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.cancel_strategy("ghost", "user-1") is False

    def test_logs_cancel_decision(self, tmp_path, caplog):
        _write_strategy(tmp_path, _make_strategy("log-cancel"))
        svc = StrategyService(strategies_dir=str(tmp_path))
        with caplog.at_level(logging.INFO):
            svc.cancel_strategy("log-cancel", "user-1")
        assert any(
            "log-cancel" in r.message or "strategy_cancelled" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# check_guardrails
# ---------------------------------------------------------------------------

class TestCheckGuardrails:
    """Tests for StrategyService.check_guardrails."""

    def _svc(self) -> StrategyService:
        return StrategyService(strategies_dir="not-used")

    def _strat(
        self,
        daily_limit: float = 100.0,
        max_trade: float = 50.0,
        spent_today: float = 0.0,
    ) -> dict:
        return {
            "guardrails": {
                "daily_limit_usdc": daily_limit,
                "max_trade_size_usdc": max_trade,
                "spent_today_usdc": spent_today,
            }
        }

    def test_passes_within_all_limits(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(self._strat(), amount_usdc=10.0)
        assert passed is True
        assert reason == "passed"

    def test_fails_when_daily_limit_exactly_exceeded(self):
        """spent + amount > daily_limit should fail."""
        svc = self._svc()
        # 60 + 50 = 110 > 100
        passed, reason = svc.check_guardrails(
            self._strat(daily_limit=100.0, spent_today=60.0), amount_usdc=50.0
        )
        assert passed is False
        assert "Daily limit exceeded" in reason

    def test_passes_when_daily_limit_exactly_met(self):
        """spent + amount == daily_limit: NOT exceeded (strict >)."""
        svc = self._svc()
        passed, reason = svc.check_guardrails(
            self._strat(daily_limit=100.0, spent_today=50.0), amount_usdc=50.0
        )
        assert passed is True

    def test_fails_when_trade_size_exceeds_max(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(
            self._strat(max_trade=50.0, daily_limit=1000.0), amount_usdc=51.0
        )
        assert passed is False
        assert "exceeds max" in reason

    def test_passes_when_trade_size_equals_max(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(
            self._strat(max_trade=50.0, daily_limit=1000.0), amount_usdc=50.0
        )
        assert passed is True

    def test_daily_limit_check_takes_priority_over_trade_size(self):
        """When daily limit is the first breach, that message is returned."""
        svc = self._svc()
        # daily limit hit first (since the check comes first in code)
        # spent=90, amount=20 → 110 > 100; also amount=20 < max_trade=50 so trade size passes
        passed, reason = svc.check_guardrails(
            self._strat(daily_limit=100.0, max_trade=50.0, spent_today=90.0),
            amount_usdc=20.0,
        )
        assert passed is False
        assert "Daily limit exceeded" in reason

    def test_missing_guardrails_key_uses_zero_defaults(self):
        """Strategy with no guardrails key defaults all values to 0.0."""
        svc = self._svc()
        # 0 + 1 > 0 → daily limit exceeded with any positive amount
        passed, reason = svc.check_guardrails({}, amount_usdc=1.0)
        assert passed is False

    def test_zero_amount_always_passes_limits(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(self._strat(), amount_usdc=0.0)
        assert passed is True

    def test_error_message_includes_amounts(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(
            self._strat(daily_limit=50.0, spent_today=40.0), amount_usdc=20.0
        )
        assert "40.00" in reason
        assert "20.00" in reason
        assert "50.00" in reason

    def test_trade_size_error_message_includes_amounts(self):
        svc = self._svc()
        passed, reason = svc.check_guardrails(
            self._strat(max_trade=30.0, daily_limit=1000.0), amount_usdc=55.5
        )
        assert "55.50" in reason
        assert "30.00" in reason


# ---------------------------------------------------------------------------
# has_open_position
# ---------------------------------------------------------------------------

class TestHasOpenPosition:
    """Tests for StrategyService.has_open_position."""

    def test_always_returns_false(self):
        svc = StrategyService(strategies_dir="not-used")
        assert svc.has_open_position("any-strategy") is False

    def test_returns_false_for_empty_string(self):
        svc = StrategyService(strategies_dir="not-used")
        assert svc.has_open_position("") is False

    def test_return_type_is_bool(self):
        svc = StrategyService(strategies_dir="not-used")
        result = svc.has_open_position("strat-x")
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _log_approval_decision
# ---------------------------------------------------------------------------

class TestLogApprovalDecision:
    """Tests for StrategyService._log_approval_decision."""

    def test_does_not_raise(self):
        svc = StrategyService(strategies_dir="not-used")
        # Should complete without error
        svc._log_approval_decision("strategy_approved", "strat-1", "user-1")

    def test_accepts_extra_kwarg(self):
        svc = StrategyService(strategies_dir="not-used")
        svc._log_approval_decision(
            "strategy_approved", "strat-1", "user-1", extra={"note": "test"}
        )

    def test_logs_decision_type(self, caplog):
        svc = StrategyService(strategies_dir="not-used")
        with caplog.at_level(logging.INFO, logger="src.coordinator.services.strategy_service"):
            svc._log_approval_decision("custom_decision", "strat-log", "user-log")
        combined = " ".join(r.message for r in caplog.records)
        assert "custom_decision" in combined
        assert "strat-log" in combined

    def test_returns_none(self):
        svc = StrategyService(strategies_dir="not-used")
        result = svc._log_approval_decision("decision", "s-id", "u-id")
        assert result is None


# ---------------------------------------------------------------------------
# Constructor / default
# ---------------------------------------------------------------------------

class TestConstructor:
    """Tests for StrategyService constructor."""

    def test_default_strategies_dir(self):
        svc = StrategyService()
        assert svc.strategies_dir == "strategies"

    def test_custom_strategies_dir(self, tmp_path):
        svc = StrategyService(strategies_dir=str(tmp_path))
        assert svc.strategies_dir == str(tmp_path)
