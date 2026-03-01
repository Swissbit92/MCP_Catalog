#!/usr/bin/env python3
"""
Unit tests for persona summary truncation functions.

Tests _count_tokens, _truncate_to_tokens, and _truncate_to_sentence.
"""

from __future__ import annotations

import sys
import io
from pathlib import Path

# Fix Windows console encoding for Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.coordinator.persona_memory import _count_tokens, _truncate_to_tokens, _truncate_to_sentence


def test_count_tokens_basic():
    """Test basic token counting."""
    print("\n=== Test: Basic Token Counting ===")

    # Empty string
    assert _count_tokens("") == 1  # max(1, ...)
    print("✓ Empty string returns 1")

    # Short text
    short = "Hello world"
    count = _count_tokens(short)
    print(f"✓ '{short}' = {count} tokens")

    # Longer text (approximate check)
    long = "This is a longer sentence with multiple words to test token counting accuracy."
    count = _count_tokens(long)
    print(f"✓ Longer text ({len(long)} chars) = {count} tokens")

    print("✓ All token counting tests passed")


def test_truncate_to_tokens():
    """Test word-boundary truncation."""
    print("\n=== Test: Truncate to Tokens (Word Boundary) ===")

    # Text under limit - no truncation
    short = "This is short."
    result = _truncate_to_tokens(short, 100)
    assert result == short
    print(f"✓ Text under limit preserved: '{result}'")

    # Text over limit - should truncate at word boundary
    long = "This is a very long sentence that should be truncated at a word boundary to stay within the token limit."
    result = _truncate_to_tokens(long, 10)
    assert _count_tokens(result) <= 10
    assert not result.endswith(" ")  # No trailing space
    print(f"✓ Long text truncated: '{result}' ({_count_tokens(result)} tokens)")

    # Verify word boundary preservation
    assert " " in result or len(result.split()) == 1  # Either multiple words or single word
    print("✓ Word boundaries preserved")

    print("✓ All word-boundary truncation tests passed")


def test_truncate_to_sentence_basic():
    """Test sentence-boundary truncation - basic cases."""
    print("\n=== Test: Truncate to Sentence (Basic) ===")

    # Text under limit - no truncation
    short = "This is short. Very brief."
    result = _truncate_to_sentence(short, 100)
    assert result == short
    print(f"✓ Text under limit preserved: '{result}'")

    # Single sentence under limit
    single = "This is a single sentence."
    result = _truncate_to_sentence(single, 50)
    assert result == single
    assert result[-1] == '.'
    print(f"✓ Single sentence preserved: '{result}'")

    print("✓ Basic sentence truncation tests passed")


def test_truncate_to_sentence_multi():
    """Test sentence-boundary truncation - multiple sentences."""
    print("\n=== Test: Truncate to Sentence (Multiple Sentences) ===")

    # Multiple sentences, keep first
    text = "First sentence here. Second sentence here. Third sentence here."
    result = _truncate_to_sentence(text, 8)  # Should keep only first
    assert result == "First sentence here."
    assert result[-1] == '.'
    print(f"✓ Kept first sentence: '{result}' ({_count_tokens(result)} tokens)")

    # Multiple sentences, keep as many as fit
    result = _truncate_to_sentence(text, 20)  # Should keep at least first two
    tokens = _count_tokens(result)
    assert tokens <= 20, f"Exceeded limit: {tokens} > 20"
    assert result[-1] == '.', f"Doesn't end with period: '{result[-1]}'"
    # Should have at least 2 sentences (first two should fit)
    assert result.count('.') >= 2, f"Expected at least 2 sentences, got: {result}"
    print(f"✓ Kept multiple sentences: '{result}' ({tokens} tokens)")

    print("✓ Multi-sentence truncation tests passed")


def test_truncate_to_sentence_punctuation():
    """Test sentence-boundary truncation with different punctuation."""
    print("\n=== Test: Truncate to Sentence (Punctuation Variants) ===")

    # Exclamation mark
    text = "This is exciting! This is calm. This is questioning?"
    result = _truncate_to_sentence(text, 8)
    # Should keep at least first sentence with exclamation
    assert "exciting!" in result
    assert result[-1] in '.!?', f"Should end with punctuation: '{result[-1]}'"
    print(f"✓ Exclamation preserved: '{result}'")

    # Multiple sentences with mixed punctuation
    result = _truncate_to_sentence(text, 20)
    tokens = _count_tokens(result)
    assert tokens <= 20, f"Exceeded limit: {tokens} > 20"
    assert result[-1] in '.!?', f"Should end with punctuation: '{result[-1]}'"
    print(f"✓ Multiple punctuation types: '{result}' ({tokens} tokens)")

    print("✓ Punctuation variant tests passed")


