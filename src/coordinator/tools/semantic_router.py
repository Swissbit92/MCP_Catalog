# src/coordinator/tools/semantic_router.py
"""Semantic embedding fallback router for intent classification.

R4: Hybrid routing — keyword fast path → embedding similarity fallback → LLM slow path.

When keyword matching in intent_classifier.py produces no signal but the persona has
MCP access, this module embeds the user query against intent centroids computed from
canonical example phrases. Uses the configured RAG embedding model (bge-m3)
(same infrastructure as memory_rag.py — zero additional setup required).

Only activated when:
  1. Keyword classifier returns NEEDS_NEITHER
  2. Persona has at least one MCP capability (brave_search or solana_wallet)
  3. The embedding model is available (degrades gracefully if not)

Example queries caught by semantic routing but not keywords:
  - "thinking of moving some funds around" → NEEDS_WALLET
  - "what's the vibe in the market today" → NEEDS_WEB_SEARCH
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent centroid definitions — representative example phrases per intent.
# Keep these diverse (varied phrasing) for robust centroid computation.
# ---------------------------------------------------------------------------

_INTENT_EXAMPLES: Dict[str, List[str]] = {
    "wallet": [
        "what's in my wallet",
        "how much sol do I have",
        "thinking of moving some funds around",
        "I want to swap some tokens",
        "check my portfolio",
        "what's my balance looking like",
        "should I rebalance my holdings",
        "thinking about making a trade",
        "I might buy some more",
        "my investments right now",
    ],
    "web_search": [
        "what's the latest news",
        "what's happening with crypto today",
        "recent developments in the market",
        "breaking news on ethereum",
        "what are analysts saying about bitcoin",
        "vibe in the market today",
        "what's the current sentiment",
        "what did the fed say",
        "any updates on the regulation front",
        "what's everyone talking about in crypto",
    ],
    "llm_only": [
        "what is blockchain technology",
        "explain defi to me",
        "how does solana work",
        "tell me about yourself",
        "what do you think about",
        "help me understand",
        "can you explain",
        "who is satoshi nakamoto",
        "what's the difference between proof of work and proof of stake",
        "help me think through this",
    ],
}

# Confidence threshold: below this, fall back to NEEDS_NEITHER rather than guess
_CONFIDENCE_THRESHOLD = 0.75

# Module-level centroid cache (computed once per process)
_centroids: Optional[Dict[str, List[float]]] = None
_embeddings_model: Optional[object] = None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _mean_vector(vectors: List[List[float]]) -> List[float]:
    """Compute element-wise mean of a list of vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def _get_embeddings_model():
    """Lazily initialize the Ollama embeddings model."""
    global _embeddings_model
    if _embeddings_model is not None:
        return _embeddings_model
    try:
        from ..config import get_settings
        cfg = get_settings()
        model = cfg.memory.embedding_model
        base_url = cfg.ollama.base
        # Prefer langchain-ollama (newer, uses /api/embed + forwards num_ctx so
        # bge-m3 gets its full 8192 window); fall back to langchain-community.
        try:
            from langchain_ollama import OllamaEmbeddings
            _embeddings_model = OllamaEmbeddings(
                model=model, base_url=base_url, num_ctx=cfg.memory.embedding_max_tokens
            )
        except ImportError:
            from langchain_community.embeddings import OllamaEmbeddings  # type: ignore[assignment]
            _embeddings_model = OllamaEmbeddings(model=model, base_url=base_url)
        logger.info(f"[SemanticRouter] Embedding model initialized: {model}")
        return _embeddings_model
    except Exception as e:
        logger.debug(f"[SemanticRouter] Embedding model unavailable: {e}")
        return None


def _build_centroids(emb_model) -> Dict[str, List[float]]:
    """Build intent centroids by embedding example phrases and averaging."""
    centroids: Dict[str, List[float]] = {}
    for intent, phrases in _INTENT_EXAMPLES.items():
        try:
            vectors = emb_model.embed_documents(phrases)
            centroids[intent] = _mean_vector(vectors)
            logger.debug(f"[SemanticRouter] Centroid computed for intent '{intent}'")
        except Exception as e:
            logger.warning(f"[SemanticRouter] Failed to compute centroid for '{intent}': {e}")
    logger.info(f"[SemanticRouter] Intent centroids built for: {list(centroids.keys())}")
    return centroids


def _ensure_centroids(emb_model) -> Optional[Dict[str, List[float]]]:
    """Return cached centroids, building them on first call."""
    global _centroids
    if _centroids is not None:
        return _centroids
    try:
        _centroids = _build_centroids(emb_model)
        return _centroids
    except Exception as e:
        logger.warning(f"[SemanticRouter] Centroid build failed: {e}")
        return None


def route_by_embedding(
    query: str,
    can_use_brave: bool,
    can_use_mongodb: bool = False,
    can_use_wallet: bool = False,
) -> Optional[str]:
    """Attempt to classify query intent via embedding similarity.

    Args:
        query: User query string
        can_use_brave: Whether Brave search is available for this persona
        can_use_mongodb: Unused (MongoDB MCP removed). Kept for call-site compat.
        can_use_wallet: Whether wallet access is available for this persona

    Returns:
        Intent label ("wallet", "web_search", "llm_only") or None if
        confidence is below threshold or embeddings are unavailable.
    """
    emb_model = _get_embeddings_model()
    if emb_model is None:
        return None

    centroids = _ensure_centroids(emb_model)
    if not centroids:
        return None

    try:
        # Guard against embedder input overflow (Ollama HTTP 500) for very long
        # first messages. Centroid phrases are short by construction; only the
        # user query needs capping.
        from ..config import get_settings
        from ..memory_text_utils import truncate_for_embedding
        safe_query = truncate_for_embedding(query, get_settings().memory.embedding_max_tokens)
        query_vec = emb_model.embed_query(safe_query)
    except Exception as e:
        logger.debug(f"[SemanticRouter] Query embedding failed: {e}")
        return None

    # Filter to only intents this persona can actually use
    available: Dict[str, List[float]] = {}
    if can_use_wallet and "wallet" in centroids:
        available["wallet"] = centroids["wallet"]
    if can_use_brave and "web_search" in centroids:
        available["web_search"] = centroids["web_search"]
    # Always include llm_only as a fallback option
    if "llm_only" in centroids:
        available["llm_only"] = centroids["llm_only"]

    if not available:
        return None

    # Rank by cosine similarity
    scores: List[Tuple[float, str]] = []
    for intent, centroid in available.items():
        sim = _cosine_similarity(query_vec, centroid)
        scores.append((sim, intent))
    scores.sort(reverse=True)

    best_score, best_intent = scores[0]
    logger.debug(
        f"[SemanticRouter] Top matches: {[(f'{s:.3f}', i) for s, i in scores[:3]]}"
    )

    if best_score < _CONFIDENCE_THRESHOLD:
        logger.debug(
            f"[SemanticRouter] Below confidence threshold ({best_score:.3f} < {_CONFIDENCE_THRESHOLD}) — falling back to llm"
        )
        return None

    if best_intent == "llm_only":
        return None  # Treat as NEEDS_NEITHER — no MCP needed

    logger.info(
        f"[SemanticRouter] Semantic route: '{best_intent}' (confidence={best_score:.3f})"
    )
    return best_intent


def warm_centroids() -> bool:
    """Pre-compute and cache intent centroids at startup.

    Returns:
        True if centroids were successfully built, False otherwise.
    """
    emb_model = _get_embeddings_model()
    if emb_model is None:
        return False
    centroids = _ensure_centroids(emb_model)
    return bool(centroids)
