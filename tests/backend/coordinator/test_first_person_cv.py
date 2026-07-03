#!/usr/bin/env python3
"""
Unit tests for first-person CV summary generation.

Tests that persona CV summaries are generated in first person
and meet quality standards.

Usage:
    python src/coordinator/test_first_person_cv.py
"""

import re
from typing import Dict, List

import pytest

from src.coordinator.persona_memory import (
    _count_tokens,
    _make_cv_summary,
    resolve_persona_to_card,
    _load_all_cards_cached,
    get_or_build_cv_summary,
)

# Every test here builds a CV summary via _make_cv_summary / get_or_build_cv_summary,
# which calls the live Ollama LLM. Gate the whole module so it auto-skips when
# Ollama is unreachable (see tests/conftest.py) instead of crawling/erroring.
pytestmark = pytest.mark.requires_ollama


def validate_first_person(summary: str, persona_name: str) -> Dict[str, any]:
    """
    Validate that summary is in first person.

    Args:
        summary: CV summary text to validate
        persona_name: Name of the persona (to check it's not in 3rd person)

    Returns:
        Dictionary with validation results:
        - starts_with_i: Summary starts with "I'm" or "I "
        - has_first_person: Contains first-person pronouns
        - no_third_person: Does NOT contain persona name in third person
        - length_ok: Token count <= 100
        - valid: All checks passed
    """
    summary_lower = summary.lower()
    first_name = persona_name.split(" — ")[0].strip().split()[0].lower()

    # Check 1: Starts with I/I'm
    starts_with_i = summary_lower.startswith(("i'm ", "i ", "i've ", "i'll "))

    # Check 2: Contains first-person pronouns
    first_person_pronouns = [" i ", " my ", " me ", " i'm ", " i've ", " i'll ", " myself "]
    has_first_person = any(pronoun in summary_lower for pronoun in first_person_pronouns)
    # Also check beginning of string
    has_first_person = has_first_person or summary_lower.startswith(("i ", "i'm ", "i've ", "i'll "))

    # Check 3: Does NOT contain third-person references like "Eeva is" or "Eeva, a"
    # Allow "I'm Eeva" and "I'm Eeva, a..." but not standalone "Eeva is" or "Eeva has"
    third_person_patterns = [
        f"{first_name} is a ",  # More specific to avoid "Eeva is" in "I am Eeva, is a" (typo)
        f"{first_name} is an ",
        f"{first_name} has ",
        f"{first_name} was ",
        f"{first_name} does ",
        f"{first_name} believes ",
    ]

    # Exception: "I'm Eeva, a..." and "I am Eeva, an..." are valid first-person
    # Only flag if NOT preceded by "I'm" or "I am"
    violations = []
    for pattern in third_person_patterns:
        if pattern in summary_lower:
            # Check context - is it preceded by "I'm" or "I am"?
            idx = summary_lower.find(pattern)
            preceding = summary_lower[max(0, idx-10):idx]  # Check 10 chars before
            if not ("i'm" in preceding or "i am" in preceding):
                violations.append(pattern)

    # Also check for possessive without self-reference: "Eeva's passion" (not "my" or "I")
    possessive_pattern = f"{first_name}'s "
    if possessive_pattern in summary_lower:
        idx = summary_lower.find(possessive_pattern)
        preceding = summary_lower[max(0, idx-20):idx]
        # Only flag if no first-person context
        if not any(pronoun in preceding for pronoun in ["i ", "my ", "me "]):
            violations.append(possessive_pattern)

    no_third_person = len(violations) == 0

    # Check 4: Length constraint
    token_count = _count_tokens(summary)
    length_ok = token_count <= 100

    # Overall validity
    valid = all([starts_with_i, has_first_person, no_third_person, length_ok])

    return {
        "starts_with_i": starts_with_i,
        "has_first_person": has_first_person,
        "no_third_person": no_third_person,
        "length_ok": length_ok,
        "token_count": token_count,
        "valid": valid,
    }


