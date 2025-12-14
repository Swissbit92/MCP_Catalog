# test_synthesis_integration.py
# Integration tests for synthesis prompt fix
# Tests the three problematic scenarios identified in the assessment

import sys
import time
import requests
import json

# Backend URL
BACKEND_URL = "http://localhost:8000"

def test_ethereum_price_no_hallucination():
    """
    Test Issue #1: LLM Hallucination (Wrong Prices)

    Expected: Persona uses web search results, NOT training data
    Previous behavior: Returns $1,850 (training data)
    Fixed behavior: Returns current price from search results (~$3,200-$3,500)
    """
    print("\n" + "="*80)
    print("TEST 1: Ethereum Price - No Hallucination")
    print("="*80)

    query = "What is the current Ethereum price?"
    persona = "eeva"  # Legendary persona with web search access

    print(f"Query: {query}")
    print(f"Persona: {persona}")
    print("\nSending request...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/persona/chat",
            json={
                "persona": persona,
                "message": query,
                "history": []
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"[FAIL] HTTP {response.status_code}: {response.text}")
            return False

        data = response.json()
        answer = data.get("answer", "")
        used_search = data.get("used_search", False)
        citation_valid = data.get("citation_valid", False)

        print(f"\nUsed Search: {used_search}")
        print(f"Citation Valid: {citation_valid}")
        print(f"\nAnswer:\n{answer}\n")

        # Validation checks
        checks_passed = []

        # Check 1: Must use web search
        if used_search:
            checks_passed.append("Used web search")
            print("[PASS] Used web search")
        else:
            print("[FAIL] Did NOT use web search")

        # Check 2: Should NOT contain training data price ($1,850)
        if "$1,850" not in answer and "$1850" not in answer:
            checks_passed.append("No hallucinated price")
            print("[PASS] Does not contain hallucinated price ($1,850)")
        else:
            print("[FAIL] Contains hallucinated price from training data")

        # Check 3: Should have citations
        if citation_valid and "Sources:" in answer:
            checks_passed.append("Valid citations")
            print("[PASS] Has valid citations")
        else:
            print("[WARN] Citations missing or invalid")

        # Check 4: Should have a price (any price)
        has_price = any(char in answer for char in ["$", "€", "£"])
        if has_price:
            checks_passed.append("Contains price")
            print("[PASS] Answer contains price information")
        else:
            print("[FAIL] Answer does not contain price")

        success = len(checks_passed) >= 3  # At least 3/4 checks passed

        print(f"\nChecks passed: {len(checks_passed)}/4")
        print(f"Result: {'[SUCCESS]' if success else '[FAIL]'}")

        return success

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def test_bitcoin_news_synthesis():
    """
    Test Issue #2: Missing Synthesis (Raw Dumps)

    Expected: Natural synthesis combining multiple sources
    Previous behavior: Just lists search result titles
    Fixed behavior: Synthesizes info into cohesive answer
    """
    print("\n" + "="*80)
    print("TEST 2: Bitcoin News - Synthesis Quality")
    print("="*80)

    query = "What's happening with Bitcoin?"
    persona = "eeva"

    print(f"Query: {query}")
    print(f"Persona: {persona}")
    print("\nSending request...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/persona/chat",
            json={
                "persona": persona,
                "message": query,
                "history": []
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"[FAIL] HTTP {response.status_code}: {response.text}")
            return False

        data = response.json()
        answer = data.get("answer", "")
        used_search = data.get("used_search", False)

        print(f"\nUsed Search: {used_search}")
        print(f"\nAnswer:\n{answer}\n")

        # Validation checks
        checks_passed = []

        # Check 1: Must use web search
        if used_search:
            checks_passed.append("Used search")
            print("[PASS] Used web search")

        # Check 2: Should NOT be just raw search result titles
        # Raw dumps have patterns like "Title 1 - Source. Title 2 - Source."
        raw_dump_indicators = [
            "CoinDesk. " in answer and "Forbes. " in answer,  # Multiple source names back-to-back
            answer.count(" - ") > 5 and answer.count(". ") > 5,  # Many title-source patterns
        ]

        if not any(raw_dump_indicators):
            checks_passed.append("Not raw dump")
            print("[PASS] Not a raw dump of search results")
        else:
            print("[FAIL] Appears to be raw dump of search results")

        # Check 3: Should be reasonable length (synthesized answers are usually 50-500 chars)
        main_answer = answer.split("Sources:")[0] if "Sources:" in answer else answer
        if 50 < len(main_answer) < 1000:
            checks_passed.append("Good length")
            print(f"[PASS] Answer length reasonable ({len(main_answer)} chars)")
        else:
            print(f"[WARN] Answer length unusual ({len(main_answer)} chars)")

        # Check 4: Should have persona voice (not generic)
        # Eeva's traits: sarcastic, uses "actually", informal
        persona_indicators = ["actually", "pretty", "though", "honestly", "kinda", "sorta"]
        has_persona_voice = any(word in answer.lower() for word in persona_indicators)

        if has_persona_voice:
            checks_passed.append("Persona voice")
            print("[PASS] Maintains persona voice")
        else:
            print("[WARN] May lack persona voice")

        success = len(checks_passed) >= 3

        print(f"\nChecks passed: {len(checks_passed)}/4")
        print(f"Result: {'[SUCCESS]' if success else '[FAIL]'}")

        return success

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def test_citation_format_bullet_points():
    """
    Test Issue #3: Inconsistent Citation Format

    Expected: Bullet point list (newline + bullet)
    Previous behavior: Inline citations [Source](url)[Source](url)
    Fixed behavior: Each source on new line with bullet
    """
    print("\n" + "="*80)
    print("TEST 3: Citation Format - Bullet Points")
    print("="*80)

    query = "Current Bitcoin price"
    persona = "eeva"

    print(f"Query: {query}")
    print(f"Persona: {persona}")
    print("\nSending request...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/persona/chat",
            json={
                "persona": persona,
                "message": query,
                "history": []
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"[FAIL] HTTP {response.status_code}: {response.text}")
            return False

        data = response.json()
        answer = data.get("answer", "")
        used_search = data.get("used_search", False)
        citation_valid = data.get("citation_valid", False)

        print(f"\nUsed Search: {used_search}")
        print(f"Citation Valid: {citation_valid}")
        print(f"\nAnswer:\n{answer}\n")

        # Validation checks
        checks_passed = []

        # Check 1: Must use web search
        if used_search:
            checks_passed.append("Used search")
            print("[PASS] Used web search")

        # Check 2: Should have "Sources:" section
        if "Sources:" in answer:
            checks_passed.append("Has sources section")
            print("[PASS] Has 'Sources:' section")
        else:
            print("[FAIL] Missing 'Sources:' section")
            return False  # Can't check format if no sources

        # Extract citation section
        citation_section = answer.split("Sources:")[1] if "Sources:" in answer else ""

        # Check 3: Should have bullet points (newline + bullet character)
        # Look for patterns like "\n•" or "\n-" or "\n*"
        has_bullets = "\n" in citation_section and any(c in citation_section for c in ["•", "-", "*"])

        if has_bullets:
            checks_passed.append("Bullet points")
            print("[PASS] Citations use bullet point format")
        else:
            print("[FAIL] Citations NOT in bullet point format")

        # Check 4: Should NOT be inline (multiple sources on same line)
        # Inline pattern: "][" (back-to-back links)
        inline_pattern = "][" in citation_section or "](http" in citation_section and citation_section.count("\n") < 2

        if not inline_pattern:
            checks_passed.append("Not inline")
            print("[PASS] Citations NOT inline (proper formatting)")
        else:
            print("[FAIL] Citations appear to be inline")

        success = len(checks_passed) >= 3

        print(f"\nChecks passed: {len(checks_passed)}/4")
        print(f"Result: {'[SUCCESS]' if success else '[FAIL]'}")

        return success

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    """Run all integration tests."""
    print("="*80)
    print("SYNTHESIS FIX INTEGRATION TESTS")
    print("="*80)
    print("\nTesting Brave MCP synthesis prompt improvements...")
    print("Backend URL:", BACKEND_URL)
    print("\nIMPORTANT: Make sure backend is running with:")
    print("  uvicorn src.coordinator.server:app --reload --port 8000")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    input()

    results = {}

    # Test 1: Ethereum price (hallucination test)
    results["hallucination"] = test_ethereum_price_no_hallucination()
    time.sleep(2)

    # Test 2: Bitcoin news (synthesis test)
    results["synthesis"] = test_bitcoin_news_synthesis()
    time.sleep(2)

    # Test 3: Citation format (bullet points test)
    results["citation_format"] = test_citation_format_bullet_points()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[SUCCESS] All integration tests PASSED!")
        print("Synthesis prompt fix is working correctly.")
        return 0
    else:
        print("\n[WARNING] Some tests failed.")
        print("Review the output above to see which checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
