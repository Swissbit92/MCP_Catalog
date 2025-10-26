# src/coordinator/stdio_client.py
import json, subprocess, threading, queue
from typing import Any, Dict, List

class StdioMCPClient:
    def __init__(self, name: str, docker_image: str, env: Dict[str, str], network: str, volumes: List[str], cmd: List[str]):
        self.name = name
        args = ["docker", "run", "--rm", "-i", "--network", network]
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        for spec in volumes:
            args += ["-v", spec]
        args += [docker_image]
        if cmd:
            args += cmd

        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self._out_q: "queue.Queue[str]" = queue.Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        self._id = 0

    def _read_stdout(self):
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self._out_q.put(line)

    def _rpc(self, method: str, params: Any) -> Any:
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        data = json.dumps(msg) + "\n"
        assert self.proc.stdin is not None
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

        while True:
            line = self._out_q.get(timeout=60)
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("id") == self._id:
                if "error" in obj:
                    raise RuntimeError(f"MCP error: {obj['error']}")
                return obj.get("result")

    def list_tools(self):
        return self._rpc("tools/list", {})

    def call_tool(self, name: str, arguments: Any):
        return self._rpc("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        try:
            self.proc.terminate()
        except Exception:
            pass
