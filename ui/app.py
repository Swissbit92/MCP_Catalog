# ui/app.py
# Streamlit UI for GraphRAG Local QA Chat with Personas
# Requires a running Local Coordinator backend.
import os
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _coord_url() -> str:
    return os.getenv("COORD_URL", "http://127.0.0.1:8000")

COORD = _coord_url()
st.set_page_config(page_title="GraphRAG — QA Chat (Local)", layout="wide")
st.title("GraphRAG — Local QA Chat (Personas)")

with st.sidebar:
    st.markdown("### Settings")
    persona = st.selectbox(
        "Persona",
        ["Eeva (Nerdy Charming)", "Cindy (Pragmatic Builder)"],
        index=0
    )
    st.caption(f"Coordinator: {COORD}")

# ----- Session state -----
if "chat_history" not in st.session_state:
    # list of {"role": "user"|"assistant", "content": str}
    st.session_state.chat_history = []

if "greeted_for_persona" not in st.session_state:
    # dict {persona_name: bool}
    st.session_state.greeted_for_persona = {}

# ----- One-time model greeting per persona -----
if not st.session_state.greeted_for_persona.get(persona, False):
    # Mark as greeted *before* the network call to avoid double-greet on reruns
    st.session_state.greeted_for_persona[persona] = True
    try:
        r = requests.post(
            f"{COORD}/persona/greet",
            json={"persona": persona},
            timeout=120
        )
        if r.ok:
            greet_text = (r.json() or {}).get("answer", "").strip()
            if greet_text:
                # Append to history only; DO NOT write directly to avoid duplicate rendering
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": greet_text}
                )
        else:
            # If coordinator returns error JSON, show a single inline note once
            msg = f"(Greeting error: {r.status_code} {r.text})"
            st.session_state.chat_history.append({"role": "assistant", "content": msg})
    except Exception as e:
        # Reset flag so we try again next load if you want; or keep it True to suppress
        st.session_state.greeted_for_persona[persona] = False
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"(Greeting error: {e})"}
        )

# ----- Render chat history (each message exactly once) -----
for m in st.session_state.chat_history:
    st.chat_message("user" if m["role"] == "user" else "assistant").write(m["content"])

# ----- Input & send -----
user_in = st.chat_input("Ask anything about your project, crypto, or the pipeline…")
if user_in:
    # Push user turn
    st.session_state.chat_history.append({"role": "user", "content": user_in})
    st.chat_message("user").write(user_in)

    payload = {
        "persona": persona,
        "history": st.session_state.chat_history[:-1],  # exclude current user turn
        "message": user_in
    }
    try:
        r = requests.post(f"{COORD}/persona/chat", json=payload, timeout=180)
        data = r.json()
        if r.ok:
            ans = data.get("answer", "").strip()
            st.chat_message("assistant").write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
        else:
            err = f"Error: {data}"
            st.chat_message("assistant").write(err)
            st.session_state.chat_history.append({"role": "assistant", "content": err})
    except Exception as e:
        err = f"Coordinator error: {e}"
        st.chat_message("assistant").write(err)
        st.session_state.chat_history.append({"role": "assistant", "content": err})
