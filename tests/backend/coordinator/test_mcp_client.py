# src/coordinator/test_mcp_client.py
# Unit tests for Brave MCP Client

import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from coordinator.mcp_client_stdio import (
    BraveMCPClientStdio as BraveMCPClient,
    get_brave_client_stdio as get_brave_client
)
from coordinator.models.mcp_models import (
    SearchResult,
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPResponseError,
)


class TestSearchResult(unittest.TestCase):
    """Test SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            description="Test description",
            age="1 day ago"
        )

        self.assertEqual(result.title, "Test Title")
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.description, "Test description")
        self.assertEqual(result.age, "1 day ago")

    def test_search_result_to_dict(self):
        """Test converting SearchResult to dict."""
        result = SearchResult(
            title="Test",
            url="https://test.com",
            description="Desc"
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict["title"], "Test")
        self.assertEqual(result_dict["url"], "https://test.com")
        self.assertEqual(result_dict["description"], "Desc")
        self.assertIsNone(result_dict["age"])


class TestBraveMCPClient(unittest.TestCase):
    """Test BraveMCPClient class."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["BRAVE_API_KEY"] = "test_api_key_12345"

    def tearDown(self):
        """Clean up after tests."""
        if "BRAVE_API_KEY" in os.environ:
            del os.environ["BRAVE_API_KEY"]

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = BraveMCPClient(api_key="test_key")

        self.assertEqual(client.api_key, "test_key")
        self.assertEqual(client.transport, "stdio")
        self.assertEqual(client.timeout, 10)
        self.assertEqual(client.max_results, 5)

    def test_init_from_env(self):
        """Test client initialization from environment."""
        client = BraveMCPClient()

        self.assertEqual(client.api_key, "test_api_key_12345")

    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        del os.environ["BRAVE_API_KEY"]

        with self.assertRaises(ValueError) as ctx:
            BraveMCPClient()

        self.assertIn("BRAVE_API_KEY", str(ctx.exception))

    def test_get_next_request_id(self):
        """Test request ID generation."""
        client = BraveMCPClient(api_key="test")

        id1 = client._get_next_request_id()
        id2 = client._get_next_request_id()
        id3 = client._get_next_request_id()

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 3)

    @patch("subprocess.Popen")
    def test_start_mcp_server_success(self, mock_popen):
        """Test successful MCP server startup."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        client = BraveMCPClient(api_key="test")
        process = client._start_mcp_server()

        self.assertIsNotNone(process)
        self.assertEqual(process.pid, 12345)
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    def test_start_mcp_server_immediate_exit(self, mock_popen):
        """Test MCP server exits immediately."""
        # Mock process that exits immediately
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited
        mock_process.stderr.read.return_value = "Docker error"
        mock_popen.return_value = mock_process

        client = BraveMCPClient(api_key="test")

        with self.assertRaises(MCPConnectionError) as ctx:
            client._start_mcp_server()

        self.assertIn("exited immediately", str(ctx.exception))

    @patch("subprocess.Popen")
    def test_start_mcp_server_docker_not_found(self, mock_popen):
        """Test Docker not installed."""
        mock_popen.side_effect = FileNotFoundError("docker not found")

        client = BraveMCPClient(api_key="test")

        with self.assertRaises(MCPConnectionError) as ctx:
            client._start_mcp_server()

        self.assertIn("Docker not found", str(ctx.exception))

    @patch("subprocess.Popen")
    def test_send_request_success(self, mock_popen):
        """Test sending a successful request."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        # Mock successful response
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Success"}]}
        }
        mock_process.stdout.readline.return_value = json.dumps(response) + "\n"

        mock_popen.return_value = mock_process
        client = BraveMCPClient(api_key="test")
        client._process = mock_process

        result = client._send_request("tools/call", {"name": "test"})

        self.assertEqual(result, response["result"])

    @patch("subprocess.Popen")
    def test_send_request_timeout(self, mock_popen):
        """Test request timeout."""
        # Mock process that never responds
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = ""  # No response

        mock_popen.return_value = mock_process
        client = BraveMCPClient(api_key="test", timeout=1)
        client._process = mock_process

        with self.assertRaises(MCPTimeoutError) as ctx:
            client._send_request("tools/call", {})

        self.assertIn("timed out", str(ctx.exception))

    @patch("subprocess.Popen")
    def test_send_request_error_response(self, mock_popen):
        """Test server error response."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        # Mock error response
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid Request"}
        }
        mock_process.stdout.readline.return_value = json.dumps(response) + "\n"

        mock_popen.return_value = mock_process
        client = BraveMCPClient(api_key="test")
        client._process = mock_process

        with self.assertRaises(MCPResponseError) as ctx:
            client._send_request("tools/call", {})

        self.assertIn("Invalid Request", str(ctx.exception))

    @patch("subprocess.Popen")
    def test_send_request_invalid_json(self, mock_popen):
        """Test invalid JSON response."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = "not valid json\n"

        mock_popen.return_value = mock_process
        client = BraveMCPClient(api_key="test")
        client._process = mock_process

        with self.assertRaises(MCPResponseError) as ctx:
            client._send_request("tools/call", {})

        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_search_web_empty_query(self):
        """Test that empty query raises ValueError."""
        client = BraveMCPClient(api_key="test")

        with self.assertRaises(ValueError) as ctx:
            client.search_web("")

        self.assertIn("cannot be empty", str(ctx.exception))

    def test_search_web_long_query_truncation(self):
        """Test that long queries are truncated."""
        client = BraveMCPClient(api_key="test")

        # Create a query longer than 400 chars
        long_query = "a" * 500

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = {"content": []}

            try:
                client.search_web(long_query)
            except:
                pass

            # Verify query was truncated
            call_args = mock_send.call_args
            query_sent = call_args[0][1]["arguments"]["query"]
            self.assertEqual(len(query_sent), 400)

    @patch("subprocess.Popen")
    def test_parse_search_results(self, mock_popen):
        """Test parsing search results."""
        # Mock MCP response
        mcp_response = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "web": {
                            "results": [
                                {
                                    "title": "Bitcoin Price",
                                    "url": "https://coindesk.com",
                                    "description": "Current Bitcoin price",
                                    "age": "1 hour ago"
                                },
                                {
                                    "title": "Crypto News",
                                    "url": "https://cryptonews.com",
                                    "description": "Latest crypto updates"
                                }
                            ]
                        }
                    })
                }
            ]
        }

        client = BraveMCPClient(api_key="test")
        results = client._parse_search_results(mcp_response)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Bitcoin Price")
        self.assertEqual(results[0].url, "https://coindesk.com")
        self.assertEqual(results[0].age, "1 hour ago")
        self.assertEqual(results[1].title, "Crypto News")

    @patch("subprocess.Popen")
    def test_search_web_integration(self, mock_popen):
        """Test full search_web method."""
        # Mock process and response
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "web": {
                                "results": [
                                    {
                                        "title": "Test Result",
                                        "url": "https://test.com",
                                        "description": "Test description"
                                    }
                                ]
                            }
                        })
                    }
                ]
            }
        }
        mock_process.stdout.readline.return_value = json.dumps(response) + "\n"
        mock_popen.return_value = mock_process

        client = BraveMCPClient(api_key="test")
        results = client.search_web("test query", count=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Result")

    @patch("subprocess.Popen")
    def test_context_manager(self, mock_popen):
        """Test using client as context manager."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with BraveMCPClient(api_key="test") as client:
            # Start the process by making a call
            client._process = mock_process
            self.assertIsNotNone(client)

        # Verify cleanup was called
        mock_process.terminate.assert_called_once()

    @patch("subprocess.Popen")
    def test_close_terminates_process(self, mock_popen):
        """Test that close() terminates the process."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        client = BraveMCPClient(api_key="test")
        client._process = mock_process

        client.close()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_get_brave_client_factory(self):
        """Test factory function."""
        os.environ["BRAVE_API_KEY"] = "factory_test_key"
        os.environ["BRAVE_SEARCH_TIMEOUT"] = "15"
        os.environ["BRAVE_MAX_RESULTS"] = "10"

        client = get_brave_client()

        self.assertEqual(client.api_key, "factory_test_key")
        self.assertEqual(client.timeout, 15)
        self.assertEqual(client.max_results, 10)


class TestMCPExceptions(unittest.TestCase):
    """Test MCP exception hierarchy."""

    def test_mcp_error_base(self):
        """Test MCPError base exception."""
        with self.assertRaises(MCPError):
            raise MCPError("Test error")

    def test_mcp_connection_error(self):
        """Test MCPConnectionError."""
        with self.assertRaises(MCPConnectionError):
            raise MCPConnectionError("Connection failed")

        # Verify it's also an MCPError
        with self.assertRaises(MCPError):
            raise MCPConnectionError("Connection failed")

    def test_mcp_timeout_error(self):
        """Test MCPTimeoutError."""
        with self.assertRaises(MCPTimeoutError):
            raise MCPTimeoutError("Timeout")

    def test_mcp_response_error(self):
        """Test MCPResponseError."""
        with self.assertRaises(MCPResponseError):
            raise MCPResponseError("Bad response")


if __name__ == "__main__":
    unittest.main()
