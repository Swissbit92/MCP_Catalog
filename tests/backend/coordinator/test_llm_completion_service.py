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
        """Test complete method with system and user prompts.

        complete() uses generate() (not invoke()) so it can read Ollama's
        prompt_eval_count for M2 token observability (ADR-006 Phase 0).
        """
        # Mock Ollama generate() -> LLMResult-like (generations[0][0].text/info)
        mock_llm = Mock()
        mock_gen = Mock()
        mock_gen.text = "Test response"
        mock_gen.generation_info = {"prompt_eval_count": 123}
        mock_result = Mock()
        mock_result.generations = [[mock_gen]]
        mock_llm.generate.return_value = mock_result
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

        # Verify LLM.generate was called with the formatted prompt (batch of 1)
        mock_llm.generate.assert_called_once_with(["formatted prompt"])
        assert response == "Test response"

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    @patch("src.coordinator.services.llm_completion_service.ChatPromptTemplate")
    def test_complete_logs_assembled_tokens(self, mock_prompt_template_class, mock_ollama_class, caplog):
        """M2: complete() emits the [Tokens-assembled] observability log line."""
        import logging

        mock_llm = Mock()
        mock_gen = Mock()
        mock_gen.text = "ok"
        mock_gen.generation_info = {"prompt_eval_count": 42}
        mock_result = Mock()
        mock_result.generations = [[mock_gen]]
        mock_llm.generate.return_value = mock_result
        mock_ollama_class.return_value = mock_llm

        mock_template = Mock()
        mock_prompt = Mock()
        mock_prompt.to_string.return_value = "some rendered prompt text"
        mock_template.format_prompt.return_value = mock_prompt
        mock_prompt_template_class.from_messages.return_value = mock_template

        service = LLMCompletionService(base="http://localhost:11434", model="llama3.1:latest")

        with caplog.at_level(logging.INFO, logger="src.coordinator.services.llm_completion_service"):
            service.complete("sys", "user")

        assert any("[Tokens-assembled]" in r.message for r in caplog.records)
        # actual prompt_eval_count is surfaced when present
        assert any("prompt_eval_count=42" in r.message for r in caplog.records)


class TestReasoningControl:
    """OLLAMA_REASONING — the thinking-model escape hatch.

    The load-bearing property is the DEFAULT: unset must leave the OllamaLLM
    constructor byte-identical to legacy, because the live backend serves from
    this same checkout and would pick the change up on any restart.
    """

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_unset_never_passes_the_key_at_all(self, mock_ollama_class, monkeypatch):
        monkeypatch.delenv("OLLAMA_REASONING", raising=False)
        LLMCompletionService(base="http://localhost:11434", model="llama3.1:latest")
        assert "reasoning" not in mock_ollama_class.call_args.kwargs

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_false_is_forwarded_so_a_thinking_model_returns_content(
        self, mock_ollama_class, monkeypatch
    ):
        """Without this a thinking model spends num_predict on its reasoning
        stream and invoke() returns an empty string."""
        monkeypatch.setenv("OLLAMA_REASONING", "false")
        from src.coordinator.config import get_settings
        get_settings.cache_clear()
        try:
            LLMCompletionService(base="http://localhost:11434", model="gemma4:26b")
            assert mock_ollama_class.call_args.kwargs["reasoning"] is False
        finally:
            get_settings.cache_clear()

    @patch("src.coordinator.services.llm_completion_service.OllamaLLM")
    def test_true_is_forwarded_too(self, mock_ollama_class, monkeypatch):
        monkeypatch.setenv("OLLAMA_REASONING", "true")
        from src.coordinator.config import get_settings
        get_settings.cache_clear()
        try:
            LLMCompletionService(base="http://localhost:11434", model="gemma4:26b")
            assert mock_ollama_class.call_args.kwargs["reasoning"] is True
        finally:
            get_settings.cache_clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
