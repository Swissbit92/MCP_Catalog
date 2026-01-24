# src/coordinator/services/query_extraction_service.py
"""
Query Extraction Service - Extract latest user message from conversation history.

Extracted from llm_client.py as part of Phase 2 Service Decomposition.
Handles parsing conversation history to extract the most recent user query.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class QueryExtractionService:
    """Service for extracting user queries from conversation history.

    Handles:
    - Parsing conversation history format
    - Extracting the latest user message
    - Fallback to full conversation if parsing fails

    This service is stateless and thread-safe.
    """

    @staticmethod
    def extract_latest_user_message(conversation: str) -> str:
        """Extract the latest user message from a conversation history.

        The conversation format is:
            User: <message 1>

            Assistant: <response 1>

            User: <message 2>

        Args:
            conversation: Full conversation history

        Returns:
            Latest user message only (without "User: " prefix)
        """
        # Split by lines and find the last "User: " message
        lines = conversation.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("User: "):
                return line[6:].strip()  # Remove "User: " prefix

        # Fallback: return entire conversation if no "User: " prefix found
        logger.warning("[Query Extraction] Could not extract latest user message, using full conversation")
        return conversation
