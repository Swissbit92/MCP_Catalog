# src/coordinator/services/argument_extractor.py
"""Grammar-constrained tool-argument extraction (HERMES-Agents Phase 3, M4).

The local 24B (Magidonia, Q4_K_M) is unreliable at emitting native tool-call
JSON — the force-search hack exists precisely because of this. Rather than ask
the model to *select* a tool (that stays on the deterministic bge-m3 router), we
constrain it to the much narrower task of *filling arguments* for an
already-selected tool, using Ollama structured output (``format=<json schema>``,
which compiles a grammar for the exact schema). Per XGrammar-2 (arXiv 2601.04426),
grammar-constrained decoding is the primary lever for format correctness — more so
than model size.

Defence in depth on top of the grammar:
* a minimal extraction prompt (NO persona voice — voice interferes with structured
  output and is applied later, in the rendering stage);
* schema-conformance check (required keys present, right shape);
* an optional semantic-coherence gate (extracted free-text must be topically
  related to the user message — catches well-formed-but-hallucinated values);
* up to N retries, then a deterministic regex fallback.

``chat_fn`` and ``embedder`` are injectable so unit tests run fully headless.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple

from .query_extraction_service import QueryExtractionService

logger = logging.getLogger(__name__)


# Per-tool JSON schemas for grammar-constrained decoding. Kept in lock-step with
# the interceptor's argument allowlist (tool_interceptor._validate_arguments).
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "brave_web_search": {
        "type": "object",
        "properties": {"query": {"type": "string", "maxLength": 300}},
        "required": ["query"],
    },
    "solana_get_quote": {
        "type": "object",
        "properties": {
            "from_token": {"type": "string", "enum": ["SOL", "USDC", "USDT"]},
            "to_token": {"type": "string", "enum": ["SOL", "USDC", "USDT"]},
            "amount": {"type": "number", "minimum": 0.000001},
        },
        "required": ["from_token", "to_token", "amount"],
    },
    "solana_propose_swap": {
        "type": "object",
        "properties": {
            "from_token": {"type": "string", "enum": ["SOL", "USDC", "USDT"]},
            "to_token": {"type": "string", "enum": ["SOL", "USDC", "USDT"]},
            "amount": {"type": "number", "minimum": 0.000001},
        },
        "required": ["from_token", "to_token", "amount"],
    },
    "solana_rsi_check": {
        "type": "object",
        "properties": {"token": {"type": "string", "enum": ["SOL", "USDC", "USDT"]}},
        "required": ["token"],
    },
    "wallet_create_guided": {
        "type": "object",
        "properties": {"wallet_name": {"type": "string", "maxLength": 32}},
        "required": ["wallet_name"],
    },
    # Read tools with no arguments need no extraction.
    "wallet_get_balances": {"type": "object", "properties": {}},
    "solana_trade_history": {"type": "object", "properties": {}},
}

_EXTRACTION_SYSTEM = (
    "You extract the structured values needed to perform an operation. "
    "Respond with ONLY a JSON object matching the requested schema — no prose, "
    "no explanation, no markdown."
)


def _extract_content(resp: Any) -> str:
    """Read the message content from an ollama ChatResponse or a dict-like stub."""
    # Attribute access (real ollama ChatResponse)
    msg = getattr(resp, "message", None)
    if msg is not None:
        content = getattr(msg, "content", None)
        if content is not None:
            return content
    # Mapping access (test stubs / dict responses)
    try:
        return resp["message"]["content"]
    except (KeyError, TypeError):
        return ""


class ArgumentExtractor:
    def __init__(
        self,
        model: Optional[str] = None,
        chat_fn: Optional[Callable[..., Any]] = None,
        embedder: Any = None,
    ):
        self._model = model
        self._chat_fn = chat_fn
        self.embedder = embedder

    # ----- ollama plumbing (lazy; overridable for tests) -----

    def _model_name(self) -> str:
        if self._model:
            return self._model
        from ..config import get_settings
        return get_settings().ollama.model

    def _chat(self, **kwargs) -> Any:
        if self._chat_fn is not None:
            return self._chat_fn(**kwargs)
        import ollama  # lazy import
        from ..config import get_settings
        client = ollama.Client(host=get_settings().ollama.base)
        return client.chat(**kwargs)

    # ----- public API -----

    def extract(
        self,
        tool_name: str,
        user_message: str,
        conversation_context: str = "",
        max_retries: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """Extract arguments for ``tool_name``.

        Returns ``(arguments, used_structured_output)``. ``used_structured_output``
        is False when the grammar path failed and the regex fallback was used.
        """
        schema = TOOL_SCHEMAS.get(tool_name)
        if schema is None:
            # Unknown tool — nothing to extract; let the interceptor reject it.
            return ({}, False)

        # No-argument tools: trivially done, no LLM call.
        if not schema.get("properties"):
            return ({}, True)

        if max_retries is None:
            from ..config import get_settings
            max_retries = get_settings().agent.extraction_max_retries

        for attempt in range(max_retries):
            try:
                resp = self._chat(
                    model=self._model_name(),
                    messages=[
                        {"role": "system", "content": _EXTRACTION_SYSTEM},
                        {"role": "user", "content": self._build_user_prompt(
                            tool_name, user_message, conversation_context)},
                    ],
                    format=schema,
                    options={"temperature": 0.0},
                )
            except Exception as e:
                logger.warning(f"[ArgExtractor] chat call failed (attempt {attempt+1}): {e}")
                continue

            content = _extract_content(resp)
            try:
                args = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                logger.debug(f"[ArgExtractor] non-JSON output (attempt {attempt+1})")
                continue

            if not isinstance(args, dict) or not self._schema_conformant(args, schema):
                continue

            if not self._coherent(tool_name, args, user_message):
                logger.debug(f"[ArgExtractor] coherence gate rejected (attempt {attempt+1})")
                continue

            return (args, True)

        # Persistent failure -> deterministic fallback.
        return (self._fallback(tool_name, user_message, conversation_context), False)

    # ----- helpers -----

    @staticmethod
    def _build_user_prompt(tool_name: str, user_message: str, context: str) -> str:
        parts = [f"Operation: {tool_name}"]
        if context:
            parts.append(f"Recent context:\n{context}")
        parts.append(f"User said: {user_message}")
        parts.append("Extract the JSON values for this operation.")
        return "\n\n".join(parts)

    @staticmethod
    def _schema_conformant(args: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Lightweight required-key + enum check (grammar guarantees the rest)."""
        for key in schema.get("required", []):
            if key not in args or args[key] in (None, ""):
                return False
        props = schema.get("properties", {})
        for key, spec in props.items():
            if key in args and "enum" in spec and args[key] not in spec["enum"]:
                return False
        return True

    def _coherent(self, tool_name: str, args: Dict[str, Any], user_message: str) -> bool:
        """Semantic-coherence gate for free-text args (brave query).

        Only applies when an embedder is available and the tool has a free-text
        field; structural (enum/number) args are already constrained.
        """
        if self.embedder is None or tool_name != "brave_web_search":
            return True
        query = args.get("query", "")
        if not query:
            return False
        try:
            from ..config import get_settings
            floor = get_settings().agent.extraction_coherence_threshold
            sim = self._cosine(query, user_message)
            return sim >= floor
        except Exception as e:  # pragma: no cover - embedder optional
            logger.debug(f"[ArgExtractor] coherence check skipped: {e}")
            return True

    def _cosine(self, a: str, b: str) -> float:
        va = self.embedder.embed_query(a)
        vb = self.embedder.embed_query(b)
        dot = sum(x * y for x, y in zip(va, vb))
        na = sum(x * x for x in va) ** 0.5
        nb = sum(x * x for x in vb) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    @staticmethod
    def _fallback(tool_name: str, user_message: str, context: str) -> Dict[str, Any]:
        """Deterministic fallback when grammar extraction fails."""
        if tool_name == "brave_web_search":
            source = context or user_message
            query = QueryExtractionService.extract_latest_user_message(source)
            return {"query": (query or user_message).strip()[:300]}
        # Wallet tools: no safe deterministic guess — return empty so the
        # interceptor rejects rather than executing a hallucinated swap.
        return {}
