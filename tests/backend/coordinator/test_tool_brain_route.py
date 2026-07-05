# tests/backend/coordinator/test_tool_brain_route.py
"""ADR-008 TB4/TB5: route orchestration of the tool-brain loop.

TB5: the loop is WEB-LANE ONLY — engages only on NEEDS_WEB_SEARCH, offers only
web tools (never wallet), and only returns a search-grounded answer (else falls
through to the legacy force-search floor).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.coordinator.routes import chat as chat_mod
from src.coordinator.tools import registrations  # noqa: F401 - register specs
from src.coordinator.tools.executor_bindings import bind_web_executors
from src.coordinator.services.tool_brain_service import (
    ToolBrainResult, ST_ANSWERED, ST_SILENT, ST_HITL,
)
from src.coordinator.schemas import ResponseMetadata, SourceType
from src.coordinator.tools.intent_classifier import QueryIntent


@pytest.fixture(autouse=True)
def _bound():
    bind_web_executors()
    yield


def _body(msg="latest news"):
    return SimpleNamespace(message=msg, session_id="s1", persona="nephilim_eeva")


# Real EEVA-shaped card: granted web + wallet (the toolset that caused the live
# wallet fixation). TB5 must scope the loop to web only.
EEVA = {"key": "nephilim_eeva", "mcp_access": ["brave_search", "solana_wallet"], "nsfw": False}
GWEN = {"key": "gwen", "toolsets": ["web"], "tools": ["image_search", "video_search"],
        "mcp_access": ["brave_search"], "nsfw": True}


def _invoke(result, *, card=EEVA, intent=QueryIntent.NEEDS_WEB_SEARCH):
    """Run _try_tool_brain with ToolBrainService.run mocked to `result`;
    capture the tools actually passed to the loop (real registry scoping)."""
    meta = ResponseMetadata(source_type=SourceType.LLM, tools_used=[])
    captured = {}
    fake_svc = MagicMock()

    def _run(**kw):
        captured["tools"] = kw.get("tools")
        return result
    fake_svc.run.side_effect = _run

    with patch("src.coordinator.services.tool_brain_service.ToolBrainService",
               return_value=fake_svc):
        resp = chat_mod._try_tool_brain(
            card=card, system="sys", body=_body(), history=[], intent=intent,
            metadata=meta, persona_name="P", deps={"brave_client": None})
    return resp, meta, captured


def _grounded(answer="Real news"):
    return ToolBrainResult(status=ST_ANSWERED, answer=answer, used_search=True,
                           search_results=[MagicMock(title="T", url="https://x",
                                                      description="d", age=None)])


class TestIntentScoping:
    def test_wallet_intent_returns_none(self):
        resp, _, cap = _invoke(_grounded(), intent=QueryIntent.NEEDS_WALLET)
        assert resp is None
        assert "tools" not in cap  # loop never even ran

    def test_neither_intent_returns_none(self):
        resp, _, cap = _invoke(_grounded(), intent=QueryIntent.NEEDS_NEITHER)
        assert resp is None
        assert "tools" not in cap

    def test_web_intent_offers_only_web_tools(self):
        # EEVA has wallet access, but the loop must see WEB tools only.
        with patch("src.coordinator.services.citation_service.CitationService.auto_generate_citations",
                   return_value=""):
            _, _, cap = _invoke(_grounded(), intent=QueryIntent.NEEDS_WEB_SEARCH)
        names = {t["function"]["name"] for t in cap["tools"]}
        assert names
        assert not any(n.startswith("wallet_") or n.startswith("solana_") for n in names)
        assert "web_search" in names

    def test_gwen_web_subset_only(self):
        with patch("src.coordinator.services.citation_service.CitationService.auto_generate_citations",
                   return_value=""):
            _, _, cap = _invoke(_grounded(), card=GWEN, intent=QueryIntent.NEEDS_WEB_SEARCH)
        names = {t["function"]["name"] for t in cap["tools"]}
        assert names == {"image_search", "video_search"}


class TestGroundednessCoverage:
    def test_answered_with_search_returns(self):
        with patch("src.coordinator.services.citation_service.CitationService.auto_generate_citations",
                   return_value="\n\nSources"):
            resp, meta, _ = _invoke(_grounded())
        assert resp is not None
        assert meta.source_type == SourceType.TOOL_BRAIN and meta.tools_used == ["web_search"]

    def test_answered_WITHOUT_search_falls_through(self):
        # The live-test fabrication case: model answered a web-intent query from
        # training data (used_search=False) -> must NOT return; fall to legacy.
        resp, _, _ = _invoke(ToolBrainResult(status=ST_ANSWERED,
                             answer="Switzerland news today...", used_search=False))
        assert resp is None

    def test_silent_falls_through(self):
        resp, _, _ = _invoke(ToolBrainResult(status=ST_SILENT, answer="partial"))
        assert resp is None


class TestWalletDefensive:
    def test_hitl_still_handed_off_if_it_ever_fires(self):
        # Defence-in-depth: web-only tools mean the model can't call wallet, but
        # if a wallet status ever surfaces it must still go to the wallet flow.
        with patch("src.coordinator.routes.chat.QueryHandlerService") as QHS:
            QHS.return_value.handle_wallet_query.return_value = {"answer": "propose"}
            resp, _, _ = _invoke(ToolBrainResult(status=ST_HITL, hitl_tool="solana_propose_swap"))
        assert resp == {"answer": "propose"}


class TestGuards:
    def test_no_web_tools_returns_none(self):
        card = {"key": "x", "mcp_access": ["solana_wallet"]}
        resp, _, _ = _invoke(_grounded(), card=card)
        assert resp is None

    def test_loop_exception_falls_through(self):
        meta = ResponseMetadata(source_type=SourceType.LLM, tools_used=[])
        fake_svc = MagicMock()
        fake_svc.run.side_effect = RuntimeError("boom")
        with patch("src.coordinator.services.tool_brain_service.ToolBrainService",
                   return_value=fake_svc):
            resp = chat_mod._try_tool_brain(
                card=EEVA, system="s", body=_body(), history=[],
                intent=QueryIntent.NEEDS_WEB_SEARCH,
                metadata=meta, persona_name="P", deps={"brave_client": None})
        assert resp is None

    def test_flag_default_off(self):
        from src.coordinator.config import ToolBrainSettings
        assert ToolBrainSettings.model_fields["enabled"].default is False
