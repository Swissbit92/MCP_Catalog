"""
Unit tests for Jupiter strategy modules:
  - strategy_base.StrategyBase (abstract base)
  - dca_strategy.DCAStrategy
  - rsi_strategy.RSIStrategy

All tests are deterministic and have no network/Solana/Ollama dependencies.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from src.coordinator.jupiter.strategies.strategy_base import StrategyBase
from src.coordinator.jupiter.strategies.dca_strategy import DCAStrategy
from src.coordinator.jupiter.strategies.rsi_strategy import RSIStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_config(
    strategy_id: str = "s-001",
    strategy_type: str = "dca",
    token_pair: dict | None = None,
    parameters: dict | None = None,
    risk_management: dict | None = None,
    guardrails: dict | None = None,
    **extra,
) -> dict:
    cfg = {
        "strategy_id": strategy_id,
        "strategy_type": strategy_type,
        "token_pair": token_pair or {"from": "USDC", "to": "SOL"},
        "parameters": parameters or {},
        "risk_management": risk_management or {},
        "guardrails": guardrails or {},
    }
    cfg.update(extra)
    return cfg


# ---------------------------------------------------------------------------
# StrategyBase — abstract contract
# ---------------------------------------------------------------------------

class TestStrategyBase:
    """Tests for the abstract StrategyBase helpers (using DCAStrategy as a concrete stand-in)."""

    def test_init_stores_fields(self):
        cfg = _base_config(
            parameters={"cycle_frequency_hours": 24},
            risk_management={"stop_loss_pct": 5.0, "take_profit_pct": 10.0},
            guardrails={"daily_limit_usdc": 200.0, "spent_today_usdc": 50.0, "max_trade_size_usdc": 75.0},
        )
        strat = DCAStrategy(cfg)
        assert strat.strategy_id == "s-001"
        assert strat.strategy_type == "dca"
        assert strat.token_pair == {"from": "USDC", "to": "SOL"}
        assert strat.params == {"cycle_frequency_hours": 24}
        assert strat.risk == {"stop_loss_pct": 5.0, "take_profit_pct": 10.0}
        assert strat.guardrails == {"daily_limit_usdc": 200.0, "spent_today_usdc": 50.0, "max_trade_size_usdc": 75.0}

    def test_repr(self):
        strat = DCAStrategy(_base_config(strategy_id="abc", strategy_type="dca"))
        assert repr(strat) == "dca(id=abc)"

    def test_daily_limit_not_exceeded(self):
        strat = DCAStrategy(_base_config(
            guardrails={"daily_limit_usdc": 100.0, "spent_today_usdc": 99.9}
        ))
        assert strat.daily_limit_exceeded() is False

    def test_daily_limit_exactly_met(self):
        strat = DCAStrategy(_base_config(
            guardrails={"daily_limit_usdc": 100.0, "spent_today_usdc": 100.0}
        ))
        assert strat.daily_limit_exceeded() is True

    def test_daily_limit_exceeded(self):
        strat = DCAStrategy(_base_config(
            guardrails={"daily_limit_usdc": 100.0, "spent_today_usdc": 150.0}
        ))
        assert strat.daily_limit_exceeded() is True

    def test_daily_limit_defaults_to_zero(self):
        # No guardrails set — both default to 0.0, so 0 >= 0 is True
        strat = DCAStrategy(_base_config(guardrails={}))
        assert strat.daily_limit_exceeded() is True

    def test_max_trade_size(self):
        strat = DCAStrategy(_base_config(guardrails={"max_trade_size_usdc": 42.5}))
        assert strat.max_trade_size() == 42.5

    def test_max_trade_size_default(self):
        strat = DCAStrategy(_base_config(guardrails={}))
        assert strat.max_trade_size() == 0.0

    def test_stop_loss_pct_present(self):
        strat = DCAStrategy(_base_config(risk_management={"stop_loss_pct": 3.5}))
        assert strat.stop_loss_pct() == 3.5

    def test_stop_loss_pct_absent(self):
        strat = DCAStrategy(_base_config(risk_management={}))
        assert strat.stop_loss_pct() is None

    def test_take_profit_pct_present(self):
        strat = DCAStrategy(_base_config(risk_management={"take_profit_pct": 7.0}))
        assert strat.take_profit_pct() == 7.0

    def test_take_profit_pct_absent(self):
        strat = DCAStrategy(_base_config(risk_management={}))
        assert strat.take_profit_pct() is None

    def test_missing_optional_keys_use_defaults(self):
        # Config with only required keys — .get() fallbacks must work
        cfg = {
            "strategy_id": "min-001",
            "strategy_type": "dca",
            "token_pair": {"from": "USDC", "to": "SOL"},
        }
        strat = DCAStrategy(cfg)
        assert strat.params == {}
        assert strat.risk == {}
        assert strat.guardrails == {}

    def test_strategy_base_is_abstract(self):
        """StrategyBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StrategyBase(_base_config())  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# DCAStrategy
# ---------------------------------------------------------------------------

