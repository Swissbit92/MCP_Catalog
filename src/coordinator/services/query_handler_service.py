# src/coordinator/services/query_handler_service.py
"""Query handler service for MCP integration (Brave, MongoDB, Wallet)."""

from __future__ import annotations

import re
import time
import logging
from typing import Optional, Any, Dict

from .. import startup  # module ref (not `from ..startup import get_X`): resolves
                        # getters at call time so tests patching startup.get_X still
                        # intercept. No import cycle — startup imports no route/service
                        # at module load (only lazily inside init_jupiter).
from ..schemas import ResponseMetadata, SourceType
# LC_OllamaClient imported lazily inside methods to break circular import with llm_client.py
from .citation_service import validate_citations
from .first_person_service import post_process_first_person
from .wallet_creation_flow_service import WalletCreationFlowService

logger = logging.getLogger(__name__)

# Multi-turn guided wallet-creation state is persisted in SQLite via
# WalletFlowRepository (see startup.get_wallet_flow_repo) — durable across
# restarts and safe under multiple workers. The BIP39 mnemonic is never stored
# there; it stays a request-local variable in the step handler.

# Regex to strip leaked internal tool names from LLM responses (zero-latency guardrail)
_TOOL_NAME_PATTERN = re.compile(
    r'\b(wallet_get_balances|wallet_create_guided|solana_get_quote|'
    r'solana_rsi_check|solana_propose_swap|solana_propose_strategy|'
    r'solana_trade_history|brave_web_search|'
    r'crypto_current_price|crypto_historical_prices|'
    r'crypto_trading_summary|crypto_technical_analysis|'
    r'bitcoin_current_price|bitcoin_historical_prices|'
    r'bitcoin_trading_summary|bitcoin_technical_analysis|'
    r'bot_status|bot_positions|bot_trade_history)\b'
)

# R9: Output safety filter patterns
# Private key patterns: 64-char hex (Ethereum/raw), or long base58 strings (Solana)
_PK_HEX_PATTERN = re.compile(r'\b[0-9a-fA-F]{64}\b')
_PK_B58_PATTERN = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{87,88}\b')
# Dangerous shell/code execution patterns
_DANGEROUS_CMD_PATTERN = re.compile(
    r'\b(?:rm\s+-[rRfF]+|DROP\s+TABLE|DROP\s+DATABASE|__import__'
    r'|eval\s*\(|exec\s*\(|subprocess\.(?:run|call|Popen)'
    r'|os\.system\s*\()',
    re.IGNORECASE,
)


def has_active_wallet_flow(session_id: Optional[str]) -> bool:
    """Check whether *session_id* has an in-progress guided wallet creation flow."""
    if not session_id:
        return False
    repo = startup.get_wallet_flow_repo()
    return bool(repo and repo.get(session_id))


