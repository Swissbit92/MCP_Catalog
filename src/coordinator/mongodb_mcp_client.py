# src/coordinator/mongodb_mcp_client.py
# Backward compatibility wrapper - core logic in mongodb/ package
# Re-exports all classes, functions, and constants for existing imports

from __future__ import annotations

import os
import logging

# Re-export everything from mongodb package
from .mongodb import (
    # Core client and factory
    MongoDBMCPClient,
    get_mongodb_client,
    # Low-level components
    MongoDBDockerClient,
    MongoDBOperations,
    # Exceptions
    MCPError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPResponseError,
    MCPPermissionError,
    # Constants
    READ_ONLY_TOOLS,
    WRITE_TOOLS,
)

# Configure logging
logger = logging.getLogger(__name__)

# Explicit exports (same as mongodb/__init__.py)
__all__ = [
    "MongoDBMCPClient",
    "get_mongodb_client",
    "MongoDBDockerClient",
    "MongoDBOperations",
    "MCPError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPResponseError",
    "MCPPermissionError",
    "READ_ONLY_TOOLS",
    "WRITE_TOOLS",
]


# Example usage / test code
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
