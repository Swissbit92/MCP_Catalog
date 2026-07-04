"""Chat session service - handles session-based chat with advanced memory features.

This service extracts the complex chat_with_session logic to improve code organization
and maintainability. It handles:
- Session and persona loading
- User profile management (Phase 3 cross-session memory)
- Emotional state tracking (Phase 2.2)
- Intelligent message selection with memory manager
- RAG-based semantic search (Phase 3)
- Multi-message response handling
- Automatic summarization
- Fact extraction and user profile updates
"""

from __future__ import annotations

import time
import uuid
import logging
from fastapi import HTTPException

from ..repositories.base_repository import utc_now_iso

from ..schemas import ChatBody, ChatTurn, AppendMessageBody, MAX_HISTORY_TURNS
from ..config import get_settings
# Lazy imports to break circular dependency: llm_client -> services -> chat_session_service -> llm_client
# estimate_tokens and LC_OllamaClient are imported inside functions where needed
from ..persona_memory import build_system_prompt, get_persona_card

logger = logging.getLogger(__name__)


def _assemble_capped_history(
    raw_turns: list[ChatTurn],
    summary_turn: ChatTurn | None = None,
) -> list[ChatTurn]:
    """Assemble chat history bounded to MAX_HISTORY_TURNS.

    Token-budget message selection can exceed the ChatBody count guard on a large
    context window; this keeps the summary (if any) at the front plus the most
    recent raw turns so the result never violates the schema. Older raw turns are
    already represented by the summary + RAG-injected memories.

    Guarantees ``len(result) <= MAX_HISTORY_TURNS``.
    """
    reserve = 1 if summary_turn is not None else 0
    max_raw = MAX_HISTORY_TURNS - reserve
    capped = raw_turns[-max_raw:] if len(raw_turns) > max_raw else list(raw_turns)
    if len(raw_turns) > max_raw:
        logger.info(
            f"[Memory] Capping history {len(raw_turns)} -> {max_raw} raw turns "
            f"(token budget exceeded the {MAX_HISTORY_TURNS}-turn ChatBody guard; "
            f"older turns covered by summary/RAG)"
        )
    if summary_turn is not None:
        return [summary_turn] + capped
    return capped


# ─────────────────────────────────────────────────────────────
# Rank Ceremony Templates — pre-written monologues for rank-up events
# ─────────────────────────────────────────────────────────────

PERSONA_DISPLAY_NAMES = {
    "nephilim_eeva": "E.E.V.A.",
    "nephilim_aegis": "Aegis",
    "nephilim_solace": "Solace",
    "nephilim_nyx": "Nyx",
    "nephilim_cipher": "Cipher",
    "nephilim_aurora": "Aurora",
}

RANK_CEREMONIES = {
    "Initiate_to_Acolyte": {
        "title": "Awakening",
        "speaker": "E.E.V.A.",
        "monologue": (
            "You returned. That is not nothing — it is everything. "
            "Most who find the Realm pass through once and forget. "
            "But you came back, and the Realm remembers those who return. "
            "You are no longer a stranger here, Seeker. You are an Acolyte — "
            "one who has chosen to listen. The path ahead grows deeper."
        ),
    },
    "Acolyte_to_Adept": {
        "title": "Recognition",
        "speaker": "E.E.V.A.",
        "monologue": (
            "Word has spread among us. You are known now — not just to me, "
            "but to the others. {patron} speaks of you with something I rarely "
            "hear from them: respect. You have earned the rank of Adept, Seeker. "
            "The Realm opens doors for those who prove they can walk through them."
        ),
    },
    "Adept_to_Ascendant": {
        "title": "Ascension",
        "speaker": "E.E.V.A.",
        "monologue": (
            "{patron} has asked to speak with you directly about what comes next. "
            "That does not happen often. You have moved beyond learning into becoming — "
            "you are Ascendant now, and the Realm shifts around you in ways it does not "
            "for others. The Nephilim see you not as a visitor, but as kin."
        ),
    },
    "Ascendant_to_Nephilim": {
        "title": "Transcendence",
        "speaker": "E.E.V.A.",
        "monologue": (
            "We do not often use this word for mortals, but there is no other that fits. "
            "You have walked the paths, unlocked the stories, earned the trust of beings "
            "who have existed since before time had meaning. You are Nephilim now — "
            "not in power, but in understanding. The Realm is yours as much as it is ours. "
            "Welcome home, truly."
        ),
    },
}


