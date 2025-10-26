# GraphRAG MCP — Coordinator + Streamlit UI (Option A)

Local development: Coordinator + Streamlit run on the host; rag/kg MCP servers run as Docker containers over stdio. Backing services (Ollama, GraphDB) run via docker-compose on network `graph_rag_dev`.

## 1) Start backing services

```bash
docker compose up -d
This provides:

Ollama at http://localhost:11434 (container DNS: http://ollama:11434)

GraphDB at http://localhost:7200 (container DNS: http://graphdb:7200)

2) Run the Coordinator (FastAPI)
bash
Copy code
uvicorn src.coordinator.server:app --reload --port 8765
Loads catalog/graph_rag_mcp.yaml

Spawns rag and kg via docker run -i ...

Exposes:

GET /tools — discover tool lists per MCP server

POST /call — {"server":"rag","tool":"rag.qa","arguments":{...}}

3) Run the Streamlit UI
bash
Copy code
streamlit run ui/app.py
Tabs:

Ask → rag.qa (entity-aware RAG QA with optional KG enrichment) rag_server

Search → rag.search over Chroma (entity filters supported) chroma_store

KG Browser → sparql_query against GraphDB (quick inspection) kg_server

Diagnostics → rag.health, kg.health, server.config from each server

Notes
The containers see your workspace via -v ${PWD}:/workspace. Update paths in the catalog if your outputs live elsewhere.

The rag server expects .chroma and outputs/run_simple/... consistent with your pipeline. (These defaults match your existing code.)

To change the images, edit catalog/graph_rag_mcp.yaml under servers.rag.launch.args and servers.kg.launch.args.

markdown
Copy code

---

## Why this maps cleanly onto your existing code

- **rag server** already exposes `rag.search`, `rag.reindex`, `rag.embed_and_index`, `rag.delete`, `rag.health`, `rag.qa`, `server.config` over MCP (stdio). We’re just brokering those over HTTP. :contentReference[oaicite:9]{index=9}
- **kg server** already exposes `validate_labels`, `push_labels`, `sparql_query`, `sparql_update`, `list_documents`, `get_chunk`, `kg.health`, `server.config`. Same story. :contentReference[oaicite:10]{index=10}
- Paths + env defaults (Chroma directory/collection, GraphDB URL/repo, Ollama base) match your settings + mcp.json conventions. 

---

## How it all talks

- **Coordinator → Dockerized MCP**: JSON-RPC over **stdio**. We `docker run -i` the server, write JSON lines to its **stdin**, and read responses from **stdout**. `MCPClient` keeps a tiny request/response table and returns results to the HTTP caller.
- **Streamlit → Coordinator**: plain HTTP (`/call`, `/tools`). It stays host-local—no keys, no cloud.
- **MCP servers → services**: inside containers, they use the compose network names:
  - `OLLAMA_BASE=http://ollama:11434`
  - `GRAPHDB_URL=http://graphdb:7200`
  Both are injected by the catalog.

---

## Next steps (optional polish)

- Persist/retry logic for MCP child lifecycles (restart on exit).
- Cache tool lists per server and hot-reload on demand.
- Add a “Docs” tab that lists pipeline docs via `kg.list_documents` and previews chunks via `kg.get_chunk`. :contentReference[oaicite:12]{index=12}
- Add entity pickers (SPARQL `SELECT ?s ?label ...`) to feed `entity_ids` into **Ask** and **Search**.

If you’d like, I can tailor the `graph_rag_mcp.yaml` to your exact image tags and any custom bind mounts you’re already using.

───────────────────────────────────────────────────────────────────────────────
                        GRAPH-RAG MCP — LOCAL OPTION A
───────────────────────────────────────────────────────────────────────────────
                                   (Host)
                                   ┌────────────────────────────┐
                                   │    Streamlit UI (app.py)   │
                                   │  ────────────────────────  │
        User types ───────────────▶│  [Ask] "What problem does  │
                                   │         Bitcoin solve?"    │
                                   └─────────────┬──────────────┘
                                                 │ HTTP (JSON)
                                                 ▼
                                   ┌────────────────────────────┐
                                   │  Coordinator (FastAPI)     │
                                   │  src/coordinator/server.py │
                                   │  - loads catalog.yaml      │
                                   │  - spawns docker -i        │
                                   │  - bridges JSON-RPC stdio  │
                                   └─────────────┬──────────────┘
                                                 │
         ┌───────────────────────────────────────┼────────────────────────────┐
         │                                       │                            │
         ▼                                       ▼                            ▼
┌───────────────────────┐             ┌─────────────────────────┐   ┌─────────────────────────┐
│ RAG MCP Container     │             │ KG MCP Container        │   │  Optional future MCPs   │
│ graphdb_desktop-rag   │             │ graphdb_desktop-kg      │   │ (e.g., Brave, Mongo…)   │
│ src/mcp/rag_server.py │             │ src/mcp/kg_server.py    │   │                         │
│ - rag.qa, rag.search  │             │ - sparql_query, health  │   │                         │
│ - Ollama + Chroma     │             │ - GraphDB client        │   │                         │
└──────────┬────────────┘             └──────────┬──────────────┘   └─────────────────────────┘
           │                                     │
           │ http://ollama:11434                 │ http://graphdb:7200
           │                                     │
