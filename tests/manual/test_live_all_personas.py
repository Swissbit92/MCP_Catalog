"""
Live API validation — 30 queries per persona (7 personas, 210 total).
Runs against the actual backend with real MCP execution.
Tests that each persona's mcp_access config is respected end-to-end.
"""

import sys
import json
import time
import urllib.request

API_URL = "http://localhost:8000/persona/chat"

# ─── Persona Configs ─────────────────────────────────────────────────────────
# (api_key, brave_access, mongodb_access)
PERSONAS = {
    "nephilim_aegis":   (True,  False),   # brave only
    "nephilim_aurora":  (True,  True),    # brave + mongodb
    "nephilim_cipher":  (True,  True),    # brave + mongodb
    "nephilim_solace":  (True,  False),   # brave only
    "nephilim_nyx":     (False, False),   # no MCP

    "Gojo":             (False, False),   # no MCP
}

# ─── 30 Test Queries ─────────────────────────────────────────────────────────
# Format: (query, expected_if_brave, expected_if_brave_mongo, expected_if_no_mcp)
# expected values match API source_type field: "brave_mcp" | "mongodb_mcp" | "llm"
QUERIES = [
    # BRAVE — Weather (5)
    ("What is the weather in London today?",             "brave_mcp", "brave_mcp", "llm"),
    ("Will it rain tomorrow in Berlin?",                 "brave_mcp", "brave_mcp", "llm"),
    ("Current temperature in Tokyo",                    "brave_mcp", "brave_mcp", "llm"),
    ("What's the forecast for Paris this weekend?",     "brave_mcp", "brave_mcp", "llm"),
    ("Is it going to be cold tomorrow?",                "brave_mcp", "brave_mcp", "llm"),

    # BRAVE — News & Events (5)
    ("What are the latest news about AI?",              "brave_mcp", "brave_mcp", "llm"),
    ("Breaking news today",                             "brave_mcp", "brave_mcp", "llm"),
    ("What's new with SpaceX?",                         "brave_mcp", "brave_mcp", "llm"),
    ("Recent developments in renewable energy",         "brave_mcp", "brave_mcp", "llm"),
    ("What happened in the US elections recently?",     "brave_mcp", "brave_mcp", "llm"),

    # BRAVE — Stocks & Opinion (5)
    ("What is the current stock price of NVIDIA?",      "brave_mcp", "brave_mcp", "llm"),
    ("How is the S&P 500 doing today?",                 "brave_mcp", "brave_mcp", "llm"),
    ("What do analysts think about Tesla stock?",       "brave_mcp", "brave_mcp", "llm"),
    ("What are predictions for the housing market?",    "brave_mcp", "brave_mcp", "llm"),
    ("What is trending on Twitter right now?",          "brave_mcp", "brave_mcp", "llm"),

    # MONGODB — Bitcoin Price (5)
    ("What is the current price of Bitcoin?",           "llm",       "mongodb_mcp", "llm"),
    ("How much is BTC worth?",                          "llm",       "mongodb_mcp", "llm"),
    ("What's BTC trading at?",                          "llm",       "mongodb_mcp", "llm"),
    ("Current Bitcoin value",                           "llm",       "mongodb_mcp", "llm"),
    ("How much does Bitcoin cost?",                     "llm",       "mongodb_mcp", "llm"),

    # MONGODB — Technical Analysis (5)
    ("What is Bitcoin's RSI right now?",                "llm",       "mongodb_mcp", "llm"),
    ("Bitcoin Bollinger Bands analysis",                "llm",       "mongodb_mcp", "llm"),
    ("What does the Bitcoin technical analysis look like?", "llm",   "mongodb_mcp", "llm"),
    ("Give me a Bitcoin trading summary",               "llm",       "mongodb_mcp", "llm"),
    ("Show me Bitcoin's historical prices from 2025-12-01", "llm",  "mongodb_mcp", "llm"),

    # PURE LLM — Always LLM (5)
    ("What is 25% of 80?",                              "llm",       "llm",       "llm"),
    ("Explain what blockchain is",                      "llm",       "llm",       "llm"),
    ("What is the capital of France?",                  "llm",       "llm",       "llm"),
    ("Who wrote Romeo and Juliet?",                     "llm",       "llm",       "llm"),
    ("How does photosynthesis work?",                   "llm",       "llm",       "llm"),
]


