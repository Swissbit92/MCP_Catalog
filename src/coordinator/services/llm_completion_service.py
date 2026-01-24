# src/coordinator/services/llm_completion_service.py
"""
LLM Completion Service - Basic completion without tool calling.

Extracted from llm_client.py as part of Phase 2 Core Refactoring.
Handles basic LLM invocations with advanced sampling support.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from ollama._types import ResponseError

from ..models.sampling_presets import SamplingConfig

logger = logging.getLogger(__name__)


class LLMCompletionService:
    """Service for basic LLM completion without tool calling.

    Handles:
    - Ollama client initialization with advanced sampling
    - Basic prompt completion
    - Error handling for Ollama connectivity
    - Sampling configuration management

    This service is stateless and thread-safe.
    """

    def __init__(
        self,
        base: str,
        model: str,
        temperature: float = 0.1,
        sampling_config: Optional[SamplingConfig] = None,
        # Individual sampling params (override sampling_config if provided)
        repeat_penalty: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ):
        """Initialize the LLM completion service.

        Args:
            base: Ollama base URL
            model: Model name (e.g., 'llama3.1:latest')
            temperature: Sampling temperature (0.0-2.0)
            sampling_config: Optional SamplingConfig for preset-based configuration
            repeat_penalty: Optional repetition penalty (1.0-2.0)
            top_k: Optional Top-K sampling (0-100)
            top_p: Optional nucleus sampling threshold (0.0-1.0)
        """
        # Build Ollama params
        ollama_params = {
            "base_url": base,
            "model": model,
            "temperature": temperature,
        }

        # Apply sampling config if provided
        if sampling_config:
            config_params = sampling_config.to_ollama_params()
            # Temperature from sampling_config unless explicitly overridden
            if temperature == 0.1:  # default value
                ollama_params["temperature"] = config_params.get("temperature", 0.1)
            if "repeat_penalty" in config_params:
                ollama_params["repeat_penalty"] = config_params["repeat_penalty"]
            if "top_k" in config_params:
                ollama_params["top_k"] = config_params["top_k"]
            if "top_p" in config_params:
                ollama_params["top_p"] = config_params["top_p"]

        # Individual params override sampling_config
        if repeat_penalty is not None:
            ollama_params["repeat_penalty"] = repeat_penalty
        if top_k is not None:
            ollama_params["top_k"] = top_k
        if top_p is not None:
            ollama_params["top_p"] = top_p

        self.llm = OllamaLLM(**ollama_params)
        self.sampling_config = sampling_config

        # Log sampling parameters
        sampling_info = f"temp={ollama_params['temperature']}"
        if "repeat_penalty" in ollama_params:
            sampling_info += f", repeat_penalty={ollama_params['repeat_penalty']}"
        if "top_k" in ollama_params:
            sampling_info += f", top_k={ollama_params['top_k']}"
        if "top_p" in ollama_params:
            sampling_info += f", top_p={ollama_params['top_p']}"

        preset_name = sampling_config.name if sampling_config else "custom"
        logger.info(
            f"Initialized LLMCompletionService: model={model}, "
            f"sampling=[{sampling_info}], preset={preset_name}"
        )

    def get_sampling_info(self) -> Dict[str, Any]:
        """Get current sampling configuration as dict for response metadata.

        Returns:
            Dictionary with sampling parameters
        """
        info = {
            "temperature": self.llm.temperature,
            "model": self.llm.model,
        }
        if hasattr(self.llm, "repeat_penalty") and self.llm.repeat_penalty:
            info["repeat_penalty"] = self.llm.repeat_penalty
        if hasattr(self.llm, "top_k") and self.llm.top_k:
            info["top_k"] = self.llm.top_k
        if hasattr(self.llm, "top_p") and self.llm.top_p:
            info["top_p"] = self.llm.top_p
        if self.sampling_config:
            info["preset"] = self.sampling_config.name
        return info

    def invoke(self, prompt: str) -> str:
        """Low-level Ollama invocation with error handling.

        Args:
            prompt: Formatted prompt string

        Returns:
            LLM response string

        Raises:
            RuntimeError: If Ollama model not found or other errors
        """
        try:
            return self.llm.invoke(prompt).strip()
        except ResponseError as e:
            msg = str(e)
            if "not found" in msg.lower():
                raise RuntimeError(
                    "Ollama model not found.\n"
                    f"Pull it:\n  ollama pull {self.llm.model}\n"
                    f"base_url={self.llm.base_url}\n"
                )
            raise

    def complete(self, system: str, user_prompt: str) -> str:
        """Complete a prompt with system and user messages.

        Args:
            system: System prompt
            user_prompt: User message

        Returns:
            LLM response string
        """
        template = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            ("user", "{user}")
        ])
        rendered = template.format_prompt(system=system, user=user_prompt).to_string()
        return self.invoke(rendered)
