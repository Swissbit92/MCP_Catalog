# MongoDB MCP Client Architecture

## Overview

The MongoDB MCP Client has been refactored from a monolithic 650-line file into a modular architecture with clear separation of concerns.

## File Structure

```
src/coordinator/
├── mongodb_mcp_client.py          (109 lines) - Backward compatibility wrapper
└── mongodb/                        (package)
    ├── __init__.py                 (106 lines) - Public API and combined client
    ├── docker_client.py            (398 lines) - Low-level protocol handling
    └── operations.py               (207 lines) - High-level MongoDB operations
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     mongodb_mcp_client.py                           │
│                   (Backward Compatibility Wrapper)                   │
│                                                                      │
│  Re-exports everything from mongodb/ package                        │
│  Preserves existing import paths for zero breaking changes          │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ imports from
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        mongodb/__init__.py                          │
│                         (Public API Layer)                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              MongoDBMCPClient (Combined Class)              │    │
│  │  ┌──────────────────────┬───────────────────────────────┐  │    │
│  │  │ MongoDBDockerClient  │   MongoDBOperations           │  │    │
│  │  │ (Low-level protocol) │   (High-level MongoDB ops)    │  │    │
│  │  └──────────────────────┴───────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  + get_mongodb_client() factory                                     │
│  + Exception classes (MCPError, MCPConnectionError, etc.)           │
│  + Constants (READ_ONLY_TOOLS, WRITE_TOOLS)                         │
└──────────────────────────────────────────────────────────────────────┘
            │                                   │
            │ imports                           │ imports
            ▼                                   ▼
┌────────────────────────────┐    ┌─────────────────────────────────┐
│  mongodb/docker_client.py  │    │   mongodb/operations.py         │
│   (Protocol Layer - 398L)  │    │   (Business Logic - 207L)       │
├────────────────────────────┤    ├─────────────────────────────────┤
│                            │    │                                 │
│ MongoDBDockerClient        │    │ MongoDBOperations               │
│  - __init__()              │    │  - __init__(docker_client)      │
│  - _start_mcp_server()     │    │  - find()                       │
│  - _send_request()         │    │  - aggregate()                  │
│  - _parse_documents()      │    │  - count()                      │
│  - _validate_tool()        │    │  - list_collections()           │
│  - is_connected()          │    │                                 │
│  - close()                 │    │ Uses docker_client internally   │
│  - __enter__/__exit__      │    │ for all operations              │
│                            │    │                                 │
│ Exception Classes:         │    └─────────────────────────────────┘
│  - MCPError                │
│  - MCPConnectionError      │
│  - MCPTimeoutError         │
│  - MCPResponseError        │
│  - MCPPermissionError      │
│                            │
│ Constants:                 │
│  - READ_ONLY_TOOLS (13)    │
│  - WRITE_TOOLS (9)         │
└────────────────────────────┘
```

## Class Relationships

### Inheritance Chain

```
MongoDBMCPClient
├── MongoDBDockerClient (provides protocol handling)
│   └── object
└── MongoDBOperations (provides MongoDB methods)
    └── object
```

### Dependency Injection

```python
# MongoDBOperations depends on MongoDBDockerClient
class MongoDBOperations:
    def __init__(self, docker_client: MongoDBDockerClient):
        self.docker_client = docker_client

    def find(self, ...):
        # Uses docker_client._send_request() internally
        result = self.docker_client._send_request("tools/call", params)
        return self.docker_client._parse_documents(result)
```

### Combined Client

```python
# MongoDBMCPClient inherits from both
class MongoDBMCPClient(MongoDBDockerClient, MongoDBOperations):
    def __init__(self, ...):
        # Initialize Docker client (handles connection)
        MongoDBDockerClient.__init__(self, ...)

        # Initialize operations (uses self as docker_client)
        MongoDBOperations.__init__(self, docker_client=self)
```

## Import Patterns

### Backward Compatible (via wrapper)

```python
# All existing code continues to work
from coordinator.mongodb_mcp_client import MongoDBMCPClient
from coordinator.mongodb_mcp_client import get_mongodb_client
from coordinator.mongodb_mcp_client import MCPError, MCPConnectionError
```

### Direct Package Import (new option)

