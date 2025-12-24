# src/coordinator/mongodb/operations.py
# High-level MongoDB operations API
# Provides semantic MongoDB methods built on top of the Docker MCP client

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any
import re

from .docker_client import MongoDBDockerClient

# Configure logging
logger = logging.getLogger(__name__)


class MongoDBOperations:
    """
    High-level MongoDB operations using MCP protocol.

    Provides semantic MongoDB methods (find, aggregate, count, list_collections)
    that abstract the underlying JSON-RPC communication.

    Depends on MongoDBDockerClient for low-level protocol handling.
    """

    def __init__(self, docker_client: MongoDBDockerClient):
        """
        Initialize MongoDB operations.

        Args:
            docker_client: Initialized MongoDBDockerClient instance
        """
        self.docker_client = docker_client

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
        elif self.docker_client.max_response_bytes:
            params["arguments"]["responseBytesLimit"] = self.docker_client.max_response_bytes

        logger.info(f"MongoDB find: db={database}, collection={collection}, limit={limit}")
        result = self.docker_client._send_request("tools/call", params)
        return self.docker_client._parse_documents(result)

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
        elif self.docker_client.max_response_bytes:
            params["arguments"]["responseBytesLimit"] = self.docker_client.max_response_bytes

        logger.info(f"MongoDB aggregate: db={database}, collection={collection}, stages={len(pipeline)}")
        result = self.docker_client._send_request("tools/call", params)
        return self.docker_client._parse_documents(result)

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
        result = self.docker_client._send_request("tools/call", params)

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
        result = self.docker_client._send_request("tools/call", params)

        # Parse collection names - MongoDB MCP returns them as quoted strings in untrusted-user-data tags
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
