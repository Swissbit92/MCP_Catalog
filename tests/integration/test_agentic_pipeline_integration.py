# test_agentic_pipeline_integration.py
# HERMES-Agents Phase 3 — live integration checks (require Ollama). Skipped
# headless (OLLAMA_BASE unreachable). These validate the two model-dependent
# claims that the headless unit/eval suites cannot: (1) grammar-constrained
# argument extraction actually conforms on the real Magidonia-24B, and (2) the
# full pipeline renders a tool result in-character without leaking tool grammar.

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from coordinator.services.argument_extractor import ArgumentExtractor


@pytest.mark.requires_ollama
def test_structured_output_conforms_on_real_model():
    """Ollama format=<schema> yields schema-conformant args on the live model."""
    ex = ArgumentExtractor()  # real ollama client, real PERSONA_MODEL
    samples = [
        "what's the current bitcoin price?",
        "look up the latest ethereum news",
        "search for solana staking yields",
    ]
    conformant = 0
    for msg in samples:
        args, structured = ex.extract("brave_web_search", msg)
        if structured and isinstance(args.get("query"), str) and args["query"].strip():
            conformant += 1
    # Allow one miss to the regex fallback; the grammar path should dominate.
    assert conformant >= len(samples) - 1


@pytest.mark.requires_ollama
def test_full_agentic_pipeline_renders_in_character():
    """End-to-end: deterministic execute -> in-voice render, no grammar leak.

    Brave is mocked (no API key needed) so this isolates the model-dependent
    rendering stage; the search executor returns canned results.
    """
    from coordinator.services.agentic_pipeline import AgenticPipeline
    from coordinator.services.tool_interceptor import ToolCallInterceptor
    from coordinator.services.injection_guard import InjectionGuard
    from coordinator.llm_client import create_llm_client
    from coordinator.tools.tool_utils import format_search_results_for_llm

    eeva = {"key": "nephilim_eeva", "mcp_access": ["brave_search", "solana_wallet"]}

    def fake_brave(args):
        return [{"title": "BTC hits 91k", "url": "http://x", "snippet": "Bitcoin rose to $91,000."}]

    class _FakeExtractor:
        def extract(self, tool, msg, ctx=""):
            return ({"query": "bitcoin price"}, True)

    pipeline = AgenticPipeline(
        interceptor=ToolCallInterceptor(),
        injection_guard=InjectionGuard(),
        extractor=_FakeExtractor(),
        tool_executors={"brave_web_search": fake_brave},
        llm_complete_fn=lambda system, user: create_llm_client(eeva).complete(
            system=system, user_prompt=user),
        result_formatters={"brave_web_search": format_search_results_for_llm},
    )
    res = pipeline.execute(
        intent_tool="brave_web_search",
        user_message="what's the bitcoin price?",
        persona_system="You are E.E.V.A., the Archon. Sardonic, precise. Address the user as 'seeker'.",
        persona_card=eeva,
    )
    assert res.was_blocked is False
    assert res.rendered_response.strip()
    low = res.rendered_response.lower()
    # No leaked tool grammar / assistant-mode reversion.
    assert "brave_web_search" not in low
    assert "function_call" not in low
    assert "as an ai" not in low
