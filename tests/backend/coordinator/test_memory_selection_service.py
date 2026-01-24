# tests/backend/coordinator/test_memory_selection_service.py
"""
Unit tests for MemorySelectionService - Memory selection and summarization.

Tests cover:
- Summarization triggering logic
- Interval-based summarization
- Error handling
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.coordinator.services.memory_selection_service import check_and_summarize


class TestCheckAndSummarize:
    """Test summarization checking and triggering."""

    @patch("src.coordinator.services.memory_selection_service.get_summarization_interval")
    @patch("src.coordinator.services.memory_selection_service.get_persona_card")
    def test_no_summarization_needed(self, mock_get_card, mock_get_interval):
        """Test that no summarization happens when not needed."""
        # Setup mocks
        mock_get_interval.return_value = 30

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = ["msg1", "msg2"]  # Only 2 messages

        summary_repo = Mock()
        summary_repo.count_summaries.return_value = 0  # No summaries yet

        conversation_summarizer = Mock()

        deps = {
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "conversation_summarizer": conversation_summarizer
        }

        # Call function
        check_and_summarize("session123", "eeva", deps)

        # Verify summarizer was NOT called (only 2 messages, need 30)
        conversation_summarizer.summarize_segment.assert_not_called()

    @patch("src.coordinator.services.memory_selection_service.get_summarization_interval")
    @patch("src.coordinator.services.memory_selection_service.get_persona_card")
    @patch("src.coordinator.services.memory_selection_service.get_ollama_base")
    @patch("src.coordinator.services.memory_selection_service.get_persona_model")
    @patch("src.coordinator.services.memory_selection_service.get_temp_summarization")
    @patch("src.coordinator.services.memory_selection_service.LC_OllamaClient")
    def test_summarization_triggered(
        self,
        mock_client_class,
        mock_get_temp,
        mock_get_model,
        mock_get_base,
        mock_get_card,
        mock_get_interval
    ):
        """Test that summarization is triggered when interval reached."""
        # Setup mocks
        mock_get_interval.return_value = 10  # Interval of 10
        mock_get_card.return_value = {"display_name": "Eeva — Bitcoin Expert"}
        mock_get_base.return_value = "http://localhost:11434"
        mock_get_model.return_value = "llama3.1:latest"
        mock_get_temp.return_value = 0.3

        # Create 10 messages
        messages = [f"msg{i}" for i in range(10)]

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = messages

        summary_repo = Mock()
        summary_repo.count_summaries.return_value = 0  # No summaries yet

        conversation_summarizer = Mock()
        conversation_summarizer.llm_client = None  # Will be set by function
        conversation_summarizer.summarize_segment.return_value = {
            "summary_text": "Test summary",
            "emotional_developments": "Positive",
            "topics_discussed": "Bitcoin",
            "token_count": 50
        }

        deps = {
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "conversation_summarizer": conversation_summarizer
        }

        # Call function
        check_and_summarize("session123", "eeva", deps)

        # Verify summarizer was called
        conversation_summarizer.summarize_segment.assert_called_once()

        # Verify summary was saved
        summary_repo.create_summary.assert_called_once()
        call_kwargs = summary_repo.create_summary.call_args.kwargs

        assert call_kwargs["session_id"] == "session123"
        assert call_kwargs["message_range"] == "1-10"
        assert call_kwargs["summary_text"] == "Test summary"

    @patch("src.coordinator.services.memory_selection_service.get_summarization_interval")
    @patch("src.coordinator.services.memory_selection_service.get_persona_card")
    @patch("src.coordinator.services.memory_selection_service.get_ollama_base")
    @patch("src.coordinator.services.memory_selection_service.get_persona_model")
    @patch("src.coordinator.services.memory_selection_service.get_temp_summarization")
    @patch("src.coordinator.services.memory_selection_service.LC_OllamaClient")
    def test_summarization_with_existing_summaries(
        self,
        mock_client_class,
        mock_get_temp,
        mock_get_model,
        mock_get_base,
        mock_get_card,
        mock_get_interval
    ):
        """Test summarization calculation with existing summaries."""
        # Setup mocks
        mock_get_interval.return_value = 10
        mock_get_card.return_value = {"display_name": "Eeva — Bitcoin Expert"}
        mock_get_base.return_value = "http://localhost:11434"
        mock_get_model.return_value = "llama3.1:latest"
        mock_get_temp.return_value = 0.3

        # 25 messages total (10 already summarized, 15 new)
        messages = [f"msg{i}" for i in range(25)]

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = messages

        summary_repo = Mock()
        summary_repo.count_summaries.return_value = 1  # Already 1 summary (10 messages)

        conversation_summarizer = Mock()
        conversation_summarizer.llm_client = Mock()  # Already set
        conversation_summarizer.summarize_segment.return_value = {
            "summary_text": "Second summary",
            "emotional_developments": "Neutral",
            "topics_discussed": "Trading",
            "token_count": 60
        }

        deps = {
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "conversation_summarizer": conversation_summarizer
        }

        # Call function
        check_and_summarize("session123", "eeva", deps)

        # Verify correct message range was summarized (11-20)
        call_args = conversation_summarizer.summarize_segment.call_args
        messages_arg = call_args.kwargs["messages"]

        # Should summarize messages 10-19 (indices, so messages[10:20])
        assert len(messages_arg) == 10

        # Verify summary range
        summary_call = summary_repo.create_summary.call_args.kwargs
        assert summary_call["message_range"] == "11-20"

    @patch("src.coordinator.services.memory_selection_service.get_summarization_interval")
    @patch("src.coordinator.services.memory_selection_service.get_persona_card")
    def test_summarization_error_handling(self, mock_get_card, mock_get_interval):
        """Test error handling when summarization fails."""
        # Setup mocks
        mock_get_interval.return_value = 10
        mock_get_card.side_effect = Exception("Persona not found")

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = [f"msg{i}" for i in range(10)]

        summary_repo = Mock()
        summary_repo.count_summaries.return_value = 0

        conversation_summarizer = Mock()

        deps = {
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "conversation_summarizer": conversation_summarizer
        }

        # Should not raise exception
        check_and_summarize("session123", "eeva", deps)

        # Verify summary was not created
        summary_repo.create_summary.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
