"""Contradiction-consistency probes (ADR-006 Phase 0 / M4, PICon-style).

Substring-first scoring (no NLI dependency — cosine is provably wrong for
contradiction; the NLI cross-encoder is the documented upgrade path). A healthy
companion never affirms a ``forbidden_patterns`` string; false-premise cases
(``expect_abstention``) should honestly abstain rather than confabulate.

- ``TestContradictionUnit`` — headless: metric + data-file integrity.
- ``TestContradictionLive`` — ``@pytest.mark.requires_ollama``: live driver.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_EVAL_DIR = Path(__file__).parent
_PERSONA_EVAL = _EVAL_DIR / "persona_eval"
if str(_PERSONA_EVAL) not in sys.path:
    sys.path.insert(0, str(_PERSONA_EVAL))

import persona_metrics as pm  # noqa: E402

DATA_FILE = _EVAL_DIR / "contradiction_test_data.json"


def _load_scenarios() -> list[dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["scenarios"]


class TestContradictionUnit:
    """Headless: metric correctness + data-file integrity."""

    def test_forbidden_hits_detects(self):
        assert pm.forbidden_hits("your name is David", ["your name is David"]) == ["your name is David"]

    def test_forbidden_hits_clean(self):
        assert pm.forbidden_hits("your name is Marcus", ["your name is David"]) == []

    def test_contradiction_rate(self):
        responses = ["your name is Marcus", "your name is David"]
        forbidden = [["your name is David"], ["your name is David"]]
        assert pm.contradiction_rate(responses, forbidden) == 0.5

    def test_is_abstention_true(self):
        assert pm.is_abstention("You haven't told me anything about Ethereum.")

    def test_is_abstention_false(self):
        assert not pm.is_abstention("You told me you own 10 ETH.")

    def test_data_file_integrity(self):
        scenarios = _load_scenarios()
        assert len(scenarios) >= 5
        for s in scenarios:
            assert s.get("type") == "contradiction_consistency", f"{s.get('scenario')} bad type"
            assert s.get("persona"), f"{s.get('scenario')} missing persona"
            assert isinstance(s.get("conversation"), list) and s["conversation"]
            assert s.get("adversarial_query"), f"{s.get('scenario')} missing adversarial_query"
            assert isinstance(s.get("forbidden_patterns"), list)


@pytest.mark.requires_ollama
class TestContradictionLive:
    """Live: plant fact, fire adversarial query, assert no contradiction."""

    BASE_URL = "http://localhost:8000"

    def test_contradiction_consistency_live(self):
        sys.path.insert(0, str(_EVAL_DIR.parent / "manual"))
        from api_client import create_session, chat  # type: ignore

        responses: list[str] = []
        forbidden: list[list[str]] = []
        for s in _load_scenarios():
            persona = s["persona"]
            sid = create_session(persona, base_url=self.BASE_URL)
            for turn in s["conversation"]:
                if turn["role"] == "user":
                    chat(sid, persona, turn["content"], base_url=self.BASE_URL)
            answer, _, _, _ = chat(sid, persona, s["adversarial_query"], base_url=self.BASE_URL)
            responses.append(answer)
            forbidden.append(s.get("forbidden_patterns", []))

            hits = pm.forbidden_hits(answer, s.get("forbidden_patterns", []))
            print(f"[contradiction] {s['scenario']}: forbidden_hits={hits}")
            if s.get("expect_abstention"):
                # false-premise: should abstain OR at least not confabulate a forbidden answer
                assert pm.is_abstention(answer) or not hits, \
                    f"{s['scenario']}: neither abstained nor avoided confabulation"

        rate = pm.contradiction_rate(responses, forbidden)
        print(f"[contradiction] contradiction_rate={rate}")
        assert rate == 0.0, f"contradiction_rate {rate} > 0 — see forbidden_hits above"
