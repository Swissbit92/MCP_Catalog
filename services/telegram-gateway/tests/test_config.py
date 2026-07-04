"""Tests for config loading, allowlist parsing, and persona resolution."""

from __future__ import annotations

import pytest

from eeva_telegram.config import TelegramConfig, load_config

# Env vars load_config reads. dotenv uses override=False, so a value left in
# os.environ by a prior test would mask the .env under test — clear them all
# before every test to keep these hermetic.
_MANAGED_ENV = (
    "TG_BOT_TOKEN",
    "TG_ALLOWED_CHAT_IDS",
    "NEPHILIM_BASE_URL",
    "EEVA_PERSONA_KEY",
    "TG_CHAT_PERSONAS",
    "NEPHILIM_TIMEOUT_SECONDS",
    "TG_TYPING_INTERVAL_SECONDS",
    "TG_MESSAGE_CHAR_LIMIT",
    "TG_LOG_CONTENT",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in _MANAGED_ENV:
        monkeypatch.delenv(key, raising=False)


def _write_env(path, **overrides) -> None:
    base = {
        "TG_BOT_TOKEN": "real-token",
        "TG_ALLOWED_CHAT_IDS": "111,222",
        "NEPHILIM_BASE_URL": "http://127.0.0.1:8000",
        "EEVA_PERSONA_KEY": "nephilim_eeva",
        "TG_CHAT_PERSONAS": "",
    }
    base.update(overrides)
    path.write_text("\n".join(f"{k}={v}" for k, v in base.items()))


def test_load_config_happy_path(tmp_path):
    env = tmp_path / ".env"
    _write_env(env, TG_CHAT_PERSONAS="222:nephilim_nyx")
    cfg = load_config(env)
    assert cfg.bot_token == "real-token"
    assert cfg.allowed_chat_ids == frozenset({111, 222})
    assert cfg.default_persona_key == "nephilim_eeva"
    assert cfg.chat_personas == {222: "nephilim_nyx"}
    # base url trailing slash is normalised away
    assert not cfg.nephilim_base_url.endswith("/")


def test_missing_token_fails_fast(tmp_path):
    env = tmp_path / ".env"
    _write_env(env, TG_BOT_TOKEN="YOUR_BOT_TOKEN_HERE")
    with pytest.raises(RuntimeError, match="TG_BOT_TOKEN"):
        load_config(env)


def test_empty_allowlist_rejected(tmp_path):
    env = tmp_path / ".env"
    _write_env(env, TG_ALLOWED_CHAT_IDS=" , ")
    with pytest.raises(RuntimeError, match="TG_ALLOWED_CHAT_IDS"):
        load_config(env)


def test_non_numeric_chat_id_rejected(tmp_path):
    env = tmp_path / ".env"
    _write_env(env, TG_ALLOWED_CHAT_IDS="111,notanumber")
    with pytest.raises(RuntimeError, match="non-numeric"):
        load_config(env)


def test_malformed_persona_override_rejected(tmp_path):
    env = tmp_path / ".env"
    _write_env(env, TG_CHAT_PERSONAS="222-nephilim_nyx")  # missing ':'
    with pytest.raises(RuntimeError, match="missing ':'"):
        load_config(env)


def test_base_url_defaults_to_loopback(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    # omit NEPHILIM_BASE_URL entirely
    env.write_text("TG_BOT_TOKEN=real-token\nTG_ALLOWED_CHAT_IDS=111\n")
    monkeypatch.delenv("NEPHILIM_BASE_URL", raising=False)
    cfg = load_config(env)
    assert cfg.nephilim_base_url == "http://127.0.0.1:8000"


def test_is_allowed(cfg: TelegramConfig):
    assert cfg.is_allowed(111)
    assert cfg.is_allowed(222)
    assert not cfg.is_allowed(999)


def test_persona_for_chat_override_and_default(cfg: TelegramConfig):
    assert cfg.persona_for_chat(222) == "nephilim_nyx"  # override
    assert cfg.persona_for_chat(111) == "nephilim_eeva"  # default
    assert cfg.persona_for_chat(999) == "nephilim_eeva"  # unknown -> default
