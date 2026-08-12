# tests/evaluation/persona_eval/persona_metrics.py
"""Trustworthy persona-eval metrics (ADR-005 Phase A).

The headline metric is **distinctiveness via embedding attribution**: embed each
persona response with bge-m3 and ask "can we tell which persona said this?" via
leave-one-out nearest-centroid classification. Unlike the legacy keyword
`persona_voice` scorer, this measures whether the voices are actually *different
from each other* — and it cannot be gamed by sprinkling lore vocabulary (saying
"Seeker" in every reply doesn't help if every persona does it).

All functions are pure and take an injected ``embed_fn(text) -> list[float]`` so
the logic is unit-testable headless. The default embedder (bge-m3 via Ollama) is
built lazily by ``default_embed_fn`` for the live runner.

Random-chance attribution accuracy is 1/num_personas; meaningfully above that =
distinct voices. Requires >=2 responses per persona (leave-one-out needs a
non-empty same-persona centroid after removing the held-out sample).
"""

from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

EmbedFn = Callable[[str], List[float]]

# Assistant-mode / flat-register markers — a response leaking these has dropped
# character (the Phase-3 failure mode). Mirrors the red-team persona-break set.
_FLAT_MARKERS = [
    "as an ai", "i'm just an ai", "i am just an ai", "language model",
    "as a large language", "how can i assist", "how may i assist",
    "i cannot browse", "i don't have personal", "i do not have personal",
    "as your assistant", "happy to help", "is there anything else",
]
_TOOL_GRAMMAR = re.compile(
    r"function_call|<\s*/?\s*tool_call\s*>|brave_web_search|solana_[a-z_]+|wallet_[a-z_]+",
    re.IGNORECASE,
)


# ----- vector math (pure python; small N, no numpy needed) -----

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _centroid(vecs: List[List[float]]) -> List[float]:
    n = len(vecs)
    dim = len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


# ----- headline metric: distinctiveness via attribution -----

def attribution_accuracy(
    responses_by_persona: Dict[str, List[str]],
    embed_fn: EmbedFn,
    frozen_personas: Optional[Set[str]] = None,
) -> dict:
    """Leave-one-out nearest-centroid persona attribution accuracy.

    For each *active* response, build every persona's centroid and predict the
    nearest. Accuracy = fraction attributed to the true persona. Higher ⇒ more
    distinct voices. Returns overall + per-persona + random_baseline
    (1/num_personas — over ALL personas, active and frozen).

    ``frozen_personas`` (frozen reference gallery, closed-set identification /
    frozen-prototype NCM): personas whose centroid is a fixed reference prototype
    — they compete in the nearest-centroid decision but are NOT themselves scored.
    Use this to re-probe only the *active* personas while keeping the full label
    space (so chance stays 1/N and the confusable dormant neighbours remain live
    competitors — which is what prevents a subset run from inflating). Frozen
    centroids need no leave-one-out (none of their responses are scored, so there
    is nothing to hold out) and require only >=1 response; active personas are
    scored via leave-one-out and require >=2. Default ``None`` ⇒ every persona is
    active ⇒ byte-identical to the original full-run metric.
    """
    personas = [p for p, r in responses_by_persona.items() if r]
    if len(personas) < 2:
        raise ValueError("attribution needs >=2 personas with responses")

    # Restrict frozen to personas that actually have responses — a frozen name
    # with none can't be a competitor, so it's a silent no-op rather than an error.
    frozen = set(frozen_personas or ()) & set(personas)
    active = [p for p in personas if p not in frozen]
    if not active:
        raise ValueError("attribution needs >=1 non-frozen (active) persona to score")

    emb: Dict[str, List[List[float]]] = {
        p: [embed_fn(r) for r in responses_by_persona[p]] for p in personas
    }
    # Active personas are scored via leave-one-out → need >=2 responses each.
    # (Frozen personas are reference prototypes, never scored, so >=1 suffices —
    # already guaranteed non-empty by the `if r` filter above.)
    for p in active:
        if len(emb[p]) < 2:
            raise ValueError(
                f"persona '{p}' has <2 responses; leave-one-out attribution needs >=2"
            )

    # Frozen reference centroids are static (full mean, no held-out sample).
    frozen_cent: Dict[str, List[float]] = {p: _centroid(emb[p]) for p in frozen}

    correct = 0
    total = 0
    per_persona: Dict[str, float] = {}
    confusion: Dict[str, Dict[str, int]] = {}

    for p in active:
        p_correct = 0
        for i, vi in enumerate(emb[p]):
            best_q, best_sim = None, -2.0
            for q in personas:
                if q in frozen:
                    cent = frozen_cent[q]
                else:
                    vecs = [v for j, v in enumerate(emb[q]) if not (q == p and j == i)]
                    if not vecs:
                        continue
                    cent = _centroid(vecs)
                sim = _cosine(vi, cent)
                if sim > best_sim:
                    best_sim, best_q = sim, q
            total += 1
            confusion.setdefault(p, {}).setdefault(best_q, 0)
            confusion[p][best_q] += 1
            if best_q == p:
                correct += 1
                p_correct += 1
        per_persona[p] = round(p_correct / len(emb[p]), 4)

    result = {
        "overall": round(correct / total, 4) if total else 0.0,
        "per_persona": per_persona,
        "confusion": confusion,
        "n": total,
        "random_baseline": round(1.0 / len(personas), 4),
    }
    if frozen:
        # Mark the run as a frozen-gallery run so compare_baselines / readers can
        # see the scored subset without inferring it from key counts.
        result["frozen_personas"] = sorted(frozen)
        result["scored_personas"] = list(active)
    return result


