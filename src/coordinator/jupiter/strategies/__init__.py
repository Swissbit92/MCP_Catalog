"""Strategy implementation classes for autonomous trading."""
from .strategy_base import StrategyBase
from .rsi_strategy import RSIStrategy
from .dca_strategy import DCAStrategy

STRATEGY_REGISTRY = {
    "RSIStrategy": RSIStrategy,
    "DCAStrategy": DCAStrategy,
}

__all__ = ["StrategyBase", "RSIStrategy", "DCAStrategy", "STRATEGY_REGISTRY"]
