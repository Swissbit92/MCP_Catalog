"""ADR-006 M3 — committed flag defaults aligned to validated prod + JWT hardening.

Asserts model_fields defaults (env-INDEPENDENT — can't be masked/forced by the
ambient .env) and the new AuthSettings fail-loud JWT validator.
"""

from __future__ import annotations

import pytest

from src.coordinator.config import (
    LoreSettings,
    AuthSettings,
)


class TestAlignedDefaults:
    """Committed defaults must match the validated prod config.

    The lean-prompt / semantic-routing / on-demand-lore flags were retired
    2026-07-04 (audit cleanup step 5) — their behavior is now unconditional, so
    there is no longer a default to assert. LORE_RANK_CONTEXT_ENABLED remains a
    live flag.
    """

    def test_rank_context_default_true(self):
        assert LoreSettings.model_fields["rank_context_enabled"].default is True


class TestJwtHardening:
    """AUTH_REQUIRED must not silently sign tokens with the public dev secret."""

    def test_raises_when_auth_required_with_dev_secret(self):
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            AuthSettings(auth_required=True)

    def test_ok_when_auth_required_with_real_secret(self):
        s = AuthSettings(auth_required=True, jwt_secret_key="a-real-secret-of-sufficient-length-xx")
        assert s.auth_required is True

    def test_ok_when_auth_disabled_with_dev_secret(self):
        # dev secret is tolerated while auth is off (the common local case)
        s = AuthSettings(auth_required=False)
        assert s.auth_required is False
