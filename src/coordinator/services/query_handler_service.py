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

# Regex to strip leaked internal tool names from LLM responses (zero-latency guardrail)
_TOOL_NAME_PATTERN = re.compile(
    r'\b(wallet_get_balances|wallet_create_guided|solana_get_quote|'
    r'solana_rsi_check|solana_propose_swap|solana_propose_strategy|'
    r'solana_trade_history|brave_web_search|bitcoin_current_price|'
    r'bitcoin_historical_prices|bitcoin_trading_summary|bitcoin_technical_analysis)\b'
)


def has_active_wallet_flow(session_id: Optional[str]) -> bool:
    """Check whether *session_id* has an in-progress guided wallet creation flow."""
    return bool(session_id and _wallet_flows.get(session_id))


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

        Includes active wallets (with full addresses), deleted wallets (history),
        cached balances, and trading activity summary. Prevents hallucination by
        giving the LLM real wallet data (or explicit "no wallet" signal).
        """
        from ..repositories.wallet_registry_repository import MAX_ACTIVE_WALLETS

        # Fetch wallet registry (multi-wallet aware)
        registry_wallets = []
        all_wallets = []
        try:
            from ..startup import get_wallet_registry_repo
            registry_repo = get_wallet_registry_repo()
            if registry_repo:
                registry_wallets = registry_repo.get_active_wallets(user_id)
                all_wallets = registry_repo.get_all_wallets(user_id)
        except Exception:
            pass

        # Fallback: if registry is empty, try legacy single-wallet repo
        if not registry_wallets and not all_wallets:
            try:
                from ..startup import get_wallet_repo
                wallet_repo = get_wallet_repo()
                if wallet_repo:
                    legacy = wallet_repo.get_active_wallet(user_id)
                    if legacy:
                        registry_wallets = [legacy]
                        all_wallets = [legacy]
            except Exception as e:
                logger.warning(f"[WalletState] Failed to fetch wallet for state injection: {e}")

        # Identify deleted wallets
        deleted_wallets = [w for w in all_wallets if w.get("status") == "deleted"]

        # Fetch balance cache and activity summary
        balance_map: dict = {}
        summary = None
        try:
            from ..startup import get_wallet_summary_repo
            summary_repo = get_wallet_summary_repo()
            if summary_repo:
                for bc in summary_repo.get_user_balances(user_id):
                    balance_map[bc.get("wallet_id", "")] = bc
                summary = summary_repo.get_summary(user_id)
        except Exception:
            pass

        # Check unlock state from session cache
        from ..jupiter.wallet_manager import wallet_unlocked

        lines = [
            "",
            "## SEEKER WALLET STATE (GROUND TRUTH — use ONLY these values)",
        ]

        active_count = len(registry_wallets)
        remaining = MAX_ACTIVE_WALLETS - active_count

        if registry_wallets:
            lines.append(f"- Active wallets: {active_count} of {MAX_ACTIVE_WALLETS} slots used")

            for i, w in enumerate(registry_wallets, 1):
                addr = w.get("public_address", "")
                name = w.get("wallet_name", "My Wallet")
                w_id = w.get("wallet_id", "")

                # Unlock state
                is_unlocked = wallet_unlocked(user_id)
                lock_str = "UNLOCKED" if is_unlocked else "LOCKED"

                # Cached balance
                bc = balance_map.get(w_id, {})
                sol_bal = bc.get("sol_balance")
                bal_str = f"{sol_bal:.4f} SOL" if sol_bal is not None else "unknown"
                checked = bc.get("last_checked", "never")

                lines.append(
                    f"- Wallet {i}: \"{name}\" | Address: {addr} | {lock_str}, {bal_str}, checked {checked}"
                )

            lines.append(f"- Available slots: {remaining} remaining")

            # Activity summary
            if summary:
                total_trades = summary.get("total_trades", 0)
                total_vol = summary.get("total_volume_usdc", 0.0)
                last_pair = summary.get("last_trade_pair", "")
                last_action = summary.get("last_trade_action", "")
                last_ts = summary.get("last_trade_timestamp", "")
                if total_trades > 0:
                    lines.append(f"- Trading activity: {total_trades} trades, ${total_vol:.2f} total volume")
                    if last_pair:
                        lines.append(f"- Last trade: {last_action.capitalize()} {last_pair} ({last_ts})")

            lines.extend([
                "",
                "RULES:",
                f"- The Seeker can create {remaining} more wallet(s) (max {MAX_ACTIVE_WALLETS}). "
                + ("If at limit, they must delete one first." if remaining == 0 else ""),
                "- For CURRENT balances, ALWAYS call wallet_get_balances. Above values are cached.",
                "- If a wallet shows LOCKED, tell the Seeker to unlock it before trading.",
                "- Never invent wallet addresses, names, balances, or trade history.",
                "- When asked for a wallet address, give the FULL address shown above — never truncate it.",
            ])
        else:
            lines.extend([
                f"The Seeker has NO active wallet (0 of {MAX_ACTIVE_WALLETS} slots used).",
                "Do NOT invent wallet addresses, names, or balances.",
                "If asked about their wallet, tell them they need to create one first.",
            ])

        # Include deleted wallet history so LLM can accurately answer about past wallets
        if deleted_wallets:
            lines.append("")
            lines.append("DELETED WALLETS (no longer active — for reference only):")
            for dw in deleted_wallets:
                d_name = dw.get("wallet_name", "Unknown")
                d_addr = dw.get("public_address", "")
                d_at = dw.get("deleted_at", "unknown date")
                lines.append(f"- \"{d_name}\" | Address: {d_addr} | Deleted: {d_at}")
            lines.append("These wallets are DELETED and cannot be used. Do not present them as active.")

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

        # Strip leaked internal tool names from response
        answer = _TOOL_NAME_PATTERN.sub('', answer).strip()

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
        from ..llm_client import create_llm_client  # noqa: PLC0415
        client = create_llm_client(persona_card)
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

        from ..llm_client import create_llm_client  # noqa: PLC0415
        client = create_llm_client(persona_card, mcp_client=self.brave_client)

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

        from ..llm_client import create_llm_client  # noqa: PLC0415
        client = create_llm_client(persona_card, mcp_client=self.brave_client)

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
            # Pre-flight: check wallet count against 3-wallet limit
            slots_used = 0
            slots_max = 3
            try:
                from ..startup import get_wallet_registry_repo
                from ..repositories.wallet_registry_repository import MAX_ACTIVE_WALLETS
                registry_repo = get_wallet_registry_repo()
                if registry_repo:
                    allowed, count, next_slot = registry_repo.can_create_wallet(user_id or "default_user")
                    slots_used = count
                    slots_max = MAX_ACTIVE_WALLETS
                    if not allowed:
                        metadata.source_type = "wallet_mcp"
                        metadata.tools_used = []
                        logger.info(f"[WalletQuery] Creation blocked — user={user_id} at limit ({count}/{MAX_ACTIVE_WALLETS})")
                        return self._finalize_response(
                            answer=(
                                f"You've reached the maximum of {MAX_ACTIVE_WALLETS} active wallets. "
                                "To create a new one, please delete an existing wallet first."
                            ),
                            persona_name=persona_name,
                            metadata=metadata,
                            used_search=False,
                        )
            except Exception as e:
                logger.warning(f"[WalletQuery] Pre-flight wallet count check failed (non-fatal): {e}")

            from ..services.wallet_proposal_service import build_wallet_creation_step
            session_key = session_id or ""
            _wallet_flows[session_key] = {
                "step": 1,
                "user_id": user_id or "default_user",
                "wallet_name": "My Wallet",
                "slots_used": slots_used,
                "slots_max": slots_max,
            }
            step_msg = build_wallet_creation_step(step=1, slots_used=slots_used, slots_max=slots_max)
            metadata.source_type = "wallet_flow"
            metadata.tools_used = ["wallet_create_guided"]
            logger.info(f"[WalletQuery] Wallet creation flow started for user={user_id} (slot {slots_used + 1}/{slots_max})")
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
        from ..llm_client import create_llm_client  # noqa: PLC0415
        client = create_llm_client(persona_card)

        # Use standard tool-calling path — LLM decides which wallet tool to call
        answer, tool_call, _ = client.complete_with_tools(
            persona_system=augmented_system_prompt,
            user_prompt=user_compiled,
            tools=wallet_tools,
        )

        # If LLM called wallet_create_guided → start wallet creation flow
        if tool_call and tool_call.name == "wallet_create_guided":
            # Count-based pre-flight check
            slots_used = 0
            slots_max = 3
            try:
                from ..startup import get_wallet_registry_repo
                from ..repositories.wallet_registry_repository import MAX_ACTIVE_WALLETS
                registry_repo = get_wallet_registry_repo()
                if registry_repo:
                    allowed, count, _ = registry_repo.can_create_wallet(user_id or "default_user")
                    slots_used = count
                    slots_max = MAX_ACTIVE_WALLETS
                    if not allowed:
                        metadata.source_type = "wallet_mcp"
                        metadata.tools_used = []
                        return self._finalize_response(
                            answer=f"You've reached the maximum of {MAX_ACTIVE_WALLETS} active wallets. Delete one first.",
                            persona_name=persona_name,
                            metadata=metadata,
                            used_search=False,
                        )
            except Exception:
                pass

            from ..services.wallet_proposal_service import build_wallet_creation_step
            session_key = session_id or ""
            _wallet_flows[session_key] = {
                "step": 1,
                "user_id": user_id,
                "wallet_name": tool_call.arguments.get("wallet_name", "My Wallet"),
                "slots_used": slots_used,
                "slots_max": slots_max,
            }
            step_msg = build_wallet_creation_step(step=1, slots_used=slots_used, slots_max=slots_max)
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
        """Handle multi-turn guided wallet creation (steps 1→2→3→4).

        Step 1: User provides wallet name
        Step 2: User provides password — generate keypair from BIP39 mnemonic, encrypt, save
        Step 3: Display 12-word mnemonic — user must confirm they saved it
        Step 4: User confirms — permanently wipe mnemonic from memory, show success
        """
        from ..services.wallet_proposal_service import build_wallet_creation_step
        from ..jupiter.wallet_manager import (
            encrypt_private_key, generate_mnemonic, generate_keypair_from_mnemonic,
            cache_session_key,
        )
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
            # User provided password — generate BIP39 mnemonic, derive keypair, encrypt
            password = message.strip()
            if len(password) < 8:
                metadata.source_type = "wallet_mcp"
                return self._finalize_response(
                    answer="That password is too short — please choose at least 8 characters.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            # Generate BIP39 mnemonic and derive keypair
            mnemonic_phrase = generate_mnemonic()
            keypair = generate_keypair_from_mnemonic(mnemonic_phrase)
            public_address = keypair["public_address"]
            private_key = keypair["private_key_b58"]

            enc = encrypt_private_key(private_key, password)

            # Save encrypted wallet to SQLite
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
                # Cache in session (wallet is unlocked immediately after creation)
                cache_session_key(user_id, private_key)
            except Exception as e:
                logger.error(f"[WalletCreation] Failed to save wallet: {e}")
                # Zero out sensitive data before clearing
                mnemonic_phrase = "\x00" * len(mnemonic_phrase)
                del mnemonic_phrase
                del _wallet_flows[session_id]
                metadata.source_type = "wallet_mcp"
                return self._finalize_response(
                    answer="I encountered an error saving your wallet. Please try again.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            # Register in wallet registry (multi-wallet tracking)
            try:
                from ..startup import get_wallet_registry_repo
                registry_repo = get_wallet_registry_repo()
                if registry_repo:
                    registry_repo.register_wallet(
                        user_id=user_id,
                        wallet_name=flow_state.get("wallet_name", "My Wallet"),
                        public_address=public_address,
                    )
            except Exception as e:
                logger.warning(f"[WalletCreation] Registry write failed (non-fatal): {e}")

            # Update activity summary
            try:
                from ..startup import get_wallet_summary_repo
                summary_repo = get_wallet_summary_repo()
                if summary_repo:
                    from ..startup import get_wallet_registry_repo
                    reg = get_wallet_registry_repo()
                    active_count = reg.get_active_count(user_id) if reg else 1
                    summary_repo.upsert_summary(
                        user_id=user_id,
                        active_wallet_count=active_count,
                        total_wallets_ever=(summary_repo.get_summary(user_id) or {}).get("total_wallets_ever", 0) + 1,
                    )
            except Exception as e:
                logger.warning(f"[WalletCreation] Summary update failed (non-fatal): {e}")

            # Hold mnemonic in flow state for step 3 display (memory only, never persisted)
            flow_state["step"] = 3
            flow_state["mnemonic"] = mnemonic_phrase
            flow_state["public_address"] = public_address
            _wallet_flows[session_id] = flow_state

            step_msg = build_wallet_creation_step(
                step=3,
                mnemonic=mnemonic_phrase,
                public_address=public_address,
            )
            metadata.source_type = "wallet_mcp"
            metadata.tools_used = ["wallet_create_guided"]
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        elif step == 3:
            # User should confirm they saved the recovery phrase
            msg_lower = message.strip().lower()
            _CONFIRM_PHRASES = [
                "i saved it", "saved it", "i've saved it", "confirm", "confirmed",
                "yes", "done", "i wrote it down", "saved", "got it", "ok", "okay",
            ]
            if not any(p in msg_lower for p in _CONFIRM_PHRASES):
                metadata.source_type = "wallet_mcp"
                return self._finalize_response(
                    answer=(
                        "Please confirm you've saved your 12-word recovery phrase before continuing. "
                        "Type **'I saved it'** or **'confirm'** to proceed. "
                        "This phrase will be permanently deleted and cannot be shown again."
                    ),
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                )

            # User confirmed — permanently wipe mnemonic
            public_address = flow_state.get("public_address", "N/A")
            mnemonic_ref = flow_state.get("mnemonic", "")

            # Overwrite mnemonic in flow state with zeros, then delete
            if mnemonic_ref:
                flow_state["mnemonic"] = "\x00" * len(mnemonic_ref)
            flow_state.pop("mnemonic", None)

            # Clear flow state entirely
            del _wallet_flows[session_id]

            logger.info(f"[WalletCreation] Mnemonic wiped for user={user_id}, wallet creation complete")

            step_msg = build_wallet_creation_step(step=4, public_address=public_address)
            metadata.source_type = "wallet_mcp"
            metadata.tools_used = ["wallet_create_guided"]
            return self._finalize_response(
                answer=step_msg["content"],
                persona_name=persona_name,
                metadata=metadata,
                used_search=True,
            )

        # Unknown step — clear and restart (also wipe any mnemonic in state)
        if "mnemonic" in flow_state:
            flow_state["mnemonic"] = "\x00" * len(flow_state["mnemonic"])
        del _wallet_flows[session_id]
        return self._finalize_response(
            answer="Something went wrong with the wallet setup. Let's start over — say 'create wallet' when ready.",
            persona_name=persona_name,
            metadata=metadata,
            used_search=False,
        )
