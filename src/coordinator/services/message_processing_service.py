# src/coordinator/services/message_processing_service.py
"""Message processing utilities for multi-message response handling."""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


def force_multi_message_split(response: str, query: str) -> str:
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
    else:
        # No tags found, return original response
        return ([response], 'single')
