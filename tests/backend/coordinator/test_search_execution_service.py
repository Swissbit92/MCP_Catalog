# tests/backend/coordinator/test_search_execution_service.py
"""Unit tests for SearchExecutionService — all branches."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.coordinator.services.search_execution_service import SearchExecutionService
from src.coordinator.tool_definitions import ToolCall


def _tool_call(query: str = "bitcoin price") -> ToolCall:
    return ToolCall(name="brave_web_search", arguments={"query": query})


class TestSearchExecutionServiceInit:
    def test_no_client_by_default(self):
        svc = SearchExecutionService()
        assert svc.mcp_client is None

    def test_client_stored(self):
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        assert svc.mcp_client is client


class TestExecuteSearch:
    """Tests for SearchExecutionService.execute_search."""

    # ------------------------------------------------------------------
    # No MCP client → returns None immediately
    # ------------------------------------------------------------------

    def test_returns_none_when_no_client(self):
        svc = SearchExecutionService(mcp_client=None)
        result = svc.execute_search(_tool_call())
        assert result is None

    # ------------------------------------------------------------------
    # Empty query → returns None
    # ------------------------------------------------------------------

    def test_empty_query_returns_none(self):
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        tc = ToolCall(name="brave_web_search", arguments={"query": ""})
        result = svc.execute_search(tc)
        assert result is None
        client.search_web.assert_not_called()

    def test_missing_query_key_returns_none(self):
        """arguments dict has no 'query' key → empty string → None."""
        client = MagicMock()
        svc = SearchExecutionService(mcp_client=client)
        tc = ToolCall(name="brave_web_search", arguments={})
        result = svc.execute_search(tc)
        assert result is None

    # ------------------------------------------------------------------
    # Successful search → returns results
    # ------------------------------------------------------------------

    def test_successful_search_returns_results(self):
        fake_results = [{"title": "BTC news", "url": "https://example.com"}]
        client = MagicMock()
        client.search_web.return_value = fake_results
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("bitcoin"))
        assert result == fake_results
        client.search_web.assert_called_once_with("bitcoin")

    def test_empty_results_list_returned(self):
        client = MagicMock()
        client.search_web.return_value = []
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("obscure query"))
        assert result == []

    # ------------------------------------------------------------------
    # Exception handling → returns None
    # ------------------------------------------------------------------

    def test_search_exception_returns_none(self):
        client = MagicMock()
        client.search_web.side_effect = RuntimeError("connection refused")
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("bitcoin"))
        assert result is None

    def test_search_timeout_returns_none(self):
        client = MagicMock()
        client.search_web.side_effect = TimeoutError("timed out")
        svc = SearchExecutionService(mcp_client=client)
        result = svc.execute_search(_tool_call("query"))
        assert result is None
