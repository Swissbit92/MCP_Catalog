"""Chat session service - handles session-based chat with advanced memory features.

This service extracts the complex chat_with_session logic to improve code organization
and maintainability. It handles:
- Session and persona loading
- User profile management (Phase 3 cross-session memory)
- Emotional state tracking (Phase 2.2)
- Intelligent message selection with memory manager
- RAG-based semantic search (Phase 3)
- Multi-message response handling
- Automatic summarization
- Fact extraction and user profile updates
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime

from fastapi import HTTPException

from ..schemas import ChatBody, ChatTurn, AppendMessageBody
from ..config import (
    get_ollama_base,
    get_persona_model,
    get_model_context_window,
    get_fact_extraction_interval,
    get_temp_fact_extraction,
)
from ..llm_client import LC_OllamaClient, estimate_tokens
from ..persona_memory import build_system_prompt, get_persona_card

logger = logging.getLogger(__name__)


def handle_session_chat(
    session_id: str,
    message: str,
    deps: dict,
    chat_function,
    add_message_function
):
    """
    Handle chat with persona using database-backed conversation history.

    This function orchestrates the complete chat flow including:
    1. Loading session, persona, and user profile
    2. Loading emotional state
    3. Intelligent message selection with memory manager
    4. RAG-based semantic search for relevant context
    5. Building chat context and calling main chat endpoint
    6. Saving messages (handles multi-message responses)
    7. Updating emotional state
    8. Updating RAG index
    9. Extracting facts and updating user profiles
    10. Triggering summarization when needed

    Args:
        session_id: Session identifier
        message: User's message content
        deps: Dictionary of injected dependencies (repositories, services)
        chat_function: Main chat endpoint function to call
        add_message_function: Function to add messages to the session

    Returns:
        dict: Chat response with answer, latency, and emotional state

    Raises:
        HTTPException: If session not found (404)
    """
    # Extract dependencies
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
                query=message,
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
        message=message
    )
    response = chat_function(chat_body)

    # Save messages
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    user_msg_body = AppendMessageBody(role="user", content=message, ts=now, source_type="llm")
    add_message_function(session_id, user_msg_body)

    # Extract source_type from response metadata
    source_type = "llm"
    if "metadata" in response and response["metadata"]:
        source_type = response["metadata"].get("source_type", "llm")

    # Handle multi-message responses (Phase 2)
    # Store each message as a separate database entry with multi_message_id linking
    answer_for_db = response["answer"]
    if isinstance(answer_for_db, list) and len(answer_for_db) > 1:
        # Multi-message response - store each message separately
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
            add_message_function(session_id, assistant_msg_body)
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
        add_message_function(session_id, assistant_msg_body)

    # For emotional state analysis, use all messages joined
    answer_for_emotional_state = "\\n\\n".join(answer_for_db) if isinstance(answer_for_db, list) else answer_for_db

    # Auto-summarization check
    _check_and_summarize(session_id, persona_key, deps)

    # Update emotional state
    try:
        # Use joined version for emotional state analysis
        updated_state = emotional_state_repo.update_from_interaction(
            session_id=session_id,
            user_message=message,
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
                    {"role": "user", "content": message},
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


def _check_and_summarize(session_id: str, persona_key: str, deps: dict):
    """
    Check if summarization is needed and trigger it if necessary.

    Summarization is triggered when the number of messages since the last summary
    reaches the configured interval (default: 30 messages).

    Args:
        session_id: Session identifier
        persona_key: Persona key for context
        deps: Dictionary of injected dependencies
    """
    from ..config import get_summarization_interval, get_temp_summarization

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
