# src/coordinator/services/force_search_service.py
"""
Force Search Service - Determine if search should be forced based on query patterns.

Extracted from llm_client.py as part of Phase 2 Service Decomposition.
Identifies high-confidence search queries to bypass LLM decision-making.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ForceSearchService:
    """Service for determining if search should be forced for a query.

    Handles:
    - Pattern matching for high-confidence search queries
    - Price/current data query detection
    - Market data query detection

    This service is stateless and thread-safe.
    """

    # High-confidence price/current data patterns
    # Format: (primary_keyword, [list of secondary keywords])
    # If primary found AND (no secondary list OR any secondary found) → force search
    FORCE_PATTERNS: List[Tuple[str, List[str]]] = [
        # Price queries
        ("price", ["ethereum", "bitcoin", "btc", "eth", "crypto", "stock", "current", "now", "right now", "today"]),
        ("cost", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),
        ("value", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),
        ("worth", ["ethereum", "bitcoin", "btc", "eth", "current", "now", "today"]),

        # Current/latest queries
        ("latest", ["news", "update", "price", "data", "info", "developments", "development"]),
        ("current", ["price", "news", "data", "status", "situation"]),
        ("right now", []),
        ("today", ["price", "news", "happening"]),
        ("recent", ["news", "update", "development", "change"]),

        # Market queries
        ("trading at", []),
        ("market price", []),
    ]

    @classmethod
    def should_force_search(cls, query: str) -> bool:
        """Determine if we should force search execution (bypass LLM decision).

        For queries with high-confidence search intent (price, current, latest),
        we force search instead of relying on LLM to call the tool.

        Args:
            query: User query string

        Returns:
            True if search should be forced, False otherwise
        """
        query_lower = query.lower()

        for primary, secondary_list in cls.FORCE_PATTERNS:
            if primary in query_lower:
                # If primary keyword found, check if any secondary keywords also present
                if not secondary_list:  # No secondary required
                    logger.debug(f"[ForceSearch] Forcing search: '{primary}' found (no secondary required)")
                    return True
                if any(sec in query_lower for sec in secondary_list):
                    logger.debug(f"[ForceSearch] Forcing search: '{primary}' + secondary keyword found")
                    return True

        return False