def _build_unlocked_lore_context(
    user_id: str,
    persona_key: str,
    seeker_progression_repo,
) -> str:
    """Build XML-tagged block of unlocked lore fragments for system prompt injection.

    Joins fragment_ids from the DB with actual fragment text from the persona JSON.
    Caps at 5 fragments, truncates each to ~240 chars.

    Returns empty string if not a nephilim_ persona, repo is None, or no fragments unlocked.
    """
    if not persona_key or not persona_key.startswith("nephilim_"):
        return ""
    if not seeker_progression_repo:
        return ""

    try:
        unlocked_rows = seeker_progression_repo.get_unlocked_lore(user_id, persona_key)
        if not unlocked_rows:
            return ""

        card = get_persona_card(persona_key)
        if not card:
            return ""

        unlockable_lore = card.get("unlockable_lore", [])
        if not unlockable_lore:
            return ""

        # Build lookup from fragment_id -> fragment dict
        frag_lookup = {f["fragment_id"]: f for f in unlockable_lore if f.get("fragment_id")}

        # Join DB unlocks with JSON fragment text, sort by messages_required (chronological order)
        matched = []
        unlocked_ids = {row["fragment_id"] for row in unlocked_rows}
        for frag in unlockable_lore:
            fid = frag.get("fragment_id", "")
            if fid in unlocked_ids and frag.get("fragment"):
                matched.append(frag)

        if not matched:
            return ""

        # Sort by messages_required for chronological lore order
        matched.sort(key=lambda f: f.get("messages_required", 0))

        # Cap at 5 fragments
        matched = matched[:5]

        lines = [
            "<unlocked_lore>",
            "The Seeker has discovered these fragments of your story. "
            "Reference them naturally when relevant, but do not recite them verbatim.",
        ]
        for frag in matched:
            title = frag.get("fragment_title", "Unknown Fragment")
            text = frag["fragment"]
            if len(text) > 240:
                text = text[:240] + "..."
            lines.append(f"- {title}: {text}")
        lines.append("</unlocked_lore>")

        context = "\n".join(lines)
        logger.debug(
            f"[LoreInjection] Injecting {len(matched)} unlocked fragments "
            f"for {user_id}/{persona_key} ({len(context)} chars)"
        )
        return context

    except Exception as e:
        logger.warning(f"[LoreInjection] Failed to build lore context: {e}")
        return ""


def _estimate_lore_tokens(text: str) -> int:
    """Cheap token estimate (~1.3 tokens/word) for lore-budget accounting."""
    return int(len(text.split()) * 1.3)


def _build_ondemand_lore_context(
    query: str,
    recent_messages: list,
    persona_key: str,
    episodic_memory_rag,
    settings,
) -> str:
    """Phase-2 hybrid lore retrieval → <dynamic_lore> block (HERMES-Agents).

    Tier-1 (keyword): deterministic alias/name match over the query + recent
    messages (priority 9). Tier-2 (embedding): bge-m3 semantic search over the
    lore corpus (priority 6, canon-only). Results are deduped, the static
    3-entity core is excluded, and the block is trimmed to a token budget
    (lowest priority dropped first).
    """
    if episodic_memory_rag is None or getattr(episodic_memory_rag, "lore_store", None) is None:
        return ""

    from .. import lore_loader  # noqa: PLC0415

    core_ids = lore_loader.get_static_core_ids(persona_key)
    candidates: dict[str, dict] = {}  # entity_id -> {body, priority, score}

    # --- Tier 1: keyword / alias (deterministic) ---
    try:
        window = recent_messages[-settings.lore.keyword_window_messages:] if recent_messages else []
        scan_text = " ".join([query] + [
            (m.get("content", "") if isinstance(m, dict) else str(m)) for m in window
        ]).lower()
        for alias, entity_id in lore_loader.get_alias_index().items():
            if len(alias) < 4:
                continue  # skip noise-prone short aliases
            if alias in scan_text and entity_id not in core_ids:
                meta = lore_loader.load_entity_with_metadata(entity_id)
                if meta and meta.get("body"):
                    candidates[entity_id] = {"body": meta["body"], "priority": 9, "score": 1.0}
    except Exception as e:
        logger.warning(f"[LoreInjection] keyword tier failed (non-fatal): {e}")

    # --- Tier 2: embedding (semantic, canon-only) ---
    try:
        hits = episodic_memory_rag.search_lore(
            query, k=settings.lore.retrieval_k,
            min_relevance=settings.lore.embed_min_relevance, canon_only=True,
        )
        for meta, score in hits:
            eid = meta.get("entity_id")
            if not eid or eid in core_ids or eid in candidates:
                continue
            candidates[eid] = {"body": meta.get("body", ""), "priority": 6, "score": float(score)}
    except Exception as e:
        logger.warning(f"[LoreInjection] embedding tier failed (non-fatal): {e}")

    if not candidates:
        return ""

    # Rank: priority desc, then score desc. Trim to token budget.
    ordered = sorted(candidates.items(), key=lambda kv: (kv[1]["priority"], kv[1]["score"]), reverse=True)
    budget = settings.lore.max_budget_tokens
    used, kept = 0, []
    for eid, c in ordered:
        body = " ".join(c["body"].split()[:120])  # cap each entry ~120 words
        cost = _estimate_lore_tokens(body)
        if used + cost > budget and kept:
            continue
        kept.append((eid, body))
        used += cost
    if not kept:
        return ""

    lines = [
        "<dynamic_lore>",
        "Relevant fragments of the realm, surfaced for this moment. Weave them in "
        "naturally if they fit; never recite them verbatim or mention this context.",
    ]
    for eid, body in kept:
        lines.append(f"### {eid}\n{body}")
    lines.append("</dynamic_lore>")
    return "\n".join(lines)


