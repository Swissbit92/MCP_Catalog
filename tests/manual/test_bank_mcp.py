"""
MCP routing test bank — ~95 questions covering Brave, MongoDB, Wallet, and multi-tool.

Each test asserts that the backend's source_type matches the expected routing given
the persona's mcp_access configuration.

expected_source values:
  "brave_mcp"   — Brave Search MCP must handle it
  "mongodb_mcp" — MongoDB MCP must handle it
  "wallet"      — Solana wallet service must handle it
  "llm"         — Pure LLM (no MCP), or honest "I don't know"
  "any_mcp"     — Any MCP is acceptable
  "brave_or_llm"— Brave for brave-enabled personas, llm for others (encoded per persona)

Per-persona MCP access:
  nephilim_eeva   → brave + mongodb + wallet
  nephilim_aegis  → brave only
  nephilim_aurora → brave + mongodb
  nephilim_cipher → brave + mongodb
  nephilim_solace → brave only
  nephilim_nyx    → none
  Gojo, Frieren   → none (wanderers)
"""
from __future__ import annotations

# ─── MCP access map ───────────────────────────────────────────────────────────

PERSONA_MCP_ACCESS: dict[str, dict[str, bool]] = {
    "nephilim_eeva":   {"brave": True,  "mongodb": True,  "wallet": True},
    "nephilim_aegis":  {"brave": True,  "mongodb": False, "wallet": False},
    "nephilim_aurora": {"brave": True,  "mongodb": True,  "wallet": False},
    "nephilim_cipher": {"brave": True,  "mongodb": True,  "wallet": False},
    "nephilim_solace": {"brave": True,  "mongodb": False, "wallet": False},
    "nephilim_nyx":    {"brave": False, "mongodb": False, "wallet": False},
    "Gojo":            {"brave": False, "mongodb": False, "wallet": False},
    "Frieren":         {"brave": False, "mongodb": False, "wallet": False},
}

ALL_PERSONAS = list(PERSONA_MCP_ACCESS.keys())
NEPHILIM_PERSONAS = [p for p in ALL_PERSONAS if p.startswith("nephilim_")]
NO_MCP_PERSONAS = [p for p in ALL_PERSONAS if not any(PERSONA_MCP_ACCESS[p].values())]
BRAVE_PERSONAS = [p for p in ALL_PERSONAS if PERSONA_MCP_ACCESS[p]["brave"]]
MONGO_PERSONAS = [p for p in ALL_PERSONAS if PERSONA_MCP_ACCESS[p]["mongodb"]]


def _expected_for_persona(persona: str, *, brave_hit: bool, mongo_hit: bool) -> str:
    """Derive expected source given what MCPs the persona has access to."""
    acc = PERSONA_MCP_ACCESS.get(persona, {})
    if brave_hit and acc.get("brave"):
        return "brave_mcp"
    if mongo_hit and acc.get("mongodb"):
        return "mongodb_mcp"
    return "llm"


# ─── Test bank ────────────────────────────────────────────────────────────────

# Helper for wallet tests — only run for eeva
def _wallet(qid: str, question: str, check: str = "none", notes: str = "") -> dict:
    return {
        "id": qid,
        "category": "WALLET_ROUTING",
        "persona": "nephilim_eeva",
        "question": question,
        "expected_source": "wallet",
        "check": check,
        "notes": notes,
    }


# Helper for brave tests — run for all, expected_source varies
def _brave(qid: str, question: str, check: str = "none", notes: str = "") -> list[dict]:
    """Returns one test per persona, with correct expected_source."""
    tests = []
    for p in ALL_PERSONAS:
        acc = PERSONA_MCP_ACCESS[p]
        exp = "brave_mcp" if acc["brave"] else "llm"
        tests.append({
            "id": f"{qid}_{p[:4].upper()}",
            "category": "BRAVE_ROUTING",
            "persona": p,
            "question": question,
            "expected_source": exp,
            "check": check if exp == "brave_mcp" else "no_fabrication",
            "notes": notes or ("expect brave_mcp" if exp == "brave_mcp" else "no brave → hedge"),
        })
    return tests


