# src/coordinator/routes/chat.py
"""Chat API endpoints."""

from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..schemas import ChatBody, GreetBody, ChatTurn, AppendMessageBody, ResponseMetadata
from ..config import (
    get_ollama_base,
    get_persona_model,
    get_persona_temperature,
    get_persona_temperature_override,
    get_model_context_window,
    get_summarization_interval,
    get_fact_extraction_interval,
    get_temp_summarization,
    get_temp_fact_extraction,
)
from ..llm_client import LC_OllamaClient, estimate_tokens, log_context_stats
from ..persona_memory import (
    build_system_prompt,
    build_greeting_user_prompt,
    get_persona_card,
)
from ..tool_definitions import (
    classify_query_intent,
    get_tools_for_query,
)
from ..services.first_person_service import post_process_first_person
from ..services.query_handler_service import QueryHandlerService
from ..services.message_processing_service import (
    force_multi_message_split,
    parse_multi_message_response,
)
from ..services.chat_session_service import handle_session_chat

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


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
    system = build_system_prompt(body.persona)

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
        model_context_window=get_model_context_window()
    )

    # Use intent classification to determine which tools to inject
    intent = classify_query_intent(body.message, persona_rarity)
    logger.info(f"[Chat] Request received: persona={persona_key}, rarity={persona_rarity}, query_preview='{body.message[:60]}...'")
    logger.info(f"[Intent] Classification result: {intent.value}")

    # Get tools based on intent
    tools = get_tools_for_query(body.message, persona_key, persona_rarity)
    tool_names = [t["function"]["name"] for t in tools] if tools else []
    logger.info(f"[Tools] Injecting {len(tools)} tool(s): {tool_names}")

    # Prepare metadata
    metadata = ResponseMetadata(
        source_type="llm",
        tools_used=[],
        cache_status=None,
        data_timestamp=None
    )

    persona_name = card.get("display_name") or card.get("key") or "Persona"

    if not tools:
        # No tools needed - regular LLM completion
        logger.info("No tools needed, using regular completion")
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature_override(card)
        )
        answer = client.complete(system=system, user_prompt=user_compiled)

        # Post-process to enforce first-person
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags
        answer = force_multi_message_split(answer, body.message)

        # PHASE 2: Parse for multi-message format
        messages, flow_type = parse_multi_message_response(answer)

        # Update metadata with multi-message info
        metadata_dict = metadata.model_dump()
        metadata_dict["is_multi_message"] = (flow_type == 'multi')
        metadata_dict["message_count"] = len(messages)

        return {
            "answer": messages if flow_type == 'multi' else messages[0],
            "message_flow": flow_type,
            "message_count": len(messages),
            "used_search": False,
            "metadata": metadata_dict,
            "rewritten": was_rewritten
        }

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
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature_override(card)
        )
        answer = client.complete(system=system, user_prompt=user_compiled)
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags
        answer = force_multi_message_split(answer, body.message)

        # PHASE 2: Parse for multi-message format
        messages, flow_type = parse_multi_message_response(answer)
        metadata_dict = metadata.model_dump()
        metadata_dict["is_multi_message"] = (flow_type == 'multi')
        metadata_dict["message_count"] = len(messages)

        return {
            "answer": messages if flow_type == 'multi' else messages[0],
            "message_flow": flow_type,
            "message_count": len(messages),
            "used_search": False,
            "metadata": metadata_dict,
            "rewritten": was_rewritten
        }


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

    client = LC_OllamaClient(
        base=get_ollama_base(),
        model=get_persona_model(),
        temperature=get_persona_temperature_override(card),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)

    # Post-process to enforce first-person
    persona_name = card.get("display_name") or card.get("key") or "Persona"
    answer, was_rewritten = post_process_first_person(answer, persona_name)

    # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags (for greetings)
    # Note: Greetings don't use the multi-message response format in API, but we still
    # apply force-split for consistency and potential future use
    answer = force_multi_message_split(answer, "greeting")

    return {"answer": answer, "rewritten": was_rewritten}
