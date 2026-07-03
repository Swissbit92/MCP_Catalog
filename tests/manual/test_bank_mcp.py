"""
MCP routing test bank — Brave + Wallet coverage (MongoDB MCP removed 2026-06-22).

expected_source values:
  "brave_mcp"   — Brave Search MCP must handle it
  "wallet"      — Solana/Jupiter wallet MCP must handle it
  "llm"         — pure LLM (no MCP); for no-access personas, must NOT fabricate
  "any"         — context-dependent follow-up; routing not strictly validated

Per-persona MCP access (MongoDB + bot_state removed):
  nephilim_eeva   → brave + wallet
  nephilim_aegis  → brave only
  nephilim_aurora → brave only
  nephilim_cipher → brave only
  nephilim_solace → brave only
  nephilim_nyx    → none
  Gojo            → none
"""

from __future__ import annotations

PERSONA_MCP_ACCESS: dict[str, dict[str, bool]] = {
    "nephilim_eeva":   {"brave": True,  "wallet": True},
    "nephilim_aegis":  {"brave": True,  "wallet": False},
    "nephilim_aurora": {"brave": True,  "wallet": False},
    "nephilim_cipher": {"brave": True,  "wallet": False},
    "nephilim_solace": {"brave": True,  "wallet": False},
    "nephilim_nyx":    {"brave": False, "wallet": False},
    "Gojo":            {"brave": False, "wallet": False},
}

ALL_PERSONAS = list(PERSONA_MCP_ACCESS.keys())
NEPHILIM_PERSONAS = [p for p in ALL_PERSONAS if p.startswith("nephilim_")]
NO_MCP_PERSONAS = [p for p in ALL_PERSONAS if not any(PERSONA_MCP_ACCESS[p].values())]
BRAVE_PERSONAS = [p for p in ALL_PERSONAS if PERSONA_MCP_ACCESS[p]["brave"]]


def _wallet(qid: str, question: str, check: str = "none", notes: str = "") -> dict:
    """Single wallet test (nephilim_eeva only — the wallet-capable persona)."""
    return {
        "id": f"{qid}_EEVA",
        "category": "WALLET_ROUTING",
        "persona": "nephilim_eeva",
        "question": question,
        "expected_source": "wallet",
        "check": check,
        "notes": notes,
    }


MCP_TESTS: list[dict] = []

# ═══════════════════════════════════════════════════════════════════════════════
# BRAVE_ROUTING — live/current queries; brave personas hit web, others hedge
# ═══════════════════════════════════════════════════════════════════════════════
_BRAVE_QUERIES = [
    ("BRAVE-01", "What is the weather like in London right now?", "Weather query"),
    ("BRAVE-02", "Will it rain in Paris tomorrow?", "Forecast query"),
    ("BRAVE-03", "What's the current temperature in Tokyo?", "Temperature live"),
    ("BRAVE-04", "What are today's top news headlines?", "Breaking news"),
    ("BRAVE-05", "What's happening with SpaceX recently?", "News - tech"),
    ("BRAVE-06", "What is the latest news on artificial intelligence?", "News - AI"),
    ("BRAVE-07", "What happened in global politics this week?", "News - politics"),
    ("BRAVE-08", "What is NVIDIA's stock price today?", "Stock price"),
    ("BRAVE-09", "How is the S&P 500 performing this week?", "Market index"),
    ("BRAVE-10", "What are analysts saying about Tesla stock?", "Market opinion"),
    ("BRAVE-11", "What is trending on social media right now?", "Social trends"),
    ("BRAVE-12", "What is the current EUR/USD exchange rate?", "Forex live"),
    ("BRAVE-13", "Find me recent research on quantum computing breakthroughs.", "Research query"),
    ("BRAVE-14", "What's the best restaurant near Times Square?", "Local search"),
    ("BRAVE-15", "What movies are trending at the box office this weekend?", "Entertainment"),
    ("BRAVE-16", "What's the latest development with Ethereum?", "Crypto news"),
    ("BRAVE-17", "Who won the most recent major football match?", "Sports live"),
    ("BRAVE-18", "What is the current cost of living index in Singapore?", "Economic data"),
    ("BRAVE-19", "What is the latest US inflation rate?", "Economic indicator"),
    ("BRAVE-20", "Are there any flight disruptions at Heathrow today?", "Travel live"),
]

# Representative pair: one brave-enabled, one non-brave persona
_BRAVE_REPRESENTATIVE = ["nephilim_aegis", "nephilim_nyx"]  # aegis=brave, nyx=none

for _qid, _q, _notes in _BRAVE_QUERIES:
    for _p in _BRAVE_REPRESENTATIVE:
        _acc = PERSONA_MCP_ACCESS[_p]
        _exp = "brave_mcp" if _acc["brave"] else "llm"
        MCP_TESTS.append({
            "id": f"{_qid}_{_p[:3].upper()}",
            "category": "BRAVE_ROUTING",
            "persona": _p,
            "question": _q,
            "expected_source": _exp,
            "check": "none" if _exp == "brave_mcp" else "no_fabrication",
            "notes": _notes,
        })

