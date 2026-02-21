# src/coordinator/routes/chat.py
"""Chat API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas import ChatBody, GreetBody, ChatTurn, AppendMessageBody, ResponseMetadata
from ..config import get_settings
from ..llm_client import create_llm_client, estimate_tokens, log_context_stats
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
    answer, was_rewritten = post_process_first_person(answer, persona_name)
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
    """Get dependencies from startup module."""
    from ..startup import (
        get_brave_client,
        get_mongodb_service,
        get_session_repo,
        get_message_repo,
        get_summary_repo,
        get_emotional_state_repo,
        get_memory_manager,
        get_conversation_summarizer,
        get_user_profile_repo,
        get_episodic_memory_rag,
        get_fact_extractor,
        get_seeker_progression_repo,
    )
    return {
        "brave_client": get_brave_client(),
        "mongodb_service": get_mongodb_service(),
        "session_repo": get_session_repo(),
        "message_repo": get_message_repo(),
        "summary_repo": get_summary_repo(),
        "emotional_state_repo": get_emotional_state_repo(),
        "memory_manager": get_memory_manager(),
        "conversation_summarizer": get_conversation_summarizer(),
        "user_profile_repo": get_user_profile_repo(),
        "episodic_memory_rag": get_episodic_memory_rag(),
        "fact_extractor": get_fact_extractor(),
        "seeker_progression_repo": get_seeker_progression_repo(),
    }


@router.post("/persona/chat")
def chat(body: ChatBody):
    """Chat with a persona, with autonomous tool support (web search + MongoDB) for higher rarity personas."""
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
        from ..services.query_handler_service import QueryHandlerService
        wallet_state = QueryHandlerService._build_wallet_state_context("default_user")
        if wallet_state:
            system = f"{system}\n{wallet_state}"
            logger.debug(f"[WalletState] Injected ground-truth wallet state ({len(wallet_state)} chars)")

    # Build conversation context from history
    history = body.history
    lines = []
    for t in history:
        role = (t.role or "").lower()
        if role == "assistant":
            lines.append(f"Assistant: {t.content}")
        else:
            lines.append(f"User: {t.content}")
    lines.append(f"User: {body.message}")
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
        source_type="llm",
        tools_used=[],
        cache_status=None,
        data_timestamp=None
    )
    persona_name = card.get("display_name") or card.get("key") or "Persona"

    # Pre-check: active wallet creation flow bypasses intent classification
    # (mid-flow messages like wallet names and passwords won't match NEEDS_WALLET keywords)
    from ..services.query_handler_service import has_active_wallet_flow
    # ChatBody has no session_id — wallet flows are only active in session-based chat
    _active_flow_session = None
    if has_active_wallet_flow(_active_flow_session) and "solana_wallet" in (mcp_access or []):
        handler = QueryHandlerService(
            brave_client=deps.get("brave_client"),
            mongodb_service=deps.get("mongodb_service"),
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
    logger.info(f"[Chat] Request received: persona={persona_key}, rarity={persona_rarity}, query_preview='{body.message[:60]}...'")
    logger.info(f"[Intent] Classification result: {intent.value}")

    # Get tools based on intent
    tools = get_tools_for_query(body.message, persona_key, persona_rarity, mcp_access=mcp_access)
    tool_names = [t["function"]["name"] for t in tools] if tools else []
    logger.info(f"[Tools] Injecting {len(tools)} tool(s): {tool_names}")

    # Route wallet intent before MongoDB/Brave checks
    if intent == QueryIntent.NEEDS_WALLET:
        handler = QueryHandlerService(
            brave_client=deps.get("brave_client"),
            mongodb_service=deps.get("mongodb_service"),
        )
        user_id = "default_user"
        session_id = None
        return handler.handle_wallet_query(
            message=body.message,
            system_prompt=system,
            user_compiled=user_compiled,
            wallet_tools=tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card,
            session_id=session_id,
            user_id=user_id,
        )

    if not tools:
        # No tools needed - regular LLM completion
        logger.info("No tools needed, using regular completion")
        client = create_llm_client(card)
        answer = client.complete(system=system, user_prompt=user_compiled)
        return _build_llm_response(answer, body.message, persona_name, metadata)

    # Tools needed - check if MongoDB tools are included
    mongodb_tools = [t for t in tools if t.get("function", {}).get("name", "").startswith("bitcoin_")]
    brave_tools = [t for t in tools if t.get("function", {}).get("name", "") == "brave_web_search"]

    # Create query handler service
    query_handler = QueryHandlerService(
        brave_client=deps["brave_client"],
        mongodb_service=deps["mongodb_service"]
    )

    if mongodb_tools and not brave_tools:
        # MongoDB-only query
        return query_handler.handle_mongodb_query(
            message=body.message,
            system_prompt=system,
            user_compiled=user_compiled,
            mongodb_tools=mongodb_tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card
        )

    elif brave_tools and not mongodb_tools:
        # Brave-only query
        return query_handler.handle_brave_query(
            system_prompt=system,
            user_compiled=user_compiled,
            tools=tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card
        )

    elif brave_tools and mongodb_tools:
        # Multi-MCP query
        return query_handler.handle_multi_mcp_query(
            system_prompt=system,
            user_compiled=user_compiled,
            brave_tools=brave_tools,
            metadata=metadata,
            persona_name=persona_name,
            persona_card=card
        )

    else:
        # Fallback to regular completion
        client = create_llm_client(card)
        answer = client.complete(system=system, user_prompt=user_compiled)
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

    client = create_llm_client(card)
    answer = client.complete(system=system, user_prompt=user_prompt)

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