class TestDCAStrategy:
    """Tests for DCAStrategy.check_signal()."""

    @pytest.mark.asyncio
    async def test_first_run_returns_buy(self):
        """No last_executed → buy immediately."""
        strat = DCAStrategy(_base_config())
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_cycle_elapsed_returns_buy(self):
        """Elapsed time >= cycle_frequency_hours → buy."""
        past = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
        strat = DCAStrategy(_base_config(
            parameters={"cycle_frequency_hours": 168},
            last_executed=past,
        ))
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_cycle_not_elapsed_returns_hold(self):
        """Elapsed time < cycle_frequency_hours → hold."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        strat = DCAStrategy(_base_config(
            parameters={"cycle_frequency_hours": 168},
            last_executed=recent,
        ))
        assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_exactly_at_cycle_boundary_returns_buy(self):
        """Elapsed == cycle → buy (>= comparison)."""
        past = (datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)).isoformat()
        strat = DCAStrategy(_base_config(
            parameters={"cycle_frequency_hours": 24},
            last_executed=past,
        ))
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_default_cycle_is_weekly(self):
        """No cycle_frequency_hours param → default 168h; recent execution → hold."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        strat = DCAStrategy(_base_config(parameters={}, last_executed=recent))
        assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_invalid_last_executed_returns_buy(self):
        """Malformed ISO string → warning + buy."""
        strat = DCAStrategy(_base_config(last_executed="not-a-date"))
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_last_executed_none_returns_buy(self):
        """last_executed=None → buy."""
        strat = DCAStrategy(_base_config(last_executed=None))
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_zulu_suffix_parsed_correctly(self):
        """'Z' suffix in ISO string is handled (replace → +00:00)."""
        past = (datetime.now(timezone.utc) - timedelta(hours=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        strat = DCAStrategy(_base_config(
            parameters={"cycle_frequency_hours": 168},
            last_executed=past,
        ))
        assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_zero_cycle_hours_returns_buy(self):
        """cycle_frequency_hours=0 → elapsed (any positive) >= 0 → buy."""
        recent = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        strat = DCAStrategy(_base_config(
            parameters={"cycle_frequency_hours": 0},
            last_executed=recent,
        ))
        assert await strat.check_signal() == "buy"


# ---------------------------------------------------------------------------
# RSIStrategy
# ---------------------------------------------------------------------------

class TestRSIStrategy:
    """Tests for RSIStrategy.check_signal()."""

    @pytest.mark.asyncio
    async def test_oversold_returns_buy(self):
        """RSI at oversold threshold → buy."""
        strat = RSIStrategy(_base_config(
            strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0},
        ))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=30.0)):
            assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_below_oversold_returns_buy(self):
        """RSI below oversold → buy (<=)."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=20.0)):
            assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_overbought_returns_sell(self):
        """RSI at overbought threshold → sell."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=70.0)):
            assert await strat.check_signal() == "sell"

    @pytest.mark.asyncio
    async def test_above_overbought_returns_sell(self):
        """RSI above overbought → sell."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=85.0)):
            assert await strat.check_signal() == "sell"

    @pytest.mark.asyncio
    async def test_neutral_returns_hold(self):
        """RSI between thresholds → hold."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=50.0)):
            assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_default_thresholds_neutral(self):
        """No params → defaults 30/70; RSI=50 → hold."""
        strat = RSIStrategy(_base_config(strategy_type="rsi", parameters={}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=50.0)):
            assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_default_thresholds_oversold(self):
        """No params → defaults 30/70; RSI=25 → buy."""
        strat = RSIStrategy(_base_config(strategy_type="rsi", parameters={}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=25.0)):
            assert await strat.check_signal() == "buy"

    @pytest.mark.asyncio
    async def test_rsi_exception_returns_hold(self):
        """If _get_current_rsi raises, signal degrades to hold."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(side_effect=RuntimeError("no data"))):
            assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_placeholder_get_current_rsi_returns_50(self):
        """Placeholder _get_current_rsi() returns 50.0 (neutral)."""
        strat = RSIStrategy(_base_config(strategy_type="rsi"))
        result = await strat._get_current_rsi()
        assert result == 50.0

    @pytest.mark.asyncio
    async def test_rsi_just_above_oversold_holds(self):
        """RSI one tick above oversold → hold, not buy."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=30.01)):
            assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_rsi_just_below_overbought_holds(self):
        """RSI one tick below overbought → hold, not sell."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 30.0, "overbought_threshold": 70.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=69.99)):
            assert await strat.check_signal() == "hold"

    @pytest.mark.asyncio
    async def test_custom_tight_thresholds(self):
        """Custom thresholds (45/55) produce signals on tight range."""
        strat = RSIStrategy(_base_config(strategy_type="rsi",
            parameters={"oversold_threshold": 45.0, "overbought_threshold": 55.0}))
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=44.0)):
            assert await strat.check_signal() == "buy"
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=56.0)):
            assert await strat.check_signal() == "sell"
        with patch.object(strat, "_get_current_rsi", new=AsyncMock(return_value=50.0)):
            assert await strat.check_signal() == "hold"
