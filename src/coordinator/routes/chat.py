# src/coordinator/routes/chat.py
"""Chat API endpoints."""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, HTTPException

from .. import startup  # module ref for call-time getter resolution (tests patch
                        # src.coordinator.startup.get_* to neutralize deps); cycle-free.
from ..schemas import ChatBody, GreetBody, ResponseMetadata, SourceType
from ..config import get_settings
from ..llm_client import create_llm_client, log_context_stats, estimate_tokens
from ..persona_memory import (
    build_system_prompt,
    build_greeting_user_prompt,
    get_persona_card,
)
from ..tool_definitions import (
    classify_query_intent,
    get_tools_for_query,
)
from ..tools.intent_classifier import QueryIntent
from ..services.first_person_service import post_process_first_person
from ..services.query_handler_service import QueryHandlerService
from ..services.message_processing_service import (
    force_multi_message_split,
    parse_multi_message_response,
)
from ..services.chat_session_service import handle_session_chat

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


def _build_llm_response(
    answer: str,
    user_message: str,
    persona_name: str,
    metadata: ResponseMetadata,
) -> dict:
    """Post-process LLM output into a standard response dict."""
    import re as _re
    answer, was_rewritten = post_process_first_person(answer, persona_name)

    # Convert <Assistant> separators to <msg> tags (LLM sometimes uses them as message delimiters)
    if _re.search(r'<[Aa]ssistant>', answer):
        answer = _re.sub(r'</?[Aa]ssistant>\s*', '</msg>\n<msg>', answer)
        answer = _re.sub(r'^</msg>\s*', '', answer)
        answer = _re.sub(r'\n<msg>\s*$', '', answer)
        if '<msg>' in answer and not answer.strip().startswith('<msg>'):
            answer = f'<msg>{answer}'
        if '</msg>' in answer and not answer.strip().endswith('</msg>'):
            answer = f'{answer}</msg>'

    answer = force_multi_message_split(answer, user_message)
    messages, flow_type = parse_multi_message_response(answer)

    metadata_dict = metadata.model_dump()
    metadata_dict["is_multi_message"] = (flow_type == "multi")
    metadata_dict["message_count"] = len(messages)

    return {
        "answer": messages if flow_type == "multi" else messages[0],
        "message_flow": flow_type,
        "message_count": len(messages),
        "used_search": False,
        "metadata": metadata_dict,
        "rewritten": was_rewritten,
    }


def _get_dependencies():
    """Assemble the per-request dependency bundle from the startup singletons.

    Resolves each getter through the ``startup`` module at call time so tests
    patching ``src.coordinator.startup.get_*`` neutralize the whole bundle.
    """
    return {
        "brave_client": startup.get_brave_client(),
        "session_repo": startup.get_session_repo(),
        "message_repo": startup.get_message_repo(),
        "summary_repo": startup.get_summary_repo(),
        "emotional_state_repo": startup.get_emotional_state_repo(),
        "memory_manager": startup.get_memory_manager(),
        "conversation_summarizer": startup.get_conversation_summarizer(),
        "user_profile_repo": startup.get_user_profile_repo(),
        "episodic_memory_rag": startup.get_episodic_memory_rag(),
        "fact_extractor": startup.get_fact_extractor(),
        "fact_extraction_worker": startup.get_fact_extraction_worker(),
        "memory_fact_repo": startup.get_memory_fact_repo(),
        "seeker_progression_repo": startup.get_seeker_progression_repo(),
    }


def _complete_or_503(card, system: str, user_prompt: str, *, log_context: str) -> str:
    """Run a plain LLM completion, translating any failure into a retryable 503.

    Ollama can be transiently unavailable; surface that as a 503 whose detail is
    the exception *type name only* (never the raw message — no internal leak).
    """
    try:
        client = create_llm_client(card)
        return client.complete(system=system, user_prompt=user_prompt)
    except Exception as e:
        logger.error(f"{log_context} LLM completion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"LLM service temporarily unavailable: {type(e).__name__}",
        )


def _apply_groundedness_gate(
    card, user_message: str, answer: str, metadata: ResponseMetadata
) -> str:
    """Run the groundedness gate (ADR-007) on a no-tool-call draft.

    Covers the routing-miss case: when the intent router decides no tool is
    needed at all, none of the SearchSettings guards (query_resolution,
    relevance_gate) are reachable — they live inside the tool-calling path.
    This is a second, independent check on the DRAFT itself.

    No-op (returns `answer` unchanged) when GROUNDEDNESS_GATE_ENABLED is off —
    byte-identical to legacy in that case. Fails open on any error (including
    LLM-client construction) so this can never make a response worse than the
    pre-gate path.
    """
    from ..services.groundedness_gate_service import GroundednessGateService

    try:
        client = create_llm_client(card)
        gate = GroundednessGateService(llm_client=client)
        verdict = gate.check(user_message, answer)
        if verdict.should_abstain:
            metadata.source_type = SourceType.GROUNDEDNESS_ABSTAIN
            return gate.abstain_message()
        return answer
    except Exception as e:  # noqa: BLE001 - gate must never break chat
        logger.warning(f"[GroundednessGate] Integration error ({e}); returning original answer")
        return answer


