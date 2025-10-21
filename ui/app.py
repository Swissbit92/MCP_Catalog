# ui/app.py
import ui.app as st
import requests
import json

COORDINATOR_BASE = "http://127.0.0.1:8765"

st.set_page_config(page_title="GraphRAG MCP UI", layout="wide")
st.title("GraphRAG MCP — Local Coordinator + UI (Option A)")

tabs = st.tabs(["Ask", "Search", "KG Browser", "Diagnostics"])

def call(server, tool, arguments):
    r = requests.post(f"{COORDINATOR_BASE}/call", json={
        "server": server, "tool": tool, "arguments": arguments or {}
    }, timeout=120)
    r.raise_for_status()
    return r.json()["result"]

with tabs[0]:
    st.subheader("Ask (rag.qa)")
    q = st.text_area("Question", "What problem does Bitcoin aim to solve?")
    ent = st.text_input("Entity IRIs (comma-separated)", "")
    k = st.slider("Top-k", 1, 16, 8)
    if st.button("Answer"):
        entity_ids = [s.strip() for s in ent.split(",") if s.strip()] or None
        res = call("rag", "rag.qa", {"question": q, "entity_ids": entity_ids, "k": k})
        st.markdown("### Answer")
        st.write(res.get("answer"))
        st.markdown("### Citations")
        for i, c in enumerate(res.get("citations", []), 1):
            st.write(f"[{i}] {c.get('doc_id')} — {c.get('chunk_id')}")
            st.caption(c.get("text", "")[:400])

with tabs[1]:
    st.subheader("Search (rag.search)")
    text = st.text_input("Query text", "consensus")
    if st.button("Search"):
        res = call("rag", "rag.search", {"text": text, "k": 8})
        docs = (res or {}).get("results", {}).get("documents", [[]])
        metas = (res or {}).get("results", {}).get("metadatas", [[]])
        if docs and isinstance(docs[0], list):  # shape from Chroma
            docs, metas = docs[0], metas[0]
        for d, m in zip(docs or [], metas or []):
            st.write(f"- {m.get('doc_id')} · {m.get('chunk_id')} · page={m.get('page')}")
            st.caption(d[:300])

with tabs[2]:
    st.subheader("KG Browser (SPARQL)")
    default_q = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    q = st.text_area("SPARQL query", default_q, height=160)
    if st.button("Run SPARQL"):
        res = call("kg", "sparql_query", {"query": q})
        st.json(res)

with tabs[3]:
    st.subheader("Diagnostics")
    col1, col2 = st.columns(2)
    with col1:
        st.write("rag.health")
        try:
            st.json(call("rag", "rag.health", {}))
        except Exception as e:
            st.error(str(e))
        st.write("rag.server.config")
        try:
            st.json(call("rag", "server.config", {}))
        except Exception as e:
            st.error(str(e))
    with col2:
        st.write("kg.health")
        try:
            st.json(call("kg", "kg.health", {}))
        except Exception as e:
            st.error(str(e))
        st.write("kg.server.config")
        try:
            st.json(call("kg", "server.config", {}))
        except Exception as e:
            st.error(str(e))
