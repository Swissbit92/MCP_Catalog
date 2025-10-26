# src/coordinator/server.py
import os, yaml, json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .stdio_client import StdioMCPClient

# NEW imports for persona routing
from .llm_client import OllamaClient
from .tools_spec import TOOLS_SPEC
from .persona_prompts import BASE_SYSTEM, PERSONA_PRESETS

CATALOG_PATH = os.getenv("COORDINATOR_CATALOG", "catalog/graph_rag_mcp.yaml")

class CallBody(BaseModel):
    server: str
    tool: str
    arguments: Dict[str, Any] = {}

# NEW: persona chat schemas
class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class PersonaChatBody(BaseModel):
    persona: str = "Nerdy Charming"
    history: List[ChatTurn] = []
    message: str
    k: int = 8  # default top-k when tools need it

app = FastAPI(title="MCP Coordinator", version="0.2.0")

_clients: Dict[str, StdioMCPClient] = {}

def _load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.on_event("startup")
def _startup():
    cat = _load_catalog()
    net = cat.get("network", "graph_rag_dev")
    for name, cfg in cat["servers"].items():
        if cfg.get("type") != "stdio":
            continue
        docker = cfg["docker"]
        image = docker["image"]
        env = docker.get("env", {})
        volumes = docker.get("volumes", [])
        network = docker.get("network", net)
        cmd = docker.get("cmd", [])
        _clients[name] = StdioMCPClient(name, image, env, network, volumes, cmd)

@app.on_event("shutdown")
def _shutdown():
    for c in _clients.values():
        c.close()

@app.get("/health")
def health():
    return {"ok": True, "servers": list(_clients.keys())}

@app.get("/tools")
def tools():
    out = {}
    for name, c in _clients.items():
        try:
            out[name] = c.list_tools()
        except Exception as e:
            out[name] = {"error": str(e)}
    return out

@app.post("/call")
def call(body: CallBody):
    c = _clients.get(body.server)
    if not c:
        raise HTTPException(status_code=404, detail=f"Unknown server '{body.server}'")
    try:
        res = c.call_tool(body.tool, body.arguments or {})
        return {"ok": True, "server": body.server, "tool": body.tool, "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# NEW: Persona Router API
# -----------------------

# Single local persona LLM (Ollama)
_llm = OllamaClient(
    base=os.getenv("OLLAMA_BASE", "http://localhost:11434"),
    model=os.getenv("PERSONA_MODEL", "llama3.1:8b"),
)

def _tool_router_call(tool_name: str, args: dict) -> dict:
    """Execute a single MCP tool call based on router decision."""
    if tool_name == "call_rag_qa":
        # args: {"question": str, "k": int, "entity_ids": [..]}   (all optional except question)
        return _clients["rag"].call_tool("rag.qa", args)
    if tool_name == "call_rag_search":
        # args: {"text": str, "k": int}
        return _clients["rag"].call_tool("rag.search", args)
    if tool_name == "call_kg_sparql":
        # args: {"query": str}
        return _clients["kg"].call_tool("sparql_query", args)
    if tool_name == "call_brave_search":
        # not wired yet: return a stub to keep persona stable
        return {"note": "Brave MCP not wired yet in Coordinator."}
    return {"error": f"unknown tool {tool_name}"}

@app.post("/persona/chat")
def persona_chat(body: PersonaChatBody):
    # Prepare system prompt from persona preset
    preset = PERSONA_PRESETS.get(body.persona, PERSONA_PRESETS["Nerdy Charming"])
    system_prompt = BASE_SYSTEM.format(**preset)

    # Compact history (cap to last few turns)
    history_msgs = [{"role": t.role, "content": t.content} for t in body.history][-6:]
    # Add the new user message
    msgs_for_router = history_msgs + [{"role": "user", "content": body.message}]

    # Ask router for either a tool call or a direct answer
    decision = _llm.chat_with_tools(system=system_prompt, messages=msgs_for_router, tools=TOOLS_SPEC)

    # If tool call requested
    if decision.get("tool"):
        tool_name = decision["tool"]["name"]
        args = decision["tool"].get("arguments", {}) or {}

        # Sensible defaults (so persona can omit noise)
        if tool_name == "call_rag_qa":
            args.setdefault("question", body.message)
            args.setdefault("k", body.k)
        if tool_name == "call_rag_search":
            args.setdefault("text", body.message)
            args.setdefault("k", body.k)
        if tool_name == "call_kg_sparql":
            args.setdefault("query", "SELECT * WHERE { ?s ?p ?o } LIMIT 5")

        observation = _tool_router_call(tool_name, args)

        # Send observation back to the LLM for the final user-facing answer
        final = _llm.complete(
            system=system_prompt,
            user_prompt=(
                "You called one tool. Write the final answer now.\n\n"
                f"User message:\n{body.message}\n\n"
                f"Tool used: {tool_name}\n"
                f"Tool arguments: {json.dumps(args, ensure_ascii=False)}\n"
                "Tool result (trim if long):\n"
                f"{json.dumps(observation, ensure_ascii=False)[:8000]}\n\n"
                "IMPORTANT:\n"
                "- If tool provided citations, preserve them exactly.\n"
                "- Be concise. Bullet points allowed.\n"
            ),
        )
        return {
            "answer": final,
            "used_tool": {"name": tool_name, "args": args},
            "observation": observation,
        }

    # No tool requested → direct answer
    return {"answer": decision.get("text", "").strip(), "used_tool": None}
