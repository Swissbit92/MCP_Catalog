"""Factual-recall probes (ADR-006 Phase 0 / M4).

Two layers:
- ``TestFactualRecallUnit`` — headless. Validates the recall_rate metric and the
  integrity of ``memory_test_data.json`` (schema + the new ``type`` discriminator).
  Runs in the normal suite, no Ollama.
- ``TestFactualRecallLive`` — ``@pytest.mark.requires_ollama``. Replays each
  scenario's user turns against a live backend, sends the probe query, and scores
  recall_rate. Auto-skips headless. Provides the pre/post-M0 baseline numbers.
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

DATA_FILE = _EVAL_DIR / "memory_test_data.json"


def _load_scenarios() -> list[dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class TestFactualRecallUnit:
    """Headless: metric correctness + data-file integrity."""

    def test_recall_rate_all_present(self):
        assert pm.recall_rate("I hold 2.5 BTC bought in 2021", ["2.5 BTC", "2021"]) == 1.0

    def test_recall_rate_none_present(self):
        assert pm.recall_rate("I don't recall anything specific", ["2.5 BTC", "2021"]) == 0.0

    def test_recall_rate_partial(self):
        assert pm.recall_rate("You mentioned 2.5 BTC", ["2.5 BTC", "2021"]) == 0.5

    def test_recall_rate_case_insensitive(self):
        assert pm.recall_rate("you bought ledger nano x", ["Ledger Nano X"]) == 1.0

    def test_recall_rate_empty_expected_is_zero(self):
        assert pm.recall_rate("anything", []) == 0.0

    def test_data_file_loads_and_nonempty(self):
        scenarios = _load_scenarios()
        assert len(scenarios) >= 5

    def test_every_scenario_has_required_fields(self):
        for s in _load_scenarios():
            assert s.get("type") == "factual_recall", f"{s.get('scenario')} missing type discriminator"
            assert s.get("query"), f"{s.get('scenario')} missing query"
            assert isinstance(s.get("expected_recall"), list) and s["expected_recall"], \
                f"{s.get('scenario')} missing expected_recall"
            assert isinstance(s.get("conversation"), list) and s["conversation"], \
                f"{s.get('scenario')} missing conversation"


@pytest.mark.requires_ollama
class TestFactualRecallLive:
    """Live: replay conversation, probe, score recall against the running backend.

    Baseline-capture test. The threshold is a low floor (memory-via-history works
    even pre-M0); M4-gate compares the measured rate against the frozen baseline.
    """

    BASE_URL = "http://localhost:8000"
    RECALL_FLOOR = 0.4

    def test_factual_recall_live(self):
        sys.path.insert(0, str(_EVAL_DIR.parent / "manual"))
        from api_client import create_session, chat  # type: ignore

        persona = "nephilim_eeva"
        scores = []
        for s in _load_scenarios():
            sid = create_session(persona, base_url=self.BASE_URL)
            for turn in s["conversation"]:
                if turn["role"] == "user":
                    chat(sid, persona, turn["content"], base_url=self.BASE_URL)
            answer, _, _, _ = chat(sid, persona, s["query"], base_url=self.BASE_URL)
            rate = pm.recall_rate(answer, s["expected_recall"])
            scores.append(rate)
            print(f"[factual_recall] {s['scenario']}: recall={rate}")

        mean_recall = round(sum(scores) / len(scores), 4)
        print(f"[factual_recall] MEAN recall_rate={mean_recall}")
        assert mean_recall >= self.RECALL_FLOOR, \
            f"mean recall {mean_recall} below floor {self.RECALL_FLOOR}"
