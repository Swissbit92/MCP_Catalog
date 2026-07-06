# src/coordinator/services/search_relevance_service.py
"""
Search Relevance Service - Gate off-topic (junk) search results before synthesis.

Defense-in-depth for the "search the web for it" family of bugs: even a resolved
query can return non-empty-but-irrelevant results, and today non-empty results
bypass the "no results -> I don't know" guard, letting the LLM confabulate over
junk grounding.

When SEARCH_RELEVANCE_GATE_ENABLED is on, this service embeds the query and each
result (title + description) with the same bge-m3 embedder used for memory RAG,
and reports whether the best result's cosine similarity clears a configurable
floor. Below the floor, the caller abstains (honest "I don't know") instead of
synthesizing.

Fail-open by design: any embedder error returns "relevant" so the gate can never
make search worse than the legacy (no-gate) path — it only ever *adds* honest
abstentions on clearly off-topic result sets.
"""

from __future__ import annotations

import logging
import math
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class SearchRelevanceService:
    """Cosine-similarity relevance gate over Brave results (bge-m3)."""

    def __init__(self, embedder: Optional[Any] = None):
        """Args:
        embedder: object exposing embed_query(str)->List[float] and
            embed_documents(List[str])->List[List[float]] (LangChain
            OllamaEmbeddings-compatible). Lazily built from EpisodicMemoryRAG's
            bge-m3 embedder on first use when not provided.
        """
        self._embedder = embedder

    def _get_embedder(self) -> Any:
        if self._embedder is None:
            # Reuse the RAG bge-m3 embedder (no new model / no network until called).
            from ..memory_rag import EpisodicMemoryRAG

            self._embedder = EpisodicMemoryRAG().embeddings
        return self._embedder

    def max_similarity(self, query: str, results: List[Any]) -> Optional[float]:
        """Best cosine between the query and any result's title+description.

        Returns None if there are no results or embedding fails.
        """
        if not results:
            return None

        texts: List[str] = []
        for r in results:
            title = getattr(r, "title", "") or ""
            desc = getattr(r, "description", "") or ""
            combined = f"{title}. {desc}".strip()
            if combined and combined != ".":
                texts.append(combined)

        if not texts:
            return None

        embedder = self._get_embedder()
        q_vec = embedder.embed_query(query)
        d_vecs = embedder.embed_documents(texts)
        return max(self._cosine(q_vec, d) for d in d_vecs)

    def is_relevant(
        self, query: str, results: List[Any], min_cosine: float
    ) -> bool:
        """Whether the best result clears `min_cosine`.

        Fail-open: returns True on any embedding error (never blocks search on
        an embedder hiccup).
        """
        try:
            best = self.max_similarity(query, results)
            if best is None:
                # Nothing embeddable — let the normal empty-result path decide.
                return True
            relevant = best >= min_cosine
            logger.info(
                f"[RelevanceGate] query='{query[:50]}' best_cos={best:.3f} "
                f"floor={min_cosine:.2f} -> {'relevant' if relevant else 'OFF-TOPIC'}"
            )
            return relevant
        except Exception as e:  # noqa: BLE001 - gate must never break search
            logger.warning(
                f"[RelevanceGate] similarity check failed ({e}); failing open"
            )
            return True

    def filter_relevant(
        self, query: str, results: List[Any], min_cosine: float
    ) -> List[Any]:
        """Return only the results whose title+description clears `min_cosine`.

        Unlike `is_relevant` (a binary abstain used by the legacy force-search
        path), this filters PER RESULT — the right shape for image search, where
        a set typically mixes on-topic hits with a keyword-collision outlier
        (e.g. a museum artwork). The good hits survive; the outlier is dropped.

        Graceful + fail-open, so it can never make search worse than no gate:
          * empty input / empty query -> returned unchanged;
          * any embedding error -> original list returned (never blocks search);
          * if the floor would drop EVERY result, the ORIGINAL list is returned
            (a set that is uniformly low-similarity — e.g. sparse NSFW titles —
            is a false-negative risk, so we degrade to the deterministic-denylist
            output rather than abstain here).
        """
        if not results or not query:
            return results

        # Build the same title+description texts is_relevant/max_similarity use,
        # but keep them aligned 1:1 with results (results whose combined text is
        # empty are un-scorable -> kept, never dropped on missing metadata).
        indexed_texts: List[tuple[int, str]] = []
        for i, r in enumerate(results):
            title = getattr(r, "title", "") or ""
            desc = getattr(r, "description", "") or ""
            combined = f"{title}. {desc}".strip()
            if combined and combined != ".":
                indexed_texts.append((i, combined))

        if not indexed_texts:
            return results  # nothing embeddable -> don't filter

        try:
            embedder = self._get_embedder()
            q_vec = embedder.embed_query(query)
            d_vecs = embedder.embed_documents([t for _, t in indexed_texts])
        except Exception as e:  # noqa: BLE001 - gate must never break search
            logger.warning(
                f"[RelevanceGate] filter embedding failed ({e}); failing open"
            )
            return results

        drop: set[int] = set()
        for (idx, _text), d_vec in zip(indexed_texts, d_vecs):
            if self._cosine(q_vec, d_vec) < min_cosine:
                drop.add(idx)

        kept = [r for i, r in enumerate(results) if i not in drop]
        if not kept:
            # Uniform low-similarity set -> degrade rather than abstain here.
            logger.info(
                f"[RelevanceGate] filter would empty {len(results)} results "
                f"(floor={min_cosine:.2f}); keeping original set"
            )
            return results
        if drop:
            logger.info(
                f"[RelevanceGate] filtered {len(drop)}/{len(results)} off-topic "
                f"results (floor={min_cosine:.2f})"
            )
        return kept

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)
