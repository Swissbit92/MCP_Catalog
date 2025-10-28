# ui/app.py
# Orchestrator for GraphRAG Coordinator UI — imports helpers and personas.

import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import coord_url, persona_model, persona_dir, APP_LOGO
    from ui.ui_helpers import (
        inject_global_css_js, render_characters_tab, render_chat_tab,
        render_bio_tab, maybe_jump_to_chat
    )
except ImportError:
    from personas import coord_url, persona_model, persona_dir, APP_LOGO  # type: ignore
    from ui_helpers import (  # type: ignore
        inject_global_css_js, render_characters_tab, render_chat_tab,
        render_bio_tab, maybe_jump_to_chat
    )

# ---------- page config ----------
st.set_page_config(page_title="EEVA — GraphRAG Personas", page_icon="🃏", layout="wide")

# ---------- globals & session defaults ----------
COORD = coord_url()
MODEL = persona_model()
P_DIR = persona_dir()

# make available to helpers via session_state (simple and explicit)
st.session_state.setdefault("P_DIR", P_DIR)
st.session_state.setdefault("MODEL", MODEL)

# session defaults
st.session_state.setdefault("selected_persona", None)
st.session_state.setdefault("selected_key", None)
st.session_state.setdefault("reveal_key", None)
st.session_state.setdefault("jump_to_chat", False)
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("greeted_for_persona", {})
st.session_state.setdefault("greeting_inflight", {})
st.session_state.setdefault("greeting_error", {})
st.session_state.setdefault("last_latency_ms", None)
st.session_state.setdefault("greet_done", {})
st.session_state.setdefault("clear_on_switch", True)

# ---------- assets & CSS/JS ----------
inject_global_css_js()

# ---------- Sidebar ----------
with st.sidebar:
    if APP_LOGO:
        st.image(APP_LOGO, width=180)
    st.markdown("### ⚙️ Settings")
    st.toggle("Clear Chat on Persona Switch", key="clear_on_switch",
              help="If on, picking a different card clears the chat.")
    st.caption(f"Coordinator: {COORD}")
    st.caption(f"Model: {MODEL}")

# ---------- Tabs ----------
tab_chars, tab_chat, tab_bio = st.tabs(["🃏 Characters", "💬 Chat", "📜 Bio"])

# Auto-jump if a persona was selected
maybe_jump_to_chat()

with tab_chars:
    render_characters_tab()

with tab_chat:
    render_chat_tab(COORD, MODEL)

with tab_bio:
    render_bio_tab()