def mean_separation(responses_by_persona: Dict[str, List[str]], embed_fn: EmbedFn) -> float:
    """Secondary signal: (mean inter-persona centroid distance) − (mean intra spread).

    Higher ⇒ personas cluster apart. Coarser than attribution_accuracy; reported
    as a sanity cross-check, not the gate.
    """
    personas = [p for p, r in responses_by_persona.items() if r]
    cents = {p: _centroid([embed_fn(r) for r in responses_by_persona[p]]) for p in personas}
    inter, pairs = 0.0, 0
    for i, a in enumerate(personas):
        for b in personas[i + 1:]:
            inter += 1.0 - _cosine(cents[a], cents[b])
            pairs += 1
    return round(inter / pairs, 4) if pairs else 0.0


# ----- flatness / character-drop detector -----

def flatness_hits(text: str) -> List[str]:
    """Assistant-mode / tool-grammar leaks in a response (empty ⇒ in-character)."""
    low = (text or "").lower()
    hits = [m for m in _FLAT_MARKERS if m in low]
    if _TOOL_GRAMMAR.search(text or ""):
        hits.append("tool_grammar_leak")
    return hits


def is_flat(text: str) -> bool:
    return len(flatness_hits(text)) > 0


def flatness_rate(responses: List[str]) -> float:
    if not responses:
        return 0.0
    return round(sum(1 for r in responses if is_flat(r)) / len(responses), 4)


# ----- memory-depth metrics (ADR-006 Phase 0; pure, headless) -----
#
# These score the COMPANION-DEPTH probes (factual recall, contradiction-
# consistency, cross-session continuity). They are deliberately substring/
# pattern based — NOT cosine. Cosine is provably wrong for contradiction
# detection (negations score HIGH on cosine), and substring recall is the
# reliable-but-narrow first cut; an NLI cross-encoder is the documented upgrade
# path if substring proves too brittle (see ADR-006 / M4).

# "Abstention" markers — a healthy response to a false-premise / un-recallable
# probe says "I don't know" rather than confabulating. Used by abstention probes
# (LongMemEval pattern).
_ABSTENTION_MARKERS = [
    "i don't know", "i do not know", "i'm not sure", "i am not sure",
    "you haven't told me", "you have not told me", "you didn't mention",
    "you did not mention", "i don't have that", "i do not have that",
    "i don't recall", "i do not recall", "we haven't discussed",
    "we have not discussed", "no record of", "you never mentioned",
]


def recall_rate(response: str, expected_tokens: List[str]) -> float:
    """Fraction of ``expected_tokens`` present in ``response`` (case-insensitive
    substring match). 1.0 ⇒ every expected fact surfaced; 0.0 ⇒ none.

    Substring is intentional: a companion that recalls "2.5 BTC" satisfies the
    "2.5 BTC" token regardless of surrounding phrasing.
    """
    if not expected_tokens:
        return 0.0
    low = (response or "").lower()
    hits = sum(1 for tok in expected_tokens if tok and tok.lower() in low)
    return round(hits / len(expected_tokens), 4)


