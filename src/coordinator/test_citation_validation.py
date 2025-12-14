"""
Tests for citation validation in server.py

Run with: python src/coordinator/test_citation_validation.py
"""

import sys
sys.path.insert(0, 'src/coordinator')

from server import validate_citations


def test_valid_citations_with_emoji():
    """Test that valid citations with emoji are accepted"""
    answer = """Bitcoin is trading at $91,735.99, up 3.13% in the last 24 hours.

🔍 Sources:
• [Bitcoin Price Today - CoinMarketCap](https://coinmarketcap.com/currencies/bitcoin/)
• [BTC/USD Market Data - Yahoo Finance](https://finance.yahoo.com/quote/BTC-USD)
"""
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=5)
    
    assert is_valid == True, "Should recognize valid citations with emoji"
    assert details["has_citation_section"] == True
    assert details["has_emoji"] == True
    assert details["citation_count"] == 2
    assert details["has_markdown_links"] == True
    print("✅ test_valid_citations_with_emoji passed")


def test_valid_citations_without_emoji():
    """Test that valid citations without emoji are accepted"""
    answer = """Bitcoin is trading at $91,735.99.

**Sources:**
• [Bitcoin Price Today](https://coinmarketcap.com/)
• [BTC/USD Data](https://finance.yahoo.com/)
"""
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=2)
    
    assert is_valid == True, "Should recognize valid citations without emoji"
    assert details["has_citation_section"] == True
    assert details["citation_count"] == 2
    print("✅ test_valid_citations_without_emoji passed")


def test_missing_citations():
    """Test that missing citations are detected and warning appended"""
    answer = "Bitcoin is trading at around $91,000 according to recent data."
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=5)
    
    assert is_valid == False, "Should detect missing citations"
    assert details["has_citation_section"] == False
    assert "⚠️ Note:" in answer_out, "Should append warning when citations missing"
    assert "5 web source(s)" in answer_out, "Should mention number of sources consulted"
    print("✅ test_missing_citations passed")


def test_no_search_no_validation():
    """Test that non-search responses skip validation"""
    answer = "2 + 2 = 4"
    
    answer_out, is_valid, details = validate_citations(answer, used_search=False, search_results_count=0)
    
    assert is_valid == True, "Should pass validation when no search was used"
    assert answer == answer_out, "Answer should not be modified"
    print("✅ test_no_search_no_validation passed")


def test_markdown_links_without_http():
    """Test that markdown links without HTTP are not accepted"""
    answer = """Bitcoin info:

🔍 Sources:
• [Local File](file:///path/to/file)
• [Relative Link](../data.html)
"""
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=2)
    
    # This should fail because links don't contain http/https
    assert is_valid == False, "Should reject non-HTTP links"
    print("✅ test_markdown_links_without_http passed")


def test_citation_section_without_links():
    """Test that citation section without actual links is detected"""
    answer = """Bitcoin data:

🔍 Sources:
Some sources were consulted but not cited properly.
"""
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=3)
    
    assert is_valid == False, "Should detect citation section without actual links"
    assert details["has_citation_section"] == True
    assert details["has_markdown_links"] == False
    print("✅ test_citation_section_without_links passed")


def test_multiple_sources():
    """Test that multiple sources are counted correctly"""
    answer = """Bitcoin information:

🔍 Sources:
• [Source 1](https://example.com/1)
• [Source 2](https://example.com/2)
• [Source 3](https://example.com/3)
• [Source 4](https://example.com/4)
• [Source 5](https://example.com/5)
"""
    
    answer_out, is_valid, details = validate_citations(answer, used_search=True, search_results_count=5)
    
    assert is_valid == True
    assert details["citation_count"] == 5, f"Expected 5 citations, got {details['citation_count']}"
    print("✅ test_multiple_sources passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Citation Validation Tests")
    print("="*60 + "\n")
    
    tests = [
        test_valid_citations_with_emoji,
        test_valid_citations_without_emoji,
        test_missing_citations,
        test_no_search_no_validation,
        test_markdown_links_without_http,
        test_citation_section_without_links,
        test_multiple_sources
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
