# src/coordinator/mcp_client.py
from __future__ import annotations
import json, threading, uuid, time
from typing import Dict, Any, Optional, List, Tuple
from .docker_stdio import StdioProcess

_JSONL = "\n"

class MCPClient:
    def __init__(self, name: str, proc: StdioProcess):
        self.name = name
        self.proc = proc
        self._lock = threading.Lock()
        self._pending: Dict[str, Any] = {}
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._init_handshake()

    def _send(self, obj: Dict[str, Any]) -> None:
        line = (json.dumps(obj) + _JSONL).encode("utf-8")
        with self._lock:
            self.proc.stdin.write(line)
            self.proc.stdin.flush()

    def _read_loop(self):
        f = self.proc.stdout
        while True:
            line = f.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception:
                continue
            mid = msg.get("id")
            if mid and mid in self._pending:
                self._pending[mid] = msg

    def _rpc(self, method: str, params: Dict[str, Any] | None = None, timeout: float = 20.0) -> Any:
        rid = str(uuid.uuid4())
        req = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        self._pending[rid] = None
        self._send(req)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._pending[rid] is not None:
                msg = self._pending.pop(rid)
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                return msg.get("result")
            time.sleep(0.01)
        raise TimeoutError(f"MCP call timed out: {method}")

    def _init_handshake(self):
        # Light handshake; many servers accept direct tool calls,
        # but we ask for a tool list for discovery.
        try:
            self.tools = self.list_tools()
        except Exception:
            self.tools = []

    # --- public API ---
    def list_tools(self) -> List[Dict[str, Any]]:
        return self._rpc("tools/list", {}) or []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})

    def server_config(self) -> Any:
        # Convention: many servers expose server.config; it's optional.
        try:
            return self.call_tool("server.config", {})
        except Exception:
            return {"ok": False, "note": "server.config not supported"}
