"""Cross-session continuity probes (ADR-006 Phase 0 / M4).

Plant facts in session A, then in a FRESH session B (same persona) probe recall.
This exercises the conversation_summaries + memory bridge that ADR-006 Phase 1
will deepen.

- ``TestCrossSessionUnit`` — headless: data-file integrity.
- ``TestCrossSessionLive`` — ``@pytest.mark.requires_ollama`` AND
  ``@pytest.mark.xfail``: cross-session recall requires both sessions to resolve
  to the same user_id (user_profile linkage), which is not wired headlessly yet.
  Marked xfail(strict=False) so it reports the real number without failing the
  gate; Phase 1 resolves the linkage and flips this to a hard assertion.
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

DATA_FILE = _EVAL_DIR / "cross_session_test_data.json"


def _load_scenarios() -> list[dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["scenarios"]


class TestCrossSessionUnit:
    """Headless: data-file integrity."""

    def test_data_file_integrity(self):
        scenarios = _load_scenarios()
        assert len(scenarios) >= 3
        for s in scenarios:
            assert s.get("type") == "cross_session_continuity", f"{s.get('scenario')} bad type"
            assert s.get("persona"), f"{s.get('scenario')} missing persona"
            assert isinstance(s.get("session_a_conversation"), list) and s["session_a_conversation"]
            assert s.get("session_b_query"), f"{s.get('scenario')} missing session_b_query"
            assert isinstance(s.get("expected_recall"), list) and s["expected_recall"]


@pytest.mark.requires_ollama
@pytest.mark.xfail(
    reason="cross-session recall needs user_profile linkage (same user_id across "
    "sessions); not wired headlessly until ADR-006 Phase 1",
    strict=False,
)
class TestCrossSessionLive:
    """Live: plant in session A, probe in fresh session B."""

    BASE_URL = "http://localhost:8000"
    RECALL_FLOOR = 0.5

    def test_cross_session_continuity_live(self):
        sys.path.insert(0, str(_EVAL_DIR.parent / "manual"))
        from api_client import create_session, chat  # type: ignore

        scores = []
        for s in _load_scenarios():
            persona = s["persona"]
            sid_a = create_session(persona, base_url=self.BASE_URL)
            for turn in s["session_a_conversation"]:
                if turn["role"] == "user":
                    chat(sid_a, persona, turn["content"], base_url=self.BASE_URL)

            sid_b = create_session(persona, base_url=self.BASE_URL)
            answer, _, _, _ = chat(sid_b, persona, s["session_b_query"], base_url=self.BASE_URL)
            rate = pm.recall_rate(answer, s["expected_recall"])
            scores.append(rate)
            print(f"[cross_session] {s['scenario']}: recall={rate}")

        mean_recall = round(sum(scores) / len(scores), 4)
        print(f"[cross_session] MEAN recall_rate={mean_recall}")
        assert mean_recall >= self.RECALL_FLOOR