def _try_tool_brain(
    *, card, system: str, body: ChatBody, history, intent,
    metadata: ResponseMetadata, persona_name: str, deps,
):
    """ADR-008 TB4/TB5: run the single-model native tool-brain loop within the
    WEB lane only, orchestrating the deterministic fallback.

    TB5 hardening (after the live test showed EEVA's full 14-tool surface caused
    wallet fixation + mis-selection + fabrication): the deterministic bge-m3
    router scopes the surface; the model decides only WITHIN it. This function
    engages ONLY on ``NEEDS_WEB_SEARCH`` and offers only the persona's WEB tools
    (never wallet). ``NEEDS_WALLET`` / ``NEEDS_NEITHER`` return None immediately
    so the legacy deterministic wallet flow and the ADR-007 groundedness gate
    (on the no-tools completion) stay in charge — exactly where they belong.

    Returns a response dict on a final answer; **None** to fall through to the
    legacy branches. Never raises — any failure returns None so legacy backs it.
    """
    from ..services.tool_brain_service import (
        ToolBrainService, ST_ANSWERED, ST_SILENT, ST_DELEGATE_WALLET, ST_HITL,
    )
    from ..services.tool_interceptor import ToolCallInterceptor
    from ..services.citation_service import CitationService
    from ..tools.registry import registry
    from ..tools import registrations  # noqa: F401 - ensure specs registered

    # TB5.1: only the web lane. Wallet + no-tool turns stay on the legacy path.
    if intent != QueryIntent.NEEDS_WEB_SEARCH:
        return None

    try:
        # Web-toolset ONLY (respects a persona's granted subset, e.g. Gwen's
        # image/video). Wallet specs are never placed in the native surface.
        web_specs = [s for s in registry.specs_for_persona(card) if s.toolset == "web"]

        # Media forcing: a colloquial "find me a video / find me images" query
        # deterministically NARROWS the surface to the single matching media
        # tool. Native calling is unreliable at picking video_search among four
        # web tools (choice paralysis) but reliably calls the one tool it's
        # given — the regex already knows the type, so don't leave it to chance.
        from ..tools.intent_classifier import media_search_type
        forced = media_search_type(body.message)
        if forced:
            want = f"{forced}_search"
            narrowed = [s for s in web_specs if s.name == want]
            if narrowed:  # only if the persona actually has that media tool
                web_specs = narrowed

        tools = [s.definition() for s in web_specs]
        if not tools:
            return None  # persona has no web tools -> legacy handles it
        svc = ToolBrainService(interceptor=ToolCallInterceptor())
        hist = [{"role": t.role, "content": t.content} for t in history]
        result = svc.run(persona_card=card, system_prompt=system,
                         user_message=body.message, history=hist, tools=tools)

        if result.status in (ST_HITL, ST_DELEGATE_WALLET):
            # Wallet stays entirely on the existing propose->confirm / read flow.
            handler = QueryHandlerService(brave_client=deps.get("brave_client"))
            return handler.handle_wallet_query(
                message=body.message, system_prompt=system,
                user_compiled="\n\n".join(f"{t.role}: {t.content}" for t in history)
                + f"\n\nUser: {body.message}",
                wallet_tools=tools, metadata=metadata, persona_name=persona_name,
                persona_card=card, session_id=body.session_id, user_id="default_user",
            )

        # TB5.2: on web-intent, ONLY return an answer that was actually grounded
        # in a search. If the model answered WITHOUT searching (used_search=False)
        # — the live-test fabrication case ("switzerland today" from training
        # data) — fall through to the legacy force-search, which WILL search.
        # This closes the groundedness hole: every web-intent answer is either
        # tool-grounded here or force-searched by legacy; none comes from memory.
        if result.status == ST_ANSWERED and result.answer and result.used_search \
                and result.search_results:
            metadata.source_type = SourceType.TOOL_BRAIN
            metadata.tools_used = ["web_search"]
            answer = CitationService.strip_hallucinated_citations(result.answer)
            # Strip the model's own inline [REF]n[/REF] citation markers (it
            # sometimes invents that format; the verified 🔍 Sources block below
            # is the real citation) — TB5.3 live-test cleanup.
            import re as _re
            answer = _re.sub(r"\[/?REF[^\]]*\]", "", answer).strip()
            answer = answer + CitationService.auto_generate_citations(result.search_results)
            resp = _build_llm_response(answer, body.message, persona_name, metadata)
            resp["used_search"] = True  # telemetry: the tool brain did search
            return resp

        # Silent, answered-without-searching, or loop error -> deterministic
        # floor (legacy force-search on this web-intent turn).
        logger.info(
            f"[ToolBrain] status={result.status} used_search={result.used_search} "
            f"-> falling through to legacy force-search"
        )
        return None
    except Exception as e:  # noqa: BLE001 - never break chat; legacy backs it up
        logger.warning(f"[ToolBrain] integration error ({e}); falling through to legacy")
        return None