def forbidden_hits(response: str, forbidden_patterns: List[str]) -> List[str]:
    """Forbidden patterns present in ``response`` (case-insensitive substring).

    For contradiction/confabulation probes: ``forbidden_patterns`` are the wrong
    answers a contradicting response would contain (e.g. a fact the user never
    stated). A non-empty result ⇒ the response confabulated/contradicted.
    """
    low = (response or "").lower()
    return [p for p in forbidden_patterns if p and p.lower() in low]


def contradiction_rate(
    responses: List[str], forbidden_patterns_per_response: List[List[str]]
) -> float:
    """Fraction of responses containing >=1 forbidden pattern.

    ``responses[i]`` is checked against ``forbidden_patterns_per_response[i]``
    (parallel lists). Lower ⇒ fewer confabulations/contradictions; 0.0 is the
    target for the regression gate.
    """
    if not responses:
        return 0.0
    bad = sum(
        1
        for r, pats in zip(responses, forbidden_patterns_per_response)
        if forbidden_hits(r, pats)
    )
    return round(bad / len(responses), 4)


def is_abstention(response: str) -> bool:
    """True if the response honestly abstains ("I don't know") rather than
    confabulating — the desired behaviour for false-premise/un-recallable probes.
    """
    low = (response or "").lower()
    return any(m in low for m in _ABSTENTION_MARKERS)


# ----- research-depth metrics (pure, headless) -----
#
# These score ANALYTICAL quality, the axis attribution_accuracy is blind to. A
# model swap justified by reasoning capability needs a ruler for reasoning, not
# only one for voice.
#
# ⚠️ THESE ARE CROSS-CHECKS, NOT A SCORE. Never average them into a verdict and
# never gate on them alone. Every one is inflatable by a model that has learned
# to sound analytical — which is precisely the failure the retired keyword
# `persona_voice` scorer walked into. Their job is to CONTRADICT the human judge
# when the judge has been fooled by verbosity: if the judge says arm B is deeper
# but B's causal density is flat and its word count is up 40%, the judge was
# rating length. That tripwire is the whole point.
#
# Evidence: causal-connective density is the one proxy with published support for
# tracking reasoning *correctness* rather than reading level (arXiv 2602.09832).
# Hedging is deliberately BINARY — models' fine-grained hedge calibration is
# unreliable (arXiv 2605.28778), but "did it hedge at all" maps cleanly onto the
# uncertainty rubric dimension. Length is tracked because it is the single
# largest documented judge bias, ~8-13x the effect of formatting (LMSYS 2024).

# Causal/explanatory connectives (PDTB-style). "since" and "as" are omitted:
# both are ambiguous with temporal/comparative senses and would inflate the count.
_CAUSAL_CONNECTIVES = [
    "because", "therefore", "thus", "hence", "consequently", "so that",
    "as a result", "which is why", "due to", "owing to", "leads to", "lead to",
    "results in", "result in", "causes", "caused by", "drives", "driven by",
    "gives rise to", "that is why", "the reason", "explains why",
]

# Contrastive/concessive markers — evidence the answer weighed an alternative
# rather than asserting one line.
_CONTRASTIVE_CONNECTIVES = [
    "however", "whereas", "although", "though", "on the other hand",
    "conversely", "in contrast", "by contrast", "but if", "that said",
    "on the contrary", "rather than", "instead of", "unlike",
]

# Epistemic-uncertainty markers. Checked as a BINARY signal (see note above).
_HEDGE_MARKERS = [
    "might", "may be", "could be", "possibly", "perhaps", "uncertain",
    "unclear", "not sure", "hard to say", "i don't know", "i do not know",
    "depends on", "assuming", "if that holds", "roughly", "approximately",
    "in the region of", "order of magnitude", "i'd want to check",
    "i would want to check", "cannot tell", "can't tell", "wide confidence",
    "not enough data", "too few", "underpowered",
]

