# src/coordinator/services/query_resolution_service.py
"""
Query Resolution Service - Resolve deictic follow-up turns into standalone
web-search queries before hitting Brave.

Fixes the "search the web for it" bug: a follow-up turn like "search the web
for it" / "look it up" / "and Geneva?" was sent to Brave verbatim, losing the
topic established in prior turns. Brave then returned junk meta-results (e.g.
"how to search the web" help pages) which, being non-empty, bypassed the
"no results -> I don't know" guard and let the LLM confabulate.

Design (flag-gated `SEARCH_QUERY_RESOLUTION_ENABLED`, default OFF):
  - flag OFF  -> byte-identical to legacy: return the raw latest user message.
  - flag ON   -> if the latest turn looks self-contained, pass it through; if it
                 looks like a follow-up (deictic / very short / bare search
                 command) AND prior turns exist, ask the LLM to rewrite it into a
                 standalone query, then sanitize. ANY failure (empty, over-long,
                 exception) falls back to the raw latest message, so resolution
                 can never be worse than the legacy path.

The rewrite reuses the loaded persona LLM (no new model); it only fires on the
cheap heuristic trigger, so self-contained queries pay no extra round-trip.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from .llm_completion_service import LLMCompletionService
from .query_extraction_service import QueryExtractionService
from ..tools.keywords import EXPLICIT_SEARCH_COMMANDS

logger = logging.getLogger(__name__)

# Whole-word deictic / referential tokens whose presence means the turn likely
# depends on prior context ("search for it", "what about them", "is that true").
_DEICTIC_TOKENS = frozenset(
    {
        "it", "its", "it's", "this", "that", "these", "those",
        "them", "they", "their", "there", "he", "she", "him",
        "her", "his", "one", "ones",
    }
)

# A turn at or below this many words is treated as a follow-up candidate even
# without an explicit pronoun (e.g. "and Geneva?"). Biased to over-trigger: a
# false positive only costs one cheap rewrite that falls back to the original.
_SHORT_TURN_MAX_WORDS = 5

# Explicit search commands that carry no topic on their own may appear in a
# slightly longer turn ("could you search the web for it please"); allow the
# trigger up to this many words when such a command is present.
_COMMAND_TURN_MAX_WORDS = 9

# Sanitization guards on the rewritten query.
_MAX_QUERY_WORDS = 25
_MAX_QUERY_CHARS = 200

# Leading labels a small model tends to prepend despite instructions.
_LABEL_PREFIX_RE = re.compile(
    r"^\s*(rewritten|standalone(?:\s+question)?|query|search\s+query|answer)\s*[:\-]\s*",
    re.IGNORECASE,
)

_WORD_RE = re.compile(r"[a-z0-9']+")


class QueryResolutionService:
    """Resolve a (possibly deictic) latest user turn into a standalone search query.

    Stateless apart from the injected LLM/extractor dependencies.
    """

    def __init__(
        self,
        llm_service: LLMCompletionService,
        query_extractor: Optional[QueryExtractionService] = None,
    ):
        self.llm_service = llm_service
        self.query_extractor = query_extractor or QueryExtractionService()

    # ------------------------------------------------------------------ public

    def resolve(self, user_prompt: str) -> str:
        """Return the query to send to Brave for this compiled conversation.

        Never raises: on any failure it degrades to the raw latest user message
        (legacy behavior).
        """
        latest = self.query_extractor.extract_latest_user_message(user_prompt)

        # Flag read at call-time so an env flip / cache_clear takes effect without
        # re-instantiating the service. Lazy import avoids a config import cycle.
        from ..config import get_settings

        if not get_settings().search.query_resolution_enabled:
            return latest

        try:
            if not self._has_prior_user_turn(user_prompt, latest):
                # First turn / no context to resolve against.
                return latest
            if not self._looks_like_followup(latest):
                return latest

            rewritten = self._llm_rewrite(user_prompt, latest)
            resolved = self._sanitize(rewritten, fallback=latest)
            if resolved != latest:
                logger.info(
                    f"[QueryResolution] Resolved follow-up '{latest[:60]}' -> "
                    f"'{resolved[:60]}'"
                )
            return resolved
        except Exception as e:  # noqa: BLE001 - resolution must never break search
            logger.warning(
                f"[QueryResolution] Resolution failed ({e}); using latest turn verbatim"
            )
            return latest

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _has_prior_user_turn(user_prompt: str, latest: str) -> bool:
        """True if the compiled conversation contains a user turn before `latest`."""
        user_turns = [
            line.strip()[6:].strip()
            for line in user_prompt.split("\n")
            if line.strip().startswith("User: ")
        ]
        # More than one user turn, or a single user turn that isn't the latest,
        # means there's prior context worth resolving against.
        return len(user_turns) >= 2 or (
            len(user_turns) == 1 and user_turns[0] != latest
        )

    @staticmethod
    def _looks_like_followup(latest: str) -> bool:
        """Cheap heuristic: does this turn likely depend on prior context?"""
        text = latest.lower()
        words = _WORD_RE.findall(text)
        n = len(words)
        if n == 0:
            return False

        if n <= _SHORT_TURN_MAX_WORDS:
            return True

        word_set = set(words)
        if word_set & _DEICTIC_TOKENS:
            return True

        if n <= _COMMAND_TURN_MAX_WORDS and any(
            cmd in text for cmd in EXPLICIT_SEARCH_COMMANDS
        ):
            return True

        return False

    def _llm_rewrite(self, user_prompt: str, latest: str) -> str:
        """Ask the LLM to rewrite `latest` into a standalone query using context."""
        context = self._recent_context(user_prompt, latest)
        system = (
            "You rewrite a user's latest message into a short, self-contained "
            "(standalone) web search query. Use the conversation ONLY to resolve "
            'references like "it", "that", "there", or "them" to the topic they '
            "point at.\n"
            "Rules:\n"
            "- Output ONLY the rewritten search query. No preamble, no quotes, no "
            "explanation.\n"
            "- Keep it short: 3 to 12 words.\n"
            "- Do NOT answer the question. Do NOT invent facts not present in the "
            "conversation.\n"
            "- If the latest message is already a complete standalone query, "
            "return it unchanged.\n\n"
            "Example:\n"
            "Conversation:\n"
            "User: tell me about the James Webb telescope's new exoplanet finding\n"
            "Assistant: I do not follow current events.\n"
            "Latest: search the web for it\n"
            "Rewritten: James Webb telescope new exoplanet finding"
        )
        user = (
            f"Conversation:\n{context}\n"
            f"Latest: {latest}\n"
            "Rewritten:"
        )
        return self.llm_service.complete(system, user)

    @staticmethod
    def _recent_context(user_prompt: str, latest: str, max_turns: int = 6) -> str:
        """Trailing conversation turns (excluding the latest), for rewrite context."""
        turn_lines = [
            line.strip()
            for line in user_prompt.split("\n")
            if line.strip().startswith(("User: ", "Assistant: "))
        ]
        # Drop the final "User: <latest>" line so it isn't duplicated below.
        if turn_lines and turn_lines[-1] == f"User: {latest}":
            turn_lines = turn_lines[:-1]
        return "\n".join(turn_lines[-max_turns:])

    @staticmethod
    def _sanitize(raw: str, *, fallback: str) -> str:
        """Clean an LLM rewrite; fall back to the original on anything suspect."""
        if not raw or not raw.strip():
            return fallback

        candidate = raw.strip()

        # Small models sometimes wrap the query in JSON: {"query": "..."}.
        if candidate.startswith("{"):
            try:
                data = json.loads(candidate)
                if isinstance(data, dict) and data.get("query"):
                    candidate = str(data["query"])
            except (json.JSONDecodeError, ValueError):
                pass

        # First non-empty line only.
        candidate = next(
            (ln.strip() for ln in candidate.splitlines() if ln.strip()), ""
        )
        # Strip a leading label ("Rewritten:", "Standalone question:", ...).
        candidate = _LABEL_PREFIX_RE.sub("", candidate).strip()
        # Strip surrounding quotes / backticks.
        candidate = candidate.strip("\"'`").strip()

        if not candidate:
            return fallback
        if len(candidate) > _MAX_QUERY_CHARS:
            return fallback
        if len(_WORD_RE.findall(candidate.lower())) > _MAX_QUERY_WORDS:
            return fallback

        return candidate
