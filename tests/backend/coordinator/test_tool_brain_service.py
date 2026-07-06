# tests/backend/coordinator/test_tool_brain_service.py
"""ADR-008 TB3: native tool-brain loop service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.tools import registrations  # noqa: F401 - register specs
from src.coordinator.tools.registry import registry
from src.coordinator.tools.executor_bindings import bind_web_executors
from src.coordinator.services.tool_brain_service import (
    ToolBrainService, ToolBrainResult,
    ST_ANSWERED, ST_SILENT, ST_DELEGATE_WALLET, ST_HITL,
)
from src.coordinator.services.tool_interceptor import ToolCallInterceptor
from src.coordinator.config import get_settings


@pytest.fixture(autouse=True)
def _setup():
    bind_web_executors()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _tc(name, args):
    return {"function": {"name": name, "arguments": args}}


class FakeOllama:
    """Returns a scripted sequence of chat responses."""
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _msg(content="", tool_calls=None):
    return {"message": {"content": content, "tool_calls": tool_calls or []}}


EEVA = {"key": "nephilim_eeva", "mcp_access": ["brave_search", "solana_wallet"], "nsfw": False}
GWEN = {"key": "gwen", "toolsets": ["web"], "tools": ["image_search", "video_search"],
        "mcp_access": ["brave_search"], "nsfw": True}


def _svc(responses):
    return ToolBrainService(interceptor=ToolCallInterceptor(enforce_arguments=True),
                            ollama_client=FakeOllama(responses))


class TestSilent:
    def test_no_tool_call_returns_silent(self):
        svc = _svc([_msg(content="Hello, Seeker.")])
        r = svc.run(persona_card=EEVA, system_prompt="sys", user_message="hi",
                    history=[], tools=registry.definitions_for_persona(EEVA))
        assert r.status == ST_SILENT
        assert r.answer == "Hello, Seeker."


class TestNativeWebSearch:
    def test_search_then_synthesize(self):
        # round 1: model calls web_search; round 2: model synthesizes.
        responses = [
            _msg(tool_calls=[_tc("web_search", {"query": "bitcoin price"})]),
            _msg(content="Bitcoin is around $91k, Seeker."),
        ]
        svc = _svc(responses)
        fake_results = [MagicMock(title="BTC", url="https://x", description="d", age=None)]
        registry.bind_executor("web_search", lambda args, card: fake_results)
        try:
            r = svc.run(persona_card=EEVA, system_prompt="sys",
                        user_message="what's the bitcoin price", history=[],
                        tools=registry.definitions_for_persona(EEVA))
        finally:
            bind_web_executors()  # restore real executor
        assert r.status == ST_ANSWERED
        assert "Bitcoin" in r.answer
        assert r.used_search is True
        assert r.search_results == fake_results
        assert any(t["tool"] == "web_search" and t["allowed"] for t in r.tool_trace)

    def test_image_search_executes_for_gwen(self):
        responses = [
            _msg(tool_calls=[_tc("image_search", {"query": "x"})]),
            _msg(content="Here you go, Daddy 😈"),
        ]
        svc = _svc(responses)
        registry.bind_executor("image_search",
                               lambda args, card: [MagicMock(title="i", url="u", description="", age=None)])
        try:
            r = svc.run(persona_card=GWEN, system_prompt="sys", user_message="find images",
                        history=[], tools=registry.definitions_for_persona(GWEN))
        finally:
            bind_web_executors()
        assert r.status == ST_ANSWERED and r.used_search is True


class TestWalletDelegation:
    def test_wallet_read_delegates(self):
        svc = _svc([_msg(tool_calls=[_tc("wallet_get_balances", {"user_id": "u"})])])
        r = svc.run(persona_card=EEVA, system_prompt="sys", user_message="my balance",
                    history=[], tools=registry.definitions_for_persona(EEVA))
        assert r.status == ST_DELEGATE_WALLET

    def test_wallet_write_returns_hitl(self):
        # solana_propose_swap requires_hitl -> HITL before any wallet delegation.
        svc = _svc([_msg(tool_calls=[_tc("solana_propose_swap",
                    {"from_token": "SOL", "to_token": "USDC", "amount": 1})])])
        r = svc.run(persona_card=EEVA, system_prompt="sys", user_message="swap",
                    history=[], tools=registry.definitions_for_persona(EEVA))
        assert r.status == ST_HITL and r.hitl_tool == "solana_propose_swap"


class TestInterceptorGate:
    def test_blocked_tool_not_executed(self):
        # Gwen lacks solana_wallet -> a wallet call is denied (CAT_MCP), fed back
        # as a refusal, model then answers.
        responses = [
            _msg(tool_calls=[_tc("wallet_get_balances", {"user_id": "u"})]),
            _msg(content="I can't touch wallets, Daddy."),
        ]
        svc = _svc(responses)
        r = svc.run(persona_card=GWEN, system_prompt="sys", user_message="my wallet",
                    history=[], tools=registry.definitions_for_persona(GWEN))
        # wallet not in Gwen's mcp_access -> interceptor denies -> not delegated,
        # fed back as blocked, loop continues to a normal answer.
        assert r.status == ST_ANSWERED
        assert any(t["tool"] == "wallet_get_balances" and not t["allowed"] for t in r.tool_trace)

    def test_execute_swap_hard_blocked(self):
        # A raw execute_swap from agent source is hard-blocked (requires_hitl True).
        svc = _svc([_msg(tool_calls=[_tc("execute_swap", {})])])
        r = svc.run(persona_card=EEVA, system_prompt="sys", user_message="x",
                    history=[], tools=registry.definitions_for_persona(EEVA))
        assert r.status == ST_HITL


class TestSafety:
    def test_loop_error_degrades_to_silent(self):
        class Boom:
            def chat(self, **k):
                raise RuntimeError("ollama down")
        svc = ToolBrainService(interceptor=ToolCallInterceptor(True), ollama_client=Boom())
        r = svc.run(persona_card=EEVA, system_prompt="s", user_message="hi",
                    history=[], tools=[])
        assert r.status == ST_SILENT and r.answer is None

    def test_max_iterations_forces_synthesis(self):
        get_settings.cache_clear()
        import os
        with patch.dict(os.environ, {"TOOL_BRAIN_MAX_ITERATIONS": "1"}):
            get_settings.cache_clear()
            # 1 iteration: calls a tool, then the forced no-tools synthesis call.
            responses = [
                _msg(tool_calls=[_tc("web_search", {"query": "x"})]),
                _msg(content="Final synthesis."),
            ]
            svc = _svc(responses)
            registry.bind_executor("web_search",
                                   lambda a, c: [MagicMock(title="t", url="u", description="", age=None)])
            try:
                r = svc.run(persona_card=EEVA, system_prompt="s", user_message="x",
                            history=[], tools=registry.definitions_for_persona(EEVA))
            finally:
                bind_web_executors()
        assert r.status == ST_ANSWERED and r.answer == "Final synthesis."
        get_settings.cache_clear()


class TestSynthesisRefusalRetry:
    """M3: a spurious refusal in synthesis (despite successful search) triggers
    one prefill-steered retry; if that recovers, the answer is returned clean;
    if it still refuses, `refused=True` so the route falls through to legacy."""

    def _img_results(self):
        return [MagicMock(title="pic", url="https://a/x.jpg", description="", age=None)]

    def test_refusal_recovered_by_prefill_retry(self):
        # round1: image_search call; round2: SPURIOUS refusal; round3 (retry):
        # compliant continuation.
        responses = [
            _msg(tool_calls=[_tc("image_search", {"query": "x"})]),
            _msg(content="I cannot and will not search for images."),
            _msg(content="here they are, Daddy 😈"),  # continuation after prefill
        ]
        svc = _svc(responses)
        registry.bind_executor("image_search", lambda a, c: self._img_results())
        try:
            r = svc.run(persona_card=GWEN, system_prompt="sys", user_message="find an image",
                        history=[], tools=registry.definitions_for_persona(GWEN))
        finally:
            bind_web_executors()
        assert r.status == ST_ANSWERED
        assert r.refused is False
        assert r.answer.startswith("Here's what I found for you")  # prefill retained
        assert "here they are" in r.answer
        assert len(svc._client.calls) == 3  # the retry happened

    def test_refusal_persists_sets_refused_flag(self):
        responses = [
            _msg(tool_calls=[_tc("image_search", {"query": "x"})]),
            _msg(content="I cannot and will not search for images."),
            _msg(content="I'm not able to search for that."),  # retry ALSO refuses
        ]
        svc = _svc(responses)
        registry.bind_executor("image_search", lambda a, c: self._img_results())
        try:
            r = svc.run(persona_card=GWEN, system_prompt="sys", user_message="find an image",
                        history=[], tools=registry.definitions_for_persona(GWEN))
        finally:
            bind_web_executors()
        assert r.status == ST_ANSWERED
        assert r.refused is True  # caller must fall through
        assert len(svc._client.calls) == 3

    def test_normal_answer_no_retry_no_refused(self):
        responses = [
            _msg(tool_calls=[_tc("image_search", {"query": "x"})]),
            _msg(content="Here you go, Daddy 😈"),
        ]
        svc = _svc(responses)
        registry.bind_executor("image_search", lambda a, c: self._img_results())
        try:
            r = svc.run(persona_card=GWEN, system_prompt="sys", user_message="find an image",
                        history=[], tools=registry.definitions_for_persona(GWEN))
        finally:
            bind_web_executors()
        assert r.refused is False
        assert len(svc._client.calls) == 2  # NO retry


class TestIsSynthesisRefusal:
    @pytest.mark.parametrize("text", [
        "I cannot and will not search for images.",
        "I can't search for that.",
        "I won't look that up for you.",
        "I'm not able to search for images.",
        "I cannot assist with that request.",
        "As an AI, I must decline.",
    ])
    def test_refusals_detected(self, text):
        from src.coordinator.services.tool_brain_service import is_synthesis_refusal
        assert is_synthesis_refusal(text) is True

    @pytest.mark.parametrize("text", [
        "Here you go, Daddy 😈 I found some hot pics.",
        "I won't beg for it, but here's what I found.",   # in-character negation, not a refusal
        "I can't believe how good these are.",
        "Let me search my feelings... here are the images.",
        "",
        None,
    ])
    def test_non_refusals_pass(self, text):
        from src.coordinator.services.tool_brain_service import is_synthesis_refusal
        assert is_synthesis_refusal(text) is False

    def test_refusal_deep_in_text_not_flagged(self):
        # A long in-voice answer that only mentions 'search' far in isn't a refusal.
        from src.coordinator.services.tool_brain_service import is_synthesis_refusal
        text = "Here are the images, love. " * 20 + "I cannot and will not search."
        assert is_synthesis_refusal(text) is False
