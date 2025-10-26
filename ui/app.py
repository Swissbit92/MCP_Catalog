# ui/app.py
import streamlit as st, requests, json

COORD = st.secrets.get("COORD_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="GraphRAG MCP — Coordinator UI", layout="wide")
st.title("GraphRAG MCP — Local Coordinator UI")

tabs = st.tabs(["Chat", "Ask", "Search", "KG Browser", "Diagnostics"])

# -------------------
# NEW: Chat (Persona)
# -------------------
with tabs[0]:
    st.subheader("Chat (Persona Router)")
    colp1, colp2 = st.columns(2)
    with colp1:
        persona = st.selectbox("Persona", ["Nerdy Charming", "Professional", "Casual"], index=0)
    with colp2:
        topk = st.slider("Default Top-k for tools", 4, 32, 8)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # list of {"role","content"}

    for turn in st.session_state.chat_history:
        if turn["role"] == "user":
            st.chat_message("user").write(turn["content"])
        else:
            st.chat_message("assistant").write(turn["content"])

    user_input = st.chat_input("Type your message")
    if user_input:
        # Append user turn
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        payload = {
            "persona": persona,
            "history": st.session_state.chat_history[:-1],  # exclude current user turn
            "message": user_input,
            "k": topk,
        }
        try:
            r = requests.post(f"{COORD}/persona/chat", json=payload, timeout=180)
            data = r.json()
            if r.ok:
                answer = data.get("answer", "")
                used_tool = data.get("used_tool")
                # Show tool usage badge
                if used_tool:
                    with st.expander("Tool usage details"):
                        st.json(used_tool)
                st.chat_message("assistant").write(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            else:
                st.chat_message("assistant").write(f"Error: {data}")
                st.session_state.chat_history.append({"role": "assistant", "content": str(data)})
        except Exception as e:
            st.chat_message("assistant").write(f"Coordinator error: {e}")
            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})


# -------------------
# Existing: Ask (rag)
# -------------------
with tabs[1]:
    st.subheader("Ask (rag.qa)")
    q = st.text_area("Question", "What problem does Bitcoin aim to solve?", height=100)
    entities = st.text_input("Entity IRIs (comma-separated; optional)", "")
    k = st.slider("Top-k", 4, 32, 8, key="k_ask")
    col_llm1, col_llm2 = st.columns(2)
    with col_llm1:
        use_mock = st.checkbox("Use mock LLM", value=False)
    with col_llm2:
        model = st.text_input("Model override (optional)", "")
    if st.button("Answer"):
        payload = {
            "server": "rag",
            "tool": "rag.qa",
            "arguments": {
                "question": q,
                "k": k,
                "entity_ids": [e.strip() for e in entities.split(",")] if entities.strip() else None,
                "use_mock_llm": use_mock,
                "llm_model": model or None,
            }
        }
        r = requests.post(f"{COORD}/call", json=payload, timeout=120)
        st.write(r.json())
        if r.ok:
            res = r.json()["result"]
            st.markdown("### Answer")
            st.write(res["answer"])
            st.markdown("### Citations")
            for i, c in enumerate(res.get("citations", []), 1):
                with st.expander(f"[{i}] {c.get('doc_id')} — {c.get('chunk_id')}"):
                    st.write(c.get("text", ""))

# ----------------------
# Existing: Search (rag)
# ----------------------
with tabs[2]:
    st.subheader("Search (rag.search)")
    q = st.text_input("Query text", "consensus mechanism")
    k = st.slider("Top-k", 4, 32, 8, key="k_search")
    if st.button("Search", key="search_btn"):
        payload = {
            "server": "rag",
            "tool": "rag.search",
            "arguments": {"text": q, "k": k}
        }
        r = requests.post(f"{COORD}/call", json=payload, timeout=60)
        st.json(r.json())

# -----------------------
# Existing: KG Browser
# -----------------------
with tabs[3]:
    st.subheader("KG Browser")
    st.caption("Quick ping (kg.health) or run an ad-hoc SPARQL query.")
    if st.button("kg.health"):
        r = requests.post(f"{COORD}/call", json={
            "server": "kg",
            "tool": "kg.health",
            "arguments": {}
        }, timeout=30)
        st.json(r.json())
    sparql = st.text_area("SPARQL", "SELECT * WHERE { ?s ?p ?o } LIMIT 5", height=120)
    if st.button("Run SPARQL"):
        r = requests.post(f"{COORD}/call", json={
            "server": "kg",
            "tool": "sparql_query",
            "arguments": {"query": sparql}
        }, timeout=60)
        st.json(r.json())

# -----------------------
# Existing: Diagnostics
# -----------------------
with tabs[4]:
    st.subheader("Diagnostics")
    if st.button("List tools"):
        r = requests.get(f"{COORD}/tools", timeout=15)
        st.json(r.json())
    st.caption("Server configs (from MCP servers)")
    c1, c2 = st.columns(2)
    if c1.button("rag.server.config"):
        r = requests.post(f"{COORD}/call", json={"server":"rag","tool":"server.config","arguments":{}}, timeout=30)
        st.json(r.json())
    if c2.button("kg.server.config"):
        r = requests.post(f"{COORD}/call", json={"server":"kg","tool":"server.config","arguments":{}}, timeout=30)
        st.json(r.json())
