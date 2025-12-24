# src/coordinator/mongodb/__init__.py
# MongoDB MCP client package
# Combines Docker client and operations into unified interface

from __future__ import annotations

import os
from typing import Optional

# Import all exceptions from docker_client
from .docker_client import (
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPResponseError,
    MCPPermissionError,
    MongoDBDockerClient,
    READ_ONLY_TOOLS,
    WRITE_TOOLS
)

# Import operations
from .operations import MongoDBOperations


class MongoDBMCPClient(MongoDBDockerClient, MongoDBOperations):
    """
    Combined MongoDB MCP client with Docker management and high-level operations.

    Inherits from:
    - MongoDBDockerClient: Low-level Docker subprocess and JSON-RPC protocol
    - MongoDBOperations: High-level MongoDB operations (find, aggregate, count, etc.)

    Usage:
        client = MongoDBMCPClient()
        results = client.find("mydb", "mycollection", limit=10)
        client.close()

    Or with context manager:
        with MongoDBMCPClient() as client:
            results = client.find("mydb", "mycollection")
    """

    def __init__(
        self,
        connection_uri: Optional[str] = None,
        transport: str = "stdio",
        timeout: int = 30,
        max_response_bytes: int = 100000
    ):
        """
        Initialize MongoDB MCP client.

        Args:
            connection_uri: MongoDB connection URI (defaults to MONGODB_URI env var)
            transport: MCP transport protocol (only 'stdio' supported)
            timeout: Timeout in seconds for MongoDB operations
            max_response_bytes: Maximum response size in bytes
        """
        # Initialize Docker client first (handles connection)
        MongoDBDockerClient.__init__(
            self,
            connection_uri=connection_uri,
            transport=transport,
            timeout=timeout,
            max_response_bytes=max_response_bytes
        )

        # Initialize operations (uses self as docker_client)
        MongoDBOperations.__init__(self, docker_client=self)


def get_mongodb_client() -> MongoDBMCPClient:
    """
    Factory function to create a MongoDBMCPClient with environment configuration.

    Returns:
        Configured MongoDBMCPClient instance
    """
    return MongoDBMCPClient(
        connection_uri=os.getenv("MONGODB_URI"),
        transport=os.getenv("MONGODB_MCP_TRANSPORT", "stdio"),
        timeout=int(os.getenv("MONGODB_TIMEOUT", "30")),
        max_response_bytes=int(os.getenv("MONGODB_MAX_RESPONSE_BYTES", "100000"))
    )


# Explicit exports for clean imports
__all__ = [
    # Core client
    "MongoDBMCPClient",
    "get_mongodb_client",
    # Low-level client
    "MongoDBDockerClient",
    # Operations
    "MongoDBOperations",
    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPResponseError",
    "MCPPermissionError",
    # Constants
    "READ_ONLY_TOOLS",
    "WRITE_TOOLS",
]
