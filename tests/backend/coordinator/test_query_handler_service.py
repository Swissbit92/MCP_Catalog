# tests/backend/coordinator/test_query_handler_service.py
"""
Unit tests for QueryHandlerService - MCP query handling.

Tests cover:
- Response finalization logic
- MongoDB query handling (mocked)
- Brave query handling (mocked)
- Multi-MCP query handling (mocked)
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.coordinator.services.query_handler_service import QueryHandlerService
from src.coordinator.schemas import ResponseMetadata


class TestFinalizeResponse:
    """Test the _finalize_response method."""

    @patch("src.coordinator.services.message_processing_service.parse_multi_message_response")
    @patch("src.coordinator.services.message_processing_service.force_multi_message_split")
    @patch("src.coordinator.services.first_person_service.post_process_first_person")
    def test_finalize_response_single_message(
        self,
        mock_post_process,
        mock_force_split,
        mock_parse
    ):
        """Test finalizing a single message response."""
        # Setup mocks
        mock_post_process.return_value = ("Finalized answer", False)  # (answer, was_rewritten)
        mock_force_split.return_value = "Finalized answer"
        mock_parse.return_value = (["Finalized answer"], "single")

        service = QueryHandlerService()
        metadata = ResponseMetadata()

        result = service._finalize_response(
            answer="Raw answer",
            persona_name="Eeva — Bitcoin Expert",
            metadata=metadata,
            used_search=False
        )

        # Verify post-processing was called
        mock_post_process.assert_called_once_with("Raw answer", "Eeva — Bitcoin Expert")

        # Verify result structure
        assert result["answer"] == "Finalized answer"
        assert result["message_flow"] == "single"
        assert result["message_count"] == 1
        assert result["used_search"] is False
        assert result["rewritten"] is False
        assert "metadata" in result

    @patch("src.coordinator.services.message_processing_service.parse_multi_message_response")
    @patch("src.coordinator.services.message_processing_service.force_multi_message_split")
    @patch("src.coordinator.services.first_person_service.post_process_first_person")
    def test_finalize_response_multi_message(
        self,
        mock_post_process,
        mock_force_split,
        mock_parse
    ):
        """Test finalizing a multi-message response."""
        # Setup mocks
        mock_post_process.return_value = ("Multi answer", True)  # Was rewritten
        mock_force_split.return_value = "<msg>First</msg>\n<msg>Second</msg>"
        mock_parse.return_value = (["First", "Second"], "multi")

        service = QueryHandlerService()
        metadata = ResponseMetadata()

        result = service._finalize_response(
            answer="Raw answer",
            persona_name="Eeva — Bitcoin Expert",
            metadata=metadata,
            used_search=True,
            citation_valid=True,
            search_results_count=5
        )

        # Verify result structure
        assert result["answer"] == ["First", "Second"]
        assert result["message_flow"] == "multi"
        assert result["message_count"] == 2
        assert result["used_search"] is True
        assert result["rewritten"] is True
        assert result["citation_valid"] is True
        assert result["search_results_count"] == 5

    @patch("src.coordinator.services.message_processing_service.parse_multi_message_response")
    @patch("src.coordinator.services.message_processing_service.force_multi_message_split")
    @patch("src.coordinator.services.first_person_service.post_process_first_person")
    def test_finalize_response_optional_fields(
        self,
        mock_post_process,
        mock_force_split,
        mock_parse
    ):
        """Test that optional fields are only added when provided."""
        # Setup mocks
        mock_post_process.return_value = ("Answer", False)
        mock_force_split.return_value = "Answer"
        mock_parse.return_value = (["Answer"], "single")

        service = QueryHandlerService()
        metadata = ResponseMetadata()

        # Call without optional fields
        result = service._finalize_response(
            answer="Raw answer",
            persona_name="Eeva",
            metadata=metadata,
            used_search=False
        )

        # Verify optional fields are not present
        assert "citation_valid" not in result
        assert "search_results_count" not in result


class TestMongoDBQueryHandler:
    """Test MongoDB query handling."""

    @patch("src.coordinator.services.query_handler_service.QueryHandlerService._finalize_response")
    @patch("src.coordinator.services.query_handler_service.LC_OllamaClient")
    @patch("src.coordinator.services.query_handler_service.build_mongodb_synthesis_prompt")
    @patch("src.coordinator.services.query_handler_service.get_ollama_base")
    @patch("src.coordinator.services.query_handler_service.get_persona_model")
    @patch("src.coordinator.services.query_handler_service.get_persona_temperature_override")
    def test_handle_mongodb_query_success(
        self,
        mock_get_temp,
        mock_get_model,
        mock_get_base,
        mock_build_prompt,
        mock_client_class,
        mock_finalize
    ):
        """Test successful MongoDB query handling."""
        # Setup mocks
        mock_get_base.return_value = "http://localhost:11434"
        mock_get_model.return_value = "llama3.1:latest"
        mock_get_temp.return_value = 0.9
        mock_build_prompt.return_value = "System prompt"

        mock_client = Mock()
        mock_client.complete.return_value = "Bitcoin is $50000"
        mock_client_class.return_value = mock_client

        mock_mongodb_service = Mock()
        mock_mongodb_service.handle_bitcoin_current_price.return_value = {
            "price": 50000,
            "cache_status": "hit",
            "timestamp": "2025-01-17T10:00:00Z"
        }

        mock_finalize.return_value = {
            "answer": "Bitcoin is $50000",
            "used_search": True
        }

        service = QueryHandlerService(mongodb_service=mock_mongodb_service)
        metadata = ResponseMetadata()

        mongodb_tools = [{
            "function": {"name": "bitcoin_current_price"}
        }]

        result = service.handle_mongodb_query(
            message="What is Bitcoin price?",
            system_prompt="System",
            user_compiled="User: What is Bitcoin price?",
            mongodb_tools=mongodb_tools,
            metadata=metadata,
            persona_name="Eeva",
            persona_card={}
        )

        # Verify MongoDB service was called
        mock_mongodb_service.handle_bitcoin_current_price.assert_called_once()

        # Verify LLM was called
        mock_client.complete.assert_called_once()

        # Verify finalize was called
        mock_finalize.assert_called_once()

        # Verify result
        assert result["answer"] == "Bitcoin is $50000"


class TestBraveQueryHandler:
    """Test Brave query handling."""

    @patch("src.coordinator.services.query_handler_service.QueryHandlerService._finalize_response")
    @patch("src.coordinator.services.query_handler_service.LC_OllamaClient")
    @patch("src.coordinator.services.query_handler_service.validate_citations")
    @patch("src.coordinator.services.query_handler_service.get_ollama_base")
    @patch("src.coordinator.services.query_handler_service.get_persona_model")
    @patch("src.coordinator.services.query_handler_service.get_persona_temperature_override")
    def test_handle_brave_query_with_search(
        self,
        mock_get_temp,
        mock_get_model,
        mock_get_base,
        mock_validate,
        mock_client_class,
        mock_finalize
    ):
        """Test Brave query handling with search results."""
        # Setup mocks
        mock_get_base.return_value = "http://localhost:11434"
        mock_get_model.return_value = "llama3.1:latest"
        mock_get_temp.return_value = 0.9

        mock_brave_client = Mock()

        mock_client = Mock()
        mock_client.complete_with_tools.return_value = (
            "Search answer with citations",
            Mock(),  # tool_call
            [Mock(), Mock()]  # search_results
        )
        mock_client_class.return_value = mock_client

        mock_validate.return_value = ("Clean answer", True, {})
        mock_finalize.return_value = {
            "answer": "Clean answer",
            "used_search": True
        }

        service = QueryHandlerService(brave_client=mock_brave_client)
        metadata = ResponseMetadata()

        result = service.handle_brave_query(
            system_prompt="System",
            user_compiled="User query",
            tools=[{"name": "brave_web_search"}],
            metadata=metadata,
            persona_name="Eeva",
            persona_card={}
        )

        # Verify client was created with brave_client
        assert mock_client_class.call_args.kwargs["mcp_client"] == mock_brave_client

        # Verify complete_with_tools was called
        mock_client.complete_with_tools.assert_called_once()

        # Verify citations were validated
        mock_validate.assert_called_once()

        # Verify result
        assert result["answer"] == "Clean answer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
