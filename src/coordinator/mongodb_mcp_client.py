# src/coordinator/mongodb_mcp_client.py
# MongoDB MCP Client for stdio-based communication with Docker MCP server
# Implements JSON-RPC 2.0 protocol for Model Context Protocol (MCP)
# READ-ONLY client - blocks all write operations

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


class MongoDBMCPClient:
    """
    Client for communicating with MongoDB MCP server via stdio.

    Uses Docker to run the MCP server as a subprocess and communicates
    via JSON-RPC 2.0 protocol over stdin/stdout.

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
        Initialize MongoDB MCP client.

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
            "Initialized MongoDBMCPClient: "
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

    def find(
        self,
        database: str,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = None,
        limit: Optional[int] = None,
        response_bytes_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run a find query against a MongoDB collection.

        Args:
            database: Database name
            collection: Collection name
            filter: Query filter (MongoDB query syntax)
            projection: Fields to include/exclude
            sort: Sort order (e.g., {"timestamp": -1})
            limit: Maximum number of documents to return
            response_bytes_limit: Max response size in bytes

        Returns:
            List of matching documents
        """
        params = {
            "name": "find",
            "arguments": {
                "database": database,
                "collection": collection
            }
        }

        if filter:
            params["arguments"]["filter"] = filter
        if projection:
            params["arguments"]["projection"] = projection
        if sort:
            params["arguments"]["sort"] = sort
        if limit:
            params["arguments"]["limit"] = limit
        if response_bytes_limit:
            params["arguments"]["responseBytesLimit"] = response_bytes_limit
        elif self.max_response_bytes:
            params["arguments"]["responseBytesLimit"] = self.max_response_bytes

        logger.info(f"MongoDB find: db={database}, collection={collection}, limit={limit}")
        result = self._send_request("tools/call", params)
        return self._parse_documents(result)

    def aggregate(
        self,
        database: str,
        collection: str,
        pipeline: List[Dict[str, Any]],
        response_bytes_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run an aggregation pipeline against a MongoDB collection.

        Args:
            database: Database name
            collection: Collection name
            pipeline: Aggregation pipeline stages
            response_bytes_limit: Max response size in bytes

        Returns:
            List of aggregation results
        """
        params = {
            "name": "aggregate",
            "arguments": {
                "database": database,
                "collection": collection,
                "pipeline": pipeline
            }
        }

        if response_bytes_limit:
            params["arguments"]["responseBytesLimit"] = response_bytes_limit
        elif self.max_response_bytes:
            params["arguments"]["responseBytesLimit"] = self.max_response_bytes

        logger.info(f"MongoDB aggregate: db={database}, collection={collection}, stages={len(pipeline)}")
        result = self._send_request("tools/call", params)
        return self._parse_documents(result)

    def count(
        self,
        database: str,
        collection: str,
        query: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count documents in a collection.

        Args:
            database: Database name
            collection: Collection name
            query: Optional filter query

        Returns:
            Number of matching documents
        """
        params = {
            "name": "count",
            "arguments": {
                "database": database,
                "collection": collection
            }
        }

        if query:
            params["arguments"]["query"] = query

        logger.info(f"MongoDB count: db={database}, collection={collection}")
        result = self._send_request("tools/call", params)

        # Parse count from response
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")
                try:
                    data = json.loads(text)
                    if "count" in data:
                        return int(data["count"])
                except:
                    pass

        return 0

    def list_collections(self, database: str) -> List[str]:
        """
        List all collections in a database.

        Args:
            database: Database name

        Returns:
            List of collection names
        """
        params = {
            "name": "list-collections",
            "arguments": {
                "database": database
            }
        }

        logger.info(f"MongoDB list-collections: db={database}")
        result = self._send_request("tools/call", params)

        # Parse collection names - MongoDB MCP returns them as quoted strings in untrusted-user-data tags
        import re
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")

                # Extract from untrusted-user-data tags
                if "<untrusted-user-data-" in text:
                    pattern = r'<untrusted-user-data-[^>]+>(.*?)</untrusted-user-data-[^>]+>'
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        extracted_text = match.group(1).strip()

                        # Parse collection names (quoted strings, one per line)
                        if extracted_text.startswith('"'):
                            collection_names = [line.strip().strip('"') for line in extracted_text.split('\n') if line.strip()]
                            return collection_names

        return []

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
                    # Use backreference to match the same UUID in opening and closing tags
                    import re
                    pattern = r'<untrusted-user-data-([^>]+)>(.*?)</untrusted-user-data-\1>'
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        text = match.group(2).strip()  # group(2) because group(1) is the UUID

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
        """
        if self._process:
            logger.info("Shutting down MongoDB MCP server...")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("MongoDB MCP server shut down successfully")
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


# Example usage
if __name__ == "__main__":
    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        print("Testing MongoDB MCP Client...")
        print("=" * 60)

        with get_mongodb_client() as client:
            # Test connection
            print(f"\n[OK] Connected: {client.is_connected()}")

            # Test list collections
            print("\nListing collections in 'btc_data'...")
            collections = client.list_collections("btc_data")
            print(f"Found {len(collections)} collections: {collections}")

            # Test find query
            print("\nQuerying latest Bitcoin price from 1h_price_data...")
            results = client.find(
                database="btc_data",
                collection="1h_price_data",
                sort={"timestamp": -1},
                limit=1
            )

            if results:
                latest = results[0]
                print(f"\nLatest price data:")
                print(f"  Timestamp: {latest.get('timestamp')}")
                print(f"  Close: ${latest.get('Close'):,.2f}")
                print(f"  RSI: {latest.get('RSI'):.2f}")
                print(f"  MACD: {latest.get('MACD_Line'):.2f}")

            # Test write protection
            print("\nTesting write protection...")
            try:
                client._send_request("tools/call", {
                    "name": "insert-many",
                    "arguments": {"database": "btc_data", "collection": "test"}
                })
                print("[ERROR] SECURITY ISSUE: Write operation succeeded!")
            except MCPPermissionError as e:
                print(f"[OK] Write blocked: {e}")

        print("\n" + "=" * 60)
        print("[OK] Test completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        logger.error("Test failed", exc_info=True)
