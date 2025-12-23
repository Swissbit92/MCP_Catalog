"""
Standalone citation validation tests

Run with: python tests/backend/coordinator/test_citations_standalone.py
"""

# Import validate_citations from server.py (single source of truth)
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.coordinator.server import validate_citations


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
