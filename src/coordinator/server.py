# src/coordinator/server.py
from __future__ import annotations
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .catalog import load_catalog
from .docker_stdio import spawn_docker_stdio
from .mcp_client import MCPClient

CATALOG_PATH = os.getenv("MCP_CATALOG", "catalog/graph_rag_mcp.yaml")

app = FastAPI(title="GraphRAG MCP Coordinator", version="0.1.0")

class CallRequest(BaseModel):
    server: str = Field(description="server key in catalog (e.g., 'rag' or 'kg')")
    tool: str = Field(description="tool name (e.g., 'rag.qa', 'rag.search', 'kg.health')")
    arguments: Dict[str, Any] = Field(default_factory=dict)

class CallResponse(BaseModel):
    ok: bool
    result: Any

class ToolsResponse(BaseModel):
    ok: bool
    servers: Dict[str, List[Dict[str, Any]]]

_clients: Dict[str, MCPClient] = {}
_catalog = load_catalog(CATALOG_PATH)

def _ensure_client(name: str) -> MCPClient:
    if name in _clients:
        return _clients[name]
    spec = _catalog.servers.get(name)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown server '{name}'")
    proc = spawn_docker_stdio(spec.launch.cmd, spec.launch.args, spec.launch.env)
    client = MCPClient(name, proc)
    _clients[name] = client
    return client

@app.get("/tools", response_model=ToolsResponse)
def list_tools():
    out: Dict[str, List[Dict[str, Any]]] = {}
    for name in _catalog.servers.keys():
        try:
            c = _ensure_client(name)
            out[name] = c.list_tools()
        except Exception as e:
            out[name] = [{"error": str(e)}]
    return ToolsResponse(ok=True, servers=out)

@app.post("/call", response_model=CallResponse)
def call_tool(req: CallRequest):
    c = _ensure_client(req.server)
    try:
        result = c.call_tool(req.tool, req.arguments)
        return CallResponse(ok=True, result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"ok": True, "servers": list(_catalog.servers.keys())}

# Dev entrypoint:
# uvicorn src.coordinator.server:app --reload --port 8765
