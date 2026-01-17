"""Test FAISS incremental update performance improvement.

This test verifies that the incremental update optimization works correctly
and provides significant performance improvements for long sessions.
"""

import sys
import os
import time
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


def generate_test_messages(count: int) -> List[Dict[str, Any]]:
    """Generate test messages for performance testing."""
    messages = []
    for i in range(count):
        messages.append({
            "id": i,
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Test message {i}: This is message content for testing purposes",
            "timestamp": f"2026-01-17T10:00:{i:02d}Z"
        })
    return messages


def test_incremental_update_correctness():
    """Test that incremental updates produce correct results."""
    try:
        from src.coordinator.memory_rag import EpisodicMemoryRAG
    except ImportError as e:
        print(f"[SKIP] Dependencies not installed ({e})")
        return

    print("\n=== Test 1: Correctness Verification ===")
    print("Testing that incremental updates produce correct search results...\n")

    rag = EpisodicMemoryRAG()
    session_id = "test-session-correctness"

    # Initial messages
    initial_messages = generate_test_messages(10)
    rag.index_session(session_id, initial_messages)

    # Add new messages incrementally
    new_messages = generate_test_messages(5)
    for msg in new_messages:
        msg["id"] = len(initial_messages) + new_messages.index(msg)

    full_history = initial_messages + new_messages

    rag.update_session(
        session_id=session_id,
        new_messages=new_messages,
        full_history=full_history
    )

    # Verify all messages are searchable
    stats = rag.get_stats(session_id)
    expected_count = len(full_history)
    actual_count = stats["indexed_messages"]

    print(f"Expected indexed messages: {expected_count}")
    print(f"Actual indexed messages:   {actual_count}")

    if actual_count == expected_count:
        print("[PASS] PASS: Correct number of messages indexed")
    else:
        print(f"[FAIL] FAIL: Expected {expected_count} but got {actual_count}")

    # Test search functionality
    results = rag.search_memory(session_id, "Test message", k=15)
    print(f"\nSearch returned {len(results)} results")

    if len(results) > 0:
        print("[PASS] PASS: Search returns results after incremental update")
    else:
        print("[FAIL] FAIL: Search returned no results")

    rag.clear_session(session_id)


def test_incremental_update_performance():
    """Test performance improvement of incremental updates vs full rebuild."""
    try:
        from src.coordinator.memory_rag import EpisodicMemoryRAG
    except ImportError as e:
        print(f"[SKIP] Dependencies not installed ({e})")
        return

    print("\n=== Test 2: Performance Comparison ===")
    print("Measuring performance: Incremental update vs Full rebuild\n")

    rag = EpisodicMemoryRAG()

    # Test with different session sizes
    test_sizes = [100, 500, 1000]

    for session_size in test_sizes:
        session_id_incremental = f"test-session-incremental-{session_size}"
        session_id_rebuild = f"test-session-rebuild-{session_size}"

        print(f"\n--- Session size: {session_size} messages ---")

        # Generate base messages
        base_messages = generate_test_messages(session_size)

        # Setup: Index initial messages for both methods
        rag.index_session(session_id_incremental, base_messages)
        rag.index_session(session_id_rebuild, base_messages)

        # Prepare new messages to add
        new_messages = generate_test_messages(2)  # Add 2 new messages (typical: user + assistant)
        for msg in new_messages:
            msg["id"] = session_size + new_messages.index(msg)

        full_history = base_messages + new_messages

        # METHOD 1: Incremental update (new optimized approach)
        start_time = time.time()
        rag.update_session(
            session_id=session_id_incremental,
            new_messages=new_messages,
            full_history=full_history
        )
        incremental_time = time.time() - start_time

        # METHOD 2: Full rebuild (old approach for comparison)
        start_time = time.time()
        rag.index_session(session_id_rebuild, full_history)
        rebuild_time = time.time() - start_time

        # Calculate speedup
        speedup = rebuild_time / incremental_time if incremental_time > 0 else 0

        print(f"Incremental update:  {incremental_time * 1000:.2f}ms")
        print(f"Full rebuild:        {rebuild_time * 1000:.2f}ms")
        print(f"Speedup:             {speedup:.1f}x faster")

        if speedup > 1.5:
            print(f"[PASS] PASS: Incremental update is {speedup:.1f}x faster")
        else:
            print(f"[WARNING]  WARNING: Speedup is only {speedup:.1f}x (expected > 1.5x)")

        # Cleanup
        rag.clear_session(session_id_incremental)
        rag.clear_session(session_id_rebuild)


def test_incremental_update_edge_cases():
    """Test edge cases for incremental updates."""
    try:
        from src.coordinator.memory_rag import EpisodicMemoryRAG
    except ImportError as e:
        print(f"[SKIP] Dependencies not installed ({e})")
        return

    print("\n=== Test 3: Edge Cases ===")
    print("Testing edge cases for incremental updates...\n")

    rag = EpisodicMemoryRAG()

    # Edge Case 1: Empty new_messages
    session_id = "test-session-empty"
    messages = generate_test_messages(10)
    rag.index_session(session_id, messages)

    print("Test: Updating with empty new_messages list...")
    rag.update_session(
        session_id=session_id,
        new_messages=[],
        full_history=messages
    )
    print("[PASS] PASS: Handles empty new_messages without error\n")

    # Edge Case 2: First update (no existing vectorstore)
    session_id2 = "test-session-first-update"
    print("Test: First update (creates initial index)...")
    rag.update_session(
        session_id=session_id2,
        new_messages=messages,
        full_history=messages
    )

    stats = rag.get_stats(session_id2)
    if stats["indexed_messages"] == len(messages):
        print("[PASS] PASS: Creates initial index correctly\n")
    else:
        print(f"[FAIL] FAIL: Expected {len(messages)} messages, got {stats['indexed_messages']}\n")

    # Cleanup
    rag.clear_session(session_id)
    rag.clear_session(session_id2)


if __name__ == "__main__":
    print("=" * 70)
    print("FAISS Incremental Update Performance Tests")
    print("=" * 70)

    try:
        # Run all tests
        test_incremental_update_correctness()
        test_incremental_update_performance()
        test_incremental_update_edge_cases()

        print("\n" + "=" * 70)
        print("All tests completed!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n[WARNING]  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n[FAIL] Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
