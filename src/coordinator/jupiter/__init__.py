# src/coordinator/jupiter/__init__.py
# Jupiter DEX MCP client package
# Uses long-running Docker STDIO client (same pattern as MongoDB MCP)

from __future__ import annotations

import os
from typing import Optional

from .jupiter_mcp_client import (
    JupiterConnectionError,
    JupiterDockerClient,
    JupiterMCPError,
    JupiterResponseError,
    JupiterTimeoutError,
    JUPITER_TOOLS,
)

from .jupiter_operations import JupiterOperations


class JupiterMCPClient(JupiterDockerClient, JupiterOperations):
    """Combined Jupiter MCP client with Docker management and high-level operations.

    Inherits from:
    - JupiterDockerClient: Long-running Docker process and JSON-RPC protocol
    - JupiterOperations: High-level Jupiter DEX operations

    Note: The Docker process is NOT started on __init__. Call set_private_key()
    to inject the decrypted wallet key and start the server.

    Usage:
        client = JupiterMCPClient()
        client.set_private_key(decrypted_key_b58)
        balance = await client.get_wallet_balance(public_address)
        client.close()

    Or with context manager:
        with JupiterMCPClient() as client:
            client.set_private_key(key)
            quote = await client.get_swap_quote(...)
    """

    def __init__(
        self,
        image: Optional[str] = None,
        solana_rpc_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize Jupiter MCP client.

        Args:
            image: Docker image for Jupiter MCP server
                   (defaults to JUPITER_MCP_IMAGE env var, then 'localhost/jupiter-mcp:latest')
            solana_rpc_url: Solana RPC endpoint URL
                            (defaults to SOLANA_RPC_URL env var, then devnet)
            timeout: Timeout in seconds for MCP operations
        """
        resolved_image = image or os.getenv("JUPITER_MCP_IMAGE", "localhost/jupiter-mcp:latest")
        resolved_rpc = solana_rpc_url or os.getenv(
            "SOLANA_RPC_URL", "https://api.devnet.solana.com"
        )

        # Initialize Docker client (does NOT start process — waits for set_private_key)
        JupiterDockerClient.__init__(
            self,
            image=resolved_image,
            solana_rpc_url=resolved_rpc,
            timeout=timeout,
        )

        # Initialize operations (passes self as the underlying client)
        JupiterOperations.__init__(self, client=self)


def get_jupiter_client() -> JupiterMCPClient:
    """Factory function to create a JupiterMCPClient from environment configuration.

    Returns:
        Configured JupiterMCPClient instance.
        Process is NOT started — call client.set_private_key() before use.
    """
    return JupiterMCPClient(
        image=os.getenv("JUPITER_MCP_IMAGE", "localhost/jupiter-mcp:latest"),
        solana_rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com"),
        timeout=int(os.getenv("JUPITER_TIMEOUT", "30")),
    )


# Explicit exports for clean imports
__all__ = [
    # Core combined client
    "JupiterMCPClient",
    "get_jupiter_client",
    # Low-level client
    "JupiterDockerClient",
    # Operations mixin
    "JupiterOperations",
    # Exceptions
    "JupiterMCPError",
    "JupiterConnectionError",
    "JupiterTimeoutError",
    "JupiterResponseError",
    # Constants
    "JUPITER_TOOLS",
]
