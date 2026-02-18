"""
Authentication middleware and FastAPI dependency for JWT verification.
"""
from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status

from ..config import get_settings

logger = logging.getLogger(__name__)


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises HTTPException on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """
    FastAPI dependency: extract and validate Bearer JWT from Authorization header.
    Returns decoded payload { sub, email, name }.
    Raises 401 if missing or invalid.
    """
    settings = get_settings()

    # AUTH_REQUIRED=false bypass: return a local dev user
    if not settings.auth.auth_required:
        return {
            "sub": "local_user",
            "email": "local@nephilim.dev",
            "name": "Local Seeker",
            "avatar": "",
        }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len("Bearer "):]
    return _decode_token(token)


async def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """
    Like get_current_user but returns None instead of raising 401.
    Useful for endpoints that work with or without auth.
    """
    settings = get_settings()

    if not settings.auth.auth_required:
        return {
            "sub": "local_user",
            "email": "local@nephilim.dev",
            "name": "Local Seeker",
            "avatar": "",
        }

    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization[len("Bearer "):]
        return _decode_token(token)
    except HTTPException:
        return None