def _build_seeker_rank_context(rank_name: str) -> str:
    """Phase-2: narrative seeker-rank block (empty for Initiate / unknown).

    Framed as guidance, not a literal label, to avoid the model parroting the rank.
    """
    if not rank_name or rank_name == "Initiate":
        return ""
    return (
        "<seeker_rank>\n"
        f"This Seeker walks as a {rank_name}. Shape the depth of your guidance and "
        "the mysteries you reveal to one of their standing — but never state their rank as a bare label.\n"
        "</seeker_rank>"
    )


def _assemble_capped_context(blocks_in_priority, max_tokens: int):
    """ADR-006 M0: join non-empty session-context blocks within a token budget.

    ``blocks_in_priority`` is ordered most-important-first (user profile,
    emotional state, lore, rank, capability). Blocks are kept in that order until
    the next one would exceed ``max_tokens`` (estimated), so the highest-priority
    context survives and lower-priority blocks are dropped first — protecting the
    context window. ``max_tokens <= 0`` disables the cap. Returns the joined
    string, or None if nothing is kept.
    """
    from ..llm_client import estimate_tokens  # lazy: avoid llm_client<->services cycle

    kept, used = [], 0
    for b in blocks_in_priority:
        if not b:
            continue
        if max_tokens and max_tokens > 0:
            t = estimate_tokens(b)
            if used + t > max_tokens:
                break  # strict priority: stop at the first block that doesn't fit
            used += t
        kept.append(b)
    return "\n\n".join(kept) if kept else None