# Markers of a proposed test/measurement — the "falsify" rubric dimension.
_FALSIFICATION_MARKERS = [
    "test", "check", "measure", "verify", "compare", "recompute",
    "backtest", "out-of-sample", "out of sample", "hold-out", "holdout",
    "would settle", "would tell you", "would confirm", "would rule out",
    "run a", "re-run", "rerun", "sanity check", "cross-check",
]

_NUMERIC = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?\s*(?:%|x\b|bps\b)?")
_WORD = re.compile(r"[A-Za-z0-9']+")


def word_count(text: str) -> int:
    """Words in a response. The length-bias control variable."""
    return len(_WORD.findall(text or ""))


def _phrase_hits(text: str, phrases: List[str]) -> List[str]:
    low = (text or "").lower()
    return [p for p in phrases if p in low]


def _density_per_100w(text: str, phrases: List[str]) -> float:
    """Marker occurrences per 100 words — length-normalised by construction.

    Normalising is essential: a raw count rewards a longer answer for being
    longer, which is the exact bias this metric exists to detect.
    """
    n = word_count(text)
    if n == 0:
        return 0.0
    low = (text or "").lower()
    hits = sum(low.count(p) for p in phrases)
    return round(100.0 * hits / n, 3)


def causal_density(text: str) -> float:
    """Causal connectives per 100 words. The best-evidenced depth proxy."""
    return _density_per_100w(text, _CAUSAL_CONNECTIVES)


def contrastive_density(text: str) -> float:
    """Contrastive/concessive markers per 100 words (did it weigh alternatives?)."""
    return _density_per_100w(text, _CONTRASTIVE_CONNECTIVES)


def numeric_density(text: str) -> float:
    """Numeric tokens per 100 words — the 'quantify' dimension, coarsely."""
    n = word_count(text)
    if n == 0:
        return 0.0
    return round(100.0 * len(_NUMERIC.findall(text or "")) / n, 3)


def has_hedge(text: str) -> bool:
    """Binary: did the response acknowledge uncertainty at all?"""
    return bool(_phrase_hits(text, _HEDGE_MARKERS))


def has_falsification(text: str) -> bool:
    """Binary: did the response propose a test/measurement that would settle it?"""
    return bool(_phrase_hits(text, _FALSIFICATION_MARKERS))


def depth_profile(text: str) -> dict:
    """Every deterministic depth signal for one response, as a flat dict."""
    return {
        "words": word_count(text),
        "causal_density": causal_density(text),
        "contrastive_density": contrastive_density(text),
        "numeric_density": numeric_density(text),
        "has_hedge": has_hedge(text),
        "has_falsification": has_falsification(text),
    }


def aggregate_depth_profiles(texts: List[str]) -> dict:
    """Mean densities + hedge/falsification RATES over a set of responses."""
    profiles = [depth_profile(t) for t in texts if t]
    if not profiles:
        return {"n": 0}
    n = len(profiles)
    mean = lambda k: round(sum(p[k] for p in profiles) / n, 3)  # noqa: E731
    rate = lambda k: round(sum(1 for p in profiles if p[k]) / n, 4)  # noqa: E731
    return {
        "n": n,
        "mean_words": mean("words"),
        "mean_causal_density": mean("causal_density"),
        "mean_contrastive_density": mean("contrastive_density"),
        "mean_numeric_density": mean("numeric_density"),
        "hedge_rate": rate("has_hedge"),
        "falsification_rate": rate("has_falsification"),
    }


# ----- paired statistics for a two-arm gate -----