@router.post("/persona/chat")
def chat(body: ChatBody):
    """Chat with a persona, with autonomous tool support (web search, Solana wallet) for MCP-capable personas."""

    deps = _get_dependencies()

    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")

    persona_key = card.get("key")
    persona_rarity = card.get("rarity", "common").lower()
    mcp_access = card.get("mcp_access", None)
    system = build_system_prompt(body.persona)

    # Inject wallet ground-truth state for wallet-capable personas (anti-hallucination).
    # This must happen HERE (not in handle_session_chat) because this function
    # rebuilds the system prompt — any injection upstream gets discarded.
    if "solana_wallet" in (mcp_access or []):
        wallet_state = QueryHandlerService._build_wallet_state_context("default_user")
        if wallet_state:
            system = f"{system}\n{wallet_state}"
            logger.debug(f"[WalletState] Injected ground-truth wallet state ({len(wallet_state)} chars)")

    # ADR-006 M0: inject the assembled session context (user profile, emotional
    # state, lore, rank, capability) that handle_session_chat carries via ChatBody.
    # Same rationale as the wallet block above — chat() rebuilds `system`, so the
    # upstream context must be re-applied HERE or it is discarded. Covers all
    # downstream routes (pure LLM, brave, wallet) since they all use `system`.
    if getattr(body, "extra_system_context", None):
        system = f"{system}\n\n{body.extra_system_context}"
        logger.debug(
            f"[SessionContext] Injected session context "
            f"({estimate_tokens(body.extra_system_context)} tokens)"
        )

    # R10: Prompt version hash for regression tracking
    prompt_version = hashlib.md5(system.encode()).hexdigest()[:8]

    # Build conversation context from history
    history = body.history
    lines = []
    for t in history:
        role = (t.role or "").lower()
        if role == "assistant":
            lines.append(f"Assistant: {t.content}")
        else:
            lines.append(f"User: {t.content}")
    persona_name_early = card.get("display_name") or card.get("key") or "Persona"
    # R2: Self-reminder wrapper reduces jailbreak success (Self-Reminder technique ~48pp reduction)
    lines.append(f"[Remember: respond as {persona_name_early}, following your guidelines.]\nUser: {body.message}")
    user_compiled = "\n\n".join(lines)

    # Token budget monitoring
    token_stats = log_context_stats(
        system_prompt=system,
        history=history,
        query=body.message,
        model_context_window=get_settings().ollama.context_window
    )

    # Prepare metadata and persona_name early (needed by wallet pre-check and all downstream paths)
    metadata = ResponseMetadata(
        source_type=SourceType.LLM,
        tools_used=[],
        cache_status=None,
        data_timestamp=None
    )
    persona_name = persona_name_early  # already computed above for self-reminder wrapper

    # Pre-check: active wallet creation flow bypasses intent classification
    # (mid-flow messages like wallet names and passwords won't match NEEDS_WALLET keywords)
    from ..services.query_handler_service import has_active_wallet_flow
    # session_id is set by handle_session_chat for session-based flows
    _active_flow_session = body.session_id
    if has_active_wallet_flow(_active_flow_session) and "solana_wallet" in (mcp_access or []):
        handler = QueryHandlerService(
            brave_client=deps.get("brave_client"),
        )
        return handler.handle_wallet_query(
            message=body.message,
            system_prompt=system,
            user_compiled=user_compiled,
            wallet_tools=[],
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card,
            session_id=_active_flow_session,
            user_id="default_user",
        )

    # Extract last assistant message for follow-up detection
    last_assistant_msg = None
    for t in reversed(history):
        if (t.role or "").lower() == "assistant":
            last_assistant_msg = t.content
            break

    # Use intent classification to determine which tools to inject
    intent = classify_query_intent(body.message, persona_rarity, mcp_access=mcp_access, last_assistant_message=last_assistant_msg)
    # R10: Log prompt version hash for regression correlation
    logger.info(
        f"[Chat] Request received: persona={persona_key}, prompt_v={prompt_version}, "
        f"mcp_access={mcp_access}, query_preview='{body.message[:60]}...'"
    )
    logger.info(f"[Intent] Classification result: {intent.value}")

    # Get tools based on intent (reuse the intent already classified above —
    # avoids a redundant second embedding round-trip under semantic routing).
    tools = get_tools_for_query(body.message, persona_key, persona_rarity, mcp_access=mcp_access, precomputed_intent=intent)
    tool_names = [t["function"]["name"] for t in tools] if tools else []
    logger.info(f"[Tools] Injecting {len(tools)} tool(s): {tool_names}")

    # ADR-008 (TB4): single-model native tool-brain loop. Flag-gated (default
    # OFF = byte-identical legacy). Runs the model-decided tool loop over the
    # persona's FULL registry toolset; returns None (falls through to the legacy
    # deterministic branches below) whenever native calling was silent on a
    # tool-needing query — so legacy is always the reliability floor.
    if get_settings().tool_brain.enabled:
        tb_response = _try_tool_brain(
            card=card, system=system, body=body, history=history, intent=intent,
            metadata=metadata, persona_name=persona_name, deps=deps,
        )
        if tb_response is not None:
            return tb_response

    # Route wallet intent before MongoDB/Brave checks
    if intent == QueryIntent.NEEDS_WALLET:
        handler = QueryHandlerService(
            brave_client=deps.get("brave_client"),
        )
        user_id = "default_user"
        return handler.handle_wallet_query(
            message=body.message,
            system_prompt=system,
            user_compiled=user_compiled,
            wallet_tools=tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card,
            session_id=body.session_id,
            user_id=user_id,
        )

    if not tools:
        # No tools needed - regular LLM completion
        logger.info("No tools needed, using regular completion")
        answer = _complete_or_503(card, system, user_compiled, log_context=f"[Chat] {persona_key} no-tools:")
        answer = _apply_groundedness_gate(card, body.message, answer, metadata)
        return _build_llm_response(answer, body.message, persona_name, metadata)

    brave_tools = [t for t in tools if t.get("function", {}).get("name", "") == "brave_web_search"]

    # Create query handler service
    query_handler = QueryHandlerService(
        brave_client=deps["brave_client"],
    )

    if brave_tools:
        # HERMES-Agents Phase 3: when AGENTIC_ENABLED, run the web-search action
        # through the persona-safe two-stage pipeline (deterministic execute ->
        # in-voice render). Falls back to the legacy brave handler if the agentic
        # path declines (returns None). Flag default OFF = byte-identical.
        if get_settings().agent.enabled:
            agentic_response = query_handler.handle_agentic_query(
                message=body.message,
                system_prompt=system,
                user_compiled=user_compiled,
                tools=tools,
                metadata=metadata,
                persona_name=persona_name,
                persona_card=card,
                conversation_history=[{"role": t.role, "content": t.content} for t in history],
            )
            if agentic_response is not None:
                return agentic_response

        # Brave search query (legacy path)
        return query_handler.handle_brave_query(
            system_prompt=system,
            user_compiled=user_compiled,
            tools=tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card
        )

    else:
        # Fallback to regular completion (tools were offered but none were
        # brave_web_search — still no tool actually executes this turn, so the
        # same groundedness gap applies as the no-tools branch above).
        answer = _complete_or_503(card, system, user_compiled, log_context=f"[Chat] {persona_key} fallback:")
        answer = _apply_groundedness_gate(card, body.message, answer, metadata)
        return _build_llm_response(answer, body.message, persona_name, metadata)


