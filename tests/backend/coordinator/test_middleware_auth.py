# tests/backend/coordinator/test_middleware_auth.py
"""
Unit tests for src/coordinator/middleware/auth.py.

Covers: _decode_token, get_current_user, get_optional_user.
All tests are deterministic — no network, no DB.
JWT tokens are minted with the same secret/algo the app uses.
"""
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import jwt
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

_TEST_SECRET = "test-secret-key-for-unit-tests-min-32-chars!!"
_TEST_ALGO = "HS256"


def _make_mock_settings(
    *,
    auth_required: bool = True,
    secret: str = _TEST_SECRET,
    algorithm: str = _TEST_ALGO,
) -> MagicMock:
    settings = MagicMock()
    settings.auth.jwt_secret_key = secret
    settings.auth.jwt_algorithm = algorithm
    settings.auth.auth_required = auth_required
    return settings


def _mint_access_token(
    sub: str = "user123",
    email: str = "user@example.com",
    name: str = "Test User",
    avatar: str = "https://example.com/avatar.png",
    expires_in: Optional[timedelta] = None,
    secret: str = _TEST_SECRET,
    algorithm: str = _TEST_ALGO,
) -> str:
    if expires_in is None:
        expires_in = timedelta(hours=1)
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "avatar": avatar,
        "exp": datetime.utcnow() + expires_in,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def _run(coro):
    """Run an async function synchronously.

    Uses asyncio.run() (fresh loop per call). asyncio.get_event_loop() raises
    "no current event loop" on Python 3.12 once an earlier suite test has closed
    the thread's loop — i.e. passes alone, fails in-suite.
    """
    return asyncio.run(coro)


# ── _decode_token ─────────────────────────────────────────────────────────────

class TestDecodeToken:
    def test_valid_token_returns_payload(self):
        token = _mint_access_token()
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            payload = _decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert payload["name"] == "Test User"

    def test_expired_token_raises_401(self):
        token = _mint_access_token(expires_in=timedelta(seconds=-1))
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_expired_token_includes_www_authenticate_header(self):
        token = _mint_access_token(expires_in=timedelta(seconds=-1))
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token(token)
        assert "WWW-Authenticate" in exc_info.value.headers

    def test_invalid_signature_raises_401(self):
        token = _mint_access_token(secret="wrong-secret-key-padded-to-32-chars-yes")
        settings = _make_mock_settings()  # uses _TEST_SECRET
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token(token)
        assert exc_info.value.status_code == 401

    def test_garbage_string_raises_401(self):
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token("not.a.jwt")
        assert exc_info.value.status_code == 401

    def test_empty_string_raises_401(self):
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException):
                _decode_token("")

    def test_invalid_token_detail_contains_message(self):
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token("garbage")
        assert "Invalid access token" in exc_info.value.detail

    def test_invalid_token_includes_www_authenticate_header(self):
        settings = _make_mock_settings()
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware.auth import _decode_token
            with pytest.raises(HTTPException) as exc_info:
                _decode_token("garbage")
        assert "WWW-Authenticate" in exc_info.value.headers


# ── get_current_user ─────────────────────────────────────────────────────────

class TestGetCurrentUser:
    def _get_user(self, authorization, settings):
        with patch(
            "src.coordinator.middleware.auth.get_settings", return_value=settings
        ):
            from src.coordinator.middleware import auth as auth_mod
            import importlib
            importlib.reload(auth_mod)
            return _run(auth_mod.get_current_user(authorization=authorization))

    def test_valid_bearer_returns_user_payload(self):
        token = _mint_access_token(sub="abc", email="a@b.com", name="Alice")
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            result = _run(get_current_user(authorization=f"Bearer {token}"))
        assert result["sub"] == "abc"
        assert result["email"] == "a@b.com"
        assert result["name"] == "Alice"

    def test_auth_required_false_returns_local_user(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            result = _run(get_current_user(authorization=None))
        assert result["sub"] == "local_user"
        assert result["email"] == "local@nephilim.dev"
        assert result["name"] == "Local Seeker"

    def test_auth_required_false_ignores_authorization_header(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            result = _run(get_current_user(authorization="Bearer invalid_token"))
        assert result["sub"] == "local_user"

    def test_missing_authorization_raises_401(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=None))
        assert exc_info.value.status_code == 401

    def test_malformed_authorization_no_bearer_raises_401(self):
        settings = _make_mock_settings(auth_required=True)
        token = _mint_access_token()
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=token))  # missing "Bearer " prefix
        assert exc_info.value.status_code == 401

    def test_wrong_scheme_raises_401(self):
        settings = _make_mock_settings(auth_required=True)
        token = _mint_access_token()
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=f"Token {token}"))
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        token = _mint_access_token(expires_in=timedelta(seconds=-1))
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=f"Bearer {token}"))
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization="Bearer garbage.token.here"))
        assert exc_info.value.status_code == 401

    def test_missing_header_detail_message(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=None))
        assert "Missing" in exc_info.value.detail or "malformed" in exc_info.value.detail

    def test_missing_header_includes_www_authenticate(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                _run(get_current_user(authorization=None))
        assert "WWW-Authenticate" in exc_info.value.headers

    def test_bypass_user_has_avatar_key(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            result = _run(get_current_user(authorization=None))
        assert "avatar" in result

    def test_valid_token_payload_has_all_expected_keys(self):
        token = _mint_access_token(sub="u1", email="u1@test.com", name="User One", avatar="http://img")
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            result = _run(get_current_user(authorization=f"Bearer {token}"))
        for key in ("sub", "email", "name", "avatar"):
            assert key in result, f"Missing key '{key}' in payload"

    def test_bearer_with_empty_token_raises_401(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_current_user
            with pytest.raises(HTTPException):
                _run(get_current_user(authorization="Bearer "))


# ── get_optional_user ─────────────────────────────────────────────────────────

class TestGetOptionalUser:
    def test_valid_bearer_returns_user_payload(self):
        token = _mint_access_token(sub="xyz", email="xyz@test.com")
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=f"Bearer {token}"))
        assert result is not None
        assert result["sub"] == "xyz"

    def test_missing_authorization_returns_none(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=None))
        assert result is None

    def test_invalid_token_returns_none(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization="Bearer not.a.valid.token"))
        assert result is None

    def test_expired_token_returns_none(self):
        token = _mint_access_token(expires_in=timedelta(seconds=-1))
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=f"Bearer {token}"))
        assert result is None

    def test_no_bearer_prefix_returns_none(self):
        token = _mint_access_token()
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=token))
        assert result is None

    def test_auth_required_false_returns_local_user(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=None))
        assert result is not None
        assert result["sub"] == "local_user"

    def test_auth_required_false_ignores_invalid_token(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization="Bearer garbage"))
        assert result is not None
        assert result["sub"] == "local_user"

    def test_wrong_scheme_returns_none(self):
        token = _mint_access_token()
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            result = _run(get_optional_user(authorization=f"Token {token}"))
        assert result is None

    def test_never_raises_on_bad_token(self):
        settings = _make_mock_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user
            # Should not raise HTTPException
            result = _run(get_optional_user(authorization="Bearer !!!invalid!!!"))
        assert result is None

    def test_bypass_user_payload_matches_get_current_user_bypass(self):
        settings = _make_mock_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            from src.coordinator.middleware.auth import get_optional_user, get_current_user
            optional_result = _run(get_optional_user(authorization=None))
            current_result = _run(get_current_user(authorization=None))
        assert optional_result == current_result