def test_cv_summary_first_person_format():
    """Test 1: CV summaries start with 'I' or 'I'm'."""
    print("\n[Test 1] CV summaries start with 'I' or 'I'm'")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        starts_with_i = summary.lower().startswith(("i'm ", "i ", "i've ", "i'll "))

        if starts_with_i:
            print(f"  ✓ {persona_name}: '{summary[:50]}...'")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: Does not start with 'I' - '{summary[:50]}...'")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def test_cv_summary_has_first_person_pronouns():
    """Test 2: CV summaries contain first-person pronouns."""
    print("\n[Test 2] CV summaries contain first-person pronouns (I, my, me)")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        summary_lower = summary.lower()
        first_person_pronouns = [" i ", " my ", " me ", " i'm ", " i've ", " myself "]
        has_pronouns = any(pronoun in summary_lower for pronoun in first_person_pronouns)
        has_pronouns = has_pronouns or summary_lower.startswith(("i ", "i'm ", "i've "))

        if has_pronouns:
            print(f"  ✓ {persona_name}")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: No first-person pronouns found")
            print(f"    Summary: {summary}")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def test_cv_summary_no_third_person():
    """Test 3: CV summaries do NOT contain third-person references."""
    print("\n[Test 3] CV summaries do NOT contain third-person references")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        # Use the comprehensive validation function
        validation = validate_first_person(summary, persona_name)

        if validation["no_third_person"]:
            print(f"  ✓ {persona_name}")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: Contains third-person reference")
            print(f"    Summary: {summary}")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def test_cv_summary_length():
    """Test 4: CV summaries are <= 100 tokens."""
    print("\n[Test 4] CV summaries are <= 100 tokens")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        token_count = _count_tokens(summary)

        if token_count <= 100:
            print(f"  ✓ {persona_name}: {token_count} tokens")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: {token_count} tokens (exceeds 100)")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def test_cv_summary_coherence():
    """Test 5: CV summaries are coherent (no truncation mid-word)."""
    print("\n[Test 5] CV summaries are coherent (complete sentences)")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        # Check 1: Doesn't end mid-word (should end with punctuation or complete word)
        ends_cleanly = summary.rstrip().endswith(('.', '!', '?', '"', "'")) or summary.rstrip()[-1].isalnum()

        # Check 2: No truncated words (no words ending with -)
        no_truncated = not summary.rstrip().endswith('-')

        # Check 3: At least 20 chars (not empty/truncated too much)
        min_length = len(summary.strip()) >= 20

        coherent = ends_cleanly and no_truncated and min_length

        if coherent:
            print(f"  ✓ {persona_name}")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: Coherence issues")
            print(f"    Summary: {summary}")
            print(f"    Ends cleanly: {ends_cleanly}, No truncation: {no_truncated}, Min length: {min_length}")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def test_all_personas_comprehensive():
    """Test 6: Comprehensive validation for all personas."""
    print("\n[Test 6] Comprehensive validation for all personas")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0
    results = []

    for card in cards:
        persona_name = card.get("display_name") or card.get("key") or "Unknown"
        summary = _make_cv_summary(card)

        validation = validate_first_person(summary, persona_name)

        if validation["valid"]:
            print(f"  ✓ {persona_name}: ALL CHECKS PASSED")
            print(f"    Summary: {summary[:80]}...")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: VALIDATION FAILED")
            print(f"    Summary: {summary}")
            print(f"    Issues:")
            if not validation["starts_with_i"]:
                print(f"      - Does not start with 'I' or 'I'm'")
            if not validation["has_first_person"]:
                print(f"      - Missing first-person pronouns")
            if not validation["no_third_person"]:
                print(f"      - Contains third-person references")
            if not validation["length_ok"]:
                print(f"      - Token count {validation['token_count']} exceeds 100")
            failed += 1

        results.append((persona_name, validation))

    print(f"\n  Result: {passed}/{passed+failed} personas passed comprehensive validation")

    # Summary table
    print("\n  Detailed Results:")
    print("  " + "-" * 80)
    print(f"  {'Persona':<20} {'Start I':<10} {'1st Person':<12} {'No 3rd':<10} {'Length':<10} {'Valid':<8}")
    print("  " + "-" * 80)

    for persona_name, validation in results:
        print(f"  {persona_name[:20]:<20} "
              f"{'✓' if validation['starts_with_i'] else '✗':<10} "
              f"{'✓' if validation['has_first_person'] else '✗':<12} "
              f"{'✓' if validation['no_third_person'] else '✗':<10} "
              f"{validation['token_count']:<10} "
              f"{'✓' if validation['valid'] else '✗':<8}")

    return failed == 0


def test_cached_summaries_first_person():
    """Test 7: Cached summaries from get_or_build_cv_summary are first-person."""
    print("\n[Test 7] Cached CV summaries are first-person")

    cards = _load_all_cards_cached()
    if not cards:
        print("  ❌ FAIL: No persona cards found")
        return False

    passed = 0
    failed = 0

    for card in cards:
        persona_key = card.get("key")
        persona_name = card.get("display_name") or persona_key or "Unknown"

        # Get or build summary (uses cache)
        result = get_or_build_cv_summary(persona_key)
        summary = result.get("summary", "")

        validation = validate_first_person(summary, persona_name)

        if validation["valid"]:
            print(f"  ✓ {persona_name}")
            passed += 1
        else:
            print(f"  ✗ {persona_name}: Cached summary not first-person")
            print(f"    Summary: {summary}")
            failed += 1

    print(f"\n  Result: {passed}/{passed+failed} personas passed")
    return failed == 0


def run_all_tests():
    """Run all unit tests."""
    print("=" * 80)
    print("FIRST-PERSON CV SUMMARY UNIT TESTS")
    print("=" * 80)

    tests = [
        ("CV summaries start with 'I' or 'I'm'", test_cv_summary_first_person_format),
        ("CV summaries contain first-person pronouns", test_cv_summary_has_first_person_pronouns),
        ("CV summaries do NOT contain third-person references", test_cv_summary_no_third_person),
        ("CV summaries are <= 100 tokens", test_cv_summary_length),
        ("CV summaries are coherent", test_cv_summary_coherence),
        ("Comprehensive validation for all personas", test_all_personas_comprehensive),
        ("Cached CV summaries are first-person", test_cached_summaries_first_person),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"\n✅ PASSED: {test_name}")
            else:
                failed += 1
                print(f"\n❌ FAILED: {test_name}")
        except Exception as e:
            failed += 1
            print(f"\n❌ ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"FINAL RESULTS: {passed}/{passed+failed} tests passed")
    print("=" * 80)

    if failed == 0:
        print("\n🎉 SUCCESS! All first-person CV summary tests PASSED!")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) FAILED. Review output above for details.")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
