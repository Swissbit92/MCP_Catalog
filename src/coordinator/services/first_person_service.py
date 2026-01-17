# src/coordinator/services/first_person_service.py
"""First-person voice enforcement service for persona responses."""

from __future__ import annotations

import logging

from ..config import get_ollama_base, get_persona_model, get_temp_rewrite
from .llm_completion_service import LLMCompletionService

logger = logging.getLogger(__name__)


def detect_third_person(answer: str, persona_name: str) -> tuple[bool, list[str]]:
    """
    Detect third-person patterns in persona response.

    Args:
        answer: Persona's response text
        persona_name: Full persona name (e.g., "Eeva — Bitcoin Expert")

    Returns:
        Tuple of (has_third_person, violations_list)
    """
    first_name = persona_name.split(" — ")[0].strip().split()[0].lower()
    answer_lower = answer.lower()

    # Check for first-person self-introduction (these are valid)
    has_first_person_intro = any(pattern in answer_lower for pattern in [
        f"i'm {first_name},",
        f"i am {first_name},",
        f"i'm {first_name} and",
        f"i am {first_name} and",
    ])

    # Third-person violation patterns
    violation_patterns = [
        f"{first_name} is a ",
        f"{first_name} is an ",
        f"{first_name} has ",
        f"{first_name} was ",
        f"{first_name} specializes ",
        f"{first_name} believes ",
        f"{first_name} works ",
        f"{first_name}'s ",
        f"about {first_name}",
    ]

    # Only flag "{name}, a/an" if NOT part of first-person intro
    if not has_first_person_intro:
        violation_patterns.extend([
            f"{first_name}, a ",
            f"{first_name}, an ",
        ])

    # Find violations
    violations = [pattern for pattern in violation_patterns if pattern in answer_lower]

    return len(violations) > 0, violations


def rewrite_to_first_person(answer: str, persona_name: str) -> str:
    """
    Use LLM to rewrite third-person response to first-person.

    Args:
        answer: Original response (in third-person)
        persona_name: Persona name for context

    Returns:
        Rewritten response in first-person
    """
    first_name = persona_name.split(" — ")[0].strip().split()[0]

    rewrite_prompt = f"""The following response was written in THIRD PERSON but should be in FIRST PERSON.

Original response:
{answer}

Your task:
1. Rewrite this response so {first_name} speaks in FIRST PERSON (I, my, me)
2. Keep the same information and tone
3. Do NOT add new information
4. Do NOT use "{first_name} is", "{first_name} has", etc.
5. Use "I am", "I have", "my", "me" instead

Rewritten first-person response:"""

    try:
        service = LLMCompletionService(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_temp_rewrite()
        )

        rewritten = service.complete(
            system="You are a helpful assistant that rewrites text from third-person to first-person. Follow the instructions exactly.",
            user_prompt=rewrite_prompt
        )

        return rewritten.strip()

    except Exception as e:
        logger.warning(f"[FirstPerson] Failed to rewrite response: {e}")
        return answer  # Return original on error


def post_process_first_person(answer: str, persona_name: str) -> tuple[str, bool]:
    """
    Post-process response to enforce first-person voice.

    Detects third-person patterns and rewrites to first-person if needed.

    Args:
        answer: Persona response
        persona_name: Full persona name

    Returns:
        Tuple of (processed_answer, was_rewritten)
    """
    has_third_person, violations = detect_third_person(answer, persona_name)

    if not has_third_person:
        logger.info("[FirstPerson] ✅ Response is first-person, no rewrite needed")
        return answer, False

    # Log violation and rewrite
    logger.warning(f"[FirstPerson] ⚠️ Third-person detected: {violations[0]}")
    logger.info("[FirstPerson] 🔄 Rewriting to first-person...")

    rewritten = rewrite_to_first_person(answer, persona_name)

    # Verify rewrite worked
    still_third_person, _ = detect_third_person(rewritten, persona_name)

    if still_third_person:
        logger.warning("[FirstPerson] ❌ Rewrite still contains third-person, using original")
        return answer, False
    else:
        logger.info("[FirstPerson] ✅ Successfully rewritten to first-person")
        return rewritten, True