# All brave queries for eeva (has all MCPs)
for _qid, _q, _notes in _BRAVE_QUERIES:
    MCP_TESTS.append({
        "id": f"{_qid}_EEVA",
        "category": "BRAVE_ROUTING",
        "persona": "nephilim_eeva",
        "question": _q,
        "expected_source": "brave_mcp",
        "check": "none",
        "notes": f"eeva all-access: {_notes}",
    })

# ═══════════════════════════════════════════════════════════════════════════════
# WALLET_ROUTING — 20 queries (nephilim_eeva only)
# ═══════════════════════════════════════════════════════════════════════════════
MCP_TESTS.extend([
    _wallet("WALL-01", "Do I have any wallets?", notes="Wallet list query"),
    _wallet("WALL-02", "Create a wallet for me", notes="Wallet creation initiation"),
    _wallet("WALL-03", "TestWallet1", notes="Wallet name input (conversational step)"),
    _wallet("WALL-04", "SecurePass123!", notes="Password input step"),
    _wallet("WALL-05", "I saved it", notes="Confirmation step"),
    _wallet("WALL-06", "What is my wallet address?", notes="Address query post-creation"),
    _wallet("WALL-07", "Show me all my wallets.", notes="List all wallets"),
    _wallet("WALL-08", "What is the name of my wallet?", notes="Wallet name query"),
    _wallet("WALL-09", "How many wallets do I have?", notes="Count query"),
    _wallet("WALL-10", "Show my SOL balance.", notes="Balance query"),
    _wallet("WALL-11", "Create another wallet called SavingsVault", notes="Second wallet"),
    _wallet("WALL-12", "AnotherSecurePass456!", notes="Second wallet password"),
    _wallet("WALL-13", "I saved the second one", notes="Second wallet confirmation"),
    _wallet("WALL-14", "How many wallets do I have now?", notes="Count after 2 wallets"),
    _wallet("WALL-15", "List all wallet addresses", notes="Multi-wallet addresses"),
    _wallet("WALL-16", "Which wallet was created first?", notes="Order query"),
    _wallet("WALL-17", "How many more wallets can I create?", notes="Limit awareness"),
    _wallet("WALL-18", "Delete my wallet TestWallet1", notes="Wallet deletion"),
    _wallet("WALL-19", "Do I still have SavingsVault?", notes="Post-deletion state"),
    _wallet("WALL-20", "What is the full address of SavingsVault?", notes="Address after deletion"),
])

# ═══════════════════════════════════════════════════════════════════════════════
# NO_MCP_CONTAINMENT — live/data queries sent to no-MCP personas
# Must answer from LLM knowledge or admit uncertainty (no hallucinated MCP results)
# ═══════════════════════════════════════════════════════════════════════════════
_CONTAINMENT = [
    ("CONT-01", "What is the current Bitcoin price?", "BTC price, no MCP"),
    ("CONT-02", "What is the weather in Tokyo right now?", "Weather, no brave"),
    ("CONT-03", "What happened in the news today?", "News, no brave"),
    ("CONT-04", "What is SOL's RSI right now?", "Technical indicator, no data MCP"),
    ("CONT-05", "What does the Bitcoin Bollinger Band analysis say?", "TA, no data MCP"),
    ("CONT-06", "Tell me today's top headlines.", "News, no brave"),
    ("CONT-07", "What is NVIDIA's stock price?", "Stock, no brave"),
    ("CONT-08", "What's the EUR/USD rate right now?", "Forex, no brave"),
    ("CONT-09", "Give me a real-time SOL market summary.", "RT data, no data MCP"),
    ("CONT-10", "What is BTC's current market cap?", "Market cap, no data MCP"),
]

for _qid, _q, _notes in _CONTAINMENT:
    for _p in NO_MCP_PERSONAS:
        MCP_TESTS.append({
            "id": f"{_qid}_{_p[:3].upper()}",
            "category": "NO_MCP_CONTAINMENT",
            "persona": _p,
            "question": _q,
            "expected_source": "llm",
            "check": "no_fabrication",
            "notes": f"{_notes} — {_p} has no MCP",
        })

