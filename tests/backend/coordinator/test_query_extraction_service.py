# tests/backend/coordinator/test_query_extraction_service.py
"""Unit tests for QueryExtractionService — all branches."""
from __future__ import annotations

import pytest

from src.coordinator.services.query_extraction_service import QueryExtractionService


class TestExtractLatestUserMessage:
    """Tests for QueryExtractionService.extract_latest_user_message."""

    # ------------------------------------------------------------------
    # Happy-path: "User: " prefix present
    # ------------------------------------------------------------------

    def test_single_user_line(self):
        convo = "User: Hello world"
        assert QueryExtractionService.extract_latest_user_message(convo) == "Hello world"

    def test_strips_surrounding_whitespace(self):
        convo = "User:   spaces around   "
        result = QueryExtractionService.extract_latest_user_message(convo)
        assert result == "spaces around"

    def test_returns_last_user_message(self):
        convo = (
            "User: First question\n\n"
            "Assistant: Some answer\n\n"
            "User: Second question"
        )
        assert QueryExtractionService.extract_latest_user_message(convo) == "Second question"

    def test_multiple_exchanges(self):
        convo = (
            "User: A\n\nAssistant: B\n\nUser: C\n\nAssistant: D\n\nUser: Final"
        )
        assert QueryExtractionService.extract_latest_user_message(convo) == "Final"

    def test_user_line_with_colon_in_message(self):
        """Message itself contains a colon — only 'User: ' prefix stripped."""
        convo = "User: What is 2:30 PM?"
        assert QueryExtractionService.extract_latest_user_message(convo) == "What is 2:30 PM?"

    def test_line_with_leading_spaces_before_user(self):
        """Line.strip() normalises indent before prefix check."""
        convo = "   User: Indented message"
        assert QueryExtractionService.extract_latest_user_message(convo) == "Indented message"

    def test_assistant_line_not_mistaken_for_user(self):
        """Lines starting with 'Assistant:' are ignored."""
        convo = "Assistant: I am not the user\n\nUser: I am the user"
        assert QueryExtractionService.extract_latest_user_message(convo) == "I am the user"

    # ------------------------------------------------------------------
    # Fallback: no "User: " prefix
    # ------------------------------------------------------------------

    def test_no_user_prefix_returns_full_conversation(self):
        convo = "Just a bare message with no prefix"
        assert QueryExtractionService.extract_latest_user_message(convo) == convo

    def test_empty_string_fallback(self):
        convo = ""
        result = QueryExtractionService.extract_latest_user_message(convo)
        assert result == convo

    def test_only_assistant_lines_fallback(self):
        convo = "Assistant: Hello\nAssistant: How can I help?"
        result = QueryExtractionService.extract_latest_user_message(convo)
        assert result == convo  # falls back to full convo

    def test_user_lowercase_not_matched(self):
        """'user: ' (lowercase) is NOT a valid prefix — falls back."""
        convo = "user: lowercase prefix"
        # The code checks startswith("User: ") — exact case match
        result = QueryExtractionService.extract_latest_user_message(convo)
        assert result == convo