def test_truncate_to_sentence_fallback():
    """Test sentence-boundary truncation fallback to word boundary."""
    print("\n=== Test: Truncate to Sentence (Fallback) ===")

    # Very long first sentence - should fall back to word boundary
    text = "This is an extremely long sentence that goes on and on without any punctuation until way past the token limit we set for truncation purposes and should trigger the fallback mechanism."
    result = _truncate_to_sentence(text, 10)

    # Should be truncated (not the full text)
    assert len(result) < len(text)

    # Should be under token limit
    assert _count_tokens(result) <= 10

    # Might not end with sentence punctuation (fallback case)
    print(f"✓ Fallback triggered: '{result}' ({_count_tokens(result)} tokens)")
    print(f"  Ends with: '{result[-1]}'")

    print("✓ Fallback mechanism works")


def test_truncate_to_sentence_edge_cases():
    """Test edge cases."""
    print("\n=== Test: Edge Cases ===")

    # Empty string
    result = _truncate_to_sentence("", 10)
    assert result == ""
    print("✓ Empty string handled")

    # Only punctuation
    result = _truncate_to_sentence(".", 10)
    assert result == "."
    print("✓ Single punctuation handled")

    # No spaces (single long word) - will fall back to word truncation
    long_word = "Supercalifragilisticexpialidocious"
    result = _truncate_to_sentence(long_word, 2)
    assert len(result) > 0, "Result should not be empty"
    assert _count_tokens(result) <= 2, f"Should be under limit: {_count_tokens(result)} > 2"
    # May or may not end with punctuation (fallback case)
    print(f"✓ Single long word handled: '{result}' ({_count_tokens(result)} tokens)")

    print("✓ Edge case tests passed")


def test_real_world_summary():
    """Test with realistic persona summary text."""
    print("\n=== Test: Real-World Summary ===")

    # Simulate a real summary that's too long
    summary = (
        "I'm Eeva, a Bitcoin enthusiast who loves breaking down complex crypto concepts "
        "into friendly explainers. I grew up taking apart gadgets and writing scripts to "
        "automate everyday tasks. My passion for clear thinking and simple explanations "
        "led me to explore algorithms in my early teens, creating small bots to help "
        "classmates debug code. I believe that every complicated problem hides a "
        "straightforward solution waiting to be discovered through careful analysis."
    )

    original_tokens = _count_tokens(summary)
    print(f"Original: {original_tokens} tokens")

    # Truncate to 120 tokens with sentence boundary
    result = _truncate_to_sentence(summary, 120)
    final_tokens = _count_tokens(result)

    print(f"Truncated: {final_tokens} tokens")
    print(f"Result: {result}")

    # Verify constraints
    assert final_tokens <= 120, f"Exceeded limit: {final_tokens} > 120"
    assert result[-1] in '.!?', f"Doesn't end with sentence punctuation: '{result[-1]}'"
    assert len(result) > 0, "Result is empty"

    print(f"✓ Real summary truncated correctly")
    print(f"  Ends with: '{result[-1]}'")
    print(f"  Tokens: {original_tokens} → {final_tokens}")

    print("✓ Real-world summary test passed")


def test_summary_quality_check():
    """Test that summaries meet quality standards."""
    print("\n=== Test: Summary Quality Standards ===")

    test_summaries = [
        "I am Gojo Satoru, the strongest sorcerer. I have guarded humanity for years.",
        "I'm Gojo Satoru, the strongest! My power is unmatched.",
        "I am Itachi Uchiha, the Silent Protector. My life has been a paradox of duty and empathy, shaped by impossible choices?",
    ]

    for i, summary in enumerate(test_summaries, 1):
        tokens = _count_tokens(summary)
        ends_properly = summary[-1] in '.!?'

        print(f"\nSummary {i}:")
        print(f"  Text: {summary}")
        print(f"  Tokens: {tokens}")
        print(f"  Ends properly: {ends_properly} ('{summary[-1]}')")

        assert ends_properly, f"Summary {i} doesn't end with proper punctuation"

        # Test truncation maintains quality
        if tokens > 15:
            truncated = _truncate_to_sentence(summary, 15)
            assert truncated[-1] in '.!?', f"Truncated summary {i} doesn't end properly"
            print(f"  Truncated: {truncated}")
            print(f"  Still ends properly: ✓")

    print("\n✓ All summaries meet quality standards")


def run_all_tests():
    """Run all test functions."""
    print("=" * 70)
    print("PERSONA TRUNCATION TESTS")
    print("=" * 70)

    test_functions = [
        test_count_tokens_basic,
        test_truncate_to_tokens,
        test_truncate_to_sentence_basic,
        test_truncate_to_sentence_multi,
        test_truncate_to_sentence_punctuation,
        test_truncate_to_sentence_fallback,
        test_truncate_to_sentence_edge_cases,
        test_real_world_summary,
        test_summary_quality_check,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {test_func.__name__}")
            print(f"   Exception: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
