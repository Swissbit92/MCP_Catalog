# src/coordinator/jupiter/jupiter_mcp_client.py
# Low-level Docker MCP server management and JSON-RPC 2.0 protocol communication
# Handles subprocess management, request/response protocol, and connection lifecycle
#
# SECURITY NOTE: Private key is injected into Docker env var (SOLANA_PRIVATE_KEY).
# It is never written to disk or logged. The container process is restarted whenever
# set_private_key() is called, flushing the old key from container memory.

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# All tools that the Jupiter MCP server exposes.
# Unlike MongoDB (read-only), Jupiter allows ALL tools — execution is gated
# at the coordinator layer via HITL confirmation and strategy guardrails.
JUPITER_TOOLS = {
    "wallet_get_balance",
    "wallet_get_quote",
    "wallet_execute_swap",
    "wallet_create_limit_order",
    "wallet_create_dca_order",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class JupiterMCPError(Exception):
    """Base exception for Jupiter MCP client errors."""


class JupiterConnectionError(JupiterMCPError):
    """Raised when unable to connect to the Jupiter MCP server."""


class JupiterTimeoutError(JupiterMCPError):
    """Raised when a Jupiter MCP operation times out."""


class JupiterResponseError(JupiterMCPError):
    """Raised when the Jupiter MCP server returns an error response."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class JupiterDockerClient:
    """Long-running Docker STDIO client for Jupiter MCP server.

    Mirrors MongoDBDockerClient pattern exactly.

    Manages:
    - Docker container lifecycle (start, stop, cleanup)
    - JSON-RPC 2.0 protocol communication over stdin/stdout
    - Request/response handling with timeout
    - Connection health monitoring
    - Private key injection (never stored plaintext on disk)

    SECURITY:
    - The process is NOT started on __init__; call set_private_key() first.
    - SOLANA_PRIVATE_KEY is passed exclusively via Docker -e flag (env var).
    - Private key is never logged or written to any file.
    - Calling set_private_key() with a new key terminates the old container
      immediately, ensuring the old key cannot linger in container memory.
    """

    def __init__(
        self,
        image: str = "localhost/jupiter-mcp:latest",
        solana_rpc_url: str = "https://api.devnet.solana.com",
        timeout: int = 30,
    ):
        """Initialize Jupiter Docker MCP client.

        Args:
            image: Docker image for Jupiter MCP server
            solana_rpc_url: Solana RPC endpoint URL
            timeout: Timeout in seconds for MCP operations

        Note:
            The Docker process is NOT started here. Call set_private_key()
            to inject the wallet key and start the server.
        """
        # Initialize process first to avoid AttributeError in __del__
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()

        self.image = image
        self.solana_rpc_url = solana_rpc_url
        self.timeout = timeout
        self._private_key: Optional[str] = None  # Set via set_private_key(); never logged

        logger.info(
            "Initialized JupiterDockerClient: "
            f"image={image}, rpc_url={solana_rpc_url}, timeout={timeout}s"
        )
        # Do NOT auto-start — process starts only when private key is set

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def set_private_key(self, private_key_b58: str) -> None:
        """Set the private key and (re)start the MCP server process.

        Terminates any running container first to ensure the old key is
        flushed from container memory before the new key is injected.

        Args:
            private_key_b58: Base58-encoded Solana private key (decrypted in-memory)

        Note:
            Never log or persist the value of private_key_b58.
        """
        self._private_key = private_key_b58
        # Terminate existing container so old key cannot linger
        if self._process and self._process.poll() is None:
            self.close()
        self._start_mcp_server()

    def is_ready(self) -> bool:
        """Return True if the process is running AND a private key is set."""
        return self._private_key is not None and self.is_connected()

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Jupiter MCP tool. Returns the raw parsed result dict.

        Args:
            tool_name: Name of the Jupiter MCP tool (e.g. 'wallet_get_balance')
            arguments: Tool-specific arguments dict

        Returns:
            Parsed result dict from the MCP server

        Raises:
            JupiterConnectionError: If wallet is not unlocked or process is down
            JupiterTimeoutError: If the request times out
            JupiterResponseError: If the server returns a JSON-RPC error
        """
        if not self.is_ready():
            raise JupiterConnectionError(
                "Jupiter MCP server is not ready. "
                "Call set_private_key() to unlock the wallet first."
            )
        return self._send_request("tools/call", {"name": tool_name, "arguments": arguments})

    def is_connected(self) -> bool:
        """Check if the MCP server process is currently running."""
        return self._process is not None and self._process.poll() is None

    def close(self) -> None:
        """Close the MCP client and terminate the Docker container.

        Graceful termination (SIGTERM) with forced kill fallback (SIGKILL).
        The private key stored in the container's environment is destroyed
        when the container exits.
        """
        if self._process:
            logger.info("Shutting down Jupiter MCP server...")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("Jupiter MCP server shut down gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("MCP server did not terminate gracefully, forcing kill...")
                self._process.kill()
                try:
                    self._process.wait(timeout=5)
                    logger.info("Jupiter MCP server killed successfully")
                except subprocess.TimeoutExpired:
                    logger.error("Container did not die after SIGKILL — this should not happen")
            except Exception as exc:
                logger.error(f"Error during shutdown: {exc}, forcing kill...")
                try:
                    self._process.kill()
                    self._process.wait(timeout=5)
                except Exception as kill_err:
                    logger.error(f"Kill failed: {kill_err}")
            finally:
                self._process = None

    def __enter__(self) -> "JupiterDockerClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_next_request_id(self) -> int:
        """Generate next JSON-RPC request ID (thread-safe)."""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _start_mcp_server(self) -> subprocess.Popen:
        """Start the Docker MCP server process and keep it alive.

        SECURITY: Resource limits applied to prevent DoS attacks:
        - Memory: 256MB max (lighter than MongoDB; swaps don't need heavy query processing)
        - CPU: 0.5 cores max
        - PIDs: 50 max (prevents fork bombs)
        - Labels: Enables orphan container detection

        The SOLANA_PRIVATE_KEY is passed via -e flag only (not in the command
        arguments list that would appear in process listings on some systems).

        Returns:
            subprocess.Popen: The running MCP server process

        Raises:
            JupiterConnectionError: If unable to start the Docker container
        """
        if self._private_key is None:
            raise JupiterConnectionError(
                "Cannot start Jupiter MCP server: private key not set. "
                "Call set_private_key() first."
            )

        logger.info("Starting Jupiter MCP Docker container...")

        cmd = [
            "docker", "run",
            "-i",                          # Interactive mode (keep stdin open)
            "--rm",                        # Remove container after exit
            "--memory=256m",               # Memory limit for swap operations
            "--cpus=0.5",                  # Half-core; signing is lightweight
            "--pids-limit=50",             # Prevent fork bombs
            "--label=mcp.coordinator.ephemeral=false",  # Long-running
            "--label=mcp.coordinator.service=jupiter",
            "-e", "SOLANA_PRIVATE_KEY",    # Injected from env — not echoed in cmd list
            "-e", "SOLANA_RPC_URL",
            self.image,
        ]

        # Build env with the private key — never log env dict
        env = os.environ.copy()
        env["SOLANA_PRIVATE_KEY"] = self._private_key
        env["SOLANA_RPC_URL"] = self.solana_rpc_url

        try:
            logger.debug(f"Docker command: docker run -i --rm ... {self.image}")
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # Line buffered
            )

            # Give Docker a moment to initialize
            time.sleep(2)

            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else "Unknown error"
                logger.error(f"Docker container failed to start: {stderr}")
                raise JupiterConnectionError(f"Docker container exited immediately: {stderr}")

            logger.info(f"Jupiter MCP server started successfully (PID: {process.pid})")
            self._process = process
            return process

        except FileNotFoundError:
            logger.error("Docker command not found — is Docker installed?")
            raise JupiterConnectionError(
                "Docker not found. Please install Docker: https://www.docker.com/get-started"
            )
        except Exception as exc:
            logger.error(f"Failed to start Jupiter MCP server: {exc}", exc_info=True)
            raise JupiterConnectionError(f"Failed to start MCP server: {exc}")

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request to the MCP server.

        Mirrors MongoDBDockerClient._send_request exactly:
        - Auto-restarts the process if it has died
        - Skips notification messages (no matching id)
        - Raises typed exceptions for timeout, connection, and response errors

        Args:
            method: The MCP method name (e.g. 'tools/call')
            params: Method parameters dict

        Returns:
            Parsed result dict from the JSON-RPC response

        Raises:
            JupiterConnectionError: If not connected
            JupiterTimeoutError: If request times out
            JupiterResponseError: If server returns a JSON-RPC error
        """
        if not self._process or self._process.poll() is not None:
            logger.warning("Jupiter MCP server process died, restarting...")
            self._process = self._start_mcp_server()

        request_id = self._get_next_request_id()

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        logger.debug(f"Sending Jupiter MCP request #{request_id}: method={method}")

        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json)
            self._process.stdin.flush()

            # Read responses — MCP server may send notifications before the result
            start_time = time.time()
            result_response = None

            while time.time() - start_time < self.timeout:
                if self._process.stdout:
                    response_line = self._process.stdout.readline()
                    if response_line and response_line.strip():
                        try:
                            response = json.loads(response_line)

                            if "id" in response and response["id"] == request_id:
                                logger.debug(f"Received Jupiter MCP response #{request_id}")
                                result_response = response
                                break

                            elif "method" in response and response.get("method") == "notifications/message":
                                logger.debug(
                                    f"Jupiter MCP notification: "
                                    f"{response.get('params', {}).get('data', '')}"
                                )

                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in Jupiter MCP response: {response_line[:100]}")

                time.sleep(0.05)

            if not result_response:
                logger.error(f"Jupiter MCP request #{request_id} timed out after {self.timeout}s")
                raise JupiterTimeoutError(f"Request timed out after {self.timeout}s")

            if "error" in result_response:
                error = result_response["error"]
                error_msg = (
                    f"Jupiter MCP Error {error.get('code', 'unknown')}: "
                    f"{error.get('message', 'Unknown error')}"
                )
                logger.error(f"Jupiter MCP server returned error: {error_msg}")
                raise JupiterResponseError(error_msg)

            return result_response.get("result", {})

        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse Jupiter MCP response: {exc}")
            raise JupiterResponseError(f"Invalid JSON response: {exc}")
        except IOError as exc:
            logger.error(f"IO error communicating with Jupiter MCP server: {exc}")
            raise JupiterConnectionError(f"IO error: {exc}")

    def _parse_tool_response(self, result: Dict[str, Any]) -> Any:
        """Parse an MCP tool response, extracting and JSON-decoding content[0].text.

        This mirrors MongoDBDockerClient._parse_documents but returns a single
        parsed value (dict or list) rather than a list of documents. The Jupiter
        MCP server is expected to return a single JSON object per tool call.

        Args:
            result: Raw MCP tool response dict

        Returns:
            Parsed Python object (dict or list) from the tool response text

        Raises:
            JupiterResponseError: If content cannot be parsed as JSON
        """
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning(f"Jupiter MCP response content is not JSON: {text[:200]}")
                        # Return raw text wrapped in dict so callers always get a dict
                        return {"raw": text}

        logger.warning("Jupiter MCP response had no parseable text content")
        return {}
