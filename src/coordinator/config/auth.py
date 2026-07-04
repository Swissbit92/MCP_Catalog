from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Google OAuth and JWT configuration."""

    google_client_id: str = Field(
        default="",
        description="Google OAuth Client ID",
        alias="GOOGLE_CLIENT_ID"
    )
    jwt_secret_key: str = Field(
        default="dev-secret-change-in-production-min-32-chars!!",
        description="Secret key for signing JWT tokens",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
        alias="JWT_ALGORITHM"
    )
    jwt_expire_hours: int = Field(
        default=1,
        ge=1,
        le=168,
        description="Access token expiry in hours",
        alias="JWT_EXPIRE_HOURS"
    )
    refresh_expire_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Refresh token expiry in days",
        alias="JWT_REFRESH_EXPIRE_DAYS"
    )
    auth_required: bool = Field(
        default=False,
        description="Require authentication (set True in production)",
        alias="AUTH_REQUIRED"
    )
    auth_env: str = Field(
        default="development",
        description="Environment: development or production",
        alias="AUTH_ENV"
    )

    # The insecure hardcoded fallback secret. Safe only while auth is disabled.
    _DEV_JWT_SECRET = "dev-secret-change-in-production-min-32-chars!!"

    @model_validator(mode="after")
    def _reject_dev_secret_when_auth_required(self) -> AuthSettings:
        """ADR-006 M3: fail loud if auth is on but JWT still uses the dev secret.

        Previously AUTH_REQUIRED=false masked the insecure default — flipping auth
        on would have silently signed tokens with a publicly-known key.
        """
        if self.auth_required and self.jwt_secret_key == self._DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a real secret when AUTH_REQUIRED=true "
                "(the built-in dev secret is publicly known)."
            )
        return self

    @property
    def cookie_secure(self) -> bool:
        """Use secure cookies in production (requires HTTPS)."""
        return self.auth_env == "production"

    @property
    def is_google_configured(self) -> bool:
        """Check if Google OAuth credentials are set."""
        return bool(self.google_client_id.strip())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
