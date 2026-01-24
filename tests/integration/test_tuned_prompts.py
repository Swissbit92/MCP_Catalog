#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test tuned prompts for improved multi-message rate."""

import sys
import io
import requests
import json
import time

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_URL = "http://127.0.0.1:8000"

# Diverse test queries
test_queries = [
    ("Emotional/Complex", "I just bought my first 0.1 BTC! I'm excited but nervous. What should I do next?"),
    ("Personal intro", "Tell me about yourself. What topics interest you?"),
    ("Decision-making", "I'm worried about the market. Should I sell or hold?"),
    ("Information", "What's a hardware wallet?"),
    ("Data request", "What's the Bitcoin price?"),
    ("Empathy needed", "I lost money on a bad trade and I'm feeling terrible"),
    ("Open-ended", "What do you think about DCA vs lump sum buying?"),
    ("User sharing", "Just set up my first hardware wallet today!"),
    ("Simple factual", "What's 2 + 2?"),
    ("Greeting", "Hi!"),
]

print("="*70)
print("TESTING TUNED PROMPTS - Multi-Message Rate")
print("="*70)
print(f"\nTarget: 40-60% multi-message usage")
print(f"Testing with {len(test_queries)} diverse queries\n")

# Create session
print("[Setup] Creating test session...")
session_resp = requests.post(
    f"{BACKEND_URL}/sessions",
    json={"persona_key": "Eeva", "title": "Tuned Prompt Test"}
)
session_id = session_resp.json()["id"]
print(f"✅ Session: {session_id}\n")

results = []
multi_count = 0
total_count = 0

for i, (category, query) in enumerate(test_queries, 1):
    print(f"\n{'='*70}")
    print(f"Test {i}/{len(test_queries)}: {category}")
    print(f"Query: {query[:60]}...")
    print('='*70)

    # Send message
    start = time.time()
    resp = requests.post(
        f"{BACKEND_URL}/sessions/{session_id}/chat",
        json={"message": query}
    )
    elapsed = time.time() - start

    if resp.status_code != 200:
        print(f"❌ Error: {resp.status_code}")
        continue

    data = resp.json()
    total_count += 1

    # Parse response
    message_flow = data.get("message_flow", "single")
    answer = data.get("answer")
    is_multi = isinstance(answer, list)
    count = len(answer) if is_multi else 1

    if is_multi:
        multi_count += 1

    # Display result
    result_symbol = "✅" if is_multi else "❌"
    result_text = f"MULTI ({count} msgs)" if is_multi else "Single"
    print(f"\n{result_symbol} {result_text} | {elapsed:.1f}s")

    # Show messages
    if is_multi:
        print("\nMessages:")
        for j, msg in enumerate(answer, 1):
            preview = msg[:80] + "..." if len(msg) > 80 else msg
            print(f"  {j}. {preview}")
    else:
        preview = answer[:100] + "..." if len(answer) > 100 else answer
        print(f"\nResponse: {preview}")

    # Track results
    results.append({
        "category": category,
        "is_multi": is_multi,
        "count": count,
        "elapsed": elapsed
    })

# Calculate statistics
print(f"\n{'='*70}")
print("RESULTS SUMMARY")
print("="*70)

usage_rate = (multi_count / total_count * 100) if total_count > 0 else 0

print(f"\nMulti-Message Usage: {multi_count}/{total_count} ({usage_rate:.1f}%)")
print(f"Target: 40-60%")
print(f"Status: {'✅ MEETS TARGET' if 40 <= usage_rate <= 60 else '⚠️ Outside target range'}")

# Breakdown by category
print(f"\nBreakdown by Query Type:")
categories = {}
for r in results:
    cat = r["category"]
    if cat not in categories:
        categories[cat] = {"multi": 0, "total": 0}
    categories[cat]["total"] += 1
    if r["is_multi"]:
        categories[cat]["multi"] += 1

for cat, stats in sorted(categories.items()):
    rate = (stats["multi"] / stats["total"] * 100) if stats["total"] > 0 else 0
    symbol = "✅" if stats["multi"] > 0 else "❌"
    print(f"  {symbol} {cat:20s}: {stats['multi']}/{stats['total']} ({rate:.0f}%)")

# Performance
avg_time = sum(r["elapsed"] for r in results) / len(results) if results else 0
print(f"\nAverage response time: {avg_time:.1f}s")

# Final verdict
print(f"\n{'='*70}")
if 40 <= usage_rate <= 60:
    print("🎉 SUCCESS: Multi-message rate is within target range!")
    print("The prompt tuning is effective.")
elif usage_rate > 60:
    print("⚠️ OVER-TUNED: Multi-message rate is above target.")
    print("Consider slightly relaxing the prompts.")
elif usage_rate < 40:
    print("❌ UNDER-TUNED: Multi-message rate is below target.")
    print("Need stronger prompt reinforcement.")
print("="*70)
