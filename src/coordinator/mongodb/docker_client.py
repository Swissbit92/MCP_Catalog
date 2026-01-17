# src/coordinator/mongodb/docker_client.py
# Low-level Docker MCP server management and JSON-RPC 2.0 protocol communication
# Handles subprocess management, request/response protocol, and connection lifecycle

from __future__ import annotations

import os
import json
import logging
import subprocess
import threading
import time
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Read-only tools whitelist
READ_ONLY_TOOLS = {
    "aggregate",
    "collection-indexes",
    "collection-schema",
    "collection-storage-size",
    "connect",
    "count",
    "db-stats",
    "explain",
    "export",
    "find",
    "list-collections",
    "list-databases",
    "mongodb-logs"
}

# Write/destructive tools blacklist
WRITE_TOOLS = {
    "create-collection",
    "create-index",
    "delete-many",
    "drop-collection",
    "drop-database",
    "drop-index",
    "insert-many",
    "rename-collection",
    "update-many"
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


class MCPPermissionError(MCPError):
    """Raised when attempting a write operation on read-only client."""
    pass


class MongoDBDockerClient:
    """
    Low-level client for Docker MCP server subprocess management.

    Handles:
    - Docker container lifecycle (start, stop, cleanup)
    - JSON-RPC 2.0 protocol communication over stdin/stdout
    - Request/response handling with timeout
    - Connection health monitoring

    SECURITY: Read-only client - blocks all write operations.
    """

    def __init__(
        self,
        connection_uri: Optional[str] = None,
        transport: str = "stdio",
        timeout: int = 30,
        max_response_bytes: int = 100000
    ):
        """
        Initialize MongoDB Docker MCP client.

        Args:
            connection_uri: MongoDB connection URI (defaults to MONGODB_URI env var)
            transport: MCP transport protocol (only 'stdio' supported)
            timeout: Timeout in seconds for MongoDB operations
            max_response_bytes: Maximum response size in bytes
        """
        # Initialize process first to avoid AttributeError in __del__
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()

        self.connection_uri = connection_uri or os.getenv("MONGODB_URI")
        if not self.connection_uri:
            raise ValueError("MONGODB_URI environment variable must be set")

        self.transport = transport
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

        logger.info(
            "Initialized MongoDBDockerClient: "
            f"transport={transport}, timeout={timeout}s, max_bytes={max_response_bytes}"
        )

        # Pre-warm the Docker container on init
        self._start_mcp_server()

    def _get_next_request_id(self) -> int:
        """Generate next JSON-RPC request ID (thread-safe)."""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _start_mcp_server(self) -> subprocess.Popen:
        """
        Start the Docker MCP server process and keep it alive.

        SECURITY: Resource limits applied to prevent DoS attacks:
        - Memory: 512MB max (MongoDB queries can be memory-intensive)
        - CPU: 1.0 cores max (query processing needs more CPU than Brave)
        - PIDs: 100 max (prevents fork bombs)
        - Labels: Enables orphan container detection

        Returns:
            subprocess.Popen: The running MCP server process

        Raises:
            MCPConnectionError: If unable to start the Docker container
        """
        logger.info("Starting MongoDB MCP Docker container...")

        cmd = [
            "docker", "run",
            "-i",  # Interactive mode (keep stdin open)
            "--rm",  # Remove container after exit
            "--memory=512m",  # Higher limit for MongoDB query processing
            "--cpus=1.0",  # Full core for query performance
            "--pids-limit=100",  # Prevent fork bombs
            "--label=mcp.coordinator.ephemeral=false",  # Long-running
            "--label=mcp.coordinator.service=mongodb",
            "-e", "MDB_MCP_CONNECTION_STRING",
            "mcp/mongodb"
        ]

        env = os.environ.copy()
        env["MDB_MCP_CONNECTION_STRING"] = self.connection_uri

        try:
            logger.debug(f"Docker command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1  # Line buffered
            )

            # Give Docker a moment to initialize
            time.sleep(2)

            # Check if process started successfully
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else "Unknown error"
                logger.error(f"Docker container failed to start: {stderr}")
                raise MCPConnectionError(f"Docker container exited immediately: {stderr}")

            logger.info(f"MongoDB MCP server started successfully (PID: {process.pid})")
            self._process = process
            return process

        except FileNotFoundError:
            logger.error("Docker command not found - is Docker installed?")
            raise MCPConnectionError(
                "Docker not found. Please install Docker: https://www.docker.com/get-started"
            )
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}", exc_info=True)
            raise MCPConnectionError(f"Failed to start MCP server: {e}")

    def _validate_tool(self, tool_name: str):
        """
        Validate that the tool is read-only.

        Args:
            tool_name: Name of the MCP tool

        Raises:
            MCPPermissionError: If tool is a write operation
        """
        if tool_name in WRITE_TOOLS:
            raise MCPPermissionError(
                f"Write operation '{tool_name}' is not allowed on read-only client. "
                f"Blocked tools: {', '.join(WRITE_TOOLS)}"
            )

        if tool_name not in READ_ONLY_TOOLS:
            logger.warning(f"Unknown tool '{tool_name}' - allowing as it's not in write blacklist")

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
            MCPPermissionError: If attempting write operation
        """
        if not self._process or self._process.poll() is not None:
            logger.warning("MCP server process died, restarting...")
            self._process = self._start_mcp_server()

        # Validate tool if it's a tool call
        if method == "tools/call" and "name" in params:
            self._validate_tool(params["name"])

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

            # Read responses with timeout
            # MCP server sends notifications first, then the actual result
            start_time = time.time()
            result_response = None

            while time.time() - start_time < self.timeout:
                if self._process.stdout:
                    response_line = self._process.stdout.readline()
                    if response_line and response_line.strip():
                        try:
                            response = json.loads(response_line)

                            # Check if this is the actual result (has matching ID)
                            if "id" in response and response["id"] == request_id:
                                logger.debug(f"Received MCP response #{request_id}: {json.dumps(response, indent=2)}")
                                result_response = response
                                break

                            # Otherwise it's a notification, log and continue
                            elif "method" in response and response.get("method") == "notifications/message":
                                logger.debug(f"Notification: {response.get('params', {}).get('data', '')}")
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in response: {response_line[:100]}")

                time.sleep(0.05)

            if not result_response:
                logger.error(f"MCP request #{request_id} timed out after {self.timeout}s")
                raise MCPTimeoutError(f"Request timed out after {self.timeout}s")

            # Check for JSON-RPC error
            if "error" in result_response:
                error = result_response["error"]
                error_msg = f"MCP Error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}"
                logger.error(f"MCP server returned error: {error_msg}")
                raise MCPResponseError(error_msg)

            return result_response.get("result", {})

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            raise MCPResponseError(f"Invalid JSON response: {e}")
        except IOError as e:
            logger.error(f"IO error communicating with MCP server: {e}")
            raise MCPConnectionError(f"IO error: {e}")

    def _parse_documents(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse MCP tool response into list of documents.

        Args:
            result: Raw MCP tool response

        Returns:
            List of parsed documents
        """
        documents = []

        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")

                # MongoDB MCP wraps data in untrusted-user-data tags
                # Extract JSON from within these tags
                if "<untrusted-user-data-" in text:
                    # Find the JSON between the tags
                    # The warning message mentions the tags before the actual data, so we need
                    # to find the match that contains actual JSON (starts with [ or {)
                    import re
                    pattern = r'<untrusted-user-data-([^>]+)>\n([\[\{].*?)\n</untrusted-user-data-\1>'
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        text = match.group(2).strip()  # group(2) because group(1) is the UUID
                    else:
                        # Fallback: try to find any JSON array or object in the text
                        json_pattern = r'\[[\s\S]*?\]|\{[\s\S]*?\}'
                        json_matches = re.findall(json_pattern, text)
                        for potential_json in json_matches:
                            try:
                                json.loads(potential_json)
                                text = potential_json
                                break
                            except json.JSONDecodeError:
                                continue

                try:
                    if text.startswith("{") or text.startswith("["):
                        data = json.loads(text)

                        # Handle different response formats
                        if isinstance(data, list):
                            documents.extend(data)
                        elif isinstance(data, dict):
                            # Single document
                            if "_id" in data or "timestamp" in data:
                                documents.append(data)
                            # Array wrapped in object
                            elif "documents" in data:
                                documents.extend(data["documents"])
                            elif "results" in data:
                                documents.extend(data["results"])
                            else:
                                documents.append(data)
                    elif text.strip().startswith('"') and text.strip().endswith('"'):
                        # MongoDB MCP may return collection names as quoted strings
                        # e.g., "BTC dayli buying"\n"1h_price_data"\n"daily_price_data"
                        collection_names = [line.strip().strip('"') for line in text.strip().split('\n') if line.strip()]
                        if collection_names:
                            return collection_names

                except json.JSONDecodeError:
                    logger.warning(f"Could not parse result as JSON: {text[:100]}")

        return documents

    def is_connected(self) -> bool:
        """Check if MCP server process is running."""
        return self._process is not None and self._process.poll() is None

    def close(self):
        """
        Close the MCP client and terminate the Docker container.

        SECURITY: Guaranteed cleanup with graceful termination and forced kill fallback.
        """
        if self._process:
            logger.info("Shutting down MongoDB MCP server...")
            try:
                # Try graceful termination first (SIGTERM)
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("MongoDB MCP server shut down gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails (SIGKILL)
                logger.warning("MCP server did not terminate gracefully, forcing kill...")
                self._process.kill()
                try:
                    self._process.wait(timeout=5)
                    logger.info("MongoDB MCP server killed successfully")
                except subprocess.TimeoutExpired:
                    # Should never happen, but log if it does
                    logger.error("Container did not die after SIGKILL - this should not happen")
            except Exception as e:
                # Catch any other errors and attempt kill
                logger.error(f"Error during shutdown: {e}, forcing kill...")
                try:
                    self._process.kill()
                    self._process.wait(timeout=5)
                except Exception as kill_error:
                    logger.error(f"Kill failed: {kill_error}")
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
