# src/coordinator/services/query_handler_service.py
"""Query handler service for MCP integration (Brave, MongoDB)."""

from __future__ import annotations

import re
import time
import json
import logging
from typing import Optional, Any

from ..schemas import ResponseMetadata
from ..config import get_ollama_base, get_persona_model, get_persona_temperature
from ..llm_client import LC_OllamaClient
from ..tool_definitions import build_mongodb_synthesis_prompt
from .citation_service import validate_citations
from .first_person_service import post_process_first_person

logger = logging.getLogger(__name__)


class QueryHandlerService:
    """Service for handling MCP-based queries (MongoDB, Brave Search, Multi-MCP)."""

    def __init__(self, brave_client: Any = None, mongodb_service: Any = None):
        """Initialize query handler service.

        Args:
            brave_client: Brave MCP client for web search
            mongodb_service: MongoDB service for trading data
        """
        self.brave_client = brave_client
        self.mongodb_service = mongodb_service

    def handle_mongodb_query(
        self,
        message: str,
        system_prompt: str,
        user_compiled: str,
        mongodb_tools: list,
        metadata: ResponseMetadata,
        persona_name: str
    ) -> dict:
        """Handle MongoDB-only query.

        Args:
            message: User's query message
            system_prompt: Persona system prompt
            user_compiled: Compiled user prompt with history
            mongodb_tools: List of MongoDB tool definitions
            metadata: Response metadata object
            persona_name: Display name of persona

        Returns:
            Response dict with answer, used_search, metadata, rewritten
        """
        logger.info("MongoDB-only query detected, using direct handlers")
        tool_name = mongodb_tools[0]["function"]["name"]
        logger.info(f"Using MongoDB tool: {tool_name}")

        try:
            mongodb_result = None
            if tool_name == "bitcoin_current_price":
                mongodb_result = self.mongodb_service.handle_bitcoin_current_price(
                    reason="User query about current price"
                )
            elif tool_name == "bitcoin_historical_prices":
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
                start_date = date_match.group(1) if date_match else "2025-12-01"
                mongodb_result = self.mongodb_service.handle_bitcoin_historical_prices(
                    reason="User query about historical data", start_date=start_date
                )
            elif tool_name == "bitcoin_trading_summary":
                mongodb_result = self.mongodb_service.handle_bitcoin_trading_summary(
                    reason="User query about trading stats"
                )
            elif tool_name == "bitcoin_technical_analysis":
                mongodb_result = self.mongodb_service.handle_bitcoin_technical_analysis(
                    reason="User query about technical analysis"
                )

            if mongodb_result:
                formatted_data = json.dumps(mongodb_result, indent=2)

                client = LC_OllamaClient(
                    base=get_ollama_base(),
                    model=get_persona_model(),
                    temperature=get_persona_temperature()
                )

                # Build enhanced synthesis prompt with persona flavor guidance
                synthesis_system = build_mongodb_synthesis_prompt(
                    persona_system=system_prompt,
                    has_mongodb_data=True
                )
                logger.info(f"[MongoDB Synthesis] Using enhanced synthesis prompt (length: {len(synthesis_system)} chars)")

                # User prompt with MongoDB data
                synthesis_prompt = f"""[MongoDB Data Retrieved]
{formatted_data}

User Query: {user_compiled}"""

                answer = client.complete(system=synthesis_system, user_prompt=synthesis_prompt)

                metadata.source_type = "mongodb_mcp"
                metadata.tools_used = [tool_name]
                metadata.cache_status = mongodb_result.get("cache_status", "miss")
                metadata.data_timestamp = mongodb_result.get("timestamp", "")

                logger.info(f"MongoDB query completed: tool={tool_name}, cache={metadata.cache_status}")

                answer, was_rewritten = post_process_first_person(answer, persona_name)

                return {
                    "answer": answer,
                    "used_search": True,
                    "metadata": metadata.model_dump(),
                    "rewritten": was_rewritten
                }
        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")

        # Fallback to regular LLM response
        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature()
        )
        answer = client.complete(system=system_prompt, user_prompt=user_compiled)
        answer, was_rewritten = post_process_first_person(answer, persona_name)
        return {
            "answer": answer,
            "used_search": False,
            "metadata": metadata.model_dump(),
            "rewritten": was_rewritten
        }

    def handle_brave_query(
        self,
        system_prompt: str,
        user_compiled: str,
        tools: list,
        metadata: ResponseMetadata,
        persona_name: str
    ) -> dict:
        """Handle Brave-only query.

        Args:
            system_prompt: Persona system prompt
            user_compiled: Compiled user prompt with history
            tools: List of tool definitions (including Brave)
            metadata: Response metadata object
            persona_name: Display name of persona

        Returns:
            Response dict with answer, used_search, metadata, citation_valid, rewritten
        """
        logger.info("[Brave] Starting Brave-only query workflow")
        start_time = time.time()

        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature(),
            mcp_client=self.brave_client
        )

        answer, tool_call, search_results = client.complete_with_tools(
            persona_system=system_prompt,
            user_prompt=user_compiled,
            tools=tools
        )

        elapsed = time.time() - start_time

        metadata.source_type = "brave_mcp"
        metadata.tools_used = ["brave_web_search"] if tool_call else []

        # Validate citations
        search_count = len(search_results) if search_results else 0
        answer, has_valid_citations, citation_details = validate_citations(
            answer=answer,
            used_search=tool_call is not None,
            search_results_count=search_count
        )

        answer, was_rewritten = post_process_first_person(answer, persona_name)

        response = {
            "answer": answer,
            "used_search": tool_call is not None,
            "metadata": metadata.model_dump(),
            "citation_valid": has_valid_citations,
            "rewritten": was_rewritten
        }

        if search_results:
            response["search_results_count"] = len(search_results)
            logger.info(
                f"[Brave] ✅ Workflow completed: used_search={tool_call is not None}, "
                f"results_count={len(search_results)}, citations_valid={has_valid_citations}, "
                f"total_time={elapsed:.2f}s"
            )
        else:
            logger.info(f"[Brave] ✅ Workflow completed: used_search=False, total_time={elapsed:.2f}s (LLM answered directly)")

        return response

    def handle_multi_mcp_query(
        self,
        system_prompt: str,
        user_compiled: str,
        brave_tools: list,
        metadata: ResponseMetadata,
        persona_name: str
    ) -> dict:
        """Handle Multi-MCP query (Brave + MongoDB).

        Args:
            system_prompt: Persona system prompt
            user_compiled: Compiled user prompt with history
            brave_tools: List of Brave tool definitions
            metadata: Response metadata object
            persona_name: Display name of persona

        Returns:
            Response dict with answer, used_search, metadata, citation_valid, search_results_count, rewritten
        """
        logger.info("Multi-MCP query detected (Brave + MongoDB)")

        client = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=get_persona_temperature(),
            mcp_client=self.brave_client
        )

        answer, tool_call, search_results = client.complete_with_tools(
            persona_system=system_prompt,
            user_prompt=user_compiled,
            tools=brave_tools
        )

        metadata.source_type = "multi_mcp"
        metadata.tools_used = ["brave_web_search"]

        # Validate citations
        search_count = len(search_results) if search_results else 0
        answer, has_valid_citations, citation_details = validate_citations(
            answer=answer,
            used_search=True,
            search_results_count=search_count
        )

        answer, was_rewritten = post_process_first_person(answer, persona_name)

        return {
            "answer": answer,
            "used_search": True,
            "metadata": metadata.model_dump(),
            "citation_valid": has_valid_citations,
            "search_results_count": search_count,
            "rewritten": was_rewritten
        }
