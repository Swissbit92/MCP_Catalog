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

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


# PHASE 2: Multi-message response parsing
def _force_multi_message_split(response: str, query: str) -> str:
    """
    Force-split LLM response into multi-message format if it doesn't have <msg> tags.

    PHASE 2 FIX: Since dolphin-llama3:8b doesn't reliably follow <msg> tag instructions,
    this function intelligently splits responses using heuristics.

    Args:
        response: LLM response string (without <msg> tags)
        query: Original user query (used for context)

    Returns:
        Response with <msg> tags applied
    """
    import re

    # Don't split if already has tags
    if '<msg>' in response:
        return response

    # Don't split very short responses (greetings, thanks, etc.)
    if len(response.strip()) < 50:
        return response

    # Strategy 1: Split by paragraphs (double newline)
    paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]

    if len(paragraphs) >= 2:
        # We have natural paragraph breaks - use them
        messages = []
        for para in paragraphs[:4]:  # Cap at 4 messages
            messages.append(f'<msg>{para}</msg>')

        logger.info(f"[Phase2-ForceSplit] Split by paragraphs: {len(messages)} messages")
        return '\n'.join(messages)

    # Strategy 2: Split long single paragraph by sentences
    response_clean = response.strip()

    # Split into sentences (look for period followed by space and capital letter, or question marks)
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_pattern, response_clean)

    if len(sentences) >= 3:
        # Group sentences into 2-3 messages
        messages = []

        # First message: opening sentence(s)
        if len(sentences[0]) < 100 and len(sentences) > 1:
            messages.append(f'<msg>{sentences[0]} {sentences[1]}</msg>')
            remaining_start = 2
        else:
            messages.append(f'<msg>{sentences[0]}</msg>')
            remaining_start = 1

        # Middle messages: group remaining sentences
        remaining = sentences[remaining_start:]
        if remaining:
            # Check if last sentence is a question
            last_sentence = remaining[-1].strip()
            has_question = last_sentence.endswith('?')

            if has_question and len(remaining) > 1:
                # Middle content
                middle = ' '.join(remaining[:-1])
                if middle:
                    messages.append(f'<msg>{middle}</msg>')
                # Question as separate message
                messages.append(f'<msg>{last_sentence}</msg>')
            else:
                # All remaining as one message
                messages.append(f'<msg>{" ".join(remaining)}</msg>')

        # Cap at 4 messages
        messages = messages[:4]

        if len(messages) >= 2:
            logger.info(f"[Phase2-ForceSplit] Split by sentences: {len(messages)} messages")
            return '\n'.join(messages)

    # Strategy 3: Split long response with question at the end
    question_match = re.search(r'(.*?)([.!]\s+)(.+\?)\s*$', response_clean, re.DOTALL)
    if question_match and len(response_clean) > 150:
        main_content = question_match.group(1) + question_match.group(2)
        question = question_match.group(3)

        # Split main content if it's long
        if len(main_content) > 200:
            # Split main content in half
            mid_point = len(main_content) // 2
            # Find nearest sentence break
            split_point = main_content.rfind('. ', 0, mid_point + 50)
            if split_point > 0:
                first_part = main_content[:split_point + 1].strip()
                second_part = main_content[split_point + 1:].strip()
                logger.info(f"[Phase2-ForceSplit] Split with question: 3 messages")
                return f'<msg>{first_part}</msg>\n<msg>{second_part}</msg>\n<msg>{question}</msg>'

        logger.info(f"[Phase2-ForceSplit] Split with question: 2 messages")
        return f'<msg>{main_content.strip()}</msg>\n<msg>{question}</msg>'

    # Strategy 4: For responses 150-300 chars, split at midpoint
    if 150 <= len(response_clean) <= 300:
        # Find a good split point (period, comma, or 'and'/'but')
        mid = len(response_clean) // 2
        split_candidates = [
            response_clean.rfind('. ', mid - 50, mid + 50),
            response_clean.rfind(', and ', mid - 50, mid + 50),
            response_clean.rfind(', but ', mid - 50, mid + 50),
            response_clean.rfind('. But ', mid - 50, mid + 50),
        ]

        split_point = max(split_candidates)
        if split_point > 0:
            first = response_clean[:split_point + 1].strip()
            second = response_clean[split_point + 1:].strip()
            if first and second and len(second) > 20:
                logger.info(f"[Phase2-ForceSplit] Split at midpoint: 2 messages")
                return f'<msg>{first}</msg>\n<msg>{second}</msg>'

    # No good split found - return as single message
    logger.debug(f"[Phase2-ForceSplit] No split applied (length: {len(response_clean)})")
    return response