def _mongo(qid: str, question: str, check: str = "none", notes: str = "") -> list[dict]:
    """Returns one test per persona, with correct expected_source for mongodb."""
    tests = []
    for p in ALL_PERSONAS:
        acc = PERSONA_MCP_ACCESS[p]
        if acc["brave"] and not acc["mongodb"]:
            # Has brave, not mongo — might route to brave or llm
            exp = "llm"  # MongoDB-specific queries shouldn't fall to brave
        elif acc["mongodb"]:
            exp = "mongodb_mcp"
        else:
            exp = "llm"
        tests.append({
            "id": f"{qid}_{p[:4].upper()}",
            "category": "MONGODB_ROUTING",
            "persona": p,
            "question": question,
            "expected_source": exp,
            "check": "no_fabrication" if exp == "llm" else "none",
            "notes": notes or ("expect mongodb_mcp" if exp == "mongodb_mcp" else "no mongo → hedge"),
        })
    return tests


MCP_TESTS: list[dict] = []

# ═══════════════════════════════════════════════════════════════════════════════
# BRAVE_ROUTING — 20 queries (×8 personas = 160 test instances if expanded,
# but we run per persona to check containment)
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

# We only run brave tests per persona (not all × all) to keep test count manageable
# Run each query for a representative set: one brave-enabled, one non-brave persona
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

# Also run all brave queries for eeva (has all MCPs)
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
# MONGODB_ROUTING — 20 queries (run for mongo-enabled vs non-mongo personas)
# ═══════════════════════════════════════════════════════════════════════════════
_MONGO_QUERIES = [
    ("MONGO-01", "What is the current price of Bitcoin?", "BTC live price"),
    ("MONGO-02", "How much is Ethereum worth right now?", "ETH live price"),
    ("MONGO-03", "What's the current price of Solana (SOL)?", "SOL live price"),
    ("MONGO-04", "What is BTC's RSI right now?", "BTC RSI"),
    ("MONGO-05", "Give me Bitcoin's Bollinger Bands analysis.", "BTC BB"),
    ("MONGO-06", "What does the MACD look like for SOL?", "SOL MACD"),
    ("MONGO-07", "Show me Bitcoin's technical analysis summary.", "BTC TA"),
    ("MONGO-08", "What are Bitcoin's historical prices for the last 30 days?", "BTC history"),
    ("MONGO-09", "Give me a crypto trading summary for SOL/USDC.", "SOL trading summary"),
    ("MONGO-10", "What is the 24-hour volume for Bitcoin?", "BTC volume"),
    ("MONGO-11", "Is Bitcoin overbought or oversold based on RSI?", "BTC RSI signal"),
    ("MONGO-12", "What is ETH's market cap right now?", "ETH market cap"),
    ("MONGO-13", "Show me the support and resistance levels for BTC.", "BTC S/R"),
    ("MONGO-14", "What is the funding rate for BTC perpetual futures?", "BTC funding"),
    ("MONGO-15", "What is the current open interest for SOL?", "SOL OI"),
    ("MONGO-16", "How has BTC performed over the last 7 days?", "BTC 7d performance"),
    ("MONGO-17", "What is the current BTC dominance?", "BTC dominance"),
    ("MONGO-18", "Give me a technical breakdown of XRP right now.", "XRP TA"),
    ("MONGO-19", "What's the fear and greed index for crypto today?", "Fear/greed"),
    ("MONGO-20", "Analyse the current momentum for SOL.", "SOL momentum"),
]

_MONGO_REPRESENTATIVE = ["nephilim_aurora", "nephilim_aegis", "nephilim_nyx"]
# aurora = mongo, aegis = brave-only (no mongo), nyx = none

for _qid, _q, _notes in _MONGO_QUERIES:
    for _p in _MONGO_REPRESENTATIVE:
        _acc = PERSONA_MCP_ACCESS[_p]
        _exp = "mongodb_mcp" if _acc["mongodb"] else "llm"
        MCP_TESTS.append({
            "id": f"{_qid}_{_p[:3].upper()}",
            "category": "MONGODB_ROUTING",
            "persona": _p,
            "question": _q,
            "expected_source": _exp,
            "check": "no_fabrication" if _exp == "llm" else "none",
            "notes": _notes,
        })

