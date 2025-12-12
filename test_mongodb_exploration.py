#!/usr/bin/env python3
"""
Quick MongoDB exploration script to understand the crypto cluster schema.
This helps us design the MongoDB MCP integration properly.
"""

import subprocess
import json
import time
import sys

MONGODB_URI = "***REMOVED***"

def run_mongodb_mcp_command(tool_name, params):
    """Execute a MongoDB MCP tool using Docker."""
    print(f"\n{'='*60}")
    print(f"Executing: {tool_name}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print(f"{'='*60}\n")

    # Build MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }

    # Run Docker MCP server
    cmd = [
        "docker", "run", "-i", "--rm",
        "-e", "MDB_MCP_CONNECTION_STRING",
        "mcp/mongodb"
    ]

    env = {"MDB_MCP_CONNECTION_STRING": MONGODB_URI}

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**subprocess.os.environ, **env},
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Send request
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=30)

        if stderr:
            print(f"STDERR: {stderr}")

        # Parse response
        if stdout:
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        response = json.loads(line)
                        if "result" in response:
                            return response["result"]
                        elif "error" in response:
                            print(f"ERROR: {response['error']}")
                            return None
                    except json.JSONDecodeError:
                        print(f"Non-JSON line: {line}")

        return None

    except subprocess.TimeoutExpired:
        process.kill()
        print("Command timed out!")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    print("MongoDB Crypto Cluster Exploration")
    print("="*60)

    # 1. List all databases
    print("\n1. Listing databases...")
    result = run_mongodb_mcp_command("list-databases", {})
    if result:
        print(json.dumps(result, indent=2))

    # 2. List collections in btc_data
    print("\n2. Listing collections in 'btc_data' database...")
    result = run_mongodb_mcp_command("list-collections", {"database": "btc_data"})
    if result:
        print(json.dumps(result, indent=2))

        # Extract collection names
        collections = []
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    try:
                        data = json.loads(text)
                        if isinstance(data, list):
                            collections = [col.get("name") for col in data if col.get("name")]
                        elif isinstance(data, dict) and "collections" in data:
                            collections = [col.get("name") for col in data["collections"] if col.get("name")]
                    except:
                        pass

        print(f"\nFound collections: {collections}")

        # 3. Explore each collection
        for collection_name in collections[:5]:  # Limit to first 5 collections
            print(f"\n3. Exploring collection: {collection_name}")

            # Get schema
            print(f"\n3a. Schema for {collection_name}:")
            result = run_mongodb_mcp_command("collection-schema", {
                "database": "btc_data",
                "collection": collection_name,
                "sampleSize": 10
            })
            if result:
                print(json.dumps(result, indent=2))

            # Get sample documents
            print(f"\n3b. Sample documents from {collection_name}:")
            result = run_mongodb_mcp_command("find", {
                "database": "btc_data",
                "collection": collection_name,
                "limit": 3
            })
            if result:
                print(json.dumps(result, indent=2))

            # Get document count
            print(f"\n3c. Document count in {collection_name}:")
            result = run_mongodb_mcp_command("count", {
                "database": "btc_data",
                "collection": collection_name
            })
            if result:
                print(json.dumps(result, indent=2))

            time.sleep(1)  # Avoid overwhelming the server


if __name__ == "__main__":
    main()
