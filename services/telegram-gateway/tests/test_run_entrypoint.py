"""Tests for the multi-instance entrypoint logic in bin/run_telegram_bot.py.

Focus: the default instance stays byte-identical (.env + data/bot.lock), and a
named instance gets an isolated env file + lock (so two bots don't collide on
the singleton flock), with the instance name sanitized against path traversal.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# bin/ is not a package; load the module by path.
_BIN = Path(__file__).resolve().parent.parent / "bin" / "run_telegram_bot.py"
_spec = importlib.util.spec_from_file_location("run_telegram_bot", _BIN)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)


def test_default_instance_is_empty(monkeypatch):
    monkeypatch.delenv("EEVA_TG_INSTANCE", raising=False)
    assert run._instance_name() == ""


def test_default_paths_are_historical():
    env_file, lock = run._paths_for_instance("")
    assert env_file.name == ".env"
    assert lock.name == "bot.lock"


def test_named_instance_paths():
    env_file, lock = run._paths_for_instance("gwen")
    assert env_file.name == ".env.gwen"
    assert lock.name == "bot.gwen.lock"


def test_default_and_named_locks_differ():
    _, default_lock = run._paths_for_instance("")
    _, gwen_lock = run._paths_for_instance("gwen")
    assert default_lock != gwen_lock  # the whole point: no singleton collision


@pytest.mark.parametrize("raw,expected", [
    ("GWEN", "gwen"),
    ("  gwen  ", "gwen"),
    ("../evil", "evil"),          # path traversal stripped
    ("a/b/c", "abc"),
    ("gwen.prod", "gwenprod"),    # dots stripped (no extra path segments)
    ("g w e n", "gwen"),
    ("gwen_2-x", "gwen_2-x"),     # underscores/hyphens kept
])
def test_instance_name_sanitized(monkeypatch, raw, expected):
    monkeypatch.setenv("EEVA_TG_INSTANCE", raw)
    assert run._instance_name() == expected


def test_sanitized_instance_cannot_escape_data_dir(monkeypatch):
    # A hostile value is sanitized, then resolves to a lock inside data/.
    monkeypatch.setenv("EEVA_TG_INSTANCE", "../../etc/passwd")
    _, lock = run._paths_for_instance(run._instance_name())
    assert lock.parent.name == "data"
    assert lock.name == "bot.etcpasswd.lock"
