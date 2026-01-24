# tests/backend/coordinator/test_llm_completion_service.py
"""
Unit tests for LLMCompletionService - Basic LLM completion without tool calling.

Tests cover:
- Service initialization with various sampling configurations
- Prompt completion with mocked LLM
- Error handling for Ollama connectivity
- Sampling configuration management
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from ollama._types import ResponseError

from src.coordinator.services.llm_completion_service import LLMCompletionService
from src.coordinator.models.sampling_presets import SamplingConfig


class TestLLMCompletionService:
    """Test LLMCompletionService functionality."""

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_init_basic(self, mock_ollama_class):
        """Test basic initialization without sampling config."""
        mock_llm = Mock()
        mock_ollama_class.return_value = mock_llm

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest",
            temperature=0.7
        )

        # Verify OllamaLLM was called with correct params
        mock_ollama_class.assert_called_once()
        call_kwargs = mock_ollama_class.call_args.kwargs
        assert call_kwargs["base_url"] == "http://localhost:11434"
        assert call_kwargs["model"] == "llama3.1:latest"
        assert call_kwargs["temperature"] == 0.7

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_init_with_sampling_config(self, mock_ollama_class):
        """Test initialization with sampling config preset."""
        mock_llm = Mock()
        mock_ollama_class.return_value = mock_llm

        sampling_config = SamplingConfig(
            name="creative",
            temperature=0.9,
            repeat_penalty=1.1,
            top_k=40,
            top_p=0.95
        )

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest",
            sampling_config=sampling_config
        )

        # Verify sampling params were applied
        call_kwargs = mock_ollama_class.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["repeat_penalty"] == 1.1
        assert call_kwargs["top_k"] == 40
        assert call_kwargs["top_p"] == 0.95

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_init_individual_params_override_config(self, mock_ollama_class):
        """Test that individual params override sampling config."""
        mock_llm = Mock()
        mock_ollama_class.return_value = mock_llm

        sampling_config = SamplingConfig(
            name="balanced",
            temperature=0.7,
            top_k=40
        )

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest",
            temperature=0.9,  # Override
            sampling_config=sampling_config,
            top_k=50  # Override
        )

        call_kwargs = mock_ollama_class.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9  # Overridden
        assert call_kwargs["top_k"] == 50  # Overridden

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_get_sampling_info(self, mock_ollama_class):
        """Test getting sampling info as dict."""
        mock_llm = Mock()
        mock_llm.temperature = 0.8
        mock_llm.model = "llama3.1:latest"
        mock_llm.repeat_penalty = 1.1
        mock_llm.top_k = 40
        mock_llm.top_p = 0.95
        mock_ollama_class.return_value = mock_llm

        sampling_config = SamplingConfig(name="test", temperature=0.8)
        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest",
            sampling_config=sampling_config
        )

        info = service.get_sampling_info()

        assert info["temperature"] == 0.8
        assert info["model"] == "llama3.1:latest"
        assert info["repeat_penalty"] == 1.1
        assert info["top_k"] == 40
        assert info["top_p"] == 0.95
        assert info["preset"] == "test"

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_invoke_success(self, mock_ollama_class):
        """Test successful LLM invocation."""
        mock_llm = Mock()
        mock_llm.invoke.return_value = "  Test response  "
        mock_ollama_class.return_value = mock_llm

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest"
        )

        response = service.invoke("Test prompt")

        assert response == "Test response"  # Stripped
        mock_llm.invoke.assert_called_once_with("Test prompt")

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_invoke_model_not_found(self, mock_ollama_class):
        """Test invoke error when model not found."""
        mock_llm = Mock()
        mock_llm.model = "llama3.1:latest"
        mock_llm.base_url = "http://localhost:11434"
        mock_llm.invoke.side_effect = ResponseError("model not found")
        mock_ollama_class.return_value = mock_llm

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest"
        )

        with pytest.raises(RuntimeError, match="Ollama model not found"):
            service.invoke("Test prompt")

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_invoke_other_error(self, mock_ollama_class):
        """Test invoke with other ResponseError."""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = ResponseError("Connection timeout")
        mock_ollama_class.return_value = mock_llm

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest"
        )

        with pytest.raises(ResponseError, match="Connection timeout"):
            service.invoke("Test prompt")

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    @patch("src.coordinator.services.llm_completion_service.ChatPromptTemplate")
    def test_complete(self, mock_prompt_template_class, mock_ollama_class):
        """Test complete method with system and user prompts."""
        # Mock Ollama
        mock_llm = Mock()
        mock_llm.invoke.return_value = "Test response"
        mock_ollama_class.return_value = mock_llm

        # Mock ChatPromptTemplate
        mock_template = Mock()
        mock_prompt = Mock()
        mock_prompt.to_string.return_value = "formatted prompt"
        mock_template.format_prompt.return_value = mock_prompt
        mock_prompt_template_class.from_messages.return_value = mock_template

        service = LLMCompletionService(
            base="http://localhost:11434",
            model="llama3.1:latest"
        )

        response = service.complete("System prompt", "User message")

        # Verify template was formatted correctly
        mock_template.format_prompt.assert_called_once_with(
            system="System prompt",
            user="User message"
        )

        # Verify LLM was invoked with formatted prompt
        mock_llm.invoke.assert_called_once_with("formatted prompt")
        assert response == "Test response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
