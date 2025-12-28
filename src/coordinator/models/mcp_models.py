# src/coordinator/models/mcp_models.py
"""Shared MCP (Model Context Protocol) models and exceptions.

This module contains data classes and exceptions used by all MCP clients
(Brave Search, MongoDB, etc.) to avoid duplication.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Represents a single search result from Brave Search.

    Attributes:
        title: The title of the search result
        url: The URL of the search result
        description: A snippet/description of the search result
        age: Optional age/date of the content (e.g., "2 days ago")
    """
    title: str
    url: str
    description: str
    age: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary format."""
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "age": self.age
        }


# MCP Exception Hierarchy
class MCPError(Exception):
    """Base exception for all MCP client errors."""
    pass


class MCPConnectionError(MCPError):
    """Raised when unable to connect to MCP server or spawn container."""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out."""
    pass


class MCPResponseError(MCPError):
    """Raised when MCP server returns an error response."""
    pass
