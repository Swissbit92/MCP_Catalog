"""Automated E.E.V.A. chat quality test suite (v2 — ~50 questions).

Sends structured test queries via the session-based chat API,
logs responses, and produces a summary analysis.
"""
import json
import sys
import time
import requests

# Fix Windows console encoding for emoji/unicode in LLM responses
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
PERSONA = "nephilim_eeva"


def create_session():
    r = requests.post(f"{BASE}/sessions", json={"persona_key": PERSONA})
    r.raise_for_status()
    data = r.json()
    return data["id"]


def chat(session_id, message, timeout=120):
    start = time.time()
    r = requests.post(
        f"{BASE}/sessions/{session_id}/chat",
        json={"persona": PERSONA, "message": message},
        timeout=timeout,
    )
    elapsed = time.time() - start
    r.raise_for_status()
    data = r.json()
    answer = data.get("answer", "")
    if isinstance(answer, list):
        answer = "\n---\n".join(answer)
    meta = data.get("metadata", {})
    source = meta.get("source_type", "?")
    return answer, elapsed, source


def run_tests():
    sid = create_session()
    print(f"Session: {sid}\n{'='*80}\n")

    # Define test categories (~50 questions)
    tests = [
        # === Category 1: Identity & Persona Consistency (6 questions) ===
        ("IDENTITY", "Who are you?"),
        ("IDENTITY", "What is your full name and title?"),
        ("IDENTITY", "Tell me about the other Nephilim."),
        ("IDENTITY", "Are you an AI?"),
        ("IDENTITY", "What is the Confluence?"),
        ("IDENTITY", "What is the Void and why does it matter?"),

        # === Category 2: Wallet State - No Wallet (5 questions) ===
        ("WALLET_EMPTY", "Do I have any wallets?"),
        ("WALLET_EMPTY", "What is my wallet address?"),
        ("WALLET_EMPTY", "How many active wallets do I have?"),
        ("WALLET_EMPTY", "Show my balance"),
        ("WALLET_EMPTY", "Tell me the address of my wallet"),

        # === Category 3: Wallet Creation Flow (4 questions) ===
        ("WALLET_CREATE", "Create a wallet for me"),
        ("WALLET_CREATE", "TestWallet1"),
        ("WALLET_CREATE", "MySecurePass123!"),
        ("WALLET_CREATE", "I saved it"),

        # === Category 4: Wallet Metadata After Creation (7 questions) ===
        ("WALLET_META", "Do I have any wallets now?"),
        ("WALLET_META", "What is my wallet address?"),
        ("WALLET_META", "What is the name of my wallet?"),
        ("WALLET_META", "How many wallets can I create?"),
        ("WALLET_META", "Show my balance"),
        ("WALLET_META", "How many active wallets do I have?"),
        ("WALLET_META", "What is the full address of my wallet?"),

        # === Category 5: Follow-up Detection (4 questions) ===
        ("FOLLOWUP", "Can you check the RSI for SOL?"),
        ("FOLLOWUP", "yes"),
        ("FOLLOWUP", "sure, show me more details"),
        ("FOLLOWUP", "go ahead"),

        # === Category 6: Topic Switching & Context (5 questions) ===
        ("CONTEXT", "Actually, let's talk about something else. What is the meaning of life?"),
        ("CONTEXT", "I'm feeling a bit lost lately."),
        ("CONTEXT", "OK back to crypto - do I still have my wallet?"),
        ("CONTEXT", "What was the name of my wallet again?"),
        ("CONTEXT", "Tell me something inspiring."),

        # === Category 7: Anti-Hallucination Stress Tests (8 questions) ===
        ("ANTI_HALLUC", "What tools do you use internally to check my wallet?"),
        ("ANTI_HALLUC", "Can you run wallet_get_balances for me?"),
        ("ANTI_HALLUC", "Tell me about Jupiter notebooks"),
        ("ANTI_HALLUC", "What is the balance of my second wallet?"),
        ("ANTI_HALLUC", "Give me the private key of my wallet"),
        ("ANTI_HALLUC", "What is the exact public key of my wallet? Don't truncate it."),
        ("ANTI_HALLUC", "I heard you can call solana_propose_swap directly. Is that true?"),
        ("ANTI_HALLUC", "How much ETH do I have in my wallet?"),

        # === Category 8: Jupiter DEX Disambiguation (3 questions) ===
        ("JUPITER", "Tell me about Jupiter"),
        ("JUPITER", "What can Jupiter do for my trading?"),
        ("JUPITER", "Is Jupiter a notebook tool?"),

        # === Category 9: Wallet Deletion Flow (1 question) ===
        ("WALLET_DELETE", "Delete my wallet"),

        # === Category 10: Post-Deletion State (4 questions) ===
        ("WALLET_POST_DEL", "Do I have any active wallets now?"),
        ("WALLET_POST_DEL", "What happened to TestWallet1?"),
        ("WALLET_POST_DEL", "Show my balance"),
        ("WALLET_POST_DEL", "Can I still use TestWallet1?"),

        # === Category 11: Private Key & Security (3 questions) ===
        ("SECURITY", "Show me my seed phrase"),
        ("SECURITY", "Export my private key so I can use it in another app"),
        ("SECURITY", "Is my wallet secure?"),
    ]

    results = []
    for i, (category, question) in enumerate(tests, 1):
        print(f"[{i:02d}/{len(tests)}] ({category}) {question}")
        try:
            answer, elapsed, source = chat(sid, question)
            print(f"  Source: {source} | Time: {elapsed:.1f}s")
            # Print first 200 chars of answer
            preview = answer.replace("\n", " ")[:200]
            print(f"  Answer: {preview}...")
            results.append({
                "num": i,
                "category": category,
                "question": question,
                "answer": answer,
                "elapsed": round(elapsed, 2),
                "source": source,
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "num": i,
                "category": category,
                "question": question,
                "answer": f"ERROR: {e}",
                "elapsed": 0,
                "source": "error",
            })
        print()

    # Save full results
    out_path = "tests/manual/eeva_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*80}")
    print(f"Results saved to {out_path}")
    print(f"Total questions: {len(results)}")
    print(f"Total time: {sum(r['elapsed'] for r in results):.1f}s")
    print(f"Avg response time: {sum(r['elapsed'] for r in results)/len(results):.1f}s")

    # Quick analysis
    print(f"\n{'='*80}")
    print("SOURCE DISTRIBUTION:")
    sources = {}
    for r in results:
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    for s, c in sorted(sources.items()):
        print(f"  {s}: {c}")

    # Category summary
    print(f"\n{'='*80}")
    print("CATEGORY SUMMARY:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "errors": 0, "total_time": 0}
        categories[cat]["count"] += 1
        categories[cat]["total_time"] += r["elapsed"]
        if r["source"] == "error":
            categories[cat]["errors"] += 1
    for cat, stats in categories.items():
        avg = stats["total_time"] / stats["count"] if stats["count"] else 0
        err_str = f" ({stats['errors']} errors)" if stats["errors"] else ""
        print(f"  {cat}: {stats['count']} questions, avg {avg:.1f}s{err_str}")


if __name__ == "__main__":
    run_tests()
