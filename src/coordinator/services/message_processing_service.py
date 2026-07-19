# src/coordinator/services/message_processing_service.py
"""Message processing utilities for multi-message response handling."""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


def force_multi_message_split(response: str, query: str) -> str:
    """
    Force-split LLM response into multi-message format if it doesn't have <msg> tags.

    BUGFIX (Dec 28, 2025): Reduced aggressiveness to prevent unwanted splits.
    Only splits responses that are VERY long (500+ chars) with clear conversational breaks.

    Args:
        response: LLM response string (without <msg> tags)
        query: Original user query (used for context)

    Returns:
        Response with <msg> tags applied
    """
    # Don't split if already has tags
    if '<msg>' in response:
        return response

    # Don't split short responses (< 500 chars) - keep them as single message
    if len(response.strip()) < 500:
        return response

    # BUGFIX: Remove paragraph splitting - too aggressive
    # Only split VERY long responses (800+ chars) with clear conversational structure
    response_clean = response.strip()

    # Strategy 1: Only split if response is VERY long (800+ chars) AND has question at end.
    # group(1) is GREEDY so it captures all body text up to the LAST sentence break
    # before the trailing question (main_content), leaving group(3) as just the final
    # question. A non-greedy (.*?) here minimised group(1) to the first sentence, which
    # both lumped the rest into the "question" message and made the 3-message split
    # (which needs main_content > 400 chars containing a '. ') unreachable.
    question_match = re.search(r'(.*)([.!]\s+)(.+\?)\s*$', response_clean, re.DOTALL)
    if question_match and len(response_clean) > 800:
        main_content = question_match.group(1) + question_match.group(2)
        question = question_match.group(3)

        # Split main content if it's very long
        if len(main_content) > 400:
            # Split main content in half
            mid_point = len(main_content) // 2
            # Find nearest sentence break
            split_point = main_content.rfind('. ', 0, mid_point + 50)
            if split_point > 0:
                first_part = main_content[:split_point + 1].strip()
                second_part = main_content[split_point + 1:].strip()
                logger.info("[Phase2-ForceSplit] Split long response with question: 3 messages")
                return f'<msg>{first_part}</msg>\n<msg>{second_part}</msg>\n<msg>{question}</msg>'

        logger.info("[Phase2-ForceSplit] Split long response with question: 2 messages")
        return f'<msg>{main_content.strip()}</msg>\n<msg>{question}</msg>'

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
                logger.info("[Phase2-ForceSplit] Split with question: 3 messages")
                return f'<msg>{first_part}</msg>\n<msg>{second_part}</msg>\n<msg>{question}</msg>'

        logger.info("[Phase2-ForceSplit] Split with question: 2 messages")
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
                logger.info("[Phase2-ForceSplit] Split at midpoint: 2 messages")
                return f'<msg>{first}</msg>\n<msg>{second}</msg>'

    # No good split found - return as single message
    logger.debug(f"[Phase2-ForceSplit] No split applied (length: {len(response_clean)})")
    return response


# A hallucinated next turn: the compiled prompt renders history as "User: ..." /
# "Assistant: ...", so the model sometimes keeps going and writes the *next* turn
# itself. Anchored to line-start so persona prose containing the word is untouched.
_HALLUCINATED_TURN_RE = re.compile(r'^\s*(?:User|Assistant)\s*:', re.MULTILINE)
_LEADING_ROLE_RE = re.compile(r'^\s*(?:Assistant|User)\s*:\s*', re.IGNORECASE)


def strip_role_prefix_leaks(answer: str) -> str:
    """Remove role-prefix artifacts leaked from the compiled prompt format.

    Two distinct leaks, both from the "User:/Assistant:" transcript framing:
      1. a leading ``Assistant:`` / ``User:`` prefix on the reply itself;
      2. a *trailing* fabricated turn — the model writes ``\\nUser: ...`` and keeps
         going (the classic missing-stop-sequence artifact). Everything from that
         line on is cut.

    Shared by both finalize paths (``routes/chat.py:_build_llm_response`` and
    ``QueryHandlerService._finalize_response``) so they can't drift apart again.
    """
    if not answer:
        return answer

    cleaned = _LEADING_ROLE_RE.sub('', answer, count=1)

    # Cut a fabricated next turn, but only if real content precedes it.
    match = _HALLUCINATED_TURN_RE.search(cleaned)
    if match and cleaned[:match.start()].strip():
        logger.info("[RoleLeak] Cut hallucinated turn at offset %d", match.start())
        cleaned = cleaned[:match.start()]

    return cleaned.strip()


def parse_multi_message_response(response: str) -> tuple[list[str], str]:
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

    # No well-formed pair matched. The model sometimes opens <msg> without ever
    # closing it, which used to fall through and leak the literal tags into the
    # chat. Recover by splitting on the opening tags (only reached when the
    # well-formed path above found nothing, so that path stays byte-identical).
    if '<msg>' in response:
        pieces = [
            re.sub(r'</msg>', '', p).strip()
            for p in response.split('<msg>')
        ]
        pieces = [p for p in pieces if p]
        if len(pieces) > 1:
            logger.info(f"[Phase2] Recovered {len(pieces)} messages from unclosed <msg> tags")
            return (pieces[:4], 'multi')
        if len(pieces) == 1:
            return ([pieces[0]], 'single')

    # No tags found, return original response
    return ([response], 'single')
