# tests/backend/coordinator/test_citation_service.py
"""
Unit tests for CitationService - Citation generation and validation.

Tests cover:
- Auto-generation of citations from search results
- Stripping hallucinated citations from LLM responses
- Citation validation logic
- Edge cases (empty results, missing fields, etc.)
"""

from __future__ import annotations

import pytest
from src.coordinator.services.citation_service import CitationService, validate_citations


class MockSearchResult:
    """Mock search result for testing."""
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url


class TestCitationService:
    """Test CitationService functionality."""

    def test_auto_generate_citations_with_results(self):
        """Test citation generation with valid search results."""
        results = [
            MockSearchResult("Article 1", "https://example.com/1"),
            MockSearchResult("Article 2", "https://example.com/2"),
            MockSearchResult("Article 3", "https://example.com/3"),
        ]

        citations = CitationService.auto_generate_citations(results)

        assert "🔍 Sources:" in citations
        assert "https://example.com/1" in citations
        assert "https://example.com/2" in citations
        assert "https://example.com/3" in citations
        assert "[Article 1](https://example.com/1)" in citations
        assert "[Article 2](https://example.com/2)" in citations

    def test_auto_generate_citations_empty_results(self):
        """Test citation generation with empty results."""
        citations = CitationService.auto_generate_citations([])
        assert citations == ""

    def test_auto_generate_citations_limits_to_five(self):
        """Test that citation generation limits to 5 results."""
        results = [
            MockSearchResult(f"Article {i}", f"https://example.com/{i}")
            for i in range(10)
        ]

        citations = CitationService.auto_generate_citations(results)

        # Should only have first 5
        assert "https://example.com/0" in citations
        assert "https://example.com/4" in citations
        # Should not have 6th onwards
        assert "https://example.com/5" not in citations
        assert "https://example.com/9" not in citations

    def test_auto_generate_citations_missing_title(self):
        """Test citation generation with missing title."""
        results = [
            MockSearchResult(None, "https://example.com/1"),
        ]

        citations = CitationService.auto_generate_citations(results)

        assert "🔍 Sources:" in citations
        assert "[Untitled](https://example.com/1)" in citations

    def test_auto_generate_citations_missing_url(self):
        """Test citation generation with missing URL."""
        results = [
            MockSearchResult("Article 1", None),
        ]

        citations = CitationService.auto_generate_citations(results)

        assert "🔍 Sources:" in citations
        assert "[Article 1](#)" in citations

    def test_strip_hallucinated_citations_with_emoji_marker(self):
        """Test stripping citations with emoji marker."""
        response = "Answer to question.\n\n🔍 Sources:\n• [Fake](http://fake.com)"
        clean = CitationService.strip_hallucinated_citations(response)

        assert "🔍 Sources:" not in clean
        assert "http://fake.com" not in clean
        assert "Answer to question." in clean

    def test_strip_hallucinated_citations_with_text_marker(self):
        """Test stripping citations with text marker."""
        response = "Answer to question.\n\nSources:\n• [Fake](http://fake.com)"
        clean = CitationService.strip_hallucinated_citations(response)

        assert "Sources:" not in clean
        assert "http://fake.com" not in clean
        assert "Answer to question." in clean

    def test_strip_hallucinated_citations_with_bold_marker(self):
        """Test stripping citations with bold marker."""
        response = "Answer to question.\n\n**Sources:**\n• [Fake](http://fake.com)"
        clean = CitationService.strip_hallucinated_citations(response)

        assert "**Sources:**" not in clean
        assert "http://fake.com" not in clean
        assert "Answer to question." in clean

    def test_strip_hallucinated_citations_no_citations(self):
        """Test stripping when there are no citations."""
        response = "Answer to question."
        clean = CitationService.strip_hallucinated_citations(response)

        assert clean == "Answer to question."

    def test_validate_citation_urls_all_present(self):
        """Test URL validation when all URLs are present."""
        text = "Text with https://example.com/1 and https://example.com/2"
        expected_urls = ["https://example.com/1", "https://example.com/2"]

        assert CitationService.validate_citation_urls(text, expected_urls) is True

    def test_validate_citation_urls_missing_url(self):
        """Test URL validation when a URL is missing."""
        text = "Text with https://example.com/1"
        expected_urls = ["https://example.com/1", "https://example.com/2"]

        assert CitationService.validate_citation_urls(text, expected_urls) is False

    def test_validate_citation_urls_empty_expected(self):
        """Test URL validation with empty expected URLs."""
        text = "Text with some content"
        expected_urls = []

        assert CitationService.validate_citation_urls(text, expected_urls) is True


class TestValidateCitationsFunction:
    """Test the validate_citations standalone function."""

    def test_validate_citations_search_used_with_citations(self):
        """Test validation when search was used and citations present."""
        answer = "Answer.\n\n🔍 Sources:\n• [Link](http://ex.com)"
        processed, valid, details = validate_citations(answer, used_search=True, search_results_count=3)

        assert valid is True
        assert details["has_citations"] is True
        assert details["search_results_count"] == 3
        assert details["status"] == "valid"
        assert processed == answer  # Unchanged

    def test_validate_citations_search_used_without_citations(self):
        """Test validation when search was used but citations missing."""
        answer = "Answer without citations."
        processed, valid, details = validate_citations(answer, used_search=True, search_results_count=3)

        assert valid is False
        assert details["has_citations"] is False
        assert details["search_results_count"] == 3
        assert details["status"] == "missing"
        assert processed == answer  # Unchanged

    def test_validate_citations_search_not_used_no_citations(self):
        """Test validation when search wasn't used and no citations."""
        answer = "Answer without citations."
        processed, valid, details = validate_citations(answer, used_search=False, search_results_count=0)

        assert valid is True
        assert details["has_citations"] is False
        assert details["search_results_count"] == 0
        assert details["status"] == "valid_no_search"
        assert processed == answer  # Unchanged

    def test_validate_citations_search_not_used_with_hallucinated_citations(self):
        """Test validation when search wasn't used but citations are hallucinated."""
        answer = "Answer.\n\n🔍 Sources:\n• [Fake](http://fake.com)"
        processed, valid, details = validate_citations(answer, used_search=False, search_results_count=0)

        assert valid is False
        assert details["has_citations"] is False
        assert details["search_results_count"] == 0
        assert details["status"] == "hallucinated_removed"
        assert "🔍 Sources:" not in processed  # Citations stripped
        assert "Answer." in processed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
