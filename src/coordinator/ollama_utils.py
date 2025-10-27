# src/coordinator/ollama_utils.py
# Utilities for interacting with Ollama LLM in GraphRAG Local QA Chat with Personas
# Functions to list local models and assert model availability.
# Handles Ollama connectivity errors.

import requests
from typing import List

class OllamaModelNotFound(RuntimeError):
    pass

def list_local_models(base_url: str) -> List[str]:
    r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=10)
    r.raise_for_status()
    data = r.json() or {}
    return [m.get("name") for m in data.get("models", []) if m.get("name")]

def assert_model_available(base_url: str, model: str) -> None:
    try:
        available = list_local_models(base_url)
    except Exception as e:
        raise RuntimeError(
            f"Could not reach Ollama at {base_url}. Is it running?\n"
            f"Original error: {e}"
        )
    if model not in available:
        hint = ""
        if available:
            hint = "Available models:\n  - " + "\n  - ".join(available)
        raise OllamaModelNotFound(
            f"Ollama model '{model}' is not available at {base_url}.\n"
            f"Pull it:\n  ollama pull {model}\n\n{hint}"
        )
