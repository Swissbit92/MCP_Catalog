from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class JupiterSettings(BaseSettings):
    """Jupiter DEX + Solana wallet configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable Jupiter wallet integration",
        alias="JUPITER_ENABLED"
    )
    mcp_image: str = Field(
        default="localhost/jupiter-mcp:latest",
        description="Docker image for Jupiter MCP server",
        alias="JUPITER_MCP_IMAGE"
    )
    slippage_bps: int = Field(
        default=50,
        ge=0,
        le=10000,
        description="Default slippage tolerance in basis points",
        alias="JUPITER_SLIPPAGE_BPS"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Jupiter MCP operation timeout in seconds",
        alias="JUPITER_TIMEOUT"
    )
    solana_rpc_url: str = Field(
        default="https://api.devnet.solana.com",
        description="Solana RPC URL (devnet by default for safety)",
        alias="SOLANA_RPC_URL"
    )
    strategies_dir: str = Field(
        default="strategies",
        description="Directory containing strategy JSON files",
        alias="STRATEGIES_DIR"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

class EmailSettings(BaseSettings):
    """Email notification configuration for trade alerts."""

    enabled: bool = Field(
        default=False,
        description="Enable email trade notifications",
        alias="EMAIL_ENABLED"
    )
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
        alias="EMAIL_SMTP_HOST"
    )
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port",
        alias="EMAIL_SMTP_PORT"
    )
    username: str = Field(
        default="",
        description="SMTP username/email",
        alias="EMAIL_USERNAME"
    )
    password: str = Field(
        default="",
        description="SMTP password or app password",
        alias="EMAIL_PASSWORD"
    )
    from_addr: str = Field(
        default="",
        description="From email address",
        alias="EMAIL_FROM"
    )
    to_addr: str = Field(
        default="",
        description="Recipient email address for trade notifications",
        alias="EMAIL_TO"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if email notifications are configured."""
        return self.enabled and bool(self.username.strip()) and bool(self.to_addr.strip())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }
