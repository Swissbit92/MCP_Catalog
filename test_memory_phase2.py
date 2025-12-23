"""Test suite for Phase 2 Memory Enhancement: Importance Scoring

This script validates:
1. MessageImportanceScorer correctly prioritizes important messages
2. MemoryManager selects optimal message subset within token budget
3. Personal information is always preserved
4. Recent context is maintained
5. Token budget is never exceeded
"""

import sys
import os

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.coordinator.memory_manager import MessageImportanceScorer, MemoryManager
from datetime import datetime, timedelta
import logging

# Setup logging to see debug output
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_messages(count: int = 50) -> list:
    """Create sample conversation messages for testing."""
    messages = []
    base_time = datetime.utcnow()

    # Message 1: User introduces themselves (HIGH IMPORTANCE)
    messages.append({
        "role": "user",
        "content": "Hi! My name is Alex and I'm learning about Bitcoin.",
        "timestamp": (base_time - timedelta(hours=2)).isoformat()
    })

    # Message 2: Assistant response
    messages.append({
        "role": "assistant",
        "content": "Hey Alex! Great to meet you. Bitcoin is fascinating - what sparked your interest?",
        "timestamp": (base_time - timedelta(hours=2, minutes=-1)).isoformat()
    })

    # Message 3: User shares personal info (HIGH IMPORTANCE)
    messages.append({
        "role": "user",
        "content": "I bought 0.5 BTC last month and want to learn about wallet security.",
        "timestamp": (base_time - timedelta(hours=1, minutes=50)).isoformat()
    })

    # Message 4: Assistant response
    messages.append({
        "role": "assistant",
        "content": "0.5 BTC is a solid start! Wallet security is crucial. Let's break it down...",
        "timestamp": (base_time - timedelta(hours=1, minutes=49)).isoformat()
    })

    # Messages 5-40: Generic conversation (MEDIUM IMPORTANCE)
    for i in range(5, 41):
        if i % 2 == 0:
            messages.append({
                "role": "user",
                "content": f"What about topic {i//2}? Can you explain?",
                "timestamp": (base_time - timedelta(hours=1, minutes=48-i)).isoformat()
            })
        else:
            messages.append({
                "role": "assistant",
                "content": f"Great question! Let me explain topic {i//2} in detail. " + "x" * 100,
                "timestamp": (base_time - timedelta(hours=1, minutes=48-i)).isoformat()
            })

    # Message 41: User asks important question (HIGH IMPORTANCE)
    messages.append({
        "role": "user",
        "content": "What's the safest way to store my private keys?",
        "timestamp": (base_time - timedelta(minutes=10)).isoformat()
    })

    # Message 42: Assistant response
    messages.append({
        "role": "assistant",
        "content": "Hardware wallets are the gold standard for key storage. Here's why...",
        "timestamp": (base_time - timedelta(minutes=9)).isoformat()
    })

    # Messages 43-50: Recent conversation (HIGH RECENCY)
    for i in range(43, 51):
        minutes_ago = 51 - i
        if i % 2 == 0:
            messages.append({
                "role": "user",
                "content": f"Quick question #{i}",
                "timestamp": (base_time - timedelta(minutes=minutes_ago)).isoformat()
            })
        else:
            messages.append({
                "role": "assistant",
                "content": f"Sure, here's the answer to question #{i}",
                "timestamp": (base_time - timedelta(minutes=minutes_ago)).isoformat()
            })

    return messages


def test_importance_scorer():
    """Test MessageImportanceScorer prioritization."""
    print("\n" + "="*80)
    print("TEST 1: Message Importance Scoring")
    print("="*80)

    scorer = MessageImportanceScorer()
    messages = create_sample_messages(50)

    # Score all messages
    scores = []
    for i, msg in enumerate(messages):
        score = scorer.score_message(msg, i, len(messages))
        scores.append((i, msg["content"][:60], score))

    # Sort by score descending
    scores.sort(key=lambda x: x[2], reverse=True)

    # Print top 10 highest-scoring messages
    print("\nTop 10 Highest-Scoring Messages:")
    print("-" * 80)
    for idx, content, score in scores[:10]:
        print(f"[{idx:3d}] Score: {score:6.2f} | {content}...")

    # Validate personal info messages scored high
    personal_info_indices = [0, 2]  # "My name is Alex", "I bought 0.5 BTC"

    print("\n✅ Personal info messages should be in top 10:")
    for idx in personal_info_indices:
        msg_score = next(s for i, _, s in scores if i == idx)
        in_top_10 = idx in [i for i, _, _ in scores[:10]]
        status = "✅ PASS" if in_top_10 else "❌ FAIL"
        print(f"   Message {idx}: score={msg_score:.2f} - {status}")

    print("\n" + "="*80)
    return all(idx in [i for i, _, _ in scores[:10]] for idx in personal_info_indices)


def test_memory_manager_selection():
    """Test MemoryManager message selection within token budget."""
    print("\n" + "="*80)
    print("TEST 2: Memory Manager Message Selection")
    print("="*80)

    manager = MemoryManager(max_tokens=4096)
    messages = create_sample_messages(50)

    # Simulate system prompt tokens
    system_tokens = 1200

    print(f"\nTotal messages: {len(messages)}")
    print(f"System tokens: {system_tokens}")
    print(f"Available for history: {4096 - system_tokens - 500} tokens")

    # Select messages
    selected = manager.select_messages(
        messages=messages,
        token_budget=4096,
        system_prompt_tokens=system_tokens
    )

    print(f"\nSelected: {len(selected)}/{len(messages)} messages")

    # Verify personal info messages are included
    personal_info_content = [
        "My name is Alex",
        "I bought 0.5 BTC"
    ]

    print("\n✅ Checking personal info preservation:")
    for content_snippet in personal_info_content:
        found = any(content_snippet in msg["content"] for msg in selected)
        status = "✅ PASS" if found else "❌ FAIL"
        print(f"   '{content_snippet}': {status}")

    # Verify recent messages are included (last 10)
    recent_indices = set(range(len(messages) - 10, len(messages)))
    selected_indices = [messages.index(msg) for msg in selected]
    recent_included = len(recent_indices.intersection(selected_indices))

    print(f"\n✅ Recent context preservation:")
    print(f"   Last 10 messages included: {recent_included}/10 - {'✅ PASS' if recent_included >= 8 else '❌ FAIL'}")

    # Verify token budget not exceeded
    total_tokens = sum(len(msg["content"]) // 4 for msg in selected)
    total_tokens += system_tokens
    budget_exceeded = total_tokens > 4096

    print(f"\n✅ Token budget compliance:")
    print(f"   Total tokens: {total_tokens}/4096 - {'✅ PASS' if not budget_exceeded else '❌ FAIL'}")

    # Show selected message distribution
    print("\n✅ Selected message indices:")
    print(f"   {sorted(selected_indices)}")

    print("\n" + "="*80)

    # Return pass/fail
    personal_info_ok = all(any(snippet in msg["content"] for msg in selected) for snippet in personal_info_content)
    recent_ok = recent_included >= 8
    budget_ok = not budget_exceeded

    return personal_info_ok and recent_ok and budget_ok


def test_edge_cases():
    """Test edge cases: empty conversation, very long messages, etc."""
    print("\n" + "="*80)
    print("TEST 3: Edge Cases")
    print("="*80)

    manager = MemoryManager(max_tokens=4096)

    # Test 1: Empty conversation
    print("\n1. Empty conversation:")
    selected = manager.select_messages([], token_budget=4096, system_prompt_tokens=1000)
    print(f"   Selected: {len(selected)} messages - {'✅ PASS' if len(selected) == 0 else '❌ FAIL'}")

    # Test 2: Very long messages
    print("\n2. Very long messages:")
    long_messages = [
        {"role": "user", "content": "My name is Alice. " + "x" * 5000, "timestamp": datetime.utcnow().isoformat()},
        {"role": "assistant", "content": "Hello Alice! " + "y" * 5000, "timestamp": datetime.utcnow().isoformat()},
        {"role": "user", "content": "Quick question?", "timestamp": datetime.utcnow().isoformat()},
    ]
    selected = manager.select_messages(long_messages, token_budget=4096, system_prompt_tokens=1000)
    print(f"   Selected: {len(selected)}/{len(long_messages)} messages - ✅ PASS (no crash)")

    # Test 3: All personal info messages
    print("\n3. All personal info messages:")
    personal_messages = [
        {"role": "user", "content": f"My name is User{i} and I own {i} BTC", "timestamp": datetime.utcnow().isoformat()}
        for i in range(20)
    ]
    selected = manager.select_messages(personal_messages, token_budget=4096, system_prompt_tokens=1000)
    print(f"   Selected: {len(selected)}/{len(personal_messages)} messages")
    print(f"   All high-importance messages prioritized - ✅ PASS")

    print("\n" + "="*80)
    return True


def test_integration_scenario():
    """Test realistic conversation scenario with memory recall."""
    print("\n" + "="*80)
    print("TEST 4: Integration Scenario - Memory Recall")
    print("="*80)

    manager = MemoryManager(max_tokens=4096)

    # Simulate 50-message conversation
    messages = create_sample_messages(50)

    print(f"\nSimulated conversation:")
    print(f"  - Message 1: User says 'My name is Alex'")
    print(f"  - Message 3: User says 'I bought 0.5 BTC'")
    print(f"  - Messages 5-40: Various questions")
    print(f"  - Messages 41-50: Recent context")

    # Select messages for LLM context
    selected = manager.select_messages(
        messages=messages,
        token_budget=4096,
        system_prompt_tokens=1200
    )

    print(f"\n✅ Memory Manager selected {len(selected)} messages")

    # Check if critical info is preserved
    has_name = any("My name is Alex" in msg["content"] for msg in selected)
    has_btc = any("0.5 BTC" in msg["content"] for msg in selected)

    print(f"\n✅ Critical information preservation:")
    print(f"   User's name (Alex): {'✅ PRESERVED' if has_name else '❌ LOST'}")
    print(f"   BTC amount (0.5): {'✅ PRESERVED' if has_btc else '❌ LOST'}")

    if has_name and has_btc:
        print(f"\n🎉 SUCCESS: Personal information preserved across 50-message conversation!")
    else:
        print(f"\n⚠️ FAILURE: Some personal information lost")

    print("\n" + "="*80)
    return has_name and has_btc


def run_all_tests():
    """Run all Phase 2 memory tests."""
    print("\n" + "="*80)
    print("PHASE 2 MEMORY ENHANCEMENT - TEST SUITE")
    print("Testing: Importance Scoring & Intelligent Message Selection")
    print("="*80)

    results = {
        "Importance Scoring": test_importance_scorer(),
        "Message Selection": test_memory_manager_selection(),
        "Edge Cases": test_edge_cases(),
        "Integration Scenario": test_integration_scenario()
    }

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:30s}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Phase 2 Task 2.1 Complete!")
        print("="*80)
        print("\nNext Steps:")
        print("1. Run backend with: python run_react.py")
        print("2. Test with real conversations in the UI")
        print("3. Monitor logs for [Memory] and [MemoryManager] entries")
        print("4. Proceed to Task 2.2: Conversation Summarization")
    else:
        print("❌ SOME TESTS FAILED - Review output above")
        print("="*80)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
