# tests/backend/coordinator/test_tool_brain_route.py
"""ADR-008 TB4: route orchestration of the tool-brain loop + fallback."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.routes import chat as chat_mod
from src.coordinator.services.tool_brain_service import (
    ToolBrainResult, ST_ANSWERED, ST_SILENT, ST_DELEGATE_WALLET, ST_HITL,
)
from src.coordinator.schemas import ResponseMetadata, SourceType
from src.coordinator.tools.intent_classifier import QueryIntent


def _body(msg="hi"):
    return SimpleNamespace(message=msg, session_id="s1", persona="gwen")


def _hist():
    return [SimpleNamespace(role="user", content="earlier"),
            SimpleNamespace(role="assistant", content="reply")]


CARD = {"key": "gwen", "toolsets": ["web"], "tools": ["image_search"],
        "mcp_access": ["brave_search"], "nsfw": True}


def _run(result, intent=QueryIntent.NEEDS_WEB_SEARCH, tools_nonempty=True):
    """Invoke _try_tool_brain with ToolBrainService.run mocked to `result`."""
    meta = ResponseMetadata(source_type=SourceType.LLM, tools_used=[])
    fake_svc = MagicMock()
    fake_svc.run.return_value = result
    defs = [{"function": {"name": "image_search"}}] if tools_nonempty else []
    with patch("src.coordinator.services.tool_brain_service.ToolBrainService",
               return_value=fake_svc), \
         patch("src.coordinator.tools.registry.registry.definitions_for_persona",
               return_value=defs):
        return chat_mod._try_tool_brain(
            card=CARD, system="sys", body=_body(), history=_hist(), intent=intent,
            metadata=meta, persona_name="Gwen", deps={"brave_client": None}), meta


class TestAnswered:
    def test_answered_no_search(self):
        resp, meta = _run(ToolBrainResult(status=ST_ANSWERED, answer="Hi Daddy"))
        assert resp is not None
        assert meta.source_type == SourceType.TOOL_BRAIN

    def test_answered_with_search_appends_citations(self):
        results = [MagicMock(title="T", url="https://x.com", description="d", age=None)]
        with patch("src.coordinator.services.citation_service.CitationService.auto_generate_citations",
                   return_value="\n\n🔍 Sources:\n• [T](https://x.com)") as cite:
            resp, meta = _run(ToolBrainResult(status=ST_ANSWERED, answer="Found it",
                                              used_search=True, search_results=results))
        assert resp is not None
        cite.assert_called_once_with(results)
        assert meta.tools_used == ["web_search"]


class TestSilentFallback:
    def test_silent_neither_uses_answer(self):
        # Router agrees no tool needed -> use the model's direct answer.
        with patch("src.coordinator.routes.chat._apply_groundedness_gate",
                   side_effect=lambda c, m, a, md: a):
            resp, meta = _run(ToolBrainResult(status=ST_SILENT, answer="Just chatting"),
                              intent=QueryIntent.NEEDS_NEITHER)
        assert resp is not None
        assert meta.source_type == SourceType.TOOL_BRAIN

    def test_silent_but_tool_needed_falls_through(self):
        # Native silent but router says web-search -> None (legacy floor handles it).
        resp, _ = _run(ToolBrainResult(status=ST_SILENT, answer="incomplete"),
                       intent=QueryIntent.NEEDS_WEB_SEARCH)
        assert resp is None

    def test_silent_no_answer_falls_through(self):
        resp, _ = _run(ToolBrainResult(status=ST_SILENT, answer=None),
                       intent=QueryIntent.NEEDS_NEITHER)
        assert resp is None


class TestWalletHandoff:
    def test_delegate_wallet_calls_handler(self):
        with patch("src.coordinator.routes.chat.QueryHandlerService") as QHS:
            QHS.return_value.handle_wallet_query.return_value = {"answer": "wallet"}
            resp, _ = _run(ToolBrainResult(status=ST_DELEGATE_WALLET))
        assert resp == {"answer": "wallet"}
        QHS.return_value.handle_wallet_query.assert_called_once()

    def test_hitl_calls_handler(self):
        with patch("src.coordinator.routes.chat.QueryHandlerService") as QHS:
            QHS.return_value.handle_wallet_query.return_value = {"answer": "propose"}
            resp, _ = _run(ToolBrainResult(status=ST_HITL, hitl_tool="solana_propose_swap"))
        assert resp == {"answer": "propose"}


class TestGuards:
    def test_no_tools_returns_none(self):
        resp, _ = _run(ToolBrainResult(status=ST_ANSWERED, answer="x"), tools_nonempty=False)
        assert resp is None

    def test_loop_exception_falls_through(self):
        meta = ResponseMetadata(source_type=SourceType.LLM, tools_used=[])
        fake_svc = MagicMock()
        fake_svc.run.side_effect = RuntimeError("boom")
        with patch("src.coordinator.services.tool_brain_service.ToolBrainService",
                   return_value=fake_svc), \
             patch("src.coordinator.tools.registry.registry.definitions_for_persona",
                   return_value=[{"function": {"name": "image_search"}}]):
            resp = chat_mod._try_tool_brain(
                card=CARD, system="s", body=_body(), history=[], intent=QueryIntent.NEEDS_NEITHER,
                metadata=meta, persona_name="Gwen", deps={"brave_client": None})
        assert resp is None


class TestFlagGating:
    def test_flag_default_off(self):
        from src.coordinator.config import ToolBrainSettings
        assert ToolBrainSettings.model_fields["enabled"].default is False