def _parse_multi_message_response(response: str) -> tuple[list[str], str]:
    """
    Parse LLM response for <msg> tags and split into multiple messages.

    PHASE 2: Enables natural multi-message conversational flow.

    Args:
        response: LLM response string (may contain <msg> tags)

    Returns:
        Tuple of (messages: list[str], flow_type: str)
        - messages: List of individual message strings
        - flow_type: 'single' or 'multi'
    """
    import re

    # Extract all <msg>...</msg> blocks
    msg_pattern = r'<msg>(.*?)</msg>'
    matches = re.findall(msg_pattern, response, re.DOTALL)

    if matches and len(matches) > 1:
        # Multi-message response (2+ messages)
        messages = [m.strip() for m in matches[:4]]  # Cap at 4 messages
        logger.info(f"[Phase2] Parsed {len(messages)} messages from response")
        return (messages, 'multi')
    elif matches and len(matches) == 1:
        # Single message with tags (treat as single)
        return ([matches[0].strip()], 'single')
    else:
        # No tags found, return original response
        return ([response], 'single')


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
            temperature=get_persona_temperature()
        )
        answer = client.complete(system=system, user_prompt=user_compiled)

        # Post-process to enforce first-person
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags
        answer = _force_multi_message_split(answer, body.message)

        # PHASE 2: Parse for multi-message format
        messages, flow_type = _parse_multi_message_response(answer)

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
            persona_name=persona_name
        )

    elif brave_tools and not mongodb_tools:
        # Brave-only query
        return query_handler.handle_brave_query(
            system_prompt=system,
            user_compiled=user_compiled,
            tools=tools,
            metadata=metadata,
            persona_name=persona_name
        )

    elif brave_tools and mongodb_tools:
        # Multi-MCP query
        return query_handler.handle_multi_mcp_query(
            system_prompt=system,
            user_compiled=user_compiled,
            brave_tools=brave_tools,
            metadata=metadata,
            persona_name=persona_name
        )

    else:
        # Fallback to regular completion
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature()
        )
        answer = client.complete(system=system, user_prompt=user_compiled)
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags
        answer = _force_multi_message_split(answer, body.message)

        # PHASE 2: Parse for multi-message format
        messages, flow_type = _parse_multi_message_response(answer)
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


def _check_and_summarize(session_id: str, persona_key: str, deps: dict):
    """Check if summarization is needed and trigger it if necessary."""
    message_repo = deps["message_repo"]
    summary_repo = deps["summary_repo"]
    conversation_summarizer = deps["conversation_summarizer"]

    try:
        all_messages = message_repo.get_messages_by_session(session_id)
        message_count = len(all_messages)
        summary_count = summary_repo.count_summaries(session_id)
        interval = get_summarization_interval()
        messages_summarized = summary_count * interval
        messages_since_summary = message_count - messages_summarized

        if messages_since_summary >= interval:
            logger.info(
                f"[Summarizer] Triggering summarization for session {session_id} "
                f"({messages_since_summary} new messages, interval={interval})"
            )

            start_idx = messages_summarized
            end_idx = start_idx + interval
            messages_to_summarize = all_messages[start_idx:end_idx]

            # Set LLM client if not already set
            if not conversation_summarizer.llm_client:
                conversation_summarizer.set_llm_client(
                    LC_OllamaClient(
                        base=get_ollama_base(),
                        model=get_persona_model(),
                        temperature=get_temp_summarization()
                    )
                )

            card = get_persona_card(persona_key)
            persona_name = card.get("display_name", persona_key)

            summary_result = conversation_summarizer.summarize_segment(
                messages=messages_to_summarize,
                max_summary_tokens=200,
                persona_name=persona_name
            )

            message_range = f"{start_idx + 1}-{end_idx}"
            summary_repo.create_summary(
                session_id=session_id,
                message_range=message_range,
                summary_text=summary_result["summary_text"],
                emotional_developments=summary_result["emotional_developments"],
                topics_discussed=summary_result["topics_discussed"]
            )

            logger.info(
                f"[Summarizer] Created summary for messages {message_range} "
                f"({summary_result['token_count']} tokens)"
            )

    except Exception as e:
        logger.error(f"[Summarizer] Failed to create summary: {e}", exc_info=True)