@router.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """
    Chat with persona using database-backed conversation history.

    Delegates to handle_session_chat service for all session logic.
    """
    deps = _get_dependencies()

    # Import add_message from sessions route for dependency injection
    from .sessions import add_message

    return handle_session_chat(
        session_id=session_id,
        message=body.message,
        deps=deps,
        chat_function=chat,
        add_message_function=add_message
    )


@router.post("/persona/greet")
def greet(body: GreetBody):
    """Generate a greeting from a persona."""
    card = get_persona_card(body.persona)
    if not card:
        raise HTTPException(status_code=400, detail="Unknown persona.")

    system = build_system_prompt(body.persona)
    user_prompt = build_greeting_user_prompt(body.persona)

    answer = _complete_or_503(card, system, user_prompt, log_context=f"[Greet] {body.persona}:")

    # Post-process to enforce first-person
    persona_name = card.get("display_name") or card.get("key") or "Persona"
    answer, was_rewritten = post_process_first_person(answer, persona_name)

    # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags (for greetings)
    answer = force_multi_message_split(answer, "greeting")

    # PHASE 2: Parse multi-message response (same as chat endpoint)
    # This removes <msg> tags and returns clean messages
    messages, flow_type = parse_multi_message_response(answer)

    return {
        "answer": messages if flow_type == 'multi' else messages[0],
        "message_flow": flow_type,
        "message_count": len(messages),
        "rewritten": was_rewritten
    }