def get_expected(row, has_brave, has_mongo):
    _, exp_brave, exp_brave_mongo, exp_no_mcp = row
    if has_brave and has_mongo:
        return exp_brave_mongo
    elif has_brave:
        return exp_brave
    else:
        return exp_no_mcp


def call_api(persona_key, query):
    payload = json.dumps({
        "persona": persona_key,
        "message": query,
        "history": []
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_persona(persona_key, has_brave, has_mongo):
    pass_count = 0
    fail_count = 0
    errors = []
    total_time = 0.0

    for i, row in enumerate(QUERIES, 1):
        query = row[0]
        expected = get_expected(row, has_brave, has_mongo)
        start = time.time()
        try:
            resp = call_api(persona_key, query)
            elapsed = time.time() - start
            total_time += elapsed

            source = resp.get("metadata", {}).get("source_type", "?")
            tools  = resp.get("metadata", {}).get("tools_used", [])
            ok = source == expected
            status = "PASS" if ok else "FAIL"

            if ok:
                pass_count += 1
            else:
                fail_count += 1
                errors.append(f"    #{i}: \"{query}\" -> expected={expected}, got={source}")

            marker = "  " if ok else ">>"
            tools_str = ",".join(tools) if tools else "none"
            print(f"  {marker} {i:2d}. {status} | exp={expected:<12} got={source:<12} tools={tools_str:<20} {elapsed:5.1f}s | {query[:60]}")

        except Exception as e:
            elapsed = time.time() - start
            total_time += elapsed
            fail_count += 1
            errors.append(f"    #{i}: \"{query}\" ERROR: {e}")
            print(f"  >> {i:2d}. ERROR | {e} | {elapsed:.1f}s | {query[:60]}")

    return pass_count, fail_count, errors, total_time


def main():
    total_q = len(QUERIES) * len(PERSONAS)
    print(f"Live API test: {len(QUERIES)} queries x {len(PERSONAS)} personas = {total_q} total")
    print(f"Endpoint: {API_URL}")
    print("=" * 110)

    all_results = {}
    grand_pass = 0
    grand_fail = 0
    grand_time = 0.0

    for persona_key, (has_brave, has_mongo) in PERSONAS.items():
        mcp_str = []
        if has_brave: mcp_str.append("brave")
        if has_mongo: mcp_str.append("mongodb")
        mcp_label = ", ".join(mcp_str) if mcp_str else "none"

        print(f"\n{'-' * 110}")
        print(f"  {persona_key} | mcp=[{mcp_label}]")
        print(f"{'-' * 110}")

        p, f, errs, t = run_persona(persona_key, has_brave, has_mongo)
        all_results[persona_key] = {"pass": p, "fail": f, "errors": errs, "time": t}
        grand_pass += p
        grand_fail += f
        grand_time += t

        print(f"  -> {p}/{p+f} PASS | {t:.0f}s total | avg {t/(p+f):.1f}s/query")

    # Summary
    total = grand_pass + grand_fail
    print(f"\n{'=' * 110}")
    print(f"GRAND TOTAL: {grand_pass}/{total} PASS ({grand_pass/total*100:.1f}%)")
    print(f"Total time: {grand_time:.0f}s ({grand_time/60:.1f} min) | avg {grand_time/total:.1f}s/query")
    print()
    print("Per-persona breakdown:")
    for key, data in all_results.items():
        has_brave, has_mongo = PERSONAS[key]
        mcp_str = []
        if has_brave: mcp_str.append("brave")
        if has_mongo: mcp_str.append("mongodb")
        mcp_label = ", ".join(mcp_str) if mcp_str else "none"
        t = data["pass"] + data["fail"]
        status = "OK" if data["fail"] == 0 else "XX"
        print(f"  {status} {key:<22} {data['pass']:2d}/{t} pass  [{mcp_label}]  {data['time']:.0f}s")

    any_failures = any(d["fail"] > 0 for d in all_results.values())
    if any_failures:
        print("\nFAILURES:")
        for key, data in all_results.items():
            if data["errors"]:
                print(f"\n  [{key}]")
                for e in data["errors"]:
                    print(e)

    return grand_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
