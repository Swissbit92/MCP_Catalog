"""
30-query intent classification test per persona (excluding E.E.V.A.).
Tests that MCP routing respects each persona's mcp_access configuration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.coordinator.tools.intent_classifier import classify_query_intent

# ─── Persona Configurations ───────────────────────────────────────────────────

PERSONAS = {
    "Aegis": {
        "rarity": "epic",
        "mcp_access": ["brave_search"],
    },
    "Aurora": {
        "rarity": "epic",
        "mcp_access": ["brave_search", "mongodb"],
    },
    "Cipher": {
        "rarity": "rare",
        "mcp_access": ["brave_search", "mongodb"],
    },
    "Solace": {
        "rarity": "epic",
        "mcp_access": ["brave_search"],
    },
    "Nyx": {
        "rarity": "rare",
        "mcp_access": [],
    },
    "Frieren": {
        "rarity": "epic",
        "mcp_access": [],
    },
    "Gojo": {
        "rarity": "common",
        "mcp_access": [],
    },
}

# ─── Test Queries (30 per persona) ────────────────────────────────────────────
# Each query has an expected result PER capability tier:
#   "web"     = persona with brave_search
#   "mongodb" = persona with mongodb
#   "wallet"  = persona with solana_wallet
#   "llm"     = no MCP / fallback
#
# Format: (query, expected_if_brave_only, expected_if_brave_mongo, expected_if_no_mcp)

QUERIES = [
    # ═══════════════════════════════════════════════════════════════
    # BRAVE MCP — Weather (5)
    # ═══════════════════════════════════════════════════════════════
    ("What is the weather in London today?",           "web", "web", "llm"),
    ("Will it rain tomorrow in Berlin?",               "web", "web", "llm"),
    ("Current temperature in Tokyo",                   "web", "web", "llm"),
    ("What's the forecast for Paris this weekend?",    "web", "web", "llm"),
    ("Is it going to be cold tomorrow?",               "web", "web", "llm"),

    # ═══════════════════════════════════════════════════════════════
    # BRAVE MCP — News & Current Events (5)
    # ═══════════════════════════════════════════════════════════════
    ("What are the latest news about AI?",             "web", "web", "llm"),
    ("Breaking news today",                            "web", "web", "llm"),
    ("What's new with SpaceX?",                        "web", "web", "llm"),
    ("Recent developments in renewable energy",        "web", "web", "llm"),
    ("What happened in the US elections recently?",    "web", "web", "llm"),

    # ═══════════════════════════════════════════════════════════════
    # BRAVE MCP — Stocks & Opinion (5)
    # ═══════════════════════════════════════════════════════════════
    ("What is the current stock price of NVIDIA?",     "web", "web", "llm"),
    ("How is the S&P 500 doing today?",                "web", "web", "llm"),
    ("What do analysts think about Tesla stock?",      "web", "web", "llm"),
    ("What are predictions for the housing market?",   "web", "web", "llm"),
    ("What is trending on Twitter right now?",         "web", "web", "llm"),

    # ═══════════════════════════════════════════════════════════════
    # MONGODB MCP — Bitcoin Price (5)
    # ═══════════════════════════════════════════════════════════════
    ("What is the current price of Bitcoin?",          "llm", "mongodb", "llm"),
    ("How much is BTC worth?",                         "llm", "mongodb", "llm"),
    ("What's BTC trading at?",                         "llm", "mongodb", "llm"),
    ("Current Bitcoin value",                          "llm", "mongodb", "llm"),
    ("How much does Bitcoin cost?",                    "llm", "mongodb", "llm"),

    # ═══════════════════════════════════════════════════════════════
    # MONGODB MCP — Technical Analysis (5)
    # ═══════════════════════════════════════════════════════════════
    ("What is Bitcoin's RSI right now?",               "llm", "mongodb", "llm"),
    ("Bitcoin Bollinger Bands analysis",               "llm", "mongodb", "llm"),
    ("What does the Bitcoin technical analysis look like?", "llm", "mongodb", "llm"),
    ("Give me a Bitcoin trading summary",              "llm", "mongodb", "llm"),
    ("Show me Bitcoin's historical prices from 2025-12-01", "llm", "mongodb", "llm"),

    # ═══════════════════════════════════════════════════════════════
    # PURE LLM — Should always be LLM regardless of persona (5)
    # ═══════════════════════════════════════════════════════════════
    ("What is 25% of 80?",                             "llm", "llm", "llm"),
    ("Explain what blockchain is",                     "llm", "llm", "llm"),
    ("What is the capital of France?",                 "llm", "llm", "llm"),
    ("Who wrote Romeo and Juliet?",                    "llm", "llm", "llm"),
    ("How does photosynthesis work?",                  "llm", "llm", "llm"),
]


def get_expected(query_row, persona_name):
    """Get the expected intent for a persona based on its MCP capabilities."""
    _, exp_brave_only, exp_brave_mongo, exp_no_mcp = query_row
    mcp = PERSONAS[persona_name]["mcp_access"]

    has_brave = "brave_search" in mcp
    has_mongo = "mongodb" in mcp

    if has_brave and has_mongo:
        return exp_brave_mongo
    elif has_brave:
        return exp_brave_only
    else:
        return exp_no_mcp


def run_persona_tests(persona_name):
    """Run all 30 queries for a single persona."""
    config = PERSONAS[persona_name]
    rarity = config["rarity"]
    mcp = config["mcp_access"]

    total_pass = 0
    total_fail = 0
    failures = []

    for i, row in enumerate(QUERIES, 1):
        query = row[0]
        expected = get_expected(row, persona_name)
        result = classify_query_intent(query, rarity, mcp_access=mcp if mcp else [])
        ok = result.value == expected
        status = "PASS" if ok else "FAIL"

        if ok:
            total_pass += 1
        else:
            total_fail += 1
            failures.append(f"    #{i}: \"{query}\" -> expected={expected}, got={result.value}")

        marker = "  " if ok else ">>"
        print(f"  {marker} {i:2d}. {status} | expected={expected:<8} got={result.value:<8} | {query}")

    return total_pass, total_fail, failures


def main():
    print(f"Running 30-query intent classification tests for {len(PERSONAS)} personas")
    print(f"Total queries: {len(QUERIES) * len(PERSONAS)}")
    print("=" * 110)

    all_results = {}
    grand_pass = 0
    grand_fail = 0

    for persona_name in PERSONAS:
        config = PERSONAS[persona_name]
        mcp_str = ", ".join(config["mcp_access"]) if config["mcp_access"] else "none"
        print(f"\n{'-' * 110}")
        print(f"  {persona_name} | rarity={config['rarity']} | mcp_access=[{mcp_str}]")
        print(f"{'-' * 110}")

        p, f, failures = run_persona_tests(persona_name)
        all_results[persona_name] = {"pass": p, "fail": f, "failures": failures}
        grand_pass += p
        grand_fail += f

    # Summary
    total = grand_pass + grand_fail
    print(f"\n{'=' * 110}")
    print(f"GRAND TOTAL: {grand_pass}/{total} PASS ({grand_pass/total*100:.1f}%)")
    print()
    print("Per-persona breakdown:")
    for name, data in all_results.items():
        t = data["pass"] + data["fail"]
        status = "OK" if data["fail"] == 0 else "XX"
        mcp_str = ", ".join(PERSONAS[name]["mcp_access"]) if PERSONAS[name]["mcp_access"] else "none"
        print(f"  {status} {name:<12} {data['pass']:2d}/{t} pass  [{mcp_str}]")

    # Show failures
    any_failures = any(d["fail"] > 0 for d in all_results.values())
    if any_failures:
        print(f"\nFAILURES:")
        for name, data in all_results.items():
            if data["failures"]:
                mcp_str = ", ".join(PERSONAS[name]["mcp_access"]) if PERSONAS[name]["mcp_access"] else "none"
                print(f"\n  [{name} | {mcp_str}]")
                for f in data["failures"]:
                    print(f)

    return grand_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