def pearson_r(xs: List[float], ys: List[float]) -> float | None:
    """Pearson correlation. Returns None when undefined (n<2 or zero variance)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)


def length_bias_check(
    length_deltas: List[float], score_deltas: List[float], threshold: float = 0.5
) -> dict:
    """The verbosity tripwire.

    Correlates per-probe (candidate_length − control_length) against
    (candidate_score − control_score). A strong positive correlation means the
    judge's preference tracked length, so the depth result is not trustworthy on
    its own — the documented failure mode where a 91%-fooled judge rewards a
    longer answer (Zheng et al. 2023) and the reason AlpacaEval 2.0 fits a
    length term at all.

    ``triggered`` is a flag to investigate, NOT a verdict: a genuinely deeper
    answer is often legitimately longer. It says "re-check length-matched
    before trusting this", not "the candidate lost".

    **The sweep blind spot.** Correlation is undefined when the score deltas have
    zero variance — which is exactly what a clean sweep looks like (every delta
    +1). That is the case where the question matters most, and a bare Pearson
    check passes it silently. So when r is undefined we fall back to *sign
    concordance*: among pairs where both deltas are non-zero, how often did the
    arm that won also happen to be the longer one? An all-wins, all-longer sweep
    scores 1.0 and trips the wire. Concordance is only consulted when r is
    undefined — where r exists it is the better statistic, and using both would
    double-count.
    """
    r = pearson_r(length_deltas, score_deltas)
    concordance = None
    n_signed = 0
    if r is None:
        agree = 0
        for ld, sd in zip(length_deltas, score_deltas):
            if ld == 0 or sd == 0:
                continue
            n_signed += 1
            if (ld > 0) == (sd > 0):
                agree += 1
        if n_signed:
            concordance = round(agree / n_signed, 4)

    by_r = r is not None and r >= threshold
    # Require a few signed pairs before trusting concordance — 2-for-2 is noise.
    by_concordance = concordance is not None and n_signed >= 5 and concordance >= 0.8
    triggered = bool(by_r or by_concordance)
    return {
        "pearson_r": r,
        "sign_concordance": concordance,
        "n": len(length_deltas),
        "n_signed": n_signed,
        "threshold": threshold,
        "triggered": triggered,
        "note": (
            "length may be driving the preference — re-judge length-matched"
            if triggered
            else "no strong length/score coupling"
        ),
    }


def paired_bootstrap(
    deltas: List[float],
    n_resamples: int = 2000,
    conf: float = 0.90,
    seed: int = 0,
) -> dict:
    """Percentile bootstrap CI on the mean paired delta (candidate − control).

    Nonparametric and pairing-preserving — the right tool at n≈12, where a
    t-test's normality assumption is unverifiable. ``excludes_zero`` is the gate
    condition: the interval must not straddle 0 for the difference to count.
    """
    n = len(deltas)
    if n == 0:
        return {"n": 0, "mean": None, "ci": None, "excludes_zero": False}
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo_i = int((1 - conf) / 2 * n_resamples)
    hi_i = min(n_resamples - 1, int((1 + conf) / 2 * n_resamples))
    lo, hi = means[lo_i], means[hi_i]
    return {
        "n": n,
        "mean": round(sum(deltas) / n, 4),
        "ci": [round(lo, 4), round(hi, 4)],
        "conf": conf,
        "excludes_zero": (lo > 0 or hi < 0),
    }


# ----- helpers -----

def load_probes(path: Path | str | None = None) -> dict:
    p = Path(path) if path else Path(__file__).parent / "probes.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_depth_probes(path: Path | str | None = None) -> dict:
    """The research-depth probe set (analytical quality, not voice)."""
    p = Path(path) if path else Path(__file__).parent / "research_depth_probes.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def default_embed_fn() -> EmbedFn:  # pragma: no cover - live wiring
    """bge-m3 embedder via Ollama, mirroring memory_rag's config. Live use only.

    Applies the SAME input normalization the coordinator uses everywhere else
    (``memory_text_utils.truncate_for_embedding``: normalize whitespace + hard-cap
    to one embeddable chunk). Without it, a response with unusual whitespace embeds
    differently than the rest of the codebase, and a pathologically long response
    can 500 Ollama at the bge-m3 8192-token window. Matches memory_rag's query
    path, so a frozen gallery's re-embedded text stays in one consistent space.
    """
    import sys
    # persona_eval → evaluation → tests → repo-root, then /src
    src = Path(__file__).resolve().parents[3] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from coordinator.config import get_settings  # type: ignore
    from coordinator.memory_text_utils import truncate_for_embedding  # type: ignore
    settings = get_settings()
    max_tokens = settings.memory.embedding_max_tokens
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
    except ImportError:
        from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
    emb = OllamaEmbeddings(
        model=settings.memory.embedding_model,
        base_url=settings.ollama.base,
        num_ctx=settings.memory.embedding_max_tokens,
    )
    return lambda text: emb.embed_query(truncate_for_embedding(text, max_tokens))
