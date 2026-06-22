"""
Unit tests for src/coordinator/jupiter/strategy_loader.py

Covers:
- load_strategies: happy path, missing dir, skip non-.json, sorted order,
  skip entries without strategy_id, handle malformed JSON, empty dir
- load_strategy: found, not found, malformed JSON
- save_strategy: creates file, round-trips JSON, creates dir if missing
- update_strategy: flat key patch, nested dict merge, strategy not found
- reset_daily_spend: resets strategies not already reset today, skips those already reset
- update_strategy_spend: accumulates spend, strategy not found

All I/O goes through pytest tmp_path — no network, no Mongo, no Ollama.
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.coordinator.jupiter.strategy_loader import (
    load_strategies,
    load_strategy,
    save_strategy,
    update_strategy,
    reset_daily_spend,
    update_strategy_spend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(directory: Path, strategy: dict) -> Path:
    sid = strategy["strategy_id"]
    fp = directory / f"{sid}.json"
    fp.write_text(json.dumps(strategy), encoding="utf-8")
    return fp


def _make_strategy(sid: str = "s-001", **kwargs) -> dict:
    return {
        "strategy_id": sid,
        "strategy_type": "dca",
        "token_pair": {"from": "USDC", "to": "SOL"},
        "parameters": {"cycle_frequency_hours": 168},
        "guardrails": {
            "daily_limit_usdc": 100.0,
            "spent_today_usdc": 0.0,
            "daily_reset_date": "1970-01-01",
        },
        **kwargs,
    }


# ---------------------------------------------------------------------------
# load_strategies
# ---------------------------------------------------------------------------

class TestLoadStrategies:
    def test_loads_single_valid_strategy(self, tmp_path):
        _write(tmp_path, _make_strategy("s-001"))
        result = load_strategies(str(tmp_path))
        assert len(result) == 1
        assert result[0]["strategy_id"] == "s-001"

    def test_loads_multiple_sorted_alphabetically(self, tmp_path):
        _write(tmp_path, _make_strategy("s-003"))
        _write(tmp_path, _make_strategy("s-001"))
        _write(tmp_path, _make_strategy("s-002"))
        result = load_strategies(str(tmp_path))
        ids = [r["strategy_id"] for r in result]
        assert ids == ["s-001", "s-002", "s-003"]

    def test_missing_directory_returns_empty(self, tmp_path):
        result = load_strategies(str(tmp_path / "nonexistent"))
        assert result == []

    def test_empty_directory_returns_empty(self, tmp_path):
        result = load_strategies(str(tmp_path))
        assert result == []

    def test_skips_non_json_files(self, tmp_path):
        _write(tmp_path, _make_strategy("s-001"))
        (tmp_path / "notes.txt").write_text("not a strategy")
        (tmp_path / "data.csv").write_text("a,b,c")
        result = load_strategies(str(tmp_path))
        assert len(result) == 1

    def test_skips_entry_missing_strategy_id(self, tmp_path):
        (tmp_path / "bad.json").write_text(json.dumps({"type": "dca"}))
        _write(tmp_path, _make_strategy("s-001"))
        result = load_strategies(str(tmp_path))
        assert len(result) == 1
        assert result[0]["strategy_id"] == "s-001"

    def test_skips_malformed_json(self, tmp_path):
        (tmp_path / "corrupt.json").write_text("{not valid json")
        _write(tmp_path, _make_strategy("s-001"))
        result = load_strategies(str(tmp_path))
        assert len(result) == 1

    def test_returns_all_fields(self, tmp_path):
        strat = _make_strategy("s-001")
        _write(tmp_path, strat)
        result = load_strategies(str(tmp_path))
        assert result[0] == strat


# ---------------------------------------------------------------------------
# load_strategy
# ---------------------------------------------------------------------------

class TestLoadStrategy:
    def test_found(self, tmp_path):
        _write(tmp_path, _make_strategy("s-001"))
        result = load_strategy("s-001", str(tmp_path))
        assert result is not None
        assert result["strategy_id"] == "s-001"

    def test_not_found_returns_none(self, tmp_path):
        result = load_strategy("s-999", str(tmp_path))
        assert result is None

    def test_malformed_json_returns_none(self, tmp_path):
        (tmp_path / "s-bad.json").write_text("{broken")
        result = load_strategy("s-bad", str(tmp_path))
        assert result is None

    def test_round_trips_all_fields(self, tmp_path):
        strat = _make_strategy("s-001", last_executed="2026-01-01T00:00:00Z")
        _write(tmp_path, strat)
        result = load_strategy("s-001", str(tmp_path))
        assert result == strat


# ---------------------------------------------------------------------------
# save_strategy
# ---------------------------------------------------------------------------

class TestSaveStrategy:
    def test_creates_file(self, tmp_path):
        strat = _make_strategy("s-001")
        fp = save_strategy(strat, str(tmp_path))
        assert Path(fp).exists()

    def test_returned_path_is_correct(self, tmp_path):
        strat = _make_strategy("s-001")
        fp = save_strategy(strat, str(tmp_path))
        assert fp == str(tmp_path / "s-001.json")

    def test_content_round_trips(self, tmp_path):
        strat = _make_strategy("s-001")
        fp = save_strategy(strat, str(tmp_path))
        loaded = json.loads(Path(fp).read_text())
        assert loaded == strat

    def test_creates_directory_if_missing(self, tmp_path):
        subdir = tmp_path / "new_subdir"
        strat = _make_strategy("s-001")
        save_strategy(strat, str(subdir))
        assert (subdir / "s-001.json").exists()

    def test_overwrites_existing(self, tmp_path):
        strat = _make_strategy("s-001")
        _write(tmp_path, strat)
        strat["parameters"]["cycle_frequency_hours"] = 24
        save_strategy(strat, str(tmp_path))
        loaded = json.loads((tmp_path / "s-001.json").read_text())
        assert loaded["parameters"]["cycle_frequency_hours"] == 24


# ---------------------------------------------------------------------------
# update_strategy
# ---------------------------------------------------------------------------

class TestUpdateStrategy:
    def test_flat_key_patch(self, tmp_path):
        _write(tmp_path, _make_strategy("s-001"))
        update_strategy("s-001", {"status": "paused"}, str(tmp_path))
        result = load_strategy("s-001", str(tmp_path))
        assert result["status"] == "paused"

    def test_nested_dict_merge(self, tmp_path):
        strat = _make_strategy("s-001")
        strat["guardrails"]["daily_limit_usdc"] = 100.0
        strat["guardrails"]["spent_today_usdc"] = 50.0
        _write(tmp_path, strat)
        update_strategy("s-001", {"guardrails": {"spent_today_usdc": 75.0}}, str(tmp_path))
        result = load_strategy("s-001", str(tmp_path))
        # Nested merge: spent updated, daily_limit preserved
        assert result["guardrails"]["spent_today_usdc"] == 75.0
        assert result["guardrails"]["daily_limit_usdc"] == 100.0

    def test_strategy_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            update_strategy("s-999", {"status": "paused"}, str(tmp_path))

    def test_flat_value_overwrites_scalar(self, tmp_path):
        strat = _make_strategy("s-001", last_executed="2026-01-01T00:00:00+00:00")
        _write(tmp_path, strat)
        update_strategy("s-001", {"last_executed": "2026-06-22T10:00:00+00:00"}, str(tmp_path))
        result = load_strategy("s-001", str(tmp_path))
        assert result["last_executed"] == "2026-06-22T10:00:00+00:00"


# ---------------------------------------------------------------------------
# reset_daily_spend
# ---------------------------------------------------------------------------

class TestResetDailySpend:
    def test_resets_strategies_not_yet_reset_today(self, tmp_path):
        strat = _make_strategy("s-001")
        strat["guardrails"]["spent_today_usdc"] = 75.0
        strat["guardrails"]["daily_reset_date"] = "1970-01-01"
        _write(tmp_path, strat)

        count = reset_daily_spend(str(tmp_path))

        assert count == 1
        result = load_strategy("s-001", str(tmp_path))
        assert result["guardrails"]["spent_today_usdc"] == 0.0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert result["guardrails"]["daily_reset_date"] == today

    def test_skips_strategies_already_reset_today(self, tmp_path):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        strat = _make_strategy("s-001")
        strat["guardrails"]["spent_today_usdc"] = 99.0
        strat["guardrails"]["daily_reset_date"] = today
        _write(tmp_path, strat)

        count = reset_daily_spend(str(tmp_path))

        assert count == 0
        result = load_strategy("s-001", str(tmp_path))
        assert result["guardrails"]["spent_today_usdc"] == 99.0  # untouched

    def test_resets_multiple_strategies(self, tmp_path):
        for i in range(3):
            strat = _make_strategy(f"s-00{i}")
            strat["guardrails"]["spent_today_usdc"] = float(i * 10)
            strat["guardrails"]["daily_reset_date"] = "1970-01-01"
            _write(tmp_path, strat)

        count = reset_daily_spend(str(tmp_path))
        assert count == 3

    def test_returns_zero_for_empty_dir(self, tmp_path):
        assert reset_daily_spend(str(tmp_path)) == 0

    def test_mixed_reset_states(self, tmp_path):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        strat_old = _make_strategy("s-001")
        strat_old["guardrails"]["daily_reset_date"] = "1970-01-01"
        strat_new = _make_strategy("s-002")
        strat_new["guardrails"]["daily_reset_date"] = today
        _write(tmp_path, strat_old)
        _write(tmp_path, strat_new)

        count = reset_daily_spend(str(tmp_path))
        assert count == 1


# ---------------------------------------------------------------------------
# update_strategy_spend
# ---------------------------------------------------------------------------

class TestUpdateStrategySpend:
    def test_adds_to_existing_spend(self, tmp_path):
        strat = _make_strategy("s-001")
        strat["guardrails"]["spent_today_usdc"] = 20.0
        _write(tmp_path, strat)

        update_strategy_spend("s-001", 30.0, str(tmp_path))

        result = load_strategy("s-001", str(tmp_path))
        assert result["guardrails"]["spent_today_usdc"] == pytest.approx(50.0)

    def test_adds_from_zero(self, tmp_path):
        strat = _make_strategy("s-001")
        strat["guardrails"]["spent_today_usdc"] = 0.0
        _write(tmp_path, strat)

        update_strategy_spend("s-001", 55.5, str(tmp_path))

        result = load_strategy("s-001", str(tmp_path))
        assert result["guardrails"]["spent_today_usdc"] == pytest.approx(55.5)

    def test_strategy_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            update_strategy_spend("s-999", 10.0, str(tmp_path))

    def test_accumulates_across_multiple_calls(self, tmp_path):
        strat = _make_strategy("s-001")
        strat["guardrails"]["spent_today_usdc"] = 0.0
        _write(tmp_path, strat)

        update_strategy_spend("s-001", 10.0, str(tmp_path))
        update_strategy_spend("s-001", 10.0, str(tmp_path))
        update_strategy_spend("s-001", 10.0, str(tmp_path))

        result = load_strategy("s-001", str(tmp_path))
        assert result["guardrails"]["spent_today_usdc"] == pytest.approx(30.0)
