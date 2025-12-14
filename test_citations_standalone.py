"""
Standalone citation validation tests

Run with: python test_citations_standalone.py
"""

import re


def validate_citations(answer: str, used_search: bool, search_results_count: int = 0):
    """Citation validation function (copied from server.py for testing)"""
    validation = {
        "has_citation_section": False,
        "has_markdown_links": False,
        "citation_count": 0,
        "has_emoji": False,
        "valid": False
    }

    if not used_search:
        validation["valid"] = True
        return answer, True, validation

    # Check for citation section markers (with or without emoji)
    has_citation_with_emoji = "🔍 Sources:" in answer or "🔍 **Sources:**" in answer
    has_citation_without_emoji = bool(re.search(r'\*\*Sources:\*\*|\nSources:\n', answer))

    validation["has_citation_section"] = has_citation_with_emoji or has_citation_without_emoji
    validation["has_emoji"] = has_citation_with_emoji

    # Check for markdown links [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', answer)
    validation["has_markdown_links"] = len(markdown_links) > 0
    validation["citation_count"] = len(markdown_links)

    # Check if links contain http/https URLs
    has_http_links = any('http' in url for _, url in markdown_links)

    # Valid if: has citation section + has markdown links with URLs
    if validation["has_citation_section"] and validation["has_markdown_links"] and has_http_links:
        validation["valid"] = True
        return answer, True, validation

    # Invalid citations - append reminder if completely missing
    if not validation["has_citation_section"]:
        reminder = f"\n\n⚠️ Note: {search_results_count} web source(s) were consulted but citations were not included in the response."
        answer = answer + reminder

    return answer, False, validation


# Test cases
def test_valid_citations_with_emoji():
    answer = """Bitcoin is trading at $91,735.99.

🔍 Sources:
• [Bitcoin Price](https://coinmarketcap.com/)
• [BTC Data](https://finance.yahoo.com/)
"""
    answer_out, is_valid, details = validate_citations(answer, True, 5)
    assert is_valid == True
    assert details["citation_count"] == 2
    print("✅ test_valid_citations_with_emoji")


def test_missing_citations():
    answer = "Bitcoin is around $91,000."
    answer_out, is_valid, details = validate_citations(answer, True, 5)
    assert is_valid == False
    assert "⚠️ Note:" in answer_out
    print("✅ test_missing_citations")


def test_no_search():
    answer = "2 + 2 = 4"
    answer_out, is_valid, details = validate_citations(answer, False, 0)
    assert is_valid == True
    print("✅ test_no_search")


# Run all tests
print("\n" + "="*60)
print("Citation Validation Tests")
print("="*60)

try:
    test_valid_citations_with_emoji()
    test_missing_citations()
    test_no_search()
    print("\n✅ All tests passed!\n")
except AssertionError as e:
    print(f"\n❌ Test failed: {e}\n")
    exit(1)