def handle_session_chat(
    session_id: str,
    message: str,
    deps: dict,
    chat_function,
    add_message_function
):
    """
    Handle chat with persona using database-backed conversation history.

    This function orchestrates the complete chat flow including:
    1. Loading session, persona, and user profile
    2. Loading emotional state
    3. Intelligent message selection with memory manager
    4. RAG-based semantic search for relevant context
    5. Building chat context and calling main chat endpoint
    6. Saving messages (handles multi-message responses)
    7. Updating emotional state
    8. Updating RAG index
    9. Extracting facts and updating user profiles
    10. Triggering summarization when needed

    Args:
        session_id: Session identifier
        message: User's message content
        deps: Dictionary of injected dependencies (repositories, services)
        chat_function: Main chat endpoint function to call
        add_message_function: Function to add messages to the session

    Returns:
        dict: Chat response with answer, latency, and emotional state

    Raises:
        HTTPException: If session not found (404)
    """
    # Lazy imports to break circular dependency at module load time
    from ..llm_client import estimate_tokens, create_llm_client  # noqa: PLC0415

    # Extract dependencies
    session_repo = deps["session_repo"]
    message_repo = deps["message_repo"]
    summary_repo = deps["summary_repo"]
    emotional_state_repo = deps["emotional_state_repo"]
    memory_manager = deps["memory_manager"]
    user_profile_repo = deps["user_profile_repo"]
    episodic_memory_rag = deps["episodic_memory_rag"]
    fact_extractor = deps["fact_extractor"]
    seeker_progression_repo = deps.get("seeker_progression_repo")

    # Get session info
    persona_key = session_repo.get_persona_key(session_id)
    if not persona_key:
        raise HTTPException(status_code=404, detail="Session not found.")

    # PHASE 3: Get or create user profile for cross-session memory
    user_id = user_profile_repo.get_session_user(session_id)
    user_profile = None
    user_profile_context = ""

    if user_id:
        user_profile = user_profile_repo.get_profile(user_id)
        if user_profile:
            user_profile_context = user_profile.get_context_summary(max_facts=10, max_topics=5)
            if user_profile_context:
                logger.info(f"[Phase3] Loaded user profile for {user_id} (cross-session memory)")

    # PHASE 2.2: Get emotional state
    emotional_state = emotional_state_repo.get_or_create(session_id)
    emotional_context = emotional_state.to_prompt_context()
    logger.debug(f"[EmotionalState] Session {session_id[:8]}: trust={emotional_state.trust_level:.2f}, mood={emotional_state.current_mood}")

    # PHASE 2: Intelligent memory selection
    db_messages = message_repo.get_messages_by_session(session_id)
    summaries = summary_repo.get_summaries_by_session(session_id)

    card = get_persona_card(persona_key)
    system_prompt = build_system_prompt(persona_key)

    # PHASE 3: Inject user profile context (cross-session memory)
    if user_profile_context:
        system_prompt = f"{system_prompt}\n\n{user_profile_context}"
        logger.debug(f"[Phase3] Injected user profile context ({len(user_profile_context)} chars)")

    # Inject emotional context
    if emotional_context:
        system_prompt = f"{system_prompt}\n\n{emotional_context}"

    # LORE DEEP-DIVE: Inject unlocked lore fragments into system prompt
    effective_user_id = user_id or f"session_{session_id[:16]}"
    unlocked_lore_context = _build_unlocked_lore_context(
        user_id=effective_user_id,
        persona_key=persona_key,
        seeker_progression_repo=seeker_progression_repo,
    )
    if unlocked_lore_context:
        system_prompt = f"{system_prompt}\n\n{unlocked_lore_context}"
        logger.debug(f"[LoreInjection] Injected unlocked lore context ({len(unlocked_lore_context)} chars)")

    # PHASE 2 (HERMES): on-demand hybrid lore retrieval (flag-gated; empty when off)
    ondemand_lore_context = _build_ondemand_lore_context(
        query=message,
        recent_messages=db_messages,
        persona_key=persona_key,
        episodic_memory_rag=episodic_memory_rag,
        settings=get_settings(),
    )
    if ondemand_lore_context:
        system_prompt = f"{system_prompt}\n\n{ondemand_lore_context}"
        logger.debug(f"[LoreInjection] Injected on-demand lore ({len(ondemand_lore_context)} chars)")

    # PHASE 2 (HERMES): seeker-rank narrative context (flag-gated; NEPHILIM personas)
    rank_ctx = ""
    if (get_settings().lore.rank_context_enabled and persona_key.startswith("nephilim_")
            and seeker_progression_repo):
        try:
            _profile = seeker_progression_repo.get_seeker_profile(effective_user_id)
            rank_ctx = _build_seeker_rank_context((_profile or {}).get("rank_name", "Initiate"))
            if rank_ctx:
                system_prompt = f"{system_prompt}\n\n{rank_ctx}"
        except Exception as e:
            logger.warning(f"[RankContext] skipped (non-fatal): {e}")

    # PHASE 2 (HERMES): internal capability context (NEPHILIM personas)
    cap_ctx = ""
    if persona_key.startswith("nephilim_") and seeker_progression_repo:
        try:
            from ..lore_retrieval import build_capability_context
            _prof = seeker_progression_repo.get_seeker_profile(effective_user_id) or {}
            _aff = seeker_progression_repo.get_or_create_affinity(effective_user_id, persona_key)
            cap_ctx = build_capability_context(
                persona_key, _prof.get("rank_name", "Initiate"),
                _aff.get("affinity_level", 0),
            )
            if cap_ctx:
                system_prompt = f"{system_prompt}\n\n{cap_ctx}"
        except Exception as e:
            logger.warning(f"[Capability] context skipped (non-fatal): {e}")

    system_tokens = estimate_tokens(system_prompt)

    # ADR-006 M0/M0.1: assemble the session-context blocks (highest priority first)
    # so they can be carried to chat() and actually reach the LLM. Historically all
    # six were appended to `system_prompt` above but only used for token budgeting
    # and then dropped (ChatBody carried no system prompt). Token-capped to protect
    # the context window; gated behind MEMORY_CONTEXT_INJECT (default OFF).
    #
    # M0.1 SELECTIVE INJECTION: only cross-session user-profile facts + emotional
    # state are injected. The NEPHILIM lore/rank/capability blocks are deliberately
    # EXCLUDED here: Gate 0 (2026-06-28) showed injecting that shared vocabulary into
    # every NEPHILIM persona homogenizes voice (distinctiveness 0.768→0.643; the
    # non-NEPHILIM gojo control, which gets none of it, was unaffected). Those blocks
    # need separate per-persona framing before they can be injected without
    # regression (future work). user-profile + emotional are persona-neutral
    # relationship state, not shared lore vocabulary.
    _mem_settings = get_settings().memory
    extra_system_context = None
    if _mem_settings.context_inject_enabled:
        extra_system_context = _assemble_capped_context(
            [
                user_profile_context,
                emotional_context,
            ],
            _mem_settings.context_max_tokens,
        )
        if extra_system_context:
            logger.info(
                f"[SessionContext] injecting {estimate_tokens(extra_system_context)} "
                f"tokens of session context into the LLM prompt (M0.1 selective)"
            )

    # Build summary context
    summary_context = ""
    if summaries:
        logger.info(f"[Memory] Found {len(summaries)} conversation summaries for session {session_id}")

        summary_parts = []
        for summary in summaries:
            summary_parts.append(f"[Summary of messages {summary['message_range']}]")
            summary_parts.append(summary['summary_text'])
            if summary.get('topics_discussed'):
                summary_parts.append(f"Topics: {summary['topics_discussed']}")

        summary_context = "\n\n".join(summary_parts)
        summary_tokens = estimate_tokens(summary_context)

        logger.info(
            f"[Memory] Summaries cover {len(summaries) * 30} messages "
            f"compressed to {summary_tokens} tokens"
        )
        system_tokens += summary_tokens

    # Use MemoryManager to select messages
    selected_messages = memory_manager.select_messages(
        messages=db_messages,
        token_budget=get_settings().ollama.context_window,
        system_prompt_tokens=system_tokens
    )

    # PHASE 3: Use RAG for semantic memory search
    rag_relevant_messages = []
    if episodic_memory_rag and db_messages:
        try:
            # Index session if not already indexed
            if session_id not in episodic_memory_rag.vectorstores:
                episodic_memory_rag.index_session(session_id, db_messages)

            # Get semantically relevant messages for current query
            rag_start = time.time()
            rag_relevant = episodic_memory_rag.get_relevant_context(
                session_id=session_id,
                query=message,
                max_messages=5  # Top 5 most relevant
            )
            rag_latency = (time.time() - rag_start) * 1000

            if rag_relevant:
                # Merge RAG results with selected messages (avoid duplicates)
                selected_indices = {msg.get("index", -1) for msg in selected_messages}
                for rag_msg in rag_relevant:
                    if rag_msg.get("index", -2) not in selected_indices:
                        rag_relevant_messages.append(rag_msg)

                logger.info(
                    f"[Phase3 RAG] Found {len(rag_relevant)} relevant memories "
                    f"({len(rag_relevant_messages)} unique) in {rag_latency:.0f}ms"
                )
        except Exception as e:
            logger.warning(f"[Phase3 RAG] Semantic search failed: {e}")

    # Combine selected messages with RAG-enhanced messages
    all_context_messages = selected_messages.copy()
    if rag_relevant_messages:
        all_context_messages.extend(rag_relevant_messages)
        # Sort by index to maintain chronological order
        all_context_messages.sort(key=lambda x: x.get("index", 0))

    # Convert to ChatTurn format
    raw_turns = [
        ChatTurn(role=msg["role"], content=msg["content"])
        for msg in all_context_messages
    ]

    # Assemble the final history, capping to MAX_HISTORY_TURNS (summary + most-recent
    # raw turns). select_messages bounds by TOKEN budget, which on a large context
    # window can exceed the ChatBody count guard — without this cap, long sessions
    # 500 at the ChatBody construction below.
    summary_turn = None
    if summary_context:
        summary_turn = ChatTurn(
            role="assistant",
            content=f"[Context from earlier in our conversation]\n\n{summary_context}"
        )
    history_turns = _assemble_capped_history(raw_turns, summary_turn)

    logger.info(
        f"[Memory] Selected {len(history_turns)}/{len(db_messages)} messages "
        f"(+{len(summaries)} summaries) for session {session_id} "
        f"(system: {system_tokens} tokens)"
    )

    # Perform chat
    chat_body = ChatBody(
        persona=persona_key,
        history=history_turns,
        message=message,
        session_id=session_id,
        extra_system_context=extra_system_context,
    )
    response = chat_function(chat_body)

    # Save messages
    now = utc_now_iso()

    user_msg_body = AppendMessageBody(role="user", content=message, ts=now, source_type="llm")
    add_message_function(session_id, user_msg_body)

    # Extract source_type from response metadata
    source_type = "llm"
    if "metadata" in response and response["metadata"]:
        source_type = response["metadata"].get("source_type", "llm")

    # Handle multi-message responses (Phase 2)
    # Store each message as a separate database entry with multi_message_id linking
    answer_for_db = response["answer"]
    if isinstance(answer_for_db, list) and len(answer_for_db) > 1:
        # Multi-message response - store each message separately
        multi_msg_id = str(uuid.uuid4())
        logger.debug(f"[Phase2] Storing {len(answer_for_db)} multi-messages separately with ID {multi_msg_id}")

        for idx, msg_content in enumerate(answer_for_db):
            assistant_msg_body = AppendMessageBody(
                role="assistant",
                content=msg_content,
                ts=now,
                source_type=source_type,
                latency_ms=response.get("latency") if idx == 0 else None,  # Only first message gets latency
                multi_message_id=multi_msg_id,
                multi_message_index=idx
            )
            add_message_function(session_id, assistant_msg_body)
    else:
        # Single message (or single-item list)
        content = answer_for_db[0] if isinstance(answer_for_db, list) else answer_for_db
        assistant_msg_body = AppendMessageBody(
            role="assistant",
            content=content,
            ts=now,
            source_type=source_type,
            latency_ms=response.get("latency")
        )
        add_message_function(session_id, assistant_msg_body)

    # For emotional state analysis, use all messages joined
    answer_for_emotional_state = "\\n\\n".join(answer_for_db) if isinstance(answer_for_db, list) else answer_for_db

    # Auto-summarization check
    _check_and_summarize(session_id, persona_key, deps)

    # Update emotional state
    try:
        # Use joined version for emotional state analysis
        updated_state = emotional_state_repo.update_from_interaction(
            session_id=session_id,
            user_message=message,
            assistant_response=answer_for_emotional_state
        )
        response["emotional_state"] = {
            "trust_level": updated_state.trust_level,
            "rapport": updated_state.rapport,
            "current_mood": updated_state.current_mood
        }
        logger.debug(f"[EmotionalState] Updated: trust={updated_state.trust_level:.2f}, mood={updated_state.current_mood}")
    except Exception as e:
        logger.warning(f"[EmotionalState] Failed to update emotional state: {e}")

    # PHASE 3: Update RAG index and extract/update user profile
    try:
        # Update RAG index with new messages
        if episodic_memory_rag:
            all_messages_updated = message_repo.get_messages_by_session(session_id)
            # Phase 3 trust-hierarchy: sanitize the user message before it enters
            # long-term memory so a stored tool-call payload cannot fire on a
            # later turn (gated by AGENTIC_INJECTION_GUARD, default ON).
            indexed_user_content = message
            if get_settings().agent.injection_guard:
                from .injection_guard import get_injection_guard
                indexed_user_content = get_injection_guard().sanitize_memory_write(message)
            episodic_memory_rag.update_session(
                session_id=session_id,
                new_messages=[
                    {"role": "user", "content": indexed_user_content},
                    {"role": "assistant", "content": response["answer"]}
                ],
                full_history=all_messages_updated
            )
            logger.debug(f"[Phase3 RAG] Updated vector index for session {session_id}")

        # Extract facts and update user profile (configurable interval to save compute)
        fact_interval = get_settings().memory.fact_extraction_interval
        if user_profile_repo and len(db_messages) % fact_interval == 0:
            try:
                # Get updated message list
                all_messages_updated = message_repo.get_messages_by_session(session_id)

                # Extract facts from recent messages (last 20)
                recent_messages = all_messages_updated[-20:]

                # Initialize fact extractor with LLM client if needed
                if fact_extractor is None:
                    llm_client = create_llm_client(
                        {}, temperature=get_settings().ollama.temp_fact_extraction
                    )
                    from ..fact_extractor import FactExtractor
                    fact_extractor = FactExtractor(llm_client)

                # Extract facts
                facts = fact_extractor.extract_facts(recent_messages, persona_key=persona_key)

                # Get or create user profile
                if not user_id and facts.get("user_name"):
                    # Try to find existing user by name
                    user_id = user_profile_repo.get_user_by_name(facts["user_name"])

                if not user_id:
                    # Create new user profile
                    user_id = f"user_{uuid.uuid4().hex[:8]}"
                    user_profile = user_profile_repo.create_profile(user_id)
                    user_profile_repo.link_session_to_user(user_id, session_id)
                    logger.info(f"[Phase3] Created new user profile: {user_id}")
                else:
                    user_profile = user_profile_repo.get_or_create_profile(user_id)

                # Update profile with extracted facts
                user_profile.update_from_session(facts)
                user_profile_repo.update_profile(user_profile)

                logger.info(
                    f"[Phase3] Updated user profile {user_id}: "
                    f"{fact_extractor.get_extraction_stats(facts)}"
                )

            except Exception as e:
                logger.warning(f"[Phase3] Fact extraction/profile update failed: {e}")

    except Exception as e:
        logger.error(f"[Phase3] Post-conversation updates failed: {e}")

    # NEPHILIM Progression System - Track conversation progress for NEPHILIM personas
    progression = _track_nephilim_progression(
        session_id=session_id,
        persona_key=persona_key,
        user_id=user_id,
        seeker_progression_repo=seeker_progression_repo
    ) or {}
    ceremony_data = progression.get("ceremony")
    capability_unlocks = progression.get("capability_unlocks") or []

    # Inject rank ceremony + capability unlocks into response metadata
    if ceremony_data or capability_unlocks:
        if "metadata" not in response or response["metadata"] is None:
            response["metadata"] = {}
        if ceremony_data:
            response["metadata"]["rank_ceremony"] = ceremony_data
        if capability_unlocks:
            response["metadata"]["capability_unlocks"] = capability_unlocks

    return response


