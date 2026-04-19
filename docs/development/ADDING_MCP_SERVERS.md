---
title: Adding MCP Servers to MCP Coordinator
status: active
created: 2026-04-03
last_reviewed_on: 2026-04-19
review_in: 6 months
applies_to: MCP_Catalog
---

# Adding MCP Servers to MCP Coordinator

**Last Updated:** February 21, 2026

This guide explains how to integrate new Model Context Protocol (MCP) servers into the MCP Coordinator project. We document the two proven patterns and provide step-by-step instructions for adding your own MCP servers.

---

## Table of Contents

- [Overview](#overview)
- [MCP Architecture Patterns](#mcp-architecture-patterns)
  - [Pattern 1: Ephemeral STDIO (Brave Search)](#pattern-1-ephemeral-stdio-brave-search)
  - [Pattern 2: Long-Running STDIO (MongoDB)](#pattern-2-long-running-stdio-mongodb)
- [Choosing a Pattern](#choosing-a-pattern)
- [Adding a New MCP Server](#adding-a-new-mcp-server)
- [Step-by-Step Examples](#step-by-step-examples)
- [Testing Your MCP Integration](#testing-your-mcp-integration)
- [Troubleshooting](#troubleshooting)
- [Celestial Order & Per-Persona MCP Access](#celestial-order--per-persona-mcp-access)
- [Best Practices](#best-practices)

---

## Overview

MCP (Model Context Protocol) is a standardized protocol that enables AI assistants to interact with external data sources and services. The MCP Coordinator uses **STDIO transport** with **Docker containers** to integrate MCP servers.

### Why Docker + STDIO?

- **Isolation**: Each MCP server runs in its own container with complete dependency isolation
- **Portability**: Works identically on Windows, macOS, and Linux
- **Scalability**: Universal pattern for ANY MCP server (Brave, MongoDB, Neo4j, Google Calendar, etc.)
- **Security**: Containers provide sandboxing and resource limits
- **Container Orchestration**: Backend mounts Docker socket to spawn containers on-demand

### Architecture Overview

```
Backend Container (mounts /var/run/docker.sock)
    │
    ├─> spawns: docker run -i --rm docker.io/mcp/brave-search
    │   (ephemeral: lives 2-3 seconds, processes request, dies)
    │
    ├─> spawns: docker run -i --rm docker.io/mcp/mongodb
    │   (long-running: stays alive for multiple requests)
    │
    └─> spawns: docker run -i --rm docker.io/mcp/[any-mcp-server]
        (universal pattern for all MCP servers)
```

**Key Components:**
- **Docker Socket**: `/var/run/docker.sock` mounted to backend enables container spawning
- **STDIO Transport**: Communication via stdin/stdout pipes using JSON-RPC 2.0
- **MCP Images**: Official Docker images from `docker.io/mcp/*` or custom builds

---

## MCP Architecture Patterns

We've validated two distinct patterns for MCP integration. Your choice depends on the MCP server's behavior.

### Pattern 1: Ephemeral STDIO (Brave Search)

**Use When:** The MCP server exits immediately after responding to a request.

**Characteristics:**
- Spawns `docker run -i --rm` per request
- Container lives 2-3 seconds
- Processes single request via stdin
- Returns result via stdout
- Dies automatically after response
- **No long-running process**

**Example MCP Servers:**
- Brave Search
- Most web APIs
- Stateless data lookups

**Implementation:**

```python
# src/coordinator/mcp_client_stdio.py (Brave Search pattern)

def _spawn_mcp_container(self, request: Dict[str, Any]) -> str:
    """
    Spawn ephemeral MCP container to process a single request.
    Container exits after sending response.
    """
    cmd = [
        "docker", "run",
        "-i",                          # Interactive (keep stdin open)
        "--rm",                        # Auto-remove after exit
        "-e", "BRAVE_API_KEY",         # Pass env var
        self.image                     # Docker image (e.g., mcp/brave-search)
    ]

    env = os.environ.copy()
    env["BRAVE_API_KEY"] = self.api_key

    # Convert request to JSON
    stdin_data = json.dumps(request) + "\n"

    # Spawn container
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=0
    )

    # Send request to stdin
    process.stdin.write(stdin_data)
    process.stdin.close()

    # Read response from stdout with timeout
    stdout_data = []
    start_time = time.time()

    while time.time() - start_time < self.timeout:
        line = process.stdout.readline()
        if line:
            stdout_data.append(line)
            # Look for response with matching ID
            if '"id":1' in line or '"id": 1' in line:
                # Give a moment for any trailing data
                time.sleep(0.1)
                # Read remaining lines
                while True:
                    remaining = process.stdout.readline()
                    if not remaining:
                        break
                    stdout_data.append(remaining)
                break

    # Container exits automatically after response
    process.wait(timeout=2)

    return ''.join(stdout_data)
```

**Key Points:**
- Container **exits on its own** after sending response
- No manual termination needed
- Timeout is for safety only
- Perfect for stateless operations

---

### Pattern 2: Long-Running STDIO (MongoDB)

**Use When:** The MCP server expects to stay alive across multiple requests.

**Characteristics:**
- Spawns `docker run -i --rm` **once**
- Container stays alive indefinitely
- Processes **multiple requests** via same stdin
- Returns results via stdout
- **Must be manually terminated** when done
- Maintains internal state

**Example MCP Servers:**
- MongoDB (database connections)
- Database clients (Postgres, Neo4j)
- Services with initialization overhead
- Stateful integrations

**Implementation:**

```python
# src/coordinator/mongodb/docker_client.py (MongoDB pattern)

def _start_mcp_server(self) -> subprocess.Popen:
    """
    Start long-running MCP server process.
    Container stays alive for multiple requests.
    """
    cmd = [
        "docker", "run",
        "-i",                          # Interactive mode (keep stdin open)
        "--rm",                        # Remove after exit
        "-e", "MDB_MCP_CONNECTION_STRING",
        "mcp/mongodb"
    ]

    env = os.environ.copy()
    env["MDB_MCP_CONNECTION_STRING"] = self.connection_uri

    # Start container (stays alive)
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

    # Store process reference for later use
    self._process = process
    return process

def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send request to long-running MCP server.
    Reuses same container for multiple calls.
    """
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    # Send to existing container
    self._process.stdin.write(json.dumps(request) + "\n")
    self._process.stdin.flush()

    # Read response (container stays alive)
    response_line = self._process.stdout.readline()
    return json.loads(response_line)

def close(self):
    """
    Terminate long-running container when done.
    """
    if self._process:
        self._process.terminate()
        self._process.wait(timeout=5)
```

**Key Points:**
- Container **does NOT exit** after response
- Reuse same process for multiple calls
- Must call `close()` to terminate
- More efficient for repeated operations

---

## Choosing a Pattern

Use this decision tree:

```
Does the MCP server exit after responding to a request?
├─ YES → Use Ephemeral STDIO Pattern (Pattern 1)
│         Examples: Brave Search, web APIs, stateless lookups
│
└─ NO → Use Long-Running STDIO Pattern (Pattern 2)
          Examples: MongoDB, database clients, stateful services
```

**How to Test:**
```bash
# Send a test request to the MCP server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  docker run -i --rm -e API_KEY=xxx mcp/your-server

# Does the container exit immediately after printing response?
# YES → Ephemeral pattern
# NO → Long-running pattern
```

---

## Adding a New MCP Server

Follow these steps to integrate a new MCP server into the MCP Coordinator.

### Step 1: Determine the Pattern

Test the MCP server to identify which pattern it follows:

```bash
# Test if container exits after response
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  docker run -i --rm -e YOUR_ENV_VAR=xxx mcp/your-server

# Observe:
# - Container exits immediately? → Ephemeral STDIO
# - Container hangs/waits? → Long-Running STDIO
```

### Step 2: Create MCP Client Module

Create a new directory: `src/coordinator/your_mcp_name/`

```
src/coordinator/your_mcp_name/
├── __init__.py           # Public API exports
├── docker_client.py      # Low-level Docker + STDIO client
└── operations.py         # High-level operations/tools
```

### Step 3: Implement Docker Client

**For Ephemeral Pattern:**

```python
# src/coordinator/your_mcp_name/docker_client.py

import subprocess
import json
import time
from typing import Dict, Any

class YourMCPClientStdio:
    """
    Ephemeral STDIO MCP client for [Your Service].
    Spawns docker run -i --rm on each request.
    """

    def __init__(
        self,
        api_key: str,
        image: str = "mcp/your-service",
        timeout: int = 30
    ):
        self.api_key = api_key
        self.image = image
        self.timeout = timeout

    def _spawn_mcp_container(self, request: Dict[str, Any]) -> str:
        """Spawn ephemeral container for single request."""
        cmd = [
            "docker", "run", "-i", "--rm",
            "-e", "YOUR_API_KEY",
            self.image
        ]

        env = os.environ.copy()
        env["YOUR_API_KEY"] = self.api_key

        stdin_data = json.dumps(request) + "\n"

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=0
        )

        # Send request
        process.stdin.write(stdin_data)
        process.stdin.close()

        # Read response with timeout
        stdout_data = []
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            line = process.stdout.readline()
            if line:
                stdout_data.append(line)
                if '"id":1' in line:
                    time.sleep(0.1)
                    while True:
                        remaining = process.stdout.readline()
                        if not remaining:
                            break
                        stdout_data.append(remaining)
                    break

        process.wait(timeout=2)
        return ''.join(stdout_data)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool (spawns new container each time)."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response_text = self._spawn_mcp_container(request)
        return json.loads(response_text)
```

**For Long-Running Pattern:**

```python
# src/coordinator/your_mcp_name/docker_client.py

import subprocess
import json
import time
from typing import Dict, Any, Optional

class YourMCPClientLongRunning:
    """
    Long-running STDIO MCP client for [Your Service].
    Starts container once, reuses for multiple requests.
    """

    def __init__(
        self,
        connection_uri: str,
        image: str = "mcp/your-service",
        timeout: int = 30
    ):
        self.connection_uri = connection_uri
        self.image = image
        self.timeout = timeout
        self._process: Optional[subprocess.Popen] = None

    def _start_mcp_server(self) -> subprocess.Popen:
        """Start long-running MCP server."""
        cmd = [
            "docker", "run", "-i", "--rm",
            "-e", "YOUR_CONNECTION_STRING",
            self.image
        ]

        env = os.environ.copy()
        env["YOUR_CONNECTION_STRING"] = self.connection_uri

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        time.sleep(2)  # Wait for initialization
        self._process = process
        return process

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool (reuses existing container)."""
        if not self._process:
            self._start_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Send to existing container
        self._process.stdin.write(json.dumps(request) + "\n")
        self._process.stdin.flush()

        # Read response
        response_line = self._process.stdout.readline()
        return json.loads(response_line)

    def close(self):
        """Terminate long-running container."""
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### Step 4: Implement Operations Layer

```python
# src/coordinator/your_mcp_name/operations.py

from typing import Dict, Any, List

class YourMCPOperations:
    """
    High-level operations for [Your Service] MCP.
    """

    def __init__(self, docker_client):
        self.docker_client = docker_client

    def your_operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        High-level operation that uses MCP tool.

        Args:
            param1: Description of param1
            param2: Description of param2

        Returns:
            Dict with operation results
        """
        arguments = {
            "param1": param1,
            "param2": param2
        }

        result = self.docker_client.call_tool("your-tool-name", arguments)
        return result
```

### Step 5: Create Public API

```python
# src/coordinator/your_mcp_name/__init__.py

from __future__ import annotations

import os
from typing import Optional

from .docker_client import YourMCPClientStdio  # or YourMCPClientLongRunning
from .operations import YourMCPOperations

class YourMCPClient(YourMCPClientStdio, YourMCPOperations):
    """
    Combined MCP client with Docker management and high-level operations.

    Usage:
        client = YourMCPClient(api_key="xxx")
        result = client.your_operation(param1="value", param2=123)
        client.close()  # Only for long-running pattern

    Or with context manager:
        with YourMCPClient(api_key="xxx") as client:
            result = client.your_operation(...)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        # Initialize Docker client
        YourMCPClientStdio.__init__(
            self,
            api_key=api_key or os.getenv("YOUR_API_KEY"),
            timeout=timeout
        )

        # Initialize operations (uses self as docker_client)
        YourMCPOperations.__init__(self, docker_client=self)

# Factory function
def get_your_mcp_client() -> YourMCPClient:
    """Factory function with environment configuration."""
    return YourMCPClient(
        api_key=os.getenv("YOUR_API_KEY"),
        timeout=int(os.getenv("YOUR_MCP_TIMEOUT", "30"))
    )

# Exports
__all__ = [
    "YourMCPClient",
    "get_your_mcp_client",
    "YourMCPClientStdio",
    "YourMCPOperations",
]
```

### Step 6: Configure Environment Variables

Add to `.env` and `.env.docker`:

```bash
# Your MCP Configuration
YOUR_API_KEY=your_api_key_here
YOUR_MCP_IMAGE=docker.io/mcp/your-service
YOUR_MCP_TIMEOUT=30
YOUR_ENABLED_RARITIES=warden,archon  # Fallback rarity-based gating (used when mcp_access not set on persona)
```

Update `src/coordinator/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Your MCP Settings
    your_api_key: Optional[str] = Field(None, env="YOUR_API_KEY")
    your_mcp_image: str = Field("docker.io/mcp/your-service", env="YOUR_MCP_IMAGE")
    your_mcp_timeout: int = Field(30, env="YOUR_MCP_TIMEOUT")
    your_enabled_rarities: str = Field("warden,archon", env="YOUR_ENABLED_RARITIES")
```

### Step 7: Register in Startup

Update `src/coordinator/startup.py`:

```python
from src.coordinator.your_mcp_name import get_your_mcp_client

async def startup_initialization():
    # ... existing initialization ...

    # Initialize Your MCP client
    if settings.your_api_key:
        logger.info("✅ Your MCP enabled")
        app.state.your_mcp_client = get_your_mcp_client()
    else:
        logger.info("⚠️ Your MCP disabled (no API key)")
        app.state.your_mcp_client = None
```

### Step 8: Create Tool Definitions

Update `src/coordinator/tool_definitions.py`:

```python
YOUR_MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "your_tool_name",
            "description": "Description of what this tool does",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "Description of param2"
                    }
                },
                "required": ["param1"]
            }
        }
    }
]

def get_tools_for_persona(
    persona_key: str,
    rarity: str,
    mcp_access: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get available tools based on per-persona mcp_access field (primary)
    or celestial order / rarity-based env var fallback.

    Args:
        persona_key: The persona's unique key (e.g. "nephilim_eeva")
        rarity: The persona's celestial order tier ("wanderer", "sage", "warden", "archon")
        mcp_access: Optional list of MCP sources from the persona's mcp_access field.
                    When present, takes priority over rarity-based gating.
                    Example: ["brave", "mongodb"]
    """
    tools = []

    # ... existing tool logic ...

    # Your MCP tools — per-persona access (primary) with rarity-based fallback
    if mcp_access is not None:
        # Per-persona field takes priority (set in persona JSON as "mcp_access": ["your_mcp"])
        if "your_mcp" in mcp_access:
            tools.extend(YOUR_MCP_TOOLS)
    else:
        # Fallback: celestial-order-based gating via env var
        your_enabled_rarities = os.getenv("YOUR_ENABLED_RARITIES", "warden,archon").split(",")
        if rarity.lower() in your_enabled_rarities:
            tools.extend(YOUR_MCP_TOOLS)

    return tools
```

### Step 9: Create Tool Handlers

Create `src/coordinator/services/your_mcp_handlers.py`:

```python
from typing import Dict, Any
from src.coordinator.your_mcp_name import YourMCPClient

async def handle_your_tool(
    arguments: Dict[str, Any],
    your_mcp_client: YourMCPClient
) -> Dict[str, Any]:
    """
    Handle your_tool_name function call.

    Args:
        arguments: Tool arguments from LLM
        your_mcp_client: Initialized MCP client

    Returns:
        Dict with tool results and metadata
    """
    try:
        result = your_mcp_client.your_operation(
            param1=arguments.get("param1"),
            param2=arguments.get("param2", 0)
        )

        return {
            "success": True,
            "data": result,
            "metadata": {
                "source": "your_mcp",
                "tool": "your_tool_name"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metadata": {
                "source": "your_mcp",
                "tool": "your_tool_name"
            }
        }
```

### Step 10: Integrate into Chat Route

Update `src/coordinator/routes/chat.py`:

```python
from src.coordinator.services.your_mcp_handlers import handle_your_tool

# In handle_function_call function:
elif tool_call.function.name == "your_tool_name":
    result = await handle_your_tool(arguments, app.state.your_mcp_client)
    tool_results.append({
        "tool_call_id": tool_call.id,
        "role": "tool",
        "name": tool_call.function.name,
        "content": json.dumps(result)
    })
```

---

## Step-by-Step Examples

### Example 1: Adding Ephemeral Weather API

```python
# src/coordinator/weather_mcp/__init__.py

from .docker_client import WeatherMCPClientStdio
from .operations import WeatherMCPOperations

class WeatherMCPClient(WeatherMCPClientStdio, WeatherMCPOperations):
    def __init__(self, api_key: str, timeout: int = 30):
        WeatherMCPClientStdio.__init__(self, api_key=api_key, timeout=timeout)
        WeatherMCPOperations.__init__(self, docker_client=self)
```

```python
# src/coordinator/weather_mcp/operations.py

class WeatherMCPOperations:
    def get_forecast(self, city: str) -> dict:
        return self.docker_client.call_tool("get_forecast", {"city": city})
```

**Configuration:**
```bash
WEATHER_API_KEY=xxx
WEATHER_ENABLED_RARITIES=sage,warden,archon  # Fallback when mcp_access not set on persona
```

**Tool Definition:**
```python
WEATHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get 7-day weather forecast for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    }
]
```

### Example 2: Adding Long-Running Database Client

```python
# src/coordinator/postgres_mcp/__init__.py

from .docker_client import PostgresMCPClientLongRunning
from .operations import PostgresMCPOperations

class PostgresMCPClient(PostgresMCPClientLongRunning, PostgresMCPOperations):
    def __init__(self, connection_uri: str, timeout: int = 30):
        PostgresMCPClientLongRunning.__init__(
            self, connection_uri=connection_uri, timeout=timeout
        )
        PostgresMCPOperations.__init__(self, docker_client=self)

    def __enter__(self):
        self._start_mcp_server()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

**Usage:**
```python
with PostgresMCPClient(connection_uri="postgresql://...") as client:
    result = client.query("SELECT * FROM users LIMIT 10")
```

---

## Testing Your MCP Integration

### 1. Unit Tests

Create `tests/backend/coordinator/test_your_mcp_client.py`:

```python
import pytest
from src.coordinator.your_mcp_name import YourMCPClient

def test_your_mcp_tool():
    """Test Your MCP tool call."""
    client = YourMCPClient(api_key="test_key")

    result = client.your_operation(param1="test", param2=123)

    assert result is not None
    assert "data" in result
```

### 2. Integration Tests

Create `tests/integration/test_your_mcp_integration.py`:

```python
import pytest
from fastapi.testclient import TestClient
from src.coordinator.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_your_mcp_via_chat(client):
    """Test Your MCP integration via chat endpoint."""
    response = client.post(
        "/persona/chat",
        json={
            "persona_key": "eeva",
            "message": "Use your MCP tool to get data"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "your_mcp" in str(data.get("metadata", {}))
```

### 3. Manual Testing via API

```bash
# Test via chat endpoint
curl -X POST http://localhost:8000/persona/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona_key": "eeva",
    "message": "Use your MCP tool"
  }'
```

### 4. UI Testing

1. Navigate to http://localhost:3000
2. Select a persona with access to your MCP
3. Send a message that should trigger your MCP tool
4. Verify:
   - Tool is called correctly
   - Results are displayed
   - Metadata shows your MCP source

---

## Troubleshooting

### Container Won't Start

**Symptom:** `docker run` fails immediately

**Diagnosis:**
```bash
# Test container manually
docker run -i --rm -e YOUR_API_KEY=xxx mcp/your-service

# Check Docker logs
docker logs <container_id>
```

**Common Causes:**
- Missing environment variables
- Wrong Docker image name
- Docker not running
- Insufficient permissions

**Solution:**
```bash
# Verify Docker is running
docker version

# Verify image exists
docker pull mcp/your-service

# Check environment variables
docker run -i --rm -e YOUR_API_KEY=xxx mcp/your-service
```

### Container Hangs/Timeout

**Symptom:** Request times out after 30 seconds

**Diagnosis:**
```bash
# Test with manual stdin
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  docker run -i --rm -e YOUR_API_KEY=xxx mcp/your-service

# Does it hang? → Long-running pattern needed
# Does it respond and exit? → Ephemeral pattern works
```

**Solution:**
- If hangs: Switch to long-running pattern
- If timeout on valid requests: Increase timeout value

### Wrong Pattern Chosen

**Symptom Ephemeral → Long-Running:**
- Requests timeout
- Container doesn't exit
- Hangs waiting for more input

**Solution:** Migrate to long-running pattern (see Pattern 2)

**Symptom Long-Running → Ephemeral:**
- Frequent container restarts
- Slow performance (spawning overhead)
- Resource waste

**Solution:** Keep long-running if there's initialization overhead, otherwise ephemeral is fine

### JSON-RPC Errors

**Symptom:** `{"error": {"code": -32600, "message": "Invalid Request"}}`

**Diagnosis:**
```python
# Print request being sent
print(json.dumps(request, indent=2))
```

**Common Causes:**
- Malformed JSON
- Wrong method name
- Missing required parameters
- Wrong parameter types

**Solution:**
```python
# Validate request structure
request = {
    "jsonrpc": "2.0",        # Required
    "id": 1,                 # Required
    "method": "tools/call",  # Required
    "params": {              # Required for tools/call
        "name": "tool_name",
        "arguments": {...}
    }
}
```

### Permission Denied (Docker Socket)

**Symptom:** `permission denied while trying to connect to the Docker daemon socket`

**Solution:**
```bash
# Verify backend container has Docker socket mounted
docker inspect ai-companion-api | grep docker.sock

# Should show:
# "/var/run/docker.sock:/var/run/docker.sock"

# If missing, update docker-compose.yml:
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

---

## Celestial Order & Per-Persona MCP Access

MCP access is controlled **per-persona** via the `mcp_access` field in the persona's JSON file. All current personas define this field explicitly. When it is absent, the system falls back to hardcoded rarity-based sets in `intent_classifier.py` and `tool_utils.py` (the `BRAVE_ENABLED_RARITIES` / `MONGODB_ENABLED_RARITIES` env vars were removed in Feb 2026 — they were never read by routing code).

### Celestial Order Tiers

| Order | Old Name | Access Level (default fallback) |
|-------|----------|---------------------------------|
| **Wanderer** | Common | Pure LLM responses only |
| **Sage** | Rare | LLM + Brave Search (fallback default) |
| **Warden** | Epic | LLM + Brave + MCP tools (fallback default) |
| **Archon** | Legendary | LLM + All MCP servers (fallback default) |

### Per-Persona Access Matrix (Primary)

The `mcp_access` field in each persona's JSON overrides the tier-based fallback:

| Persona | Order | `mcp_access` |
|---------|-------|--------------|
| E.E.V.A. | Archon | `["brave", "mongodb"]` |
| Aegis | Warden | `["brave"]` |
| Aurora | Warden | `["brave", "mongodb"]` |
| Solace | Warden | `["brave"]` |
| Cipher | Sage | `["brave", "mongodb"]` |
| Nyx | Sage | `[]` (none) |
| Legacy / Wanderer personas | Wanderer | not set (fallback: none) |

### How It Works

The `get_tools_for_persona` function accepts an optional `mcp_access` parameter. When the persona JSON includes `mcp_access`, that list is passed in and takes priority. When it is absent, the function falls back to the rarity/order-based env var logic.

```python
# src/coordinator/tool_definitions.py

def get_tools_for_persona(
    persona_key: str,
    rarity: str,
    mcp_access: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Dynamically inject tools based on per-persona mcp_access (primary)
    or celestial-order-based env var fallback.

    Args:
        persona_key: The persona's unique key (e.g. "nephilim_eeva")
        rarity: The persona's celestial order tier ("wanderer", "sage", "warden", "archon")
        mcp_access: Optional list from the persona JSON mcp_access field.
                    When present, takes priority over rarity-based gating.
    """
    tools = []

    # --- Primary: per-persona mcp_access field ---
    if mcp_access is not None:
        if "brave" in mcp_access:
            tools.extend(BRAVE_TOOLS)
        if "mongodb" in mcp_access:
            tools.extend(MONGODB_TOOLS)
        return tools

    # --- Fallback: hardcoded rarity sets for personas without mcp_access field ---
    # BRAVE_ENABLED_RARITIES / MONGODB_ENABLED_RARITIES env vars were removed (Feb 2026).
    # All current personas define mcp_access explicitly; these sets are a safety net.
    if rarity.lower() in {"rare", "epic", "legendary"}:
        tools.extend(BRAVE_TOOLS)

    if rarity.lower() in {"epic", "legendary"}:
        tools.extend(MONGODB_TOOLS)

    return tools
```

### Adding mcp_access to a Persona JSON

```json
{
  "key": "nephilim_cipher",
  "celestial_order": "sage",
  "mcp_access": ["brave_search", "mongodb"],
  ...
}
```

Personas without `mcp_access` defined (including all Wanderer/legacy personas) fall back to
hardcoded rarity-based gating in `intent_classifier.py` and `tool_utils.py`. New personas
should always set `mcp_access` explicitly.

### Testing MCP Access

```python
# Test per-persona mcp_access field (primary path)
from src.coordinator.tool_definitions import get_tools_for_persona

# Cipher: Sage with explicit mcp_access overriding the fallback
cipher_tools = get_tools_for_persona("nephilim_cipher", "sage", mcp_access=["brave", "mongodb"])
assert any(t["function"]["name"] == "brave_web_search" for t in cipher_tools)
assert any(t["function"]["name"].startswith("mongodb") for t in cipher_tools)

# Nyx: Sage with empty mcp_access — no tools despite sage tier
nyx_tools = get_tools_for_persona("nephilim_nyx", "sage", mcp_access=[])
assert len(nyx_tools) == 0

# Wanderer (legacy): no mcp_access field — falls back to order-based gating → no tools
wanderer_tools = get_tools_for_persona("legacy_persona", "wanderer")
assert len(wanderer_tools) == 0

# E.E.V.A.: Archon with full mcp_access
eeva_tools = get_tools_for_persona("nephilim_eeva", "archon", mcp_access=["brave", "mongodb"])
assert len(eeva_tools) > 0
```

---

## Best Practices

### 1. Always Use Docker Images

✅ **DO:**
```python
image = "docker.io/mcp/your-service"  # Official registry
```

❌ **DON'T:**
```python
image = "localhost/custom-mcp"  # Won't work in production
```

### 2. Handle Errors Gracefully

```python
try:
    result = client.your_operation(param1="test")
except Exception as e:
    logger.error(f"MCP error: {e}")
    return {
        "success": False,
        "error": "Service temporarily unavailable",
        "metadata": {"source": "your_mcp"}
    }
```

### 3. Use Context Managers for Long-Running

```python
# ✅ Good
with YourMCPClient(api_key="xxx") as client:
    result = client.query()
# Container automatically closed

# ❌ Bad
client = YourMCPClient(api_key="xxx")
result = client.query()
# Container left running!
```

### 4. Log Everything

```python
import logging

logger = logging.getLogger(__name__)

def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
    logger.info(f"[YourMCP] Calling tool: {tool_name}")
    logger.debug(f"[YourMCP] Arguments: {arguments}")

    result = self._execute(tool_name, arguments)

    logger.info(f"[YourMCP] Success: {tool_name}")
    return result
```

### 5. Validate Environment Variables

```python
def __init__(self, api_key: Optional[str] = None):
    if not api_key:
        raise ValueError(
            "YOUR_API_KEY environment variable required. "
            "Set in .env or pass to constructor."
        )
```

### 6. Add Type Hints Everywhere

```python
from typing import Dict, Any, Optional, List

def your_operation(
    self,
    param1: str,
    param2: Optional[int] = None
) -> Dict[str, Any]:
    """Clear docstring with types."""
    ...
```

### 7. Write Comprehensive Tests

```python
# Unit tests
def test_tool_call():
    ...

# Integration tests
def test_via_chat_endpoint():
    ...

# Manual test instructions in docstring
"""
Manual Test:
1. Start backend
2. Send: "Use your MCP to get X"
3. Verify: Response includes MCP data
"""
```

### 8. Document Your MCP

Create `docs/YOUR_MCP_INTEGRATION.md`:

```markdown
# Your MCP Integration

## Overview
Brief description of what this MCP does.

## Configuration
- `YOUR_API_KEY`: Required API key
- `YOUR_ENABLED_RARITIES`: Celestial order tiers with fallback access (used when persona has no mcp_access field)

## Tools
- `your_tool_name`: Description

## Testing
Step-by-step testing instructions

## Troubleshooting
Common issues and solutions
```

---

## Summary Checklist

When adding a new MCP server, ensure:

- [ ] Identified correct pattern (ephemeral vs long-running)
- [ ] Created MCP module: `src/coordinator/your_mcp_name/`
- [ ] Implemented Docker client (`docker_client.py`)
- [ ] Implemented operations layer (`operations.py`)
- [ ] Created public API (`__init__.py`)
- [ ] Added environment variables to `.env` and `.env.docker`
- [ ] Updated `config.py` with new settings
- [ ] Registered in `startup.py`
- [ ] Created tool definitions in `tool_definitions.py`
- [ ] Implemented tool handlers in `services/`
- [ ] Integrated into `routes/chat.py`
- [ ] Added per-persona MCP access (mcp_access field) or rarity-based gating
- [ ] Wrote unit tests
- [ ] Wrote integration tests
- [ ] Tested via API (curl)
- [ ] Tested via UI (browser)
- [ ] Documented in `docs/`
- [ ] Updated `CLAUDE.md` and `README.md`

---

## Related Documentation

- **[CLAUDE.md](../CLAUDE.md)** - Developer guide and project structure
- **[README.md](../README.md)** - User-facing documentation

---

## Keyword Force-Search Pattern (Feb 2026)

When using small local LLMs (e.g., Gemma 9B via Ollama), the model may be unreliable at generating structured JSON tool calls. The project addresses this with a **keyword force-search** pattern in `tool_calling_service.py`:

1. **Intent classifier** (`tools/intent_classifier.py`) uses keyword dictionaries (`tools/keywords.py`) to determine which MCP should handle a query
2. **Keyword filter** (`tool_utils.py:should_use_keyword_filter()`) independently checks if web search is needed
3. When the keyword filter confirms search is needed, `tool_calling_service.py` **force-executes** the Brave search directly — bypassing the LLM tool-calling loop entirely
4. Search results are fed to the LLM for synthesis, and citations are auto-generated from actual results (not LLM-hallucinated)

This pattern is recommended for any new MCP integration where the local LLM cannot reliably generate tool calls. The keyword dictionaries in `tools/keywords.py` can be extended for new MCP services.

---

**Questions?** Check the troubleshooting section or examine the reference implementations:
- Brave MCP: `src/coordinator/mcp_client_stdio.py`
- MongoDB MCP: `src/coordinator/mongodb/`
- Intent classifier: `src/coordinator/tools/intent_classifier.py`
- Keywords: `src/coordinator/tools/keywords.py`
- Force-search: `src/coordinator/services/tool_calling_service.py` (lines 176-212)
