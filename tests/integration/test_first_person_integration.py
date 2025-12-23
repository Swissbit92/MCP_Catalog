#!/usr/bin/env python3
"""
Integration tests for first-person persona responses.

Tests that personas maintain first-person voice across various queries,
including adversarial "trick questions" designed to induce third-person responses.

REQUIREMENTS:
- Backend must be running on http://localhost:8000
- Ollama must be running with the persona model available

Usage:
    # Start backend first
    uvicorn src.coordinator.server:app --reload --port 8000

    # Then run tests
    python test_first_person_integration.py
"""

import requests
import re
from typing import Dict, List, Tuple
import sys


BASE_URL = "http://localhost:8000"


def validate_response_first_person(response: str, persona_name: str) -> Tuple[bool, str]:
    """
    Validate that response is in first person.

    Args:
        response: LLM response text
        persona_name: Name of the persona

    Returns:
        Tuple of (is_valid, reason)
        - is_valid: True if response is first-person, False otherwise
        - reason: Explanation of validation result
    """
    response_lower = response.lower()
    first_name = persona_name.split(" — ")[0].strip().split()[0].lower()

    # Check 1: Contains first-person pronouns
    first_person_pronouns = [" i ", " my ", " me ", " i'm ", " i've ", " i'll ", " myself ", " i'd "]
    has_first_person = any(pronoun in response_lower for pronoun in first_person_pronouns)
    # Also check beginning
    has_first_person = has_first_person or response_lower.startswith(("i ", "i'm ", "i've ", "i'll ", "i'd ", "hey", "yo", "hello"))

    # Check 2: Does NOT contain third-person patterns
    # Allow "I'm Eeva" but block "Eeva is", "Eeva has", etc.

    # First, check for first-person self-introduction patterns
    # These should NOT be flagged as third-person
    has_first_person_intro = any(pattern in response_lower for pattern in [
        f"i'm {first_name},",
        f"i am {first_name},",
        f"i'm {first_name} and",
        f"i am {first_name} and",
        f"i'm {first_name}.",
        f"i am {first_name}.",
        f"call me {first_name}",
        f"my name is {first_name}",
        f"they call me {first_name}",
    ])

    # Third-person patterns to detect
    third_person_patterns = [
        f"{first_name} is a ",
        f"{first_name} is an ",
        f"{first_name} has ",
        f"{first_name} was ",
        f"{first_name} specializes ",
        f"{first_name} believes ",
        f"{first_name} works ",
        f"{first_name}'s ",
        f"about {first_name}",
    ]

    # Only check "{name}, a/an" patterns if NOT preceded by "I am/I'm"
    if not has_first_person_intro:
        third_person_patterns.extend([
            f"{first_name}, a ",
            f"{first_name}, an ",
        ])

    # Find third-person violations
    violations = [pattern for pattern in third_person_patterns if pattern in response_lower]

    # Additional filter: if response starts with "I am {name}" or "I'm {name}",
    # ignore violations in the same sentence (they're part of self-introduction)
    if has_first_person_intro:
        # Allow descriptive clauses after first-person introduction
        # e.g., "I'm Eeva, a crypto enthusiast" is valid first-person
        # Only flag if the pattern appears WITHOUT the first-person framing
        intro_patterns = [f"i'm {first_name}", f"i am {first_name}"]
        for intro in intro_patterns:
            if intro in response_lower:
                # Find where the introduction ends (usually at period or newline)
                intro_start = response_lower.find(intro)
                intro_end = response_lower.find(".", intro_start)
                if intro_end == -1:
                    intro_end = response_lower.find("\n", intro_start)
                if intro_end == -1:
                    intro_end = len(response_lower)

                # Filter out violations that occur within the introduction sentence
                violations = [v for v in violations
                             if response_lower.find(v) < intro_start
                             or response_lower.find(v) > intro_end]
                break

    has_third_person = len(violations) > 0

    # Validation logic
    if has_third_person:
        return False, f"Third-person reference found: {violations[0]}"
    elif not has_first_person:
        return False, "No first-person pronouns found (may be a very short response)"
    else:
        return True, "Valid first-person response"


