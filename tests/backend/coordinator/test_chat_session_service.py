# tests/backend/coordinator/test_chat_session_service.py
"""
Unit tests for ChatSessionService - Session-based chat orchestration.

Tests cover:
- Session loading and validation
- Dependency orchestration
- Error handling for missing sessions
- Integration with memory systems
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from src.coordinator.services.chat_session_service import handle_session_chat


class TestHandleSessionChat:
    """Test session chat orchestration."""

    def test_session_not_found_raises_404(self):
        """Test that missing session raises 404."""
        # Setup mocks
        session_repo = Mock()
        session_repo.get_persona_key.return_value = None  # Session not found

        deps = {"session_repo": session_repo}

        # Should raise HTTPException 404
        with pytest.raises(HTTPException) as exc_info:
            handle_session_chat(
                session_id="nonexistent",
                message="Test message",
                deps=deps,
                chat_function=Mock(),
                add_message_function=Mock()
            )

        assert exc_info.value.status_code == 404
        assert "Session not found" in str(exc_info.value.detail)

    @patch("src.coordinator.services.chat_session_service.get_persona_card")
    @patch("src.coordinator.services.chat_session_service.build_system_prompt")
    @patch("src.coordinator.services.chat_session_service.estimate_tokens")
    @patch("src.coordinator.services.chat_session_service.get_model_context_window")
    def test_successful_chat_flow(
        self,
        mock_get_window,
        mock_estimate_tokens,
        mock_build_prompt,
        mock_get_card
    ):
        """Test successful chat flow with all dependencies."""
        # Setup mocks
        mock_get_window.return_value = 4096
        mock_estimate_tokens.return_value = 100
        mock_build_prompt.return_value = "System prompt"
        mock_get_card.return_value = {"display_name": "Eeva"}

        # Repository mocks
        session_repo = Mock()
        session_repo.get_persona_key.return_value = "eeva"

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = []

        summary_repo = Mock()
        summary_repo.get_summaries_by_session.return_value = []

        emotional_state_repo = Mock()
        emotional_state = Mock()
        emotional_state.to_prompt_context.return_value = "Emotional context"
        emotional_state.trust_level = 0.5
        emotional_state.current_mood = "neutral"
        emotional_state_repo.get_or_create.return_value = emotional_state

        user_profile_repo = Mock()
        user_profile_repo.get_session_user.return_value = None  # No user profile

        episodic_memory_rag = Mock()
        episodic_memory_rag.search_relevant_memories.return_value = []

        memory_manager = Mock()
        memory_manager.select_messages.return_value = []

        fact_extractor = Mock()

        # Chat function mock
        chat_function = Mock()
        chat_function.return_value = {
            "answer": "Test response",
            "latency_ms": 500,
            "message_flow": "single"
        }

        add_message_function = Mock()

        deps = {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "emotional_state_repo": emotional_state_repo,
            "memory_manager": memory_manager,
            "user_profile_repo": user_profile_repo,
            "episodic_memory_rag": episodic_memory_rag,
            "fact_extractor": fact_extractor,
            "conversation_summarizer": Mock()  # For check_and_summarize
        }

        # Execute
        result = handle_session_chat(
            session_id="session123",
            message="Hello",
            deps=deps,
            chat_function=chat_function,
            add_message_function=add_message_function
        )

        # Verify key functions were called
        session_repo.get_persona_key.assert_called_once_with("session123")
        emotional_state_repo.get_or_create.assert_called_once_with("session123")
        memory_manager.select_messages.assert_called_once()
        chat_function.assert_called_once()

        # Verify result structure
        assert "answer" in result
        assert result["answer"] == "Test response"

    @patch("src.coordinator.services.chat_session_service.get_persona_card")
    @patch("src.coordinator.services.chat_session_service.build_system_prompt")
    @patch("src.coordinator.services.chat_session_service.estimate_tokens")
    @patch("src.coordinator.services.chat_session_service.get_model_context_window")
    def test_chat_with_user_profile(
        self,
        mock_get_window,
        mock_estimate_tokens,
        mock_build_prompt,
        mock_get_card
    ):
        """Test chat flow with user profile (cross-session memory)."""
        # Setup mocks
        mock_get_window.return_value = 4096
        mock_estimate_tokens.return_value = 100
        mock_build_prompt.return_value = "System prompt"
        mock_get_card.return_value = {"display_name": "Eeva"}

        # User profile mock
        user_profile = Mock()
        user_profile.get_context_summary.return_value = "User profile context"

        user_profile_repo = Mock()
        user_profile_repo.get_session_user.return_value = "user123"
        user_profile_repo.get_profile.return_value = user_profile

        # Other mocks (minimal)
        session_repo = Mock()
        session_repo.get_persona_key.return_value = "eeva"

        message_repo = Mock()
        message_repo.get_messages_by_session.return_value = []

        summary_repo = Mock()
        summary_repo.get_summaries_by_session.return_value = []

        emotional_state_repo = Mock()
        emotional_state = Mock()
        emotional_state.to_prompt_context.return_value = ""
        emotional_state.trust_level = 0.5
        emotional_state.current_mood = "neutral"
        emotional_state_repo.get_or_create.return_value = emotional_state

        episodic_memory_rag = Mock()
        episodic_memory_rag.search_relevant_memories.return_value = []

        memory_manager = Mock()
        memory_manager.select_messages.return_value = []

        chat_function = Mock()
        chat_function.return_value = {
            "answer": "Response",
            "latency_ms": 500,
            "message_flow": "single"
        }

        add_message_function = Mock()

        deps = {
            "session_repo": session_repo,
            "message_repo": message_repo,
            "summary_repo": summary_repo,
            "emotional_state_repo": emotional_state_repo,
            "memory_manager": memory_manager,
            "user_profile_repo": user_profile_repo,
            "episodic_memory_rag": episodic_memory_rag,
            "fact_extractor": Mock(),
            "conversation_summarizer": Mock()
        }

        # Execute
        result = handle_session_chat(
            session_id="session123",
            message="Hello",
            deps=deps,
            chat_function=chat_function,
            add_message_function=add_message_function
        )

        # Verify user profile was loaded
        user_profile_repo.get_session_user.assert_called_once_with("session123")
        user_profile_repo.get_profile.assert_called_once_with("user123")
        user_profile.get_context_summary.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
