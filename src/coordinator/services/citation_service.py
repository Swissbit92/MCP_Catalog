# src/coordinator/services/citation_service.py
"""Citation validation service for web search responses."""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


def validate_citations(
    answer: str,
    used_search: bool,
    search_results_count: int = 0
) -> tuple[str, bool, dict]:
    """
    Validate that web search responses include proper source citations.

    Args:
        answer: LLM's response text
        used_search: Whether web search was used
        search_results_count: Number of search results returned

    Returns:
        Tuple of (answer, has_valid_citations, validation_details)
        - answer: Potentially modified answer (with warning if citations missing)
        - has_valid_citations: Boolean indicating if citations are valid
        - validation_details: Dict with validation results
    """
    validation = {
        "has_citation_section": False,
        "has_markdown_links": False,
        "citation_count": 0,
        "has_emoji": False,
        "valid": False
    }

    if not used_search:
        validation["valid"] = True
        return answer, True, validation

    # Check for citation section markers (with or without emoji)
    has_citation_with_emoji = "🔍 Sources:" in answer or "🔍 **Sources:**" in answer
    has_citation_without_emoji = bool(re.search(r'\*\*Sources:\*\*|\nSources:\n', answer))

    validation["has_citation_section"] = has_citation_with_emoji or has_citation_without_emoji
    validation["has_emoji"] = has_citation_with_emoji

    # Check for markdown links [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', answer)
    validation["has_markdown_links"] = len(markdown_links) > 0
    validation["citation_count"] = len(markdown_links)

    # Check if links contain http/https URLs
    has_http_links = any('http' in url for _, url in markdown_links)

    # Valid if: has citation section + has markdown links with URLs
    if validation["has_citation_section"] and validation["has_markdown_links"] and has_http_links:
        validation["valid"] = True
        logger.info(
            f"[Citations] ✅ Valid citations found: {validation['citation_count']} sources, "
            f"emoji={'✅' if validation['has_emoji'] else '❌'}"
        )
        return answer, True, validation

    # Invalid citations - log warning
    logger.warning("[Citations] ❌ Missing or invalid citations for search query")
    logger.warning(
        f"[Citations] Details: section={validation['has_citation_section']}, "
        f"links={validation['has_markdown_links']}, count={validation['citation_count']}"
    )

    # Auto-append reminder if citations are completely missing
    if not validation["has_citation_section"] and search_results_count > 0:
        reminder = (
            f"\n\n⚠️ Note: {search_results_count} web source(s) were consulted "
            "but citations were not included in the response."
        )
        answer = answer + reminder
        logger.info("[Citations] Appended missing citation reminder to response")

    return answer, False, validation
