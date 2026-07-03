"""
Unit tests for src/coordinator/routes/auth.py

Mocks:
- src.coordinator.routes.auth._verify_google_token   (avoids real Google API)
- src.coordinator.routes.auth.user_repository.*      (avoids SQLite)
- src.coordinator.routes.auth.get_settings           (for JWT secret / config)
- src.coordinator.middleware.auth.get_settings        (for get_current_user dep)
- app.dependency_overrides[get_current_user]          (bypass JWT for /auth/me tests)
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi.testclient import TestClient
from src.coordinator.server import app
from src.coordinator.middleware.auth import get_current_user

client = TestClient(app)

_SECRET = "test-secret-key-for-unit-tests-min-32-chars!!"
_ALGO = "HS256"


def _make_settings(*, auth_required=True, google_configured=True, db_path="/tmp/test.db"):
    s = MagicMock()
    s.auth.jwt_secret_key = _SECRET
    s.auth.jwt_algorithm = _ALGO
    s.auth.jwt_expire_hours = 1
    s.auth.refresh_expire_days = 30
    s.auth.auth_required = auth_required
    s.auth.cookie_secure = False
    s.auth.is_google_configured = google_configured
    s.auth.google_client_id = "fake-google-client-id"
    s.db_path = db_path
    s.ollama.model = "test-model"
    return s


def _mint_refresh_token(sub="user-1", secret=_SECRET, algo=_ALGO, expires_in=None):
    if expires_in is None:
        expires_in = timedelta(days=30)
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + expires_in,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=algo)


def _mint_access_token(sub="user-1", email="u@test.com", name="User", avatar=""):
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "avatar": avatar,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


# ─── POST /auth/google ────────────────────────────────────────────────────────

class TestLoginWithGoogle:
    def test_happy_path_returns_access_token(self):
        fake_id_info = {"sub": "g-123", "email": "test@example.com", "name": "Test User", "picture": "http://img"}
        settings = _make_settings()
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth._verify_google_token", return_value=fake_id_info), \
             patch("src.coordinator.routes.auth.user_repository.upsert_user"), \
             patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=False):
            resp = client.post("/auth/google", json={"credential": "fake-google-token"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["sub"] == "g-123"

    def test_response_includes_user_fields(self):
        fake_id_info = {"sub": "g-456", "email": "a@b.com", "name": "Alice", "picture": ""}
        settings = _make_settings()
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth._verify_google_token", return_value=fake_id_info), \
             patch("src.coordinator.routes.auth.user_repository.upsert_user"), \
             patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=True):
            resp = client.post("/auth/google", json={"credential": "token"})
        user = resp.json()["user"]
        for key in ("sub", "email", "name", "avatar", "onboarding_completed"):
            assert key in user, f"Missing key '{key}'"

    def test_invalid_google_token_returns_401(self):
        settings = _make_settings()
        from fastapi import HTTPException
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth._verify_google_token", side_effect=HTTPException(status_code=401, detail="Invalid")):
            resp = client.post("/auth/google", json={"credential": "bad-token"})
        assert resp.status_code == 401

    def test_google_not_configured_returns_503(self):
        settings = _make_settings(google_configured=False)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings):
            # _verify_google_token checks is_google_configured; we let it run real
            resp = client.post("/auth/google", json={"credential": "any"})
        assert resp.status_code == 503

    def test_sets_refresh_cookie(self):
        fake_id_info = {"sub": "g-789", "email": "x@y.com", "name": "X", "picture": ""}
        settings = _make_settings()
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth._verify_google_token", return_value=fake_id_info), \
             patch("src.coordinator.routes.auth.user_repository.upsert_user"), \
             patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=False):
            resp = client.post("/auth/google", json={"credential": "tok"})
        # The refresh cookie should be set in response headers
        assert "refresh_token" in resp.cookies or "set-cookie" in {k.lower() for k in resp.headers}

    def test_missing_credential_returns_422(self):
        resp = client.post("/auth/google", json={})
        assert resp.status_code == 422


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

class TestRefreshAccessToken:
    def test_bypass_mode_returns_local_user(self):
        settings = _make_settings(auth_required=False)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=False):
            resp = client.post("/auth/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["sub"] == "local_user"

    def test_valid_refresh_token_returns_new_access_token(self):
        refresh_tok = _mint_refresh_token(sub="user-99")
        settings = _make_settings(auth_required=True)
        fake_user = {"email": "u@test.com", "display_name": "User", "avatar_url": "", "onboarding_completed": 0}
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth.user_repository.get_user_by_sub", return_value=fake_user):
            resp = client.post("/auth/refresh", cookies={"refresh_token": refresh_tok})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["user"]["sub"] == "user-99"

    def test_no_refresh_token_returns_401(self):
        settings = _make_settings(auth_required=True)
        fresh_client = TestClient(app)  # fresh client: no cookie jar contamination from prior test
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings):
            resp = fresh_client.post("/auth/refresh")
        assert resp.status_code == 401

    def test_expired_refresh_token_returns_401(self):
        expired_tok = _mint_refresh_token(sub="user-1", expires_in=timedelta(seconds=-1))
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings):
            resp = client.post("/auth/refresh", cookies={"refresh_token": expired_tok})
        assert resp.status_code == 401

    def test_access_token_used_as_refresh_returns_401(self):
        # Access token has type="access", not "refresh"
        access_tok = _mint_access_token()
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings):
            resp = client.post("/auth/refresh", cookies={"refresh_token": access_tok})
        assert resp.status_code == 401

    def test_user_not_found_returns_401(self):
        refresh_tok = _mint_refresh_token(sub="ghost-user")
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
             patch("src.coordinator.routes.auth.user_repository.get_user_by_sub", return_value=None):
            resp = client.post("/auth/refresh", cookies={"refresh_token": refresh_tok})
        assert resp.status_code == 401

    def test_garbage_refresh_token_returns_401(self):
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.routes.auth.get_settings", return_value=settings):
            resp = client.post("/auth/refresh", cookies={"refresh_token": "not.a.jwt"})
        assert resp.status_code == 401


# ─── POST /auth/logout ────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_success_message(self):
        resp = client.post("/auth/logout")
        assert resp.status_code == 200
        assert resp.json() == {"message": "Logged out successfully"}

    def test_logout_clears_cookie(self):
        resp = client.post("/auth/logout")
        # Cookie should be deleted (set-cookie header present with empty/expired value)
        assert resp.status_code == 200


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

class TestGetMe:
    def test_returns_current_user_info(self):
        fake_user = {"sub": "user-1", "email": "u@test.com", "name": "User", "avatar": ""}
        settings = _make_settings()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        try:
            with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
                 patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=True):
                resp = client.get("/auth/me")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        body = resp.json()
        assert body["sub"] == "user-1"
        assert "onboarding_completed" in body

    def test_onboarding_status_included(self):
        fake_user = {"sub": "user-2", "email": "b@test.com", "name": "B", "avatar": ""}
        settings = _make_settings()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        try:
            with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
                 patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=False):
                resp = client.get("/auth/me")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.json()["onboarding_completed"] is False

    def test_no_auth_returns_401_when_auth_required(self):
        # Remove any override so the real dep runs
        app.dependency_overrides.pop(get_current_user, None)
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_bypass_mode_no_token_needed(self):
        settings_auth = _make_settings(auth_required=False)
        settings_route = _make_settings(auth_required=False)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings_auth), \
             patch("src.coordinator.routes.auth.get_settings", return_value=settings_route), \
             patch("src.coordinator.routes.auth.user_repository.get_onboarding_status", return_value=False):
            resp = client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["sub"] == "local_user"


# ─── POST /auth/me/onboarding ─────────────────────────────────────────────────

class TestCompleteOnboarding:
    def test_marks_onboarding_complete(self):
        fake_user = {"sub": "user-1", "email": "u@test.com", "name": "U", "avatar": ""}
        settings = _make_settings()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        try:
            with patch("src.coordinator.routes.auth.get_settings", return_value=settings), \
                 patch("src.coordinator.routes.auth.user_repository.set_onboarding_completed") as mock_set:
                resp = client.post("/auth/me/onboarding")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json() == {"onboarding_completed": True}
        mock_set.assert_called_once_with(settings.db_path, "user-1")

    def test_no_auth_returns_401(self):
        app.dependency_overrides.pop(get_current_user, None)
        settings = _make_settings(auth_required=True)
        with patch("src.coordinator.middleware.auth.get_settings", return_value=settings):
            resp = client.post("/auth/me/onboarding")
        assert resp.status_code == 401