```python
# Can now import directly from package
from coordinator.mongodb import MongoDBMCPClient
from coordinator.mongodb import MongoDBDockerClient, MongoDBOperations
from coordinator.mongodb import get_mongodb_client
```

### Internal Relative Imports

```python
# Within mongodb package
from .docker_client import MongoDBDockerClient, MCPError, ...
from .operations import MongoDBOperations
```

## Responsibilities

### docker_client.py (Protocol Layer)
- **Focus**: JSON-RPC 2.0 protocol and Docker subprocess management
- **Responsibilities**:
  - Start/stop Docker container running MCP server
  - Send JSON-RPC 2.0 requests over stdin
  - Read JSON-RPC 2.0 responses from stdout
  - Handle timeouts and errors
  - Parse MCP response format
  - Validate read-only access (block write operations)
  - Manage connection lifecycle

### operations.py (Business Logic)
- **Focus**: High-level MongoDB semantic operations
- **Responsibilities**:
  - Provide MongoDB query methods (find, aggregate, count)
  - Construct MCP tool call parameters
  - Handle MongoDB-specific response parsing
  - Abstract away JSON-RPC details from users
  - Depend on docker_client via constructor injection

### __init__.py (Public API)
- **Focus**: Clean public interface and re-exports
- **Responsibilities**:
  - Combine DockerClient and Operations into unified client
  - Re-export all public classes, functions, constants
  - Provide factory function (get_mongodb_client)
  - Define explicit __all__ for clean imports
  - Serve as single entry point for package

### mongodb_mcp_client.py (Compatibility Layer)
- **Focus**: Backward compatibility
- **Responsibilities**:
  - Re-export everything from mongodb package
  - Preserve existing import paths
  - Maintain test code in __main__ block
  - Zero breaking changes for existing code

## Benefits

### 1. Modularity
- Each file has single, clear responsibility
- Protocol handling separated from business logic
- No file exceeds 400 lines (was 650)

### 2. Testability
- Can mock MongoDBDockerClient for testing operations
- Can test protocol handling independently
- Dependency injection enables unit testing

### 3. Maintainability
- Smaller files are easier to understand
- Clear boundaries between components
- Changes to protocol don't affect business logic

### 4. Extensibility
- Easy to add new MongoDB operations to operations.py
- Protocol changes isolated to docker_client.py
- Can add new transport mechanisms alongside stdio

### 5. Backward Compatibility
- Zero breaking changes for existing code
- All imports continue to work
- Test code preserved in wrapper

## Migration Path (Optional)

While not required due to backward compatibility, teams can optionally migrate to direct package imports:

### Phase 1 (Current - No Changes Required)
```python
# Continue using wrapper imports
from coordinator.mongodb_mcp_client import MongoDBMCPClient
```

### Phase 2 (Optional - New Code)
```python
# Use direct package imports for new code
from coordinator.mongodb import MongoDBMCPClient
```

### Phase 3 (Optional - Future)
```python
# Eventually deprecate wrapper (if desired)
# All code uses direct package imports
from coordinator.mongodb import MongoDBMCPClient
```

**Note**: Phase 1 is permanent - the wrapper can remain indefinitely with zero downsides.

## Verification

All verification tests pass:
- ✓ Backward compatibility imports
- ✓ Direct package imports
- ✓ Class identity via both import paths
- ✓ Correct inheritance chain
- ✓ All expected methods present
- ✓ Exception hierarchy intact
- ✓ Constants preserved
- ✓ Factory function works
- ✓ Dependency injection pattern
- ✓ File structure complete

## Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total lines | 650 | 820 | +170 (+26%) |
| Largest file | 650 | 398 | -252 (-39%) |
| Number of files | 1 | 4 | +3 |
| Public classes | 1 | 3 | +2 |
| Breaking changes | N/A | 0 | Zero |

## Related Documentation

- `MONGODB_MCP_REFACTORING.md` - Detailed refactoring summary
- `MONGODB_MCP_IMPLEMENTATION.md` - Original feature specification
- `PHASE_4_COMPLETION_SUMMARY.md` - MongoDB MCP integration completion

---

**Last Updated**: 2025-12-24
**Status**: ✓ Complete - Production Ready
**Backward Compatibility**: 100%
