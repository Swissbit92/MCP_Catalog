# src/coordinator/services/memory_selection_service.py
"""Memory selection and summarization utilities."""

from __future__ import annotations

import logging
from typing import Optional

from ..config import (
    get_ollama_base,
    get_persona_model,
    get_summarization_interval,
    get_temp_summarization,
)
from ..llm_client import LC_OllamaClient  # For conversation_summarizer
from ..persona_memory import get_persona_card

logger = logging.getLogger(__name__)


def check_and_summarize(session_id: str, persona_key: str, deps: dict) -> None:
    """
    Check if summarization is needed and trigger it if necessary.

    Args:
        session_id: Chat session identifier
        persona_key: Persona key for contextual summarization
        deps: Dictionary of dependencies (repos, services)
    """
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
