# src/coordinator/llm_client.py
# LLM client wrapper for GraphRAG Local QA Chat with Personas
# Uses LangChain's OllamaLLM with ChatPromptTemplate for prompt formatting.
# Handles Ollama connectivity errors.

from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from ollama._types import ResponseError

class LC_OllamaClient:
    """Thin wrapper around LangChain's OllamaLLM using ChatPromptTemplate."""

    def __init__(self, base: str, model: str, temperature: float = 0.1):
        self.llm = OllamaLLM(base_url=base, model=model, temperature=temperature)

    def _invoke(self, prompt: str) -> str:
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
        template = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            ("user", "{user}")
        ])
        rendered = template.format_prompt(system=system, user=user_prompt).to_string()
        return self._invoke(rendered)
