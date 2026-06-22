# src/coordinator/tools/wallet_tool_generators.py
"""LLM tool definitions for Solana wallet operations (Jupiter DEX).

These tools are only injected for archon-order personas with 'solana_wallet' in mcp_access.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def get_wallet_tools() -> List[Dict[str, Any]]:
    """Return all 7 wallet tool definitions."""
    return [
        get_wallet_get_balances_tool(),
        get_wallet_create_guided_tool(),
        get_solana_get_quote_tool(),
        get_solana_rsi_check_tool(),
        get_solana_propose_swap_tool(),
        get_solana_propose_strategy_tool(),
        get_solana_trade_history_tool(),
    ]


def get_wallet_get_balances_tool() -> Dict[str, Any]:
    """Get the user's Solana wallet balances — SOL and all token holdings."""
    return {
        "type": "function",
        "function": {
            "name": "wallet_get_balances",
            "description": (
                "Get the user's Solana wallet balances — SOL and all token holdings. "
                "Use when user asks: 'what's my balance', 'how much SOL do I have', "
                "'show me my wallet', 'what tokens do I hold'.\n\n"
                "Returns real wallet data. Present results in persona voice. "
                "If this tool has NOT been called, never fabricate balance information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to look up wallet for"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you need the balance"
                    }
                },
                "required": ["user_id"]
            }
        }
    }


def get_wallet_create_guided_tool() -> Dict[str, Any]:
    """Start the guided wallet creation flow."""
    return {
        "type": "function",
        "function": {
            "name": "wallet_create_guided",
            "description": (
                "Start the guided wallet creation flow. Use when user says "
                "'create a wallet', 'I need a Solana wallet', 'set up my wallet'. "
                "This initiates a step-by-step chat flow — no private key is generated yet. "
                "Frame wallet creation with appropriate gravitas. This is a trust moment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID for the new wallet"
                    },
                    "wallet_name": {
                        "type": "string",
                        "description": "Optional name for the wallet"
                    }
                },
                "required": ["user_id"]
            }
        }
    }


def get_solana_get_quote_tool() -> Dict[str, Any]:
    """Fetch a real-time swap quote from Jupiter aggregator."""
    return {
        "type": "function",
        "function": {
            "name": "solana_get_quote",
            "description": (
                "Fetch a real-time swap quote from Jupiter aggregator. "
                "Use when user asks: 'how much SOL would I get for X USDC', "
                "'what's the exchange rate', 'quote me a swap'. "
                "Does NOT execute — just shows the rate. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_token": {
                        "type": "string",
                        "description": "Token to sell (e.g. 'USDC', 'SOL')"
                    },
                    "to_token": {
                        "type": "string",
                        "description": "Token to buy (e.g. 'SOL', 'USDC')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount in human-readable units (e.g. 50 for 50 USDC)"
                    },
                    "slippage_bps": {
                        "type": "integer",
                        "description": "Slippage tolerance in basis points (default: 50)"
                    }
                },
                "required": ["from_token", "to_token", "amount"]
            }
        }
    }


def get_solana_rsi_check_tool() -> Dict[str, Any]:
    """Check the current RSI for a token, optionally triggering autonomous execution."""
    return {
        "type": "function",
        "function": {
            "name": "solana_rsi_check",
            "description": (
                "Check the current RSI for a token. If an active RSI strategy exists, "
                "this may trigger autonomous execution (per approved guardrails). "
                "Otherwise returns current RSI value. "
                "Use when user asks about RSI, technical signals, or 'what does the RSI say'. "
                "Present RSI findings in persona voice. If near threshold (30/70), mention the signal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Token symbol (e.g. 'SOL', 'BTC')"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe: '1d', '4h', '1h'",
                        "enum": ["1d", "4h", "1h"]
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID to check for active strategies"
                    }
                },
                "required": ["token", "user_id"]
            }
        }
    }


def get_solana_propose_swap_tool() -> Dict[str, Any]:
    """Propose an ad-hoc token swap that requires explicit user confirmation."""
    return {
        "type": "function",
        "function": {
            "name": "solana_propose_swap",
            "description": (
                "Propose an ad-hoc token swap that requires explicit user confirmation. "
                "Use when user says: 'swap X SOL for USDC', 'buy some SOL', 'sell my USDC'. "
                "Creates a ProposalCard in chat — NEVER executes automatically. "
                "User must click Confirm before any transaction occurs. "
                "Always provide brief market context before calling. The Seeker must confirm — never suggest executing directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string"
                    },
                    "from_token": {
                        "type": "string",
                        "description": "Token to sell"
                    },
                    "to_token": {
                        "type": "string",
                        "description": "Token to buy"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to sell"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why E.E.V.A. is proposing this swap"
                    }
                },
                "required": ["user_id", "from_token", "to_token", "amount"]
            }
        }
    }


def get_solana_propose_strategy_tool() -> Dict[str, Any]:
    """Propose a new autonomous trading strategy requiring one-time user approval."""
    return {
        "type": "function",
        "function": {
            "name": "solana_propose_strategy",
            "description": (
                "Propose a new autonomous trading strategy. Requires ONE-TIME user approval. "
                "Use when user says: 'set up an RSI strategy', 'start DCA buying SOL', "
                "'create an automated strategy'. "
                "Creates a StrategyApprovalCard — strategy only activates after user approves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string"
                    },
                    "strategy_type": {
                        "type": "string",
                        "enum": ["RSIStrategy", "DCAStrategy"],
                        "description": "Strategy implementation class"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable strategy name"
                    },
                    "from_token": {
                        "type": "string",
                        "description": "Token to sell (usually USDC)"
                    },
                    "to_token": {
                        "type": "string",
                        "description": "Token to buy"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Strategy-specific parameters"
                    },
                    "max_trade_size_usdc": {
                        "type": "number",
                        "description": "Max per-trade size in USDC"
                    },
                    "daily_limit_usdc": {
                        "type": "number",
                        "description": "Daily spending limit in USDC"
                    },
                    "stop_loss_pct": {
                        "type": "number",
                        "description": "Stop-loss percentage (e.g. 7 for 7%)"
                    },
                    "take_profit_pct": {
                        "type": "number",
                        "description": "Take-profit percentage (e.g. 50 for 50%)"
                    }
                },
                "required": [
                    "user_id",
                    "strategy_type",
                    "name",
                    "from_token",
                    "to_token",
                    "parameters",
                    "max_trade_size_usdc",
                    "daily_limit_usdc"
                ]
            }
        }
    }


def get_solana_trade_history_tool() -> Dict[str, Any]:
    """Get the user's recent trade history and active strategies."""
    return {
        "type": "function",
        "function": {
            "name": "solana_trade_history",
            "description": (
                "Get the user's recent trade history and active strategies. "
                "Reads from the local trade history store and strategies/ folder. "
                "Use when user asks: 'how did my strategy perform', 'show me recent trades', "
                "'what strategies are running', 'what\\'s my P&L'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max trades to return (default 10)"
                    },
                    "strategy_id": {
                        "type": "string",
                        "description": "Optional: filter by strategy ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    }


# Wallet tool registry
WALLET_TOOLS = {tool["function"]["name"]: tool for tool in get_wallet_tools()}
