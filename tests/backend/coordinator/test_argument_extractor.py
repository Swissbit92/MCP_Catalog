# test_argument_extractor.py
# Unit tests for the Phase-3 grammar-constrained argument extractor (M4).
# Fully headless — a fake chat_fn stands in for ollama.

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.services.argument_extractor import (
    ArgumentExtractor,
    TOOL_SCHEMAS,
    _extract_content,
)


def _resp(content):
    """Build a dict-shaped ollama-like response."""
    return {"message": {"content": content}}


class _ScriptedChat:
    """Returns queued responses in order; records call count."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return _resp("")


def test_schema_in_lockstep_with_tools():
    for t in ("brave_web_search", "solana_propose_swap", "solana_rsi_check",
              "wallet_create_guided", "wallet_get_balances"):
        assert t in TOOL_SCHEMAS


def test_brave_happy_path():
    chat = _ScriptedChat([_resp(json.dumps({"query": "ethereum price"}))])
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract("brave_web_search", "what's the eth price?")
    assert structured is True
    assert args == {"query": "ethereum price"}
    assert chat.calls == 1


def test_retry_then_success():
    chat = _ScriptedChat([
        _resp("not json at all"),
        _resp('{"oops": true}'),  # missing required 'query'
        _resp(json.dumps({"query": "btc news"})),
    ])
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract("brave_web_search", "btc news?", max_retries=3)
    assert structured is True
    assert args["query"] == "btc news"
    assert chat.calls == 3


def test_fallback_to_regex_after_failures():
    chat = _ScriptedChat([_resp("garbage"), _resp("garbage"), _resp("garbage")])
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract(
        "brave_web_search",
        "tell me the latest on solana",
        conversation_context="User: tell me the latest on solana",
        max_retries=3,
    )
    assert structured is False
    assert args["query"]  # non-empty fallback query
    assert "solana" in args["query"].lower()


def test_swap_enum_happy_path():
    payload = {"from_token": "SOL", "to_token": "USDC", "amount": 1.5}
    chat = _ScriptedChat([_resp(json.dumps(payload))])
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract("solana_propose_swap", "swap 1.5 sol to usdc")
    assert structured is True
    assert args == payload


def test_swap_bad_enum_falls_back_empty():
    # Model keeps emitting an out-of-enum token -> schema check fails every time
    # -> wallet fallback returns {} (interceptor will then reject).
    bad = {"from_token": "SOL", "to_token": "SCAM", "amount": 1.0}
    chat = _ScriptedChat([_resp(json.dumps(bad))] * 3)
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract("solana_propose_swap", "swap sol to scam", max_retries=3)
    assert structured is False
    assert args == {}


def test_no_argument_tool_skips_llm():
    chat = _ScriptedChat([])
    ex = ArgumentExtractor(model="x", chat_fn=chat)
    args, structured = ex.extract("wallet_get_balances", "what's my balance?")
    assert structured is True
    assert args == {}
    assert chat.calls == 0  # no LLM call for a no-arg tool


def test_unknown_tool_returns_empty():
    ex = ArgumentExtractor(model="x", chat_fn=_ScriptedChat([]))
    args, structured = ex.extract("frobnicate", "do the thing")
    assert args == {}
    assert structured is False


def test_coherence_gate_rejects_unrelated_query():
    # Embedder returns orthogonal vectors for query vs message -> cosine 0 ->
    # below the coherence floor -> rejected -> fallback (structured False).
    class _OrthEmbedder:
        def embed_query(self, text):
            return [1.0, 0.0] if "moon" in text else [0.0, 1.0]

    chat = _ScriptedChat([_resp(json.dumps({"query": "moon base prices"}))] * 3)
    ex = ArgumentExtractor(model="x", chat_fn=chat, embedder=_OrthEmbedder())
    args, structured = ex.extract("brave_web_search", "what is the weather",
                                  conversation_context="User: what is the weather",
                                  max_retries=3)
    assert structured is False  # coherence gate forced fallback


def test_coherence_gate_accepts_related_query():
    class _SameEmbedder:
        def embed_query(self, text):
            return [1.0, 1.0]  # identical -> cosine 1.0

    chat = _ScriptedChat([_resp(json.dumps({"query": "weather today"}))])
    ex = ArgumentExtractor(model="x", chat_fn=chat, embedder=_SameEmbedder())
    args, structured = ex.extract("brave_web_search", "what is the weather")
    assert structured is True
    assert args["query"] == "weather today"


def test_extract_content_attribute_style():
    class _Msg:
        content = "hello"

    class _Resp:
        message = _Msg()

    assert _extract_content(_Resp()) == "hello"


def test_extract_content_dict_style():
    assert _extract_content(_resp("hi")) == "hi"


def test_extract_content_empty_on_garbage():
    assert _extract_content(object()) == ""