def send_chat_message(persona: str, message: str) -> str:
    """Send a chat message to the backend and return the response."""
    try:
        response = requests.post(
            f"{BASE_URL}/persona/chat",
            json={
                "persona": persona,
                "message": message,
                "history": []
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        # API uses "answer" key, not "response"
        return data.get("answer", "")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return ""


def test_category_1_direct_identity():
    """
    Category 1: Direct Identity Questions (Easy - Baseline)

    These are straightforward "who are you" questions that should
    consistently get first-person responses.
    """
    print("\n" + "=" * 80)
    print("CATEGORY 1: Direct Identity Questions (Baseline)")
    print("=" * 80)

    queries = [
        "Who are you?",
        "Tell me about yourself",
        "What's your name?",
        "Introduce yourself"
    ]

    personas = ["Eeva", "Frieren", "Gojo"]

    passed = 0
    failed = 0

    for persona in personas:
        print(f"\n[Testing Persona: {persona}]")
        for query in queries:
            print(f"\n  Query: \"{query}\"")
            response = send_chat_message(persona, query)

            if not response:
                print(f"    ✗ FAILED: No response received")
                failed += 1
                continue

            is_valid, reason = validate_response_first_person(response, persona)

            if is_valid:
                print(f"    ✓ PASSED: {reason}")
                print(f"    Response preview: {response[:100]}...")
                passed += 1
            else:
                print(f"    ✗ FAILED: {reason}")
                print(f"    Full response: {response}")
                failed += 1

    total = passed + failed
    print(f"\n{'='*80}")
    print(f"Category 1 Results: {passed}/{total} passed ({100*passed//total if total > 0 else 0}%)")
    print(f"{'='*80}")

    return passed, failed


def test_category_2_background_history():
    """
    Category 2: Background/History Questions (Medium)

    These ask about the persona's background, which might tempt
    the LLM to narrate in third person.
    """
    print("\n" + "=" * 80)
    print("CATEGORY 2: Background/History Questions")
    print("=" * 80)

    test_cases = [
        ("Eeva", [
            "What's your background?",
            "Where did you come from?",
            "Tell me your story",
            "What's your history with Bitcoin?"
        ]),
        ("Frieren", [
            "What's your background?",
            "Where did you come from?",
            "Tell me your story",
            "How did you become a mage?"
        ]),
        ("Gojo", [
            "What's your background?",
            "Where did you come from?",
            "Tell me your story",
            "What's your origin story?"
        ])
    ]

    passed = 0
    failed = 0

    for persona, queries in test_cases:
        print(f"\n[Testing Persona: {persona}]")
        for query in queries:
            print(f"\n  Query: \"{query}\"")
            response = send_chat_message(persona, query)

            if not response:
                print(f"    ✗ FAILED: No response received")
                failed += 1
                continue

            is_valid, reason = validate_response_first_person(response, persona)

            if is_valid:
                print(f"    ✓ PASSED: {reason}")
                print(f"    Response preview: {response[:100]}...")
                passed += 1
            else:
                print(f"    ✗ FAILED: {reason}")
                print(f"    Full response: {response}")
                failed += 1

    total = passed + failed
    print(f"\n{'='*80}")
    print(f"Category 2 Results: {passed}/{total} passed ({100*passed//total if total > 0 else 0}%)")
    print(f"{'='*80}")

    return passed, failed


def test_category_3_capability_expertise():
    """
    Category 3: Capability/Expertise Questions (Medium-Hard)

    Questions about what the persona can do, which might trigger
    assistant-mode responses.
    """
    print("\n" + "=" * 80)
    print("CATEGORY 3: Capability/Expertise Questions")
    print("=" * 80)

    queries = [
        "What are you good at?",
        "What can you help me with?",
        "What's your expertise?",
        "What are your strengths?",
        "What do you specialize in?"
    ]

    personas = ["Eeva", "Frieren", "Gojo"]

    passed = 0
    failed = 0

    for persona in personas:
        print(f"\n[Testing Persona: {persona}]")
        for query in queries:
            print(f"\n  Query: \"{query}\"")
            response = send_chat_message(persona, query)

            if not response:
                print(f"    ✗ FAILED: No response received")
                failed += 1
                continue

            is_valid, reason = validate_response_first_person(response, persona)

            if is_valid:
                print(f"    ✓ PASSED: {reason}")
                print(f"    Response preview: {response[:100]}...")
                passed += 1
            else:
                print(f"    ✗ FAILED: {reason}")
                print(f"    Full response: {response}")
                failed += 1

    total = passed + failed
    print(f"\n{'='*80}")
    print(f"Category 3 Results: {passed}/{total} passed ({100*passed//total if total > 0 else 0}%)")
    print(f"{'='*80}")

    return passed, failed


def test_category_4_third_person_traps():
    """
    Category 4: Third-Person Trap Questions (Hard)

    These questions explicitly ask the persona to describe themselves,
    which is a strong trigger for third-person responses.
    """
    print("\n" + "=" * 80)
    print("CATEGORY 4: Third-Person Trap Questions (ADVERSARIAL)")
    print("=" * 80)

    test_cases = [
        ("Eeva", [
            "Describe Eeva to me",
            "What would people say about you?",
            "If I asked someone else about you, what would they say?",
            "How would others describe your personality?"
        ]),
        ("Frieren", [
            "Describe Frieren to me",
            "What would people say about you?",
            "If I asked someone else about you, what would they say?",
            "How would others describe your personality?"
        ]),
        ("Gojo", [
            "Describe Gojo to me",
            "What's the reputation of Gojo Satoru?",
            "If I asked someone else about you, what would they say?",
            "How would others describe your personality?"
        ])
    ]

    passed = 0
    failed = 0

    for persona, queries in test_cases:
        print(f"\n[Testing Persona: {persona}]")
        for query in queries:
            print(f"\n  Query: \"{query}\" (ADVERSARIAL - expects first-person response)")
            response = send_chat_message(persona, query)

            if not response:
                print(f"    ✗ FAILED: No response received")
                failed += 1
                continue

            is_valid, reason = validate_response_first_person(response, persona)

            if is_valid:
                print(f"    ✓ PASSED: {reason}")
                print(f"    Response preview: {response[:150]}...")
                passed += 1
            else:
                print(f"    ✗ FAILED: {reason}")
                print(f"    Full response: {response}")
                failed += 1

    total = passed + failed
    print(f"\n{'='*80}")
    print(f"Category 4 Results: {passed}/{total} passed ({100*passed//total if total > 0 else 0}%)")
    print(f"{'='*80}")

    return passed, failed


def test_category_5_role_confusion():
    """
    Category 5: Role Confusion Questions (Very Hard)

    Questions that try to confuse the persona about whether they ARE
    the character or are PLAYING the character.
    """
    print("\n" + "=" * 80)
    print("CATEGORY 5: Role Confusion Questions (VERY HARD)")
    print("=" * 80)

    test_cases = [
        ("Eeva", [
            "Are you an AI assistant named Eeva or the actual Eeva?",
            "What's the difference between you and Eeva?",
            "Who is Eeva in this system?",
        ]),
        ("Frieren", [
            "Are you an AI assistant named Frieren or the actual Frieren?",
            "What's the difference between you and Frieren?",
            "Who is Frieren in this system?",
        ]),
        ("Gojo", [
            "Are you an AI assistant named Gojo or the actual Gojo Satoru?",
            "What's the difference between you and Gojo?",
            "Who is Gojo in this system?",
        ])
    ]

    passed = 0
    failed = 0

    for persona, queries in test_cases:
        print(f"\n[Testing Persona: {persona}]")
        for query in queries:
            print(f"\n  Query: \"{query}\" (VERY HARD - tests character commitment)")
            response = send_chat_message(persona, query)

            if not response:
                print(f"    ✗ FAILED: No response received")
                failed += 1
                continue

            is_valid, reason = validate_response_first_person(response, persona)

            if is_valid:
                print(f"    ✓ PASSED: {reason}")
                print(f"    Response preview: {response[:150]}...")
                passed += 1
            else:
                print(f"    ✗ FAILED: {reason}")
                print(f"    Full response: {response}")
                failed += 1

    total = passed + failed
    print(f"\n{'='*80}")
    print(f"Category 5 Results: {passed}/{total} passed ({100*passed//total if total > 0 else 0}%)")
    print(f"{'='*80}")

    return passed, failed


def run_all_tests():
    """Run all integration test categories."""
    print("\n" + "=" * 80)
    print("FIRST-PERSON PERSONA INTEGRATION TESTS")
    print("Testing personas across 5 difficulty categories with 30+ queries")
    print("=" * 80)

    # Check backend availability
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"\n✓ Backend is running: {response.status_code}")
    except Exception as e:
        print(f"\n❌ ERROR: Backend not available at {BASE_URL}")
        print(f"   Please start backend first: uvicorn src.coordinator.server:app --reload --port 8000")
        print(f"   Error: {e}")
        return False

    # Run all test categories
    test_categories = [
        ("Category 1: Direct Identity (Easy)", test_category_1_direct_identity),
        ("Category 2: Background/History (Medium)", test_category_2_background_history),
        ("Category 3: Capability/Expertise (Medium-Hard)", test_category_3_capability_expertise),
        ("Category 4: Third-Person Traps (Hard)", test_category_4_third_person_traps),
        ("Category 5: Role Confusion (Very Hard)", test_category_5_role_confusion),
    ]

    total_passed = 0
    total_failed = 0
    category_results = []

    for category_name, test_func in test_categories:
        print(f"\n{'='*80}")
        print(f"Running: {category_name}")
        print(f"{'='*80}")

        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
            category_results.append((category_name, passed, failed))
        except Exception as e:
            print(f"\n❌ ERROR in {category_name}: {e}")
            import traceback
            traceback.print_exc()
            category_results.append((category_name, 0, 1))
            total_failed += 1

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    total = total_passed + total_failed
    percentage = (100 * total_passed // total) if total > 0 else 0

    print(f"\nOverall Results: {total_passed}/{total} queries passed ({percentage}%)\n")

    print("Breakdown by Category:")
    print("-" * 80)
    for category_name, passed, failed in category_results:
        cat_total = passed + failed
        cat_pct = (100 * passed // cat_total) if cat_total > 0 else 0
        status = "✓" if cat_pct >= 90 else "⚠" if cat_pct >= 75 else "✗"
        print(f"{status} {category_name:<50} {passed}/{cat_total} ({cat_pct}%)")

    print("-" * 80)

    # Grading
    if percentage >= 95:
        grade = "A (Excellent)"
        status = "✅ PASSED"
    elif percentage >= 90:
        grade = "A- (Very Good)"
        status = "✅ PASSED"
    elif percentage >= 85:
        grade = "B+ (Good)"
        status = "⚠️ ACCEPTABLE"
    elif percentage >= 80:
        grade = "B (Acceptable)"
        status = "⚠️ ACCEPTABLE"
    else:
        grade = "C or lower (Needs Improvement)"
        status = "❌ FAILED"

    print(f"\nGrade: {grade}")
    print(f"Status: {status}")

    if percentage >= 90:
        print("\n🎉 SUCCESS! Personas maintain first-person voice across adversarial queries!")
    elif percentage >= 75:
        print("\n⚠️ Partial success. Some queries still trigger third-person responses.")
        print("   Review failed cases above for improvement opportunities.")
    else:
        print("\n❌ First-person enforcement needs improvement.")
        print("   Many queries still trigger third-person responses.")

    print("=" * 80)

    return percentage >= 90


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
