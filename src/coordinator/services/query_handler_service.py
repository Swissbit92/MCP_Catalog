# src/coordinator/services/query_handler_service.py
"""Query handler service for MCP integration (Brave, MongoDB, Wallet)."""

from __future__ import annotations

import re
import time
import json
import logging
from typing import Optional, Any

from ..schemas import ResponseMetadata
from ..config import get_settings, get_persona_temperature_override
from .llm_completion_service import LLMCompletionService
# LC_OllamaClient imported lazily inside methods to break circular import with llm_client.py
from ..tool_definitions import build_mongodb_synthesis_prompt
from .citation_service import CitationService, validate_citations
from .first_person_service import post_process_first_person

logger = logging.getLogger(__name__)

# In-memory multi-turn wallet creation state
# session_id -> {"step": int, "user_id": str, "wallet_name": str}
# Cleared on server restart (acceptable for guided UI flow)
_wallet_flows: dict[str, dict] = {}


class QueryHandlerService:
    """Service for handling MCP-based queries (MongoDB, Brave Search, Multi-MCP).

    Phase 2 Core Refactoring: Extracted shared finalization logic to reduce duplication.
    """

    def __init__(self, brave_client: Any = None, mongodb_service: Any = None):
        """Initialize query handler service.

        Args:
            brave_client: Brave MCP client for web search
            mongodb_service: MongoDB service for trading data
        """
        self.brave_client = brave_client
        self.mongodb_service = mongodb_service

    @staticmethod
    def _build_wallet_state_context(user_id: str) -> str:
        """Build a ground-truth wallet state block to inject into the LLM system prompt.

        Prevents hallucination by giving the LLM real wallet data (or explicit "no wallet" signal).
        """
        try:
            from ..startup import get_wallet_repo
            wallet_repo = get_wallet_repo()
            if not wallet_repo:
                return ""
            wallet = wallet_repo.get_active_wallet(user_id)
        except Exception as e:
            logger.warning(f"[WalletState] Failed to fetch wallet for state injection: {e}")
            return ""

        lines = [
            "",
            "## SEEKER WALLET STATE (GROUND TRUTH)",
        ]

        if wallet:
            addr = wallet.get("public_address", "")
            name = wallet.get("wallet_name", "My Wallet")
            short_addr = f"{addr[:8]}...{addr[-4:]}" if len(addr) > 12 else addr
            lines.extend([
                f"- Wallet name: {name}",
                f"- Public address: {addr}",
                f"- Short address: {short_addr}",
                f"- Network: devnet",
                f"- Status: active",
                "",
                "Use ONLY these values when referring to the Seeker's wallet.",
                "Do NOT invent or guess any wallet details.",
            ])
        else:
            lines.extend([
                "The Seeker has NO active wallet.",
                "Do NOT invent wallet addresses, names, or balances.",
                "If asked about their wallet, tell them they need to create one first.",
            ])

        return "\n".join(lines)

    def _finalize_response(
        self,
        answer: str,
        persona_name: str,
        metadata: ResponseMetadata,
        used_search: bool = False,
        citation_valid: Optional[bool] = None,
        search_results_count: Optional[int] = None
    ) -> dict:
        """Finalize response with common post-processing.

        Shared finalization logic extracted from all query handlers (Phase 2 DRY).
        Applies: first-person rewrite, multi-message splitting, response formatting.

        Args:
            answer: Raw LLM answer
            persona_name: Display name of persona
            metadata: Response metadata object
            used_search: Whether search was used
            citation_valid: Optional citation validation result
            search_results_count: Optional search results count

        Returns:
            Standardized response dict
        """
        # Apply first-person voice enforcement
        answer, was_rewritten = post_process_first_person(answer, persona_name)

        # Import message processing functions
        from .message_processing_service import force_multi_message_split, parse_multi_message_response

        # Force-split into multi-message if LLM didn't use <msg> tags
        answer = force_multi_message_split(answer, "")

        # Parse for multi-message format
        messages, flow_type = parse_multi_message_response(answer)

        # Build response dict
        response = {
            "answer": messages if flow_type == 'multi' else messages[0],
            "message_flow": flow_type,
            "message_count": len(messages),
            "used_search": used_search,
            "metadata": metadata.model_dump(),
            "rewritten": was_rewritten
        }

        # Add optional fields
        if citation_valid is not None:
            response["citation_valid"] = citation_valid
        if search_results_count is not None:
            response["search_results_count"] = search_results_count

        return response

    def handle_mongodb_query(
        self,
        message: str,
        system_prompt: str,
        user_compiled: str,
        mongodb_tools: list,
        metadata: ResponseMetadata,
        persona_name: str,
        persona_card: dict
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

                service = LLMCompletionService(
                    base=get_settings().ollama.base,
                    model=get_settings().ollama.model,
                    temperature=get_persona_temperature_override(persona_card)
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

                answer = service.complete(system=synthesis_system, user_prompt=synthesis_prompt)

                metadata.source_type = "mongodb_mcp"
                metadata.tools_used = [tool_name]
                metadata.cache_status = mongodb_result.get("cache_status", "miss")
                metadata.data_timestamp = mongodb_result.get("timestamp", "")

                logger.info(f"MongoDB query completed: tool={tool_name}, cache={metadata.cache_status}")

                # Use shared finalization logic (Phase 2 DRY)
                return self._finalize_response(
                    answer=answer,
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=True
                )
        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")

        # Fallback to regular LLM response
        from ..llm_client import LC_OllamaClient  # noqa: PLC0415
        client = LC_OllamaClient(
            base=get_settings().ollama.base,
            model=get_settings().ollama.model,
            temperature=get_persona_temperature_override(persona_card)
        )
        answer = client.complete(system=system_prompt, user_prompt=user_compiled)

        # Use shared finalization logic (Phase 2 DRY)
        return self._finalize_response(
            answer=answer,
            persona_name=persona_name,
            metadata=metadata,
            used_search=False
        )

    def handle_brave_query(
        self,
        system_prompt: str,
        user_compiled: str,
        tools: list,
        metadata: ResponseMetadata,
        persona_name: str,
        persona_card: dict
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

        from ..llm_client import LC_OllamaClient  # noqa: PLC0415
        client = LC_OllamaClient(
            base=get_settings().ollama.base,
            model=get_settings().ollama.model,
            temperature=get_persona_temperature_override(persona_card),
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

        # Use shared finalization logic (Phase 2 DRY)
        response = self._finalize_response(
            answer=answer,
            persona_name=persona_name,
            metadata=metadata,
            used_search=tool_call is not None,
            citation_valid=has_valid_citations,
            search_results_count=search_count if search_results else None
        )

        # Log completion
        if search_results:
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
        persona_name: str,
        persona_card: dict
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

        from ..llm_client import LC_OllamaClient  # noqa: PLC0415
        client = LC_OllamaClient(
            base=get_settings().ollama.base,
            model=get_settings().ollama.model,
            temperature=get_persona_temperature_override(persona_card),
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

        # Use shared finalization logic (Phase 2 DRY)
        return self._finalize_response(
            answer=answer,
            persona_name=persona_name,
            metadata=metadata,
            used_search=True,
            citation_valid=has_valid_citations,
            search_results_count=search_count
        )

    def handle_wallet_query(
        self,
        message: str,
        system_prompt: str,
        user_compiled: str,
        wallet_tools: list,
        metadata: ResponseMetadata,
        persona_name: str,
        persona_card: dict,
        session_id: Optional[str] = None,
        user_id: Optional[str] = "default_user",
    ) -> dict:
        """Handle wallet-intent queries — the E.E.V.A. financial co-pilot path.

        For read-only ops (balance, quote, RSI check): calls Jupiter MCP and synthesizes
        response in E.E.V.A.'s voice.

        For write ops (propose swap, propose strategy, create wallet): returns a
        ProposalCard or StrategyApprovalCard structured message WITHOUT calling
        Jupiter MCP execute tools.

        Multi-turn wallet creation flow is managed via _wallet_flows session state.
        """
        from ..tools.wallet_tool_generators import WALLET_TOOLS

        logger.info(f"[WalletQuery] Handling wallet intent for user={user_id}")

        # Check if this is part of a guided wallet creation flow
        flow_state = _wallet_flows.get(session_id or "")
        if flow_state:
            return self._handle_wallet_creation_step(
                message=message,
                flow_state=flow_state,
                session_id=session_id or "",
                user_id=user_id,
                persona_name=persona_name,
                metadata=metadata,
            )

        # Wallet deletion via chat — return a confirmation card (HITL)
        _DELETION_PATTERN = re.compile(
            r"(?:delete|remove|destroy|deactivate|wipe|clear|get rid of|nuke)"
            r"(?:\s+)"
            r"(?:my |all |all my |the |the created |every )?"
            r"(?:wallet|wallets)",
            re.IGNORECASE,
        )
        msg_lower = message.lower()
        if _DELETION_PATTERN.search(msg_lower):
            logger.info(f"[WalletQuery] Wallet deletion intent detected for user={user_id}")
            try:
                from ..startup import get_wallet_repo
                wallet_repo = get_wallet_repo()
                wallet = wallet_repo.get_active_wallet(user_id or "default_user") if wallet_repo else None
            except Exception as e:
                logger.warning(f"[WalletQuery] Wallet lookup failed during deletion: {e}")
                wallet = None

            if not wallet:
                metadata.source_type = "wallet_mcp"
                metadata.tools_used = []
                return self._finalize_response(
                    answer="You have no active wallet to delete.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            # Build and return a deletion confirmation card
            from ..services.wallet_proposal_service import build_wallet_deletion_proposal
            proposal = build_wallet_deletion_proposal(
                user_id=user_id or "default_user",
                wallet_name=wallet.get("wallet_name", "My Wallet"),
                public_address=wallet.get("public_address", ""),
            )
            metadata.source_type = proposal["metadata"]["source_type"]
            metadata.proposal_type = proposal["metadata"]["proposal_type"]
            metadata.proposal = proposal["metadata"]["proposal"]
            metadata.tools_used = []
            return self._finalize_response(
                answer=proposal["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=False,
            )

        # Keyword-based wallet creation detection — deterministic, doesn't rely on LLM tool call
        # If message clearly asks to create a wallet and no flow is active, start it directly.
        _CREATION_TRIGGERS = [
            "create a wallet", "create my wallet", "create wallet",
            "set up a wallet", "set up my wallet", "setup wallet",
            "make a wallet", "new wallet", "generate a wallet",
            "solana wallet", "create solana", "i want to create a",
        ]
        if any(t in msg_lower for t in _CREATION_TRIGGERS):
            # Pre-flight: check if user already has an active wallet
            try:
                from ..startup import get_wallet_repo
                wallet_repo = get_wallet_repo()
                if wallet_repo:
                    existing = wallet_repo.get_active_wallet(user_id or "default_user")
                    if existing:
                        metadata.source_type = "wallet_mcp"
                        metadata.tools_used = []
                        addr = existing.get("public_address", "")
                        short = f"{addr[:8]}...{addr[-4:]}" if len(addr) > 12 else addr
                        logger.info(f"[WalletQuery] Creation blocked — wallet already exists for user={user_id}")
                        return self._finalize_response(
                            answer=(
                                f"You already have an active wallet ({short}). "
                                "Each account can only hold one active Solana wallet at a time. "
                                "If you'd like to replace it, please delete the existing one first via the Wallet settings."
                            ),
                            persona_name=persona_name,
                            metadata=metadata,
                            used_search=False,
                        )
            except Exception as e:
                logger.warning(f"[WalletQuery] Pre-flight wallet check failed (non-fatal): {e}")

            from ..services.wallet_proposal_service import build_wallet_creation_step
            session_key = session_id or ""
            _wallet_flows[session_key] = {
                "step": 1,
                "user_id": user_id or "default_user",
                "wallet_name": "My Wallet",
            }
            step_msg = build_wallet_creation_step(step=1)
            metadata.source_type = "wallet_flow"
            metadata.tools_used = ["wallet_create_guided"]
            logger.info(f"[WalletQuery] Wallet creation flow started for user={user_id}")
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        # Inject wallet ground-truth state into system prompt to prevent hallucination
        wallet_state_block = self._build_wallet_state_context(user_id or "default_user")
        augmented_system_prompt = system_prompt + wallet_state_block if wallet_state_block else system_prompt

        # Regular wallet query: let LLM choose the right tool via standard tool-calling flow
        from ..llm_client import LC_OllamaClient  # noqa: PLC0415
        client = LC_OllamaClient(
            base=get_settings().ollama.base,
            model=get_settings().ollama.model,
            temperature=get_persona_temperature_override(persona_card),
        )

        # Use standard tool-calling path — LLM decides which wallet tool to call
        answer, tool_call, _ = client.complete_with_tools(
            persona_system=augmented_system_prompt,
            user_prompt=user_compiled,
            tools=wallet_tools,
        )

        # If LLM called wallet_create_guided → start wallet creation flow
        if tool_call and tool_call.name == "wallet_create_guided":
            from ..services.wallet_proposal_service import build_wallet_creation_step
            session_key = session_id or ""
            _wallet_flows[session_key] = {
                "step": 1,
                "user_id": user_id,
                "wallet_name": tool_call.arguments.get("wallet_name", "My Wallet"),
            }
            step_msg = build_wallet_creation_step(step=1)
            metadata.source_type = "wallet_mcp"
            metadata.tools_used = ["wallet_create_guided"]
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        metadata.source_type = "wallet_mcp"
        metadata.tools_used = [tool_call.name] if tool_call else []

        return self._finalize_response(
            answer=answer,
            persona_name=persona_name,
            metadata=metadata,
            used_search=tool_call is not None,
        )

    def _handle_wallet_creation_step(
        self,
        message: str,
        flow_state: dict,
        session_id: str,
        user_id: str,
        persona_name: str,
        metadata: ResponseMetadata,
    ) -> dict:
        """Handle multi-turn guided wallet creation (steps 1→2→3)."""
        from ..services.wallet_proposal_service import build_wallet_creation_step
        from ..jupiter.wallet_manager import encrypt_private_key, generate_new_keypair, cache_session_key
        from ..startup import get_wallet_repo

        step = flow_state.get("step", 1)

        if step == 1:
            # User provided wallet name
            flow_state["wallet_name"] = message.strip() or "My Wallet"
            flow_state["step"] = 2
            _wallet_flows[session_id] = flow_state
            step_msg = build_wallet_creation_step(step=2, wallet_name=flow_state["wallet_name"])
            metadata.source_type = "wallet_mcp"
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        elif step == 2:
            # User provided password — generate keypair and encrypt
            password = message.strip()
            if len(password) < 8:
                metadata.source_type = "wallet_mcp"
                return self._finalize_response(
                    answer="That password is too short — please choose at least 8 characters.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            keypair = generate_new_keypair()
            public_address = keypair["public_address"]
            private_key = keypair["private_key_b58"]

            enc = encrypt_private_key(private_key, password)

            # Save to SQLite
            try:
                wallet_repo = get_wallet_repo()
                wallet_repo.create_wallet(
                    user_id=user_id,
                    wallet_name=flow_state.get("wallet_name", "My Wallet"),
                    public_address=public_address,
                    encrypted_private_key=enc.encrypted,
                    key_salt=enc.salt,
                    key_nonce=enc.nonce,
                )
                # Cache in session
                cache_session_key(user_id, private_key)
            except Exception as e:
                logger.error(f"[WalletCreation] Failed to save wallet: {e}")
                del _wallet_flows[session_id]
                metadata.source_type = "wallet_mcp"
                return self._finalize_response(
                    answer="I encountered an error saving your wallet. Please try again.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            # Clear flow state
            del _wallet_flows[session_id]

            step_msg = build_wallet_creation_step(step=3, public_address=public_address)
            metadata.source_type = "wallet_mcp"
            metadata.tools_used = ["wallet_create_guided"]
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        # Unknown step — clear and restart
        del _wallet_flows[session_id]
        return self._finalize_response(
            answer="Something went wrong with the wallet setup. Let's start over — say 'create wallet' when ready.",
            persona_name=persona_name,
            metadata=metadata,
            used_search=False,
        )