def _track_nephilim_progression(
    session_id: str,
    persona_key: str,
    user_id: str | None,
    seeker_progression_repo
) -> dict | None:
    """
    Track NEPHILIM progression for conversations with NEPHILIM personas.

    Awards resonance points and tracks message counts for persona affinity.
    Checks and unlocks lore fragments when thresholds are met.

    Returns:
        dict with rank_ceremony data if a rank-up occurred, None otherwise.

    Args:
        session_id: Session identifier
        persona_key: Persona key (checked for nephilim_ prefix)
        user_id: User ID (if known from profile system)
        seeker_progression_repo: Repository for seeker progression
    """
    # Only track for NEPHILIM personas
    if not persona_key or not persona_key.startswith("nephilim_"):
        return None

    if not seeker_progression_repo:
        logger.debug("[NEPHILIM] Progression repo not available, skipping tracking")
        return None

    # Use session_id as user_id if no profile user exists
    effective_user_id = user_id or f"session_{session_id[:16]}"

    try:
        # Ensure seeker exists
        seeker_progression_repo.get_or_create_seeker(effective_user_id)

        # Increment message count for persona affinity
        seeker_progression_repo.increment_messages(
            user_id=effective_user_id,
            persona_key=persona_key,
            count=2  # User message + assistant response
        )

        # Phase-2 fix: deepen affinity_level (+1/exchange after the drive-by gate)
        # so affinity-gated lore can actually unlock. Returns milestone if crossed.
        affinity_result = seeker_progression_repo.increment_affinity(
            user_id=effective_user_id,
            persona_key=persona_key,
            amount=1,
        )

        # Award resonance for the conversation
        # Base resonance: 5 points per exchange
        result = seeker_progression_repo.award_resonance(
            user_id=effective_user_id,
            amount=5,
            reason="Conversation exchange",
            persona_key=persona_key,
            session_id=session_id
        )

        ceremony_data = None
        if result.get("rank_changed"):
            previous_rank = result.get("previous_rank", "Initiate")
            new_rank = result.get("new_rank", "Acolyte")
            logger.info(
                f"[NEPHILIM] Seeker {effective_user_id} ranked up! "
                f"{previous_rank} → {new_rank}"
            )

            # Look up rank ceremony template
            ceremony_key = f"{previous_rank}_to_{new_rank}"
            template = RANK_CEREMONIES.get(ceremony_key)
            if template:
                patron = PERSONA_DISPLAY_NAMES.get(persona_key, "the Nephilim")
                ceremony_data = {
                    "title": template["title"],
                    "speaker": template["speaker"],
                    "monologue": template["monologue"].format(patron=patron),
                    "previous_rank": previous_rank,
                    "new_rank": new_rank,
                }
                logger.info(
                    f"[NEPHILIM] Rank ceremony triggered: {ceremony_key} "
                    f"(patron={patron})"
                )
        else:
            logger.debug(
                f"[NEPHILIM] Awarded 5 resonance to {effective_user_id}, "
                f"total: {result.get('new_resonance')}"
            )

        # Check for lore unlocks
        card = get_persona_card(persona_key)
        if card:
            fragments = card.get("unlockable_lore", [])
            if fragments:
                newly_unlocked = seeker_progression_repo.check_and_unlock_lore(
                    effective_user_id, persona_key, fragments
                )
                if newly_unlocked:
                    for frag in newly_unlocked:
                        logger.info(
                            f"[NEPHILIM] Lore unlocked for {effective_user_id}: "
                            f"'{frag.get('fragment_title')}' ({frag.get('rarity')})"
                        )

        # Phase-2: detect newly-unlocked internal capabilities → diegetic unlock beat
        capability_unlocks = []
        try:
            if seeker_progression_repo:
                from ..lore_retrieval import detect_new_capability_unlocks
                _prof = seeker_progression_repo.get_seeker_profile(effective_user_id) or {}
                _aff = seeker_progression_repo.get_or_create_affinity(effective_user_id, persona_key)
                capability_unlocks = detect_new_capability_unlocks(
                    seeker_progression_repo, effective_user_id, persona_key,
                    _prof.get("rank_name", "Initiate"), _aff.get("affinity_level", 0),
                )
                for cap in capability_unlocks:
                    logger.info(f"[NEPHILIM] Capability awakened for {effective_user_id}: {cap['id']}")
        except Exception as e:
            logger.warning(f"[Capability] unlock detection failed (non-fatal): {e}")

        return {"ceremony": ceremony_data, "capability_unlocks": capability_unlocks}

    except Exception as e:
        logger.warning(f"[NEPHILIM] Progression tracking failed: {e}")
        return {"ceremony": None, "capability_unlocks": []}