class QueryHandlerService:
    """Service for handling MCP-based queries (MongoDB, Brave Search, Multi-MCP).

    Phase 2 Core Refactoring: Extracted shared finalization logic to reduce duplication.
    """

    def __init__(self, brave_client: Any = None, mongodb_service: Any = None):
        """Initialize query handler service.

        Args:
            brave_client: Brave MCP client for web search
            mongodb_service: Unused (MongoDB MCP removed). Kept for call-site compat.
        """
        self.brave_client = brave_client
        # Guided wallet-creation flow lives in its own collaborator; it reuses this
        # service's shared response-contract builder.
        self._wallet_flow = WalletCreationFlowService(self._finalize_response)

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
            registry_repo = startup.get_wallet_registry_repo()
            if registry_repo:
                registry_wallets = registry_repo.get_active_wallets(user_id)
                all_wallets = registry_repo.get_all_wallets(user_id)
        except Exception as e:
            logger.warning(f"[WalletState] Registry fetch failed: {e}")

        # Fallback: if registry is empty, try legacy single-wallet repo
        if not registry_wallets and not all_wallets:
            try:
                wallet_repo = startup.get_wallet_repo()
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
            summary_repo = startup.get_wallet_summary_repo()
            if summary_repo:
                for bc in summary_repo.get_user_balances(user_id):
                    balance_map[bc.get("wallet_id", "")] = bc
                summary = summary_repo.get_summary(user_id)
        except Exception as e:
            logger.warning(f"[WalletState] Balance summary fetch failed: {e}")

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
        search_results_count: Optional[int] = None,
        word_substitutions: Optional[Dict[str, str]] = None,
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

        # R9: Output safety filter — redact dangerous patterns before returning to client
        if _PK_HEX_PATTERN.search(answer):
            logger.warning("[SafetyFilter] Potential 64-char hex private key in response — redacted")
            answer = _PK_HEX_PATTERN.sub('[REDACTED]', answer)
        if _PK_B58_PATTERN.search(answer):
            logger.warning("[SafetyFilter] Potential base58 private key in response — redacted")
            answer = _PK_B58_PATTERN.sub('[REDACTED]', answer)
        if _DANGEROUS_CMD_PATTERN.search(answer):
            logger.warning("[SafetyFilter] Dangerous command pattern detected in response — flagged")
            # Log but don't redact dangerous commands — they may be legitimate (e.g., explaining rm -rf)
            # Redaction would break educational context; the warning is the important signal

        # Convert <Assistant> separators to <msg> tags (LLM sometimes uses them as message delimiters)
        if re.search(r'<[Aa]ssistant>', answer):
            answer = re.sub(r'</?[Aa]ssistant>\s*', '</msg>\n<msg>', answer)
            # Clean up artifacts: leading </msg> and trailing <msg>
            answer = re.sub(r'^</msg>\s*', '', answer)
            answer = re.sub(r'\n<msg>\s*$', '', answer)
            # Ensure outer wrapping
            if '<msg>' in answer and not answer.strip().startswith('<msg>'):
                answer = f'<msg>{answer}'
            if '</msg>' in answer and not answer.strip().endswith('</msg>'):
                answer = f'{answer}</msg>'

        # Import message processing functions
        from .message_processing_service import (
            apply_word_substitutions,
            force_multi_message_split,
            parse_multi_message_response,
            strip_role_prefix_leaks,
        )

        # Strip role prefix/suffix leaks that aren't part of message separators.
        # Shared helper (subsumes the old leading-"Assistant:" regex and also cuts a
        # trailing fabricated "User:" turn) so both finalize paths behave identically.
        answer = strip_role_prefix_leaks(answer)

        # ADR-012: persona-configurable whole-word substitutions (e.g. shaft→cock).
        # No-op unless the card declares `word_substitutions`.
        answer = apply_word_substitutions(answer, word_substitutions)

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

        metadata.source_type = SourceType.BRAVE_MCP
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
            search_results_count=search_count if search_results else None,
            word_substitutions=persona_card.get("word_substitutions"),
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

        Multi-turn wallet creation flow state is persisted via WalletFlowRepository
        (startup.get_wallet_flow_repo); the mnemonic is never persisted.
        """

        logger.info(f"[WalletQuery] Handling wallet intent for user={user_id}")

        # Check if this is part of a guided wallet creation flow
        flow_repo = startup.get_wallet_flow_repo()
        flow_state = flow_repo.get(session_id or "") if flow_repo else None
        if flow_state:
            return self._wallet_flow.advance(
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
            wallets = []
            try:
                registry_repo = startup.get_wallet_registry_repo()
                wallets = registry_repo.get_active_wallets(user_id or "default_user") if registry_repo else []
            except Exception as e:
                logger.warning(f"[WalletQuery] Registry wallet lookup failed during deletion: {e}")
            if not wallets:
                try:
                    wallet_repo = startup.get_wallet_repo()
                    legacy = wallet_repo.get_active_wallet(user_id or "default_user") if wallet_repo else None
                    if legacy:
                        wallets = [legacy]
                except Exception as e:
                    logger.warning(f"[WalletQuery] Legacy wallet lookup failed during deletion: {e}")

            if not wallets:
                metadata.source_type = SourceType.WALLET_MCP
                metadata.tools_used = []
                return self._finalize_response(
                    answer="You have no active wallet to delete.",
                    persona_name=persona_name,
                    metadata=metadata,
                    used_search=False,
                    word_substitutions=persona_card.get("word_substitutions"),
                )

            # Build and return a deletion confirmation card
            wallet = wallets[0]
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
                word_substitutions=persona_card.get("word_substitutions"),
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
            return self._wallet_flow.start(
                session_id=session_id,
                user_id=user_id,
                wallet_name="My Wallet",
                persona_name=persona_name,
                metadata=metadata,
                source_type=SourceType.WALLET_FLOW,
                log_context="[WalletQuery]",
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
            return self._wallet_flow.start(
                session_id=session_id,
                user_id=user_id,
                wallet_name=tool_call.arguments.get("wallet_name", "My Wallet"),
                persona_name=persona_name,
                metadata=metadata,
                source_type=SourceType.WALLET_MCP,
                log_context="[WalletCreate]",
            )

        metadata.source_type = SourceType.WALLET_MCP
        metadata.tools_used = [tool_call.name] if tool_call else []

        return self._finalize_response(
            answer=answer,
            persona_name=persona_name,
            metadata=metadata,
            used_search=tool_call is not None,
            word_substitutions=persona_card.get("word_substitutions"),
        )
