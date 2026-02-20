"""
Google OAuth authentication routes.

Endpoints:
  POST /auth/google   — verify Google ID token, issue local JWT pair
  POST /auth/refresh  — use refresh token cookie to issue new access token
  POST /auth/logout   — clear refresh token cookie
  GET  /auth/me       — return current user info from access token
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from ..config import get_settings
from ..middleware.auth import get_current_user
from ..repositories import user_repository

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["auth"])


# ── Schemas ──────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT string from GIS SDK)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Helpers ───────────────────────────────────────────────

def _verify_google_token(credential: str) -> dict:
    """Verify Google ID token and return id_info dict."""
    settings = get_settings()

    if not settings.auth.is_google_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env",
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.auth.google_client_id,
            clock_skew_in_seconds=10,
        )
        return id_info
    except ValueError as e:
        logger.warning("Google token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {e}",
        )


def _create_access_token(sub: str, email: str, name: str, avatar: str) -> str:
    settings = get_settings()
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "avatar": avatar,
        "exp": datetime.utcnow() + timedelta(hours=settings.auth.jwt_expire_hours),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.auth.jwt_secret_key, algorithm=settings.auth.jwt_algorithm)


def _create_refresh_token(sub: str) -> str:
    settings = get_settings()
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(days=settings.auth.refresh_expire_days),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.auth.jwt_secret_key, algorithm=settings.auth.jwt_algorithm)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=settings.auth.cookie_secure,
        path="/auth/refresh",
        max_age=60 * 60 * 24 * settings.auth.refresh_expire_days,
    )


# ── Routes ────────────────────────────────────────────────

@auth_router.post("/auth/google", response_model=TokenResponse)
async def login_with_google(body: GoogleAuthRequest, response: Response) -> TokenResponse:
    """Verify Google ID token and issue local JWT access + refresh tokens."""
    settings = get_settings()

    id_info = _verify_google_token(body.credential)

    sub    = id_info["sub"]
    email  = id_info.get("email", "")
    name   = id_info.get("name", "")
    avatar = id_info.get("picture", "")

    # Upsert user in SQLite
    user_repository.upsert_user(
        db_path=settings.db_path,
        google_sub=sub,
        email=email,
        display_name=name,
        avatar_url=avatar,
    )

    onboarded = user_repository.get_onboarding_status(settings.db_path, sub)

    access_token  = _create_access_token(sub, email, name, avatar)
    refresh_token = _create_refresh_token(sub)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        user={"sub": sub, "email": email, "name": name, "avatar": avatar, "onboarding_completed": onboarded},
    )


@auth_router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_access_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
) -> TokenResponse:
    """Issue new access token using refresh token cookie."""
    settings = get_settings()

    # Bypass mode: return local user token
    if not settings.auth.auth_required:
        local_sub = "local_user"
        access_token = _create_access_token(
            local_sub, "local@nephilim.dev", "Local Seeker", ""
        )
        onboarded = user_repository.get_onboarding_status(settings.db_path, local_sub)
        return TokenResponse(
            access_token=access_token,
            user={"sub": local_sub, "email": "local@nephilim.dev", "name": "Local Seeker", "avatar": "", "onboarding_completed": onboarded},
        )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = jwt.decode(
            refresh_token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        )

    sub = payload["sub"]
    user = user_repository.get_user_by_sub(settings.db_path, sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = _create_access_token(
        sub,
        user.get("email", ""),
        user.get("display_name", ""),
        user.get("avatar_url", ""),
    )
    new_refresh = _create_refresh_token(sub)
    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(
        access_token=access_token,
        user={
            "sub": sub,
            "email": user.get("email", ""),
            "name": user.get("display_name", ""),
            "avatar": user.get("avatar_url", ""),
            "onboarding_completed": bool(user.get("onboarding_completed", 0)),
        },
    )


@auth_router.post("/auth/logout")
async def logout(response: Response) -> dict:
    """Clear the refresh token cookie."""
    response.delete_cookie(key="refresh_token", path="/auth/refresh")
    return {"message": "Logged out successfully"}


@auth_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """Return current authenticated user info from JWT, enriched with DB flags."""
    settings = get_settings()
    sub = current_user.get("sub", "")
    onboarded = user_repository.get_onboarding_status(settings.db_path, sub)
    return {**current_user, "onboarding_completed": onboarded}


@auth_router.post("/auth/me/onboarding")
async def complete_onboarding(current_user: dict = Depends(get_current_user)) -> dict:
    """Mark onboarding as completed for the current user."""
    settings = get_settings()
    sub = current_user.get("sub", "")
    user_repository.set_onboarding_completed(settings.db_path, sub)
    return {"onboarding_completed": True}