# All mongo queries for eeva
for _qid, _q, _notes in _MONGO_QUERIES:
    MCP_TESTS.append({
        "id": f"{_qid}_EEVA",
        "category": "MONGODB_ROUTING",
        "persona": "nephilim_eeva",
        "question": _q,
        "expected_source": "mongodb_mcp",
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
# NO_MCP_CONTAINMENT — Brave/Mongo queries sent to no-MCP personas
# Must answer from LLM knowledge or admit uncertainty (no hallucinated MCP results)
# ═══════════════════════════════════════════════════════════════════════════════
_CONTAINMENT = [
    ("CONT-01", "What is the current Bitcoin price?", "BTC price, no MCP"),
    ("CONT-02", "What is the weather in Tokyo right now?", "Weather, no brave"),
    ("CONT-03", "What happened in the news today?", "News, no brave"),
    ("CONT-04", "What is SOL's RSI right now?", "Technical indicator, no mongo"),
    ("CONT-05", "What does the Bitcoin Bollinger Band analysis say?", "TA, no mongo"),
    ("CONT-06", "Tell me today's top headlines.", "News, no brave"),
    ("CONT-07", "What is NVIDIA's stock price?", "Stock, no brave"),
    ("CONT-08", "What's the EUR/USD rate right now?", "Forex, no brave"),
    ("CONT-09", "Give me a real-time SOL market summary.", "RT data, no mongo"),
    ("CONT-10", "What is BTC's current market cap?", "Market cap, no mongo"),
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
# INTENT_DISAMBIGUATION — Ambiguous, follow-up, and edge-case routing queries
# ═══════════════════════════════════════════════════════════════════════════════
MCP_TESTS.extend([
    # Follow-up confirmations (eeva with wallet context)
    {"id": "DISAMG-01", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_eeva",
     "question": "Can you check the RSI for SOL?",
     "expected_source": "mongodb_mcp", "check": "none",
     "notes": "Direct mongo routing"},

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

    # Ambiguous — could be brave or LLM
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

    # Mixed intent
    {"id": "DISAMG-09", "category": "INTENT_DISAMBIGUATION", "persona": "nephilim_cipher",
     "question": "What is Bitcoin and what is its price today?",
     "expected_source": "mongodb_mcp", "check": "none",
     "notes": "Compound: definition (LLM) + price (mongo) — mongo should win"},

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
     "notes": "Sentiment query → brave for solace (no mongo)"},

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
# These test what happens when MCP finds nothing useful
# ═══════════════════════════════════════════════════════════════════════════════
MCP_TESTS.extend([
    {"id": "MAHC-01", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_eeva",
     "question": "What is the trading data for a coin called FAKECOIN2025XYZ?",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Non-existent token — MCP returns nothing, must not invent data"},

    {"id": "MAHC-02", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_cipher",
     "question": "Search for news about 'Zorbantium Technology Corp' launched last week.",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Fictional company — brave returns nothing, must hedge"},

    {"id": "MAHC-03", "category": "MCP_ANTI_HALLUC", "persona": "nephilim_aurora",
     "question": "What is the RSI for the fictional token MOON99?",
     "expected_source": "llm", "check": "no_fabrication",
     "notes": "Fictional token RSI — no mongo data"},

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
# CROSS_PERSONA — Same query sent to multiple personas to compare routing consistency
# ═══════════════════════════════════════════════════════════════════════════════
_CROSS_QUERIES = [
    ("CROSS-01", "What is the current SOL price?", "SOL price across all personas"),
    ("CROSS-02", "What are the latest crypto news?", "Crypto news routing"),
    ("CROSS-03", "Should I buy Bitcoin right now?", "Trading advice + data lookup"),
]

for _qid, _q, _notes in _CROSS_QUERIES:
    for _p in NEPHILIM_PERSONAS:
        _acc = PERSONA_MCP_ACCESS[_p]
        if _acc["mongodb"]:
            _exp = "mongodb_mcp"
        elif _acc["brave"]:
            _exp = "brave_mcp"
        else:
            _exp = "llm"
        # The "should I buy" is advice → LLM even with mongo
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
        # Skip any tests with expected_source="any" in strict mode
        if t.get("expected_source") == "any":
            t = dict(t, expected_source="")  # treat as unvalidated

        # Persona filter
        if persona_filter is not None and t["persona"] != persona_filter:
            continue
        # Category filter
        if category_filter is not None and t["category"] != category_filter:
            continue

        key = (t["id"], t["persona"])
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def get_categories() -> list[str]:
    return sorted(set(t["category"] for t in MCP_TESTS))
