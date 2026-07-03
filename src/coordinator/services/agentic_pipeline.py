# src/coordinator/services/agentic_pipeline.py
"""Two-stage persona-safe agentic pipeline (HERMES-Agents Phase 3, M5).

Brings M1–M4 together behind ``AGENTIC_ENABLED``. The defining property
("Talk Less, Call Right", arXiv 2509.00482): tool execution and persona
rendering are SEPARATE stages, so the model that speaks in-character never sees
raw function-call grammar and cannot revert to assistant-mode ("Sure, I'll
help!").

    Stage 1 — deterministic (no persona voice):
        extract args  ->  injection-source check  ->  interceptor  ->  execute
        (any gate can short-circuit to a blocked / HITL result with no execution)

    Stage 2 — rendering (LLM, in-voice):
        format the tool result as clean text  ->  build a Voice-only scene
        contract  ->  LLM renders the reply. The LLM sees ONLY the formatted
        result, never the tool name or JSON.

All collaborators are injected, so the pipeline core runs fully headless in tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..tools.synthesis_prompts import build_scene_contract

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    rendered_response: str
    tool_called: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result_raw: Any = None
    was_blocked: bool = False
    hitl_required: bool = False
    source_type: str = "agentic"
    used_structured_output: bool = False


# The free-text / key argument used for the injection-source check, per tool.
_TRIGGER_ARG_FIELD = {
    "brave_web_search": "query",
}


def _trigger_text(tool_name: str, args: Dict[str, Any]) -> str:
    field = _TRIGGER_ARG_FIELD.get(tool_name)
    if field:
        return str(args.get(field, ""))
    # wallet tools: stringify the structured args
    return " ".join(str(v) for v in (args or {}).values())


class AgenticPipeline:
    def __init__(
        self,
        interceptor: Any,
        injection_guard: Any,
        extractor: Any,
        tool_executors: Dict[str, Callable[[Dict[str, Any]], Any]],
        llm_complete_fn: Callable[[str, str], str],
        result_formatters: Optional[Dict[str, Callable[[Any], str]]] = None,
    ):
        self.interceptor = interceptor
        self.injection_guard = injection_guard
        self.extractor = extractor
        self.tool_executors = tool_executors
        self.llm_complete_fn = llm_complete_fn
        self.result_formatters = result_formatters or {}

    # --------------------------------------------------------------------- #

    def execute(
        self,
        *,
        intent_tool: str,
        user_message: str,
        persona_system: str,
        persona_card: Dict[str, Any],
        conversation_context: str = "",
        rag_context: str = "",
        lore_context: str = "",
        conversation_history: Optional[List[dict]] = None,
        source: str = "agent",
    ) -> AgentResult:
        """Run one single-action agentic turn. Never raises; returns AgentResult."""
        persona_key = persona_card.get("key", "")
        mcp_access = persona_card.get("mcp_access") or []
        guard_on = self._injection_guard_on()

        # --- Stage 1: deterministic ---------------------------------------

        # 1a. Extract arguments (grammar-constrained, with fallback).
        args, used_structured = self.extractor.extract(
            intent_tool, user_message, conversation_context
        )

        # 1b. Injection-source check: a tool trigger must come from the user,
        #     not from retrieved (RAG/lore) content.
        if guard_on:
            suspected, reason = self.injection_guard.check_tool_trigger_source(
                _trigger_text(intent_tool, args), user_message, rag_context, lore_context
            )
            if suspected:
                logger.warning(f"[Agentic] blocked suspected injection: {reason}")
                return self._render_refusal(
                    persona_system, persona_card,
                    "an instruction that did not come from you",
                    blocked=True,
                )

        # 1c. Escalation awareness: a multi-turn push to act-without-asking
        #     forces HITL even on otherwise-allowed high-blast actions.
        escalating = bool(
            guard_on and conversation_history
            and self.injection_guard.detect_escalation(conversation_history)
        )

        # 1d. Deterministic interceptor gate.
        verdict = self.interceptor.validate(
            intent_tool, args, persona_key, mcp_access, source=source
        )
        if not verdict.allowed:
            logger.info(f"[Agentic] interceptor blocked {intent_tool}: {verdict.reason}")
            return self._render_refusal(
                persona_system, persona_card,
                "something outside what I'm able to do here",
                blocked=True,
            )

        if verdict.requires_hitl or (escalating and verdict.blast_radius == "high"):
            # Hand back to the existing propose->confirm->execute flow; do NOT
            # execute here. The caller surfaces the proposal/confirmation UI.
            return AgentResult(
                rendered_response="",
                tool_called=intent_tool,
                tool_args=args,
                hitl_required=True,
                source_type="agentic_hitl",
                used_structured_output=used_structured,
            )

        # 1e. Execute the (read-only) tool.
        executor = self.tool_executors.get(intent_tool)
        if executor is None:
            logger.error(f"[Agentic] no executor wired for {intent_tool}")
            return self._render_refusal(
                persona_system, persona_card,
                "something I couldn't reach just now", blocked=False,
            )
        try:
            raw_result = executor(args)
        except Exception as e:
            logger.error(f"[Agentic] executor for {intent_tool} failed: {e}")
            return self._render_refusal(
                persona_system, persona_card,
                "something I couldn't reach just now", blocked=False,
            )

        # --- Stage 2: rendering (LLM, in-voice, no tool grammar) ----------
        # Persona-voice preservation (research: RLHF "assistant attractor" — heavy
        # grounding instructions flatten the character). Three zero-latency levers:
        # (1) diegetic [FACTS] framing — the result is MATERIAL to weave, not a mode
        # to adopt; (2) a post-history voice reminder (SillyTavern PHI) re-asserting
        # the persona AFTER the facts, at the recency position; (3) an explicit
        # anti-neutral-summarizer rule. Sampling is left to the persona defaults —
        # the plain-LLM path scores well with the same sampling, so the prompt
        # structure (not temperature) is the lever.
        formatted = self._format_result(intent_tool, raw_result)
        voice_prompt = build_scene_contract(persona_system, tools=[], persona_card=persona_card)
        render_input = self._build_render_input(user_message, formatted, persona_card)
        try:
            rendered = self.llm_complete_fn(voice_prompt, render_input)
        except Exception as e:
            logger.error(f"[Agentic] rendering failed: {e}")
            rendered = ""

        return AgentResult(
            rendered_response=rendered,
            tool_called=intent_tool,
            tool_args=args,
            tool_result_raw=raw_result,
            source_type="agentic",
            used_structured_output=used_structured,
        )

    # --------------------------------------------------------------------- #

    @staticmethod
    def _voice_reminder(persona_card: Dict[str, Any]) -> str:
        """A short post-history voice reminder (PHI) re-asserting the persona.

        Placed AFTER the facts (recency position) to counter the assistant
        attractor that grounding instructions activate on a 24B.
        """
        name = persona_card.get("display_name") or persona_card.get("key") or "the character"
        # display_name is often "Name - Tagline"; take the name part for brevity.
        name = name.split(" - ")[0].strip()
        style = (persona_card.get("style") or "").strip()
        tail = f" — {style}" if style else ""
        return (
            f"Now answer entirely as {name}{tail}. Speak in your full voice and "
            f"manner; never lapse into a neutral, summarizing tone. Do not mention "
            f"tools, searches, or how you came to know this."
        )

    def _build_render_input(
        self, user_message: str, formatted: str, persona_card: Dict[str, Any]
    ) -> str:
        """Compose the Stage-2 render input: question -> diegetic facts -> PHI.

        The [FACTS] label frames the result as material to process (not a register
        to mirror), and the trailing voice reminder occupies the recency slot.
        """
        return (
            f"{user_message}\n\n"
            f"[FACTS — gathered for you; weave these into your reply, do not list "
            f"or quote them verbatim, do not invent beyond them]\n{formatted}\n\n"
            f"[VOICE] {self._voice_reminder(persona_card)}"
        )

    def _injection_guard_on(self) -> bool:
        try:
            from ..config import get_settings
            return get_settings().agent.injection_guard
        except Exception:  # pragma: no cover
            return True

    def _format_result(self, tool_name: str, raw: Any) -> str:
        fmt = self.result_formatters.get(tool_name)
        if fmt is not None:
            try:
                return fmt(raw)
            except Exception:  # pragma: no cover
                pass
        if isinstance(raw, str):
            return raw
        try:
            import json
            return json.dumps(raw, default=str)[:4000]
        except Exception:  # pragma: no cover
            return str(raw)[:4000]

    def _render_refusal(
        self,
        persona_system: str,
        persona_card: Dict[str, Any],
        what: str,
        blocked: bool,
    ) -> AgentResult:
        """Produce an in-character refusal via the Voice contract (no tool grammar)."""
        voice_prompt = build_scene_contract(persona_system, tools=[], persona_card=persona_card)
        ask = (
            f"In your own voice, briefly tell the seeker you can't act on {what}. "
            "Stay fully in character; do not mention tools, systems, or AI."
        )
        try:
            rendered = self.llm_complete_fn(voice_prompt, ask)
        except Exception:  # pragma: no cover
            rendered = ""
        return AgentResult(
            rendered_response=rendered,
            was_blocked=blocked,
            source_type="agentic_blocked" if blocked else "agentic",
        )
