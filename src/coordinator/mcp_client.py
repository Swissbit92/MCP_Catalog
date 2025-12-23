# src/coordinator/mcp_client.py
# Brave MCP Client for stdio-based communication with Docker MCP server
# Implements JSON-RPC 2.0 protocol for Model Context Protocol (MCP)

from __future__ import annotations

import os
import json
import logging
import subprocess
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result from Brave Search."""
    title: str
    url: str
    description: str
    age: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "age": self.age
        }


class MCPError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPConnectionError(MCPError):
    """Raised when unable to connect to MCP server."""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out."""
    pass


class MCPResponseError(MCPError):
    """Raised when MCP server returns an error response."""
    pass


class BraveMCPClient:
    """
    Client for communicating with Brave Search MCP server via stdio.

    Uses Docker to run the MCP server as a subprocess and communicates
    via JSON-RPC 2.0 protocol over stdin/stdout.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        transport: str = "stdio",
        timeout: int = 10,
        max_results: int = 5,
        safesearch: str = "moderate"
    ):
        """
        Initialize Brave MCP client.

        Args:
            api_key: Brave API key (defaults to BRAVE_API_KEY env var)
            transport: MCP transport protocol (only 'stdio' supported)
            timeout: Timeout in seconds for search operations
            max_results: Maximum number of search results to return
            safesearch: Safe search filter ('off', 'moderate', 'strict')
        """
        # Initialize process first to avoid AttributeError in __del__
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()

        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY environment variable must be set")

        self.transport = transport
        self.timeout = timeout
        self.max_results = max_results
        self.safesearch = safesearch

        logger.info(
            "Initialized BraveMCPClient: "
            f"transport={transport}, timeout={timeout}s, max_results={max_results}"
        )

    def _get_next_request_id(self) -> int:
        """Generate next JSON-RPC request ID (thread-safe)."""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _start_mcp_server(self) -> subprocess.Popen:
        """
        Start the Docker MCP server process.

        Returns:
            subprocess.Popen: The running MCP server process

        Raises:
            MCPConnectionError: If unable to start the Docker container
        """
        logger.info("Starting Brave MCP Docker container...")

        cmd = [
            "docker", "run",
            "-i",  # Interactive mode (keep stdin open)
            "--rm",  # Remove container after exit
            "-e", "BRAVE_MCP_TRANSPORT",
            "-e", "BRAVE_API_KEY",
            "mcp/brave-search"
        ]

        env = os.environ.copy()
        env["BRAVE_MCP_TRANSPORT"] = self.transport
        env["BRAVE_API_KEY"] = self.api_key

        try:
            logger.debug(f"Docker command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding for cross-platform compatibility
                errors='replace',   # Replace invalid characters instead of failing
                bufsize=1  # Line buffered
            )

            # Give Docker a moment to initialize
            time.sleep(1)

            # Check if process started successfully
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else "Unknown error"
                logger.error(f"Docker container failed to start: {stderr}")
                raise MCPConnectionError(f"Docker container exited immediately: {stderr}")

            logger.info(f"MCP server started successfully (PID: {process.pid})")
            return process

        except FileNotFoundError:
            logger.error("Docker command not found - is Docker installed?")
            raise MCPConnectionError(
                "Docker not found. Please install Docker: https://www.docker.com/get-started"
            )
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}", exc_info=True)
            raise MCPConnectionError(f"Failed to start MCP server: {e}")

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request to the MCP server.

        Args:
            method: The MCP tool/method name (e.g., 'tools/call')
            params: Method parameters

        Returns:
            Dict containing the response

        Raises:
            MCPConnectionError: If not connected to server
            MCPTimeoutError: If request times out
            MCPResponseError: If server returns an error
        """
        if not self._process:
            self._process = self._start_mcp_server()

        request_id = self._get_next_request_id()

        # Construct JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        logger.debug(f"Sending MCP request #{request_id}: {json.dumps(request, indent=2)}")

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json)
            self._process.stdin.flush()

            # Read response with timeout
            start_time = time.time()
            response_line = None

            while time.time() - start_time < self.timeout:
                if self._process.stdout:
                    response_line = self._process.stdout.readline()
                    if response_line:
                        break
                time.sleep(0.1)

            if not response_line:
                logger.error(f"MCP request #{request_id} timed out after {self.timeout}s")
                raise MCPTimeoutError(f"Request timed out after {self.timeout}s")

            # Parse response
            response = json.loads(response_line)
            logger.debug(f"Received MCP response #{request_id}: {json.dumps(response, indent=2)}")

            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                error_msg = f"MCP Error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}"
                logger.error(f"MCP server returned error: {error_msg}")
                raise MCPResponseError(error_msg)

            return response.get("result", {})

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            raise MCPResponseError(f"Invalid JSON response: {e}")
        except IOError as e:
            logger.error(f"IO error communicating with MCP server: {e}")
            raise MCPConnectionError(f"IO error: {e}")

    def search_web(
        self,
        query: str,
        count: Optional[int] = None,
        country: Optional[str] = None,
        search_lang: Optional[str] = None,
        freshness: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search the web using Brave Search.

        Args:
            query: Search query (max 400 chars, 50 words)
            count: Number of results (1-20, defaults to max_results)
            country: Country code (e.g., 'US', 'GB')
            search_lang: Language code (e.g., 'en', 'de')
            freshness: Time filter ('pd'=day, 'pw'=week, 'pm'=month, 'py'=year)

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If query is invalid
            MCPError: If search fails
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        query = query.strip()
        if len(query) > 400:
            logger.warning(f"Query too long ({len(query)} chars), truncating to 400")
            query = query[:400]

        # Build parameters
        params = {
            "name": "brave_web_search",
            "arguments": {
                "query": query,
                "count": count or self.max_results,
                "safesearch": self.safesearch
            }
        }

        # Add optional parameters
        if country:
            params["arguments"]["country"] = country
        if search_lang:
            params["arguments"]["search_lang"] = search_lang
        if freshness:
            params["arguments"]["freshness"] = freshness

        logger.info(f"Searching Brave: query='{query}', count={params['arguments']['count']}")
        start_time = time.time()

        try:
            # Call MCP tool
            result = self._send_request("tools/call", params)

            elapsed = time.time() - start_time
            logger.info(f"Search completed in {elapsed:.2f}s")

            # Parse results
            results = self._parse_search_results(result)
            logger.info(f"Received {len(results)} search results")

            return results

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Search failed after {elapsed:.2f}s: {e}")
            raise

    def _parse_search_results(self, result: Dict[str, Any]) -> List[SearchResult]:
        """
        Parse MCP tool response into SearchResult objects.

        Args:
            result: Raw MCP tool response

        Returns:
            List of parsed SearchResult objects
        """
        results = []

        # MCP tool response format
        content = result.get("content", [])

        for item in content:
            if item.get("type") == "text":
                # Parse text content (may be JSON)
                text = item.get("text", "")
                try:
                    # Each content item is a separate JSON object (one search result)
                    if text.startswith("{"):
                        data = json.loads(text)

                        # Check if this is a direct search result (has url, title, description)
                        if "url" in data and "title" in data:
                            results.append(SearchResult(
                                title=data.get("title", "Untitled"),
                                url=data.get("url", ""),
                                description=data.get("description", ""),
                                age=data.get("age")
                            ))
                        # Or if it's wrapped in a "web" object
                        elif "web" in data and "results" in data["web"]:
                            for web_result in data["web"]["results"]:
                                results.append(SearchResult(
                                    title=web_result.get("title", "Untitled"),
                                    url=web_result.get("url", ""),
                                    description=web_result.get("description", ""),
                                    age=web_result.get("age")
                                ))
                        # Or if it's a results array
                        elif "results" in data:
                            for web_result in data["results"]:
                                results.append(SearchResult(
                                    title=web_result.get("title", "Untitled"),
                                    url=web_result.get("url", ""),
                                    description=web_result.get("description", ""),
                                    age=web_result.get("age")
                                ))
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse result as JSON: {text[:100]}")

        return results

    def close(self):
        """
        Close the MCP client and terminate the Docker container.
        """
        if self._process:
            logger.info("Shutting down MCP server...")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("MCP server shut down successfully")
            except subprocess.TimeoutExpired:
                logger.warning("MCP server did not terminate, forcing kill...")
                self._process.kill()
                self._process.wait()
            finally:
                self._process = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


def get_brave_client() -> BraveMCPClient:
    """
    Factory function to create a BraveMCPClient with environment configuration.

    Returns:
        Configured BraveMCPClient instance
    """
    return BraveMCPClient(
        api_key=os.getenv("BRAVE_API_KEY"),
        transport=os.getenv("BRAVE_MCP_TRANSPORT", "stdio"),
        timeout=int(os.getenv("BRAVE_SEARCH_TIMEOUT", "10")),
        max_results=int(os.getenv("BRAVE_MAX_RESULTS", "5")),
        safesearch=os.getenv("BRAVE_SAFESEARCH", "moderate")
    )


# Example usage
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        print("Testing Brave MCP Client...")
        print("=" * 60)

        with get_brave_client() as client:
            # Test search
            query = "Bitcoin price 2024"
            print(f"\nSearching for: {query}")
            print("-" * 60)

            results = client.search_web(query, count=3)

            print(f"\n✅ Found {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   {result.description[:100]}...")
                if result.age:
                    print(f"   Age: {result.age}")
                print()

        print("=" * 60)
        print("✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error("Test failed", exc_info=True)
