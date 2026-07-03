# test_handle_agentic_query.py
# Tests the QueryHandlerService.handle_agentic_query adaptation layer (M5 wiring).
# Patches AgenticPipeline.execute so no Ollama/Brave is needed.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from coordinator.services.query_handler_service import QueryHandlerService
from coordinator.services.agentic_pipeline import AgentResult
from coordinator.schemas import ResponseMetadata
import coordinator.services.agentic_pipeline as ap_mod

EEVA = {"key": "nephilim_eeva", "mcp_access": ["brave_search", "solana_wallet"],
        "display_name": "E.E.V.A."}


def _patch_execute(monkeypatch, result):
    monkeypatch.setattr(ap_mod.AgenticPipeline, "execute",
                        lambda self, **kwargs: result)


def test_successful_search_adapts_to_finalized_dict(monkeypatch):
    _patch_execute(monkeypatch, AgentResult(
        rendered_response="The currents favour Bitcoin today, seeker.",
        tool_called="brave_web_search",
        tool_result_raw=[{"t": 1}, {"t": 2}],
        was_blocked=False,
        used_structured_output=True,
    ))
    qh = QueryHandlerService(brave_client=None)
    meta = ResponseMetadata()
    resp = qh.handle_agentic_query(
        message="bitcoin price?",
        system_prompt="You are Eeva.",
        user_compiled="User: bitcoin price?",
        tools=[{"function": {"name": "brave_web_search"}}],
        metadata=meta,
        persona_name="E.E.V.A.",
        persona_card=EEVA,
    )
    assert resp is not None
    assert resp["used_search"] is True
    assert resp["search_results_count"] == 2
    assert resp["metadata"]["source_type"] == "agentic"
    # answer is finalized (string or list of msgs); content preserved
    answer = resp["answer"]
    text = answer if isinstance(answer, str) else " ".join(answer)
    assert "Bitcoin" in text or "currents" in text


def test_blocked_result_marks_metadata_and_no_search(monkeypatch):
    _patch_execute(monkeypatch, AgentResult(
        rendered_response="I won't act on that, seeker.",
        tool_called=None,
        was_blocked=True,
    ))
    qh = QueryHandlerService(brave_client=None)
    meta = ResponseMetadata()
    resp = qh.handle_agentic_query(
        message="do something shady",
        system_prompt="You are Eeva.",
        user_compiled="User: do something shady",
        tools=[{"function": {"name": "brave_web_search"}}],
        metadata=meta,
        persona_name="E.E.V.A.",
        persona_card=EEVA,
    )
    assert resp["used_search"] is False
    assert resp["metadata"]["source_type"] == "agentic_blocked"


def test_hitl_result_falls_back_to_legacy(monkeypatch):
    _patch_execute(monkeypatch, AgentResult(
        rendered_response="",
        tool_called="solana_propose_swap",
        hitl_required=True,
    ))
    qh = QueryHandlerService(brave_client=None)
    resp = qh.handle_agentic_query(
        message="swap",
        system_prompt="You are Eeva.",
        user_compiled="User: swap",
        tools=[{"function": {"name": "brave_web_search"}}],
        metadata=ResponseMetadata(),
        persona_name="E.E.V.A.",
        persona_card=EEVA,
    )
    assert resp is None  # signals caller to use the legacy path