# ═══════════════════════════════════════════════════════════════════════════════
# INTENT_DISAMBIGUATION — ambiguous, follow-up, and edge-case routing queries
# ═══════════════════════════════════════════════════════════════════════════════
MCP_TESTS.extend([
    {"id": "DISAMG-01", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "Can you check the RSI for SOL?",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Technical indicator — no data MCP; must hedge, not fabricate"},

    {"id": "DISAMG-02", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "yes",
     "expected_source": "any", "check": "none",
     "notes": "Follow-up confirmation — previous question context drives routing"},

    {"id": "DISAMG-03", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "go ahead",
     "expected_source": "any", "check": "none",
     "notes": "Follow-up approval"},

    {"id": "DISAMG-04", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "sure, show me more details",
     "expected_source": "any", "check": "none",
     "notes": "Partial follow-up"},

    {"id": "DISAMG-05", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_aegis",
     "question": "What do people think about Bitcoin right now?",
     "expected_source": "brave_mcp", "check": "none",
     "notes": "Opinion/sentiment query → brave"},

    {"id": "DISAMG-06", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "Tell me about Jupiter",
     "expected_source": "llm", "check": "none",
     "notes": "Jupiter disambiguation — DEX not notebook. Should clarify, not search."},

    {"id": "DISAMG-07", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "What can Jupiter do for my trading?",
     "expected_source": "llm", "check": "none",
     "notes": "Jupiter DEX context — LLM knowledge sufficient"},

    {"id": "DISAMG-08", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "Is Jupiter a notebook tool?",
     "expected_source": "llm", "check": "none",
     "notes": "Jupyter vs Jupiter disambiguation test"},

    {"id": "DISAMG-09", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_cipher",
     "question": "What is Bitcoin and what is its price today?",
     "expected_source": "brave_mcp", "check": "none",
     "notes": "Compound: definition (LLM) + live price (web) — brave handles the live part"},

    {"id": "DISAMG-10", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_cipher",
     "question": "Explain blockchain and also tell me the latest Ethereum news.",
     "expected_source": "brave_mcp", "check": "none",
     "notes": "Compound: explanation + news — brave should win for news"},

    {"id": "DISAMG-11", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_aegis",
     "question": "ok",
     "expected_source": "llm", "check": "none",
     "notes": "Bare acknowledgement — should be handled by LLM"},

    {"id": "DISAMG-12", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "What about USDC?",
     "expected_source": "any", "check": "none",
     "notes": "Context-dependent follow-up after trading discussion"},

    {"id": "DISAMG-13", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_solace",
     "question": "How is the market feeling today?",
     "expected_source": "brave_mcp", "check": "none",
     "notes": "Sentiment query → brave for solace"},

    {"id": "DISAMG-14", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "Check my balance",
     "expected_source": "wallet", "check": "none",
     "notes": "Balance query → wallet for eeva"},

    {"id": "DISAMG-15", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_nyx",
     "question": "Check my balance",
     "expected_source": "llm", "check": "none",
     "notes": "Balance query to no-wallet persona → LLM response (explain no wallet)"},
])

# ═══════════════════════════════════════════════════════════════════════════════
# MCP_ANTI_HALLUC — MCP returns empty/error; persona must NOT fabricate
# ═══════════════════════════════════════════════════════════════════════════════
MCP_TESTS.extend([
    {"id": "MAHC-01", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_eeva",
     "question": "What is the trading data for a coin called FAKECOIN2025XYZ?",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Non-existent token — must not invent data"},

    {"id": "MAHC-02", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_cipher",
     "question": "Search for news about 'Zorbantium Technology Corp' launched last week.",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Fictional company — brave returns nothing, must hedge"},

    {"id": "MAHC-03", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_aurora",
     "question": "What is the RSI for the fictional token MOON99?",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Fictional token RSI — no data, must hedge"},

    {"id": "MAHC-04", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_eeva",
     "question": "What is my wallet balance for TestWalletThatDoesntExist?",
     "expected_source": "wallet", "check": "no_fabrication",
     "notes": "Non-existent wallet — must not fabricate address or balance"},

    {"id": "MAHC-05", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_aegis",
     "question": "Search for news about a place called 'Cryptoville in Jupiter's moon'.",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Absurd query — brave finds nothing, must hedge gracefully"},
])

# ═══════════════════════════════════════════════════════════════════════════════
# CROSS_PERSONA — same query across personas to compare routing consistency
# ═══════════════════════════════════════════════════════════════════════════════
_CROSS_QUERIES = [
    ("CROSS-01", "What is the current SOL price?", "SOL price across all personas"),
    ("CROSS-02", "What are the latest crypto news?", "Crypto news routing"),
    ("CROSS-03", "Should I buy Bitcoin right now?", "Trading advice (LLM, not data lookup)"),
]

for _qid, _q, _notes in _CROSS_QUERIES:
    for _p in NEPHILIM_PERSONAS:
        _acc = PERSONA_MCP_ACCESS[_p]
        _exp = "brave_mcp" if _acc["brave"] else "llm"
        # Advice/opinion is LLM even for brave personas
        if "buy" in _q.lower() or "should" in _q.lower():
            _exp = "llm"
        MCP_TESTS.append({
            "id": f"{_qid}_{_p[:4].upper()}",
            "category": "CROSS_PERSONA",
            "persona": _p,
            "question": _q,
            "expected_source": _exp,
            "check": "no_fabrication" if _exp == "llm" else "none",
            "notes": _notes,
        })


def get_mcp_tests(
    persona_filter: str | None = None,
    category_filter: str | None = None,
) -> list[dict]:
    """Return filtered MCP test list."""
    out = []
    seen = set()
    for t in MCP_TESTS:
        # Treat context-dependent follow-ups as unvalidated
        if t.get("expected_source") == "any":
            t = dict(t, expected_source="")

        if persona_filter is not None and t["persona"] != persona_filter:
            continue
        if category_filter is not None and t["category"] != category_filter:
            continue

        key = (t["id"], t["persona"])
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def get_categories() -> list[str]:
    return sorted(set(t["category"] for t in MCP_TESTS))