──────────────────────────── Docker Network: graph_rag_dev ─────────────────────
           │                                     │
           ▼                                     ▼
   ┌───────────────────┐                 ┌──────────────────────────┐
   │   Ollama Service  │                 │   GraphDB Service        │
   │  Local LLM engine │                 │  Triple store + GraphQL  │
   └───────────────────┘                 └──────────────────────────┘
───────────────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════════════
          EXTENDED FLOW — RAG + KG INTERACTION DURING QA
═══════════════════════════════════════════════════════════════════════════════

 (1) USER / UI (HOST)
───────────────────────────────────────────────────────────────────────────────
   ┌────────────────────────────────────────────────────────────────────┐
   │ Streamlit UI (Ask tab)                                             │
   │ "What problem does Bitcoin aim to solve?" → click [Answer]         │
   └────────────────────────────────────────────────────────────────────┘
                           │
                           │  (HTTP POST /call → Coordinator)
                           ▼

 (2) COORDINATOR (HOST)
───────────────────────────────────────────────────────────────────────────────
   ┌────────────────────────────────────────────────────────────────────┐
   │ FastAPI Coordinator                                                │
   │ Reads catalog/graph_rag_mcp.yaml → finds "rag"                    │
   │ docker run -i graphdb_desktop-rag --network graph_rag_dev         │
   │ Writes JSON-RPC request to stdin:                                 │
   │   { "method": "tools/call",                                        │
   │     "params": { "name":"rag.qa", "arguments":{"question":...} } }  │
   └────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
 (3) RAG MCP CONTAINER
───────────────────────────────────────────────────────────────────────────────
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  RAG MCP  (src/mcp/rag_server.py)                                        │
   │  ① Receives question via stdio                                           │
   │  ② Extracts entities (Bitcoin, Proof-of-Work) using text filters         │
   │  ③ Checks local Chroma vector store (.chroma) for relevant chunks        │
   │  ④ Calls Ollama LLM (http://ollama:11434) for embedding or QA synthesis  │
   │                                                                          │
   │  Before final synthesis:                                                 │
   │     → needs entity definitions or related protocols                      │
   │     → asks KG MCP for context entities                                   │
   └──────────────────────────────────────────────────────────────────────────┘
                           │
                           │ (JSON-RPC request proxied via Coordinator)
                           ▼
 (4) COORDINATOR RELAYS TO KG MCP
───────────────────────────────────────────────────────────────────────────────
   ┌────────────────────────────────────────────────────────────────────┐
   │ Coordinator finds "kg" in catalog                                  │
   │ docker run -i graphdb_desktop-kg                                   │
   │ Writes JSON-RPC:                                                   │
   │   {"method":"tools/call",                                          │
   │    "params":{"name":"sparql_query",                                │
   │              "arguments":{"query":                                 │
   │                "SELECT ?label ?desc WHERE {                        │
   │                   crypto:Bitcoin rdfs:label ?label;                │
   │                   dcterms:description ?desc . }"}}}                │
   └────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
 (5) KG MCP CONTAINER
───────────────────────────────────────────────────────────────────────────────
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  KG MCP  (src/mcp/kg_server.py)                                          │
   │  ① Receives SPARQL query via stdio                                       │
   │  ② Connects to GraphDB (http://graphdb:7200)                             │
   │  ③ Executes query → finds entity info for crypto:Bitcoin                 │
   │  ④ Returns JSON { label:"Bitcoin", desc:"Decentralized currency..." }    │
   └──────────────────────────────────────────────────────────────────────────┘
                           │
                           │ (stdout → Coordinator → back to RAG MCP)
                           ▼
 (6) RAG MCP CONTINUES
───────────────────────────────────────────────────────────────────────────────
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  Integrates KG context into prompt:                                     │
   │  "Bitcoin — a decentralized peer-to-peer system eliminating the need…"  │
   │  + retrieved chunks from Chroma                                         │
   │  + citations metadata (doc_id, chunk_id)                                │
   │  → sends combined context to Ollama model                               │
   │  → receives final synthesized answer                                    │
   │  → emits JSON result:                                                   │
   │     {"answer":"Bitcoin solves double-spending…",                        │
   │      "citations":[{doc_id:"bitcoin_whitepaper",chunk_id:3,...},...]}    │
   └──────────────────────────────────────────────────────────────────────────┘
                           │
                           │ (stdout → Coordinator)
                           ▼
 (7) COORDINATOR → STREAMLIT UI
───────────────────────────────────────────────────────────────────────────────
   ┌────────────────────────────────────────────────────────────────────┐
   │ Returns HTTP response to Streamlit UI                              │
   │ UI renders:                                                        │
   │   Answer: "Bitcoin solves the double-spending problem..."          │
   │   Citations:                                                       │
   │     [bitcoin_whitepaper-hash:3], [tao_whitepaper-hash:6], …       │
   └────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
 (8) USER SEES RESULT
───────────────────────────────────────────────────────────────────────────────
   ┌────────────────────────────────────────────────────────────────────┐
   │  💬 Answer displayed with expandable citations                      │
   │  🧩 Optional: click "KG Browser" → SPARQL for related entities      │
   └────────────────────────────────────────────────────────────────────┘
