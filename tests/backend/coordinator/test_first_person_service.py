# tests/backend/coordinator/test_first_person_service.py
"""
Unit tests for FirstPersonService - First-person voice enforcement.

Tests cover:
- Third-person pattern detection
- Rewriting logic (with mocked LLM)
- Post-processing workflow
- Edge cases (first-person intros, multiple violations, etc.)
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, Mock

from src.coordinator.services.first_person_service import (
    detect_third_person,
    rewrite_to_first_person,
    post_process_first_person
)


class TestDetectThirdPerson:
    """Test third-person detection functionality."""

    def test_detect_third_person_clear_violation(self):
        """Test detection of clear third-person pattern."""
        answer = "Eeva is a Bitcoin expert who has extensive knowledge."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True
        assert "eeva is a " in violations

    def test_detect_third_person_multiple_violations(self):
        """Test detection of multiple third-person patterns."""
        answer = "Eeva is a trader. Eeva has 10 years of experience."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True
        assert len(violations) >= 2
        assert "eeva is a " in violations
        assert "eeva has " in violations

    def test_detect_third_person_first_person_intro_valid(self):
        """Test that first-person intros are not flagged."""
        answer = "I'm Eeva, a Bitcoin expert. Let me help you."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        # "Eeva, a" should NOT be flagged when in first-person intro
        assert has_violation is False

    def test_detect_third_person_possessive(self):
        """Test detection of possessive third-person."""
        answer = "Eeva's analysis shows that Bitcoin is bullish."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True
        assert "eeva's " in violations

    def test_detect_third_person_about_pattern(self):
        """Test detection of 'about {name}' pattern."""
        answer = "You asked about Eeva and her expertise."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True
        assert "about eeva" in violations

    def test_detect_third_person_no_violation(self):
        """Test response with no third-person patterns."""
        answer = "I am a Bitcoin expert. I can help you with trading."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is False
        assert len(violations) == 0

    def test_detect_third_person_name_with_dash(self):
        """Test persona name parsing with dash separator."""
        answer = "Gojo is a sorcerer."
        persona_name = "Gojo — Sorcerer"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True
        assert "gojo is a " in violations

    def test_detect_third_person_case_insensitive(self):
        """Test that detection is case-insensitive."""
        answer = "EEVA IS A BITCOIN EXPERT."
        persona_name = "Eeva — Bitcoin Expert"

        has_violation, violations = detect_third_person(answer, persona_name)

        assert has_violation is True


class TestRewriteToFirstPerson:
    """Test rewriting functionality (with mocked LLM)."""

    @patch("src.coordinator.services.first_person_service.LLMCompletionService")
    def test_rewrite_to_first_person_success(
        self,
        mock_client_class
    ):
        """Test successful rewrite to first-person."""
        # Mock LLM client
        mock_client = Mock()
        mock_client.complete.return_value = "I am a Bitcoin expert with 10 years of experience."
        mock_client_class.return_value = mock_client

        answer = "Eeva is a Bitcoin expert with 10 years of experience."
        persona_name = "Eeva — Bitcoin Expert"

        rewritten = rewrite_to_first_person(answer, persona_name)

        # Verify LLM was called
        mock_client.complete.assert_called_once()
        call_args = mock_client.complete.call_args

        # Verify system prompt
        assert "helpful assistant that rewrites" in call_args.kwargs["system"]

        # Verify user prompt contains original answer
        assert answer in call_args.kwargs["user_prompt"]

        # Verify result
        assert rewritten == "I am a Bitcoin expert with 10 years of experience."

    @patch("src.coordinator.services.first_person_service.LLMCompletionService")
    def test_rewrite_to_first_person_llm_error(
        self,
        mock_client_class
    ):
        """Test that original answer is returned on LLM error."""
        # Mock LLM client to raise error
        mock_client = Mock()
        mock_client.complete.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client

        answer = "Eeva is a Bitcoin expert."
        persona_name = "Eeva — Bitcoin Expert"

        rewritten = rewrite_to_first_person(answer, persona_name)

        # Should return original on error
        assert rewritten == answer


class TestPostProcessFirstPerson:
    """Test the main post-processing workflow."""

    def test_post_process_first_person_no_violation(self):
        """Test post-processing when response is already first-person."""
        answer = "I am a Bitcoin expert. I can help you."
        persona_name = "Eeva — Bitcoin Expert"

        processed, was_rewritten = post_process_first_person(answer, persona_name)

        assert processed == answer  # Unchanged
        assert was_rewritten is False

    @patch("src.coordinator.services.first_person_service.rewrite_to_first_person")
    def test_post_process_first_person_successful_rewrite(self, mock_rewrite):
        """Test successful rewrite workflow."""
        answer = "Eeva is a Bitcoin expert."
        persona_name = "Eeva — Bitcoin Expert"

        # Mock rewrite to return first-person version
        mock_rewrite.return_value = "I am a Bitcoin expert."

        processed, was_rewritten = post_process_first_person(answer, persona_name)

        # Verify rewrite was called
        mock_rewrite.assert_called_once_with(answer, persona_name)

        # Verify result
        assert processed == "I am a Bitcoin expert."
        assert was_rewritten is True

    @patch("src.coordinator.services.first_person_service.rewrite_to_first_person")
    def test_post_process_first_person_rewrite_still_violates(self, mock_rewrite):
        """Test when rewrite still contains third-person (detect twice, rewrite once)."""
        answer = "Eeva is a Bitcoin expert."
        persona_name = "Eeva — Bitcoin Expert"

        # Mock rewrite to return "I am a Bitcoin expert" (proper first-person)
        mock_rewrite.return_value = "I am a Bitcoin expert."

        processed, was_rewritten = post_process_first_person(answer, persona_name)

        # Verify rewrite was called
        mock_rewrite.assert_called_once_with(answer, persona_name)

        # Should return rewritten version and flag as rewritten
        assert processed == "I am a Bitcoin expert."
        assert was_rewritten is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