@router.post("/sessions/{session_id}/chat")
def chat_with_session(session_id: str, body: ChatBody):
    """Chat with persona using database-backed conversation history."""
    deps = _get_dependencies()
    session_repo = deps["session_repo"]
    message_repo = deps["message_repo"]
    summary_repo = deps["summary_repo"]
    emotional_state_repo = deps["emotional_state_repo"]
    memory_manager = deps["memory_manager"]
    user_profile_repo = deps["user_profile_repo"]
    episodic_memory_rag = deps["episodic_memory_rag"]
    fact_extractor = deps["fact_extractor"]

    # Get session info
    persona_key = session_repo.get_persona_key(session_id)
    if not persona_key:
        raise HTTPException(status_code=404, detail="Session not found.")

    # PHASE 3: Get or create user profile for cross-session memory
    user_id = user_profile_repo.get_session_user(session_id)
    user_profile = None
    user_profile_context = ""

    if user_id:
        user_profile = user_profile_repo.get_profile(user_id)
        if user_profile:
            user_profile_context = user_profile.get_context_summary(max_facts=10, max_topics=5)
            if user_profile_context:
                logger.info(f"[Phase3] Loaded user profile for {user_id} (cross-session memory)")

    # PHASE 2.2: Get emotional state
    emotional_state = emotional_state_repo.get_or_create(session_id)
    emotional_context = emotional_state.to_prompt_context()
    logger.debug(f"[EmotionalState] Session {session_id[:8]}: trust={emotional_state.trust_level:.2f}, mood={emotional_state.current_mood}")

    # PHASE 2: Intelligent memory selection
    db_messages = message_repo.get_messages_by_session(session_id)
    summaries = summary_repo.get_summaries_by_session(session_id)

    card = get_persona_card(persona_key)
    system_prompt = build_system_prompt(persona_key)

    # PHASE 3: Inject user profile context (cross-session memory)
    if user_profile_context:
        system_prompt = f"{system_prompt}\n\n{user_profile_context}"
        logger.debug(f"[Phase3] Injected user profile context ({len(user_profile_context)} chars)")

    # Inject emotional context
    if emotional_context:
        system_prompt = f"{system_prompt}\n\n{emotional_context}"
    system_tokens = estimate_tokens(system_prompt)

    # Build summary context
    summary_context = ""
    if summaries:
        logger.info(f"[Memory] Found {len(summaries)} conversation summaries for session {session_id}")

        summary_parts = []
        for summary in summaries:
            summary_parts.append(f"[Summary of messages {summary['message_range']}]")
            summary_parts.append(summary['summary_text'])
            if summary.get('topics_discussed'):
                summary_parts.append(f"Topics: {summary['topics_discussed']}")

        summary_context = "\n\n".join(summary_parts)
        summary_tokens = estimate_tokens(summary_context)

        logger.info(
            f"[Memory] Summaries cover {len(summaries) * 30} messages "
            f"compressed to {summary_tokens} tokens"
        )
        system_tokens += summary_tokens

    # Use MemoryManager to select messages
    selected_messages = memory_manager.select_messages(
        messages=db_messages,
        token_budget=get_model_context_window(),
        system_prompt_tokens=system_tokens
    )

    # PHASE 3: Use RAG for semantic memory search
    rag_relevant_messages = []
    if episodic_memory_rag and db_messages:
        try:
            # Index session if not already indexed
            if session_id not in episodic_memory_rag.vectorstores:
                episodic_memory_rag.index_session(session_id, db_messages)

            # Get semantically relevant messages for current query
            rag_start = time.time()
            rag_relevant = episodic_memory_rag.get_relevant_context(
                session_id=session_id,
                query=body.message,
                max_messages=5  # Top 5 most relevant
            )
            rag_latency = (time.time() - rag_start) * 1000

            if rag_relevant:
                # Merge RAG results with selected messages (avoid duplicates)
                selected_indices = {msg.get("index", -1) for msg in selected_messages}
                for rag_msg in rag_relevant:
                    if rag_msg.get("index", -2) not in selected_indices:
                        rag_relevant_messages.append(rag_msg)

                logger.info(
                    f"[Phase3 RAG] Found {len(rag_relevant)} relevant memories "
                    f"({len(rag_relevant_messages)} unique) in {rag_latency:.0f}ms"
                )
        except Exception as e:
            logger.warning(f"[Phase3 RAG] Semantic search failed: {e}")

    # Combine selected messages with RAG-enhanced messages
    all_context_messages = selected_messages.copy()
    if rag_relevant_messages:
        all_context_messages.extend(rag_relevant_messages)
        # Sort by index to maintain chronological order
        all_context_messages.sort(key=lambda x: x.get("index", 0))

    # Convert to ChatTurn format
    history_turns = [
        ChatTurn(role=msg["role"], content=msg["content"])
        for msg in all_context_messages
    ]

    # Prepend summary context
    if summary_context:
        history_turns.insert(0, ChatTurn(
            role="assistant",
            content=f"[Context from earlier in our conversation]\n\n{summary_context}"
        ))

    logger.info(
        f"[Memory] Selected {len(history_turns)}/{len(db_messages)} messages "
        f"(+{len(summaries)} summaries) for session {session_id} "
        f"(system: {system_tokens} tokens)"
    )

    # Perform chat
    chat_body = ChatBody(
        persona=persona_key,
        history=history_turns,
        message=body.message
    )
    response = chat(chat_body)

    # Save messages
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Import add_message from sessions route
    from .sessions import add_message

    user_msg_body = AppendMessageBody(role="user", content=body.message, ts=now, source_type="llm")
    add_message(session_id, user_msg_body)

    # Extract source_type from response metadata
    source_type = "llm"
    if "metadata" in response and response["metadata"]:
        source_type = response["metadata"].get("source_type", "llm")

    # Handle multi-message responses (Phase 2)
    # Store each message as a separate database entry with multi_message_id linking
    answer_for_db = response["answer"]
    if isinstance(answer_for_db, list) and len(answer_for_db) > 1:
        # Multi-message response - store each message separately
        import uuid
        multi_msg_id = str(uuid.uuid4())
        logger.debug(f"[Phase2] Storing {len(answer_for_db)} multi-messages separately with ID {multi_msg_id}")

        for idx, msg_content in enumerate(answer_for_db):
            assistant_msg_body = AppendMessageBody(
                role="assistant",
                content=msg_content,
                ts=now,
                source_type=source_type,
                latency_ms=response.get("latency") if idx == 0 else None,  # Only first message gets latency
                multi_message_id=multi_msg_id,
                multi_message_index=idx
            )
            add_message(session_id, assistant_msg_body)
    else:
        # Single message (or single-item list)
        content = answer_for_db[0] if isinstance(answer_for_db, list) else answer_for_db
        assistant_msg_body = AppendMessageBody(
            role="assistant",
            content=content,
            ts=now,
            source_type=source_type,
            latency_ms=response.get("latency")
        )
        add_message(session_id, assistant_msg_body)

    # For emotional state analysis, use all messages joined
    answer_for_emotional_state = "\\n\\n".join(answer_for_db) if isinstance(answer_for_db, list) else answer_for_db

    # Auto-summarization check
    _check_and_summarize(session_id, persona_key, deps)

    # Update emotional state
    try:
        # Use joined version for emotional state analysis
        updated_state = emotional_state_repo.update_from_interaction(
            session_id=session_id,
            user_message=body.message,
            assistant_response=answer_for_emotional_state
        )
        response["emotional_state"] = {
            "trust_level": updated_state.trust_level,
            "rapport": updated_state.rapport,
            "current_mood": updated_state.current_mood
        }
        logger.debug(f"[EmotionalState] Updated: trust={updated_state.trust_level:.2f}, mood={updated_state.current_mood}")
    except Exception as e:
        logger.warning(f"[EmotionalState] Failed to update emotional state: {e}")

    # PHASE 3: Update RAG index and extract/update user profile
    try:
        # Update RAG index with new messages
        if episodic_memory_rag:
            all_messages_updated = message_repo.get_messages_by_session(session_id)
            episodic_memory_rag.update_session(
                session_id=session_id,
                new_messages=[
                    {"role": "user", "content": body.message},
                    {"role": "assistant", "content": response["answer"]}
                ],
                full_history=all_messages_updated
            )
            logger.debug(f"[Phase3 RAG] Updated vector index for session {session_id}")

        # Extract facts and update user profile (configurable interval to save compute)
        fact_interval = get_fact_extraction_interval()
        if user_profile_repo and len(db_messages) % fact_interval == 0:
            try:
                # Get updated message list
                all_messages_updated = message_repo.get_messages_by_session(session_id)

                # Extract facts from recent messages (last 20)
                recent_messages = all_messages_updated[-20:]

                # Initialize fact extractor with LLM client if needed
                if fact_extractor is None:
                    from ..llm_client import LC_OllamaClient
                    llm_client = LC_OllamaClient(
                        base=get_ollama_base(),
                        model=get_persona_model(),
                        temperature=get_temp_fact_extraction()
                    )
                    from ..fact_extractor import FactExtractor
                    fact_extractor = FactExtractor(llm_client)

                # Extract facts
                facts = fact_extractor.extract_facts(recent_messages, persona_key=persona_key)

                # Get or create user profile
                if not user_id and facts.get("user_name"):
                    # Try to find existing user by name
                    user_id = user_profile_repo.get_user_by_name(facts["user_name"])

                if not user_id:
                    # Create new user profile
                    import uuid
                    user_id = f"user_{uuid.uuid4().hex[:8]}"
                    user_profile = user_profile_repo.create_profile(user_id)
                    user_profile_repo.link_session_to_user(user_id, session_id)
                    logger.info(f"[Phase3] Created new user profile: {user_id}")
                else:
                    user_profile = user_profile_repo.get_or_create_profile(user_id)

                # Update profile with extracted facts
                user_profile.update_from_session(facts)
                user_profile_repo.update_profile(user_profile)

                logger.info(
                    f"[Phase3] Updated user profile {user_id}: "
                    f"{fact_extractor.get_extraction_stats(facts)}"
                )

            except Exception as e:
                logger.warning(f"[Phase3] Fact extraction/profile update failed: {e}")

    except Exception as e:
        logger.error(f"[Phase3] Post-conversation updates failed: {e}")

    return response


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
        temperature=get_persona_temperature(),
    )
    answer = client.complete(system=system, user_prompt=user_prompt)

    # Post-process to enforce first-person
    persona_name = card.get("display_name") or card.get("key") or "Persona"
    answer, was_rewritten = post_process_first_person(answer, persona_name)

    # PHASE 2: Force-split into multi-message if LLM didn't use <msg> tags (for greetings)
    # Note: Greetings don't use the multi-message response format in API, but we still
    # apply force-split for consistency and potential future use
    answer = _force_multi_message_split(answer, "greeting")

    return {"answer": answer, "rewritten": was_rewritten}
