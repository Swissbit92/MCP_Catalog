# src/coordinator/config.py
# Configuration utilities for GraphRAG Local QA Chat with Personas
# Functions to retrieve required environment variables.
# Uses python-dotenv to load .env files.

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _required(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Set it in your .env (e.g. {name}=value)"
        )
    return val

def get_ollama_base() -> str:
    return _required("OLLAMA_BASE")

def get_persona_model() -> str:
    return _required("PERSONA_MODEL")

def get_persona_dir() -> str:
    return os.getenv("PERSONA_DIR", "personas")

def get_persona_temperature() -> float:
    try:
        return float(os.getenv("PERSONA_TEMPERATURE", "0.1"))
    except ValueError:
        return 0.1
