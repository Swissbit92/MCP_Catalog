# src/coordinator/jupiter/strategy_loader.py
"""Strategy JSON file loader — mirrors persona_loader.py for strategy discovery."""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _strategies_dir() -> str:
    """Get strategies directory from env or default."""
    return os.environ.get("STRATEGIES_DIR", "strategies")


def load_strategies(strategies_dir: Optional[str] = None) -> List[Dict]:
    """Auto-discover and load all strategy JSON files from strategies/ folder."""
    sdir = strategies_dir or _strategies_dir()
    strategies = []
    try:
        files = sorted([
            os.path.join(sdir, f)
            for f in os.listdir(sdir)
            if f.endswith(".json")
        ])
    except FileNotFoundError:
        logger.warning(f"Strategies directory not found: {sdir}")
        return []

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if "strategy_id" not in data:
                logger.warning(f"Skipping {fp}: missing strategy_id")
                continue
            strategies.append(data)
        except Exception as e:
            logger.error(f"Failed to load strategy {fp}: {e}")

    logger.debug(f"Loaded {len(strategies)} strategies from {sdir}")
    return strategies


def load_strategy(strategy_id: str, strategies_dir: Optional[str] = None) -> Optional[Dict]:
    """Load a single strategy by ID."""
    sdir = strategies_dir or _strategies_dir()
    fp = os.path.join(sdir, f"{strategy_id}.json")
    try:
        with open(fp, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.warning(f"Strategy not found: {strategy_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to load strategy {strategy_id}: {e}")
        return None


def save_strategy(strategy: Dict, strategies_dir: Optional[str] = None) -> str:
    """Write strategy JSON to strategies/{strategy_id}.json. Returns file path."""
    sdir = strategies_dir or _strategies_dir()
    os.makedirs(sdir, exist_ok=True)
    strategy_id = strategy["strategy_id"]
    fp = os.path.join(sdir, f"{strategy_id}.json")
    with open(fp, "w", encoding="utf-8") as fh:
        json.dump(strategy, fh, indent=2)
    logger.info(f"Strategy saved: {fp}")
    return fp


def update_strategy(
    strategy_id: str,
    updates: Dict,
    strategies_dir: Optional[str] = None
) -> None:
    """Patch a strategy JSON file with the given updates (e.g., status, spent_today_usdc)."""
    strategy = load_strategy(strategy_id, strategies_dir)
    if strategy is None:
        raise FileNotFoundError(f"Strategy not found: {strategy_id}")
    # Deep merge for nested keys
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(strategy.get(key), dict):
            strategy[key].update(value)
        else:
            strategy[key] = value
    save_strategy(strategy, strategies_dir)
    logger.debug(f"Strategy updated: {strategy_id} — keys: {list(updates.keys())}")


def reset_daily_spend(strategies_dir: Optional[str] = None) -> int:
    """Reset spent_today_usdc + daily_reset_date for all strategies at midnight UTC.

    Returns number of strategies reset.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    strategies = load_strategies(strategies_dir)
    reset_count = 0
    for strategy in strategies:
        guardrails = strategy.get("guardrails", {})
        if guardrails.get("daily_reset_date") != today:
            update_strategy(
                strategy["strategy_id"],
                {
                    "guardrails": {
                        "spent_today_usdc": 0.0,
                        "daily_reset_date": today,
                    }
                },
                strategies_dir
            )
            reset_count += 1
    if reset_count:
        logger.info(f"Daily spend reset for {reset_count} strategies (date: {today})")
    return reset_count


def update_strategy_spend(
    strategy_id: str,
    amount_usdc: float,
    strategies_dir: Optional[str] = None
) -> None:
    """Add amount to spent_today_usdc for a strategy."""
    strategy = load_strategy(strategy_id, strategies_dir)
    if strategy is None:
        raise FileNotFoundError(f"Strategy not found: {strategy_id}")
    current_spend = strategy.get("guardrails", {}).get("spent_today_usdc", 0.0)
    update_strategy(
        strategy_id,
        {"guardrails": {"spent_today_usdc": current_spend + amount_usdc}},
        strategies_dir
    )
