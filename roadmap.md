# 🧭 GraphRAG Coordinator UI — Roadmap

> _Last updated : 2025-11-01_  
> _Focus : from local alpha → internal production-ready beta_

---

## 🔥 Now — Critical / Unblockers ( Milestone v0.2 )

- [ ] **Add `/persona/summary` endpoint**  
  - Return cached short persona summaries for the Bio tab.  
  - Reuse existing summarizer + cache logic.  
  - Response shape: `{persona_key, summary, timestamp}`.  

- [ ] **Improve Coordinator ↔ UI error handling**  
  - Wrap all POSTs with structured JSON error envelopes.  
  - Streamlit toasts show clear messages (“Coordinator unreachable”, “LLM timeout”, etc.).  

- [ ] **Add `/health` endpoint**  
  - Simple GET returning `{status, model, uptime}`.  
  - Diagnostics tab pings this for quick checks.  

---

## 🧩 Next — Feature Tier ( Milestone v0.3 )

- [ ] **Local chat persistence + chat groups**  
  - Use SQLite / JSONL to store chats and messages.  
  - UI: list chats → resume · rename · delete.  
  - Auto-restore last chat per persona.

- [ ] **Persona → MCP Tool Routing**  
  - Map each persona to its allowed MCPs (GraphRAG · Brave · KG …).  
  - `/persona/chat` may invoke `call_mcp_tool()` when prompt pattern matches.  
  - Introduce `settings.py` + `catalog.yaml` for endpoint declarations.  

- [ ] **Streaming responses**  
  - Replace blocking replies with SSE / chunked streaming.  
  - Progressive token rendering for snappier UX.  

- [ ] **Structured logging & metrics**  
  - Log request id · persona · latency · error type.  
  - Optional Prometheus counter or in-memory stats endpoint.  

---

## 🧱 Later — Production Hardening ( Milestone v1.0 )

- [ ] **Coordinator auth layer**  
  - Simple API-key header for non-localhost use.

- [ ] **Multi-user session support**  
  - User profiles + persona preferences; segregated chat stores.  

- [ ] **Observability dashboard**  
  - Minimal admin page showing uptime · recent logs · model stats.  

- [ ] **Tests & CI pipeline**  
  - ✅ FastAPI unit tests (greet / chat / summary)  
  - ✅ Streamlit smoke tests (import + render)  
  - ✅ Formatting / lint checks (black · flake8 · pytest workflow)  

---

### ✅ After Now + Next

The Coordinator UI reaches **internal beta readiness**:

- Bio tab functional (`/persona/summary`)  
- Persistent, groupable chat history  
- Persona-aware MCP tool routing (GraphRAG · Brave · KG)  
- Streaming UX + basic observability

---

**Owner:** GraphRAG Team  
**Maintainer:** E.E.V.A / Coordinator Module  
**License:** Private (Local Use)