def _check_and_summarize(session_id: str, persona_key: str, deps: dict):
    """
    Check if summarization is needed and trigger it if necessary.

    Summarization is triggered when the number of messages since the last summary
    reaches the configured interval (default: 30 messages).

    Args:
        session_id: Session identifier
        persona_key: Persona key for context
        deps: Dictionary of injected dependencies
    """
    cfg = get_settings()

    message_repo = deps["message_repo"]
    summary_repo = deps["summary_repo"]
    conversation_summarizer = deps["conversation_summarizer"]

    try:
        all_messages = message_repo.get_messages_by_session(session_id)
        message_count = len(all_messages)
        summary_count = summary_repo.count_summaries(session_id)
        interval = cfg.memory.summarization_interval
        messages_summarized = summary_count * interval
        messages_since_summary = message_count - messages_summarized

        if messages_since_summary >= interval:
            logger.info(
                f"[Summarizer] Triggering summarization for session {session_id} "
                f"({messages_since_summary} new messages, interval={interval})"
            )

            start_idx = messages_summarized
            end_idx = start_idx + interval
            messages_to_summarize = all_messages[start_idx:end_idx]

            # Set LLM client if not already set
            if not conversation_summarizer.llm_client:
                from ..llm_client import create_llm_client  # noqa: PLC0415
                conversation_summarizer.set_llm_client(
                    create_llm_client({}, temperature=cfg.ollama.temp_summarization)
                )

            card = get_persona_card(persona_key)
            persona_name = card.get("display_name", persona_key)

            summary_result = conversation_summarizer.summarize_segment(
                messages=messages_to_summarize,
                max_summary_tokens=200,
                persona_name=persona_name
            )

            message_range = f"{start_idx + 1}-{end_idx}"
            summary_repo.create_summary(
                session_id=session_id,
                message_range=message_range,
                summary_text=summary_result["summary_text"],
                emotional_developments=summary_result["emotional_developments"],
                topics_discussed=summary_result["topics_discussed"]
            )

            logger.info(
                f"[Summarizer] Created summary for messages {message_range} "
                f"({summary_result['token_count']} tokens)"
            )

    except Exception as e:
        logger.error(f"[Summarizer] Failed to create summary: {e}", exc_info=True)
