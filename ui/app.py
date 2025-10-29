# ui/app.py
# Orchestrator for GraphRAG Coordinator UI — imports styles, tabs, personas.

import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import (
        coord_url, persona_model, persona_dir, APP_LOGO,
        load_persona_cards, build_coordinator_label
    )
    from ui.ui_style import inject_global_css_js
    # Split tabs (modular)
    from ui.tabs.characters import render_characters_tab
    from ui.tabs.chat import render_chat_tab
    from ui.tabs.bio import render_bio_tab
    from ui.tabs.common import maybe_jump_to_chat, _resolve_persona_logo_for_sidebar
except ImportError:
    from personas import (  # type: ignore
        coord_url, persona_model, persona_dir, APP_LOGO,
        load_persona_cards, build_coordinator_label
    )
    from ui_style import inject_global_css_js  # type: ignore
    from tabs.characters import render_characters_tab  # type: ignore
    from tabs.chat import render_chat_tab  # type: ignore
    from tabs.bio import render_bio_tab  # type: ignore
    from tabs.common import maybe_jump_to_chat, _resolve_persona_logo_for_sidebar  # type: ignore

# ---------- page config ----------
st.set_page_config(page_title="EEVA — GraphRAG Personas", page_icon="🃏", layout="wide")

# ---------- globals & session defaults ----------
COORD = coord_url()
MODEL = persona_model()
P_DIR = persona_dir()

# expose to tabs via session_state
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
st.session_state.setdefault("active_tab", "characters")  # characters | chat | bio
st.session_state.setdefault("mode_radio", "Local (Chat-only)")

# ---------- assets & CSS/JS ----------
inject_global_css_js()

# ---------- Query params sync ----------
try:
    qp = st.query_params  # new API

    # Active tab from ?tab=
    tab_q = qp.get("tab", "characters")
    if isinstance(tab_q, list):
        tab_q = tab_q[0] if tab_q else "characters"
    if tab_q in ("characters", "chat", "bio"):
        st.session_state.active_tab = tab_q

    # Handle selection from ?select=<Key>
    sel_q = qp.get("select", None)
    if isinstance(sel_q, list):
        sel_q = sel_q[0] if sel_q else None
    if sel_q:
        key = str(sel_q).strip()
        cards = load_persona_cards(P_DIR)
        card = next((c for c in cards if str(c.get("key", "")).lower().startswith(key.lower())), None)
        if card:
            new_persona = build_coordinator_label(card, key)
            if st.session_state.selected_persona != new_persona and st.session_state.clear_on_switch:
                st.session_state.chat_history = []
                st.toast("Chat cleared due to persona switch.", icon="🧹")

            st.session_state.selected_persona = new_persona
            st.session_state.selected_key = key
            st.session_state.reveal_key = key
            st.session_state.greeting_error[new_persona] = False
            st.session_state.greeted_for_persona[new_persona] = st.session_state.greeted_for_persona.get(new_persona, False)
            st.session_state.greet_done[new_persona] = st.session_state.greet_done.get(new_persona, False)

            # Jump to chat
            st.session_state.active_tab = "chat"
            st.session_state.jump_to_chat = True

        # Clean URL (remove select param after consumption) without opening new window
        try:
            current = dict(st.query_params)
            if "select" in current:
                del current["select"]
            st.query_params.clear()
            for k, v in current.items():
                if isinstance(v, list):
                    for item in v:
                        st.query_params.append(k, item)
                else:
                    st.query_params[k] = v
        except Exception:
            pass

except Exception:
    pass

# ---------- Sidebar ----------
with st.sidebar:
    if APP_LOGO:
        st.image(APP_LOGO, width=180)

    st.markdown("### ⚙️ Settings")
    st.session_state.mode_radio = st.radio(
        "Mode (future-ready):",
        options=["Local (Chat-only)", "Local + MCP (soon)"],
        index=0 if st.session_state.mode_radio.startswith("Local (Chat-only)") else 1,
        help="UI only for now. MCP routing to be enabled in a later update."
    )

    st.caption(f"Coordinator: {COORD}")
    st.caption(f"Model: {MODEL}")

    # Persona summary + logo (only if selected)
    sel_key = st.session_state.selected_key
    sel_label = st.session_state.selected_persona
    if sel_key and sel_label:
        # Embed persona logo only in Chat tab
        if st.session_state.active_tab == "chat":
            logo_uri = _resolve_persona_logo_for_sidebar()
            if logo_uri:
                st.image(logo_uri, width=160)
            else:
                # emoji fallback from persona json
                emoji = "🧠"
                try:
                    cards = load_persona_cards(P_DIR)
                    card = next((c for c in cards if str(c.get("key","")).lower().startswith(sel_key.lower())), None)
                    if card and isinstance(card.get("emoji"), str) and card["emoji"].strip():
                        emoji = card["emoji"].strip()
                except Exception:
                    pass
                st.markdown(f"<div style='font-size:42px;line-height:1;'>{emoji}</div>", unsafe_allow_html=True)

        # Always show summary + highlights
        try:
            cards = load_persona_cards(P_DIR)
            card = next((c for c in cards if str(c.get("key","")).lower().startswith(sel_key.lower())), None)
        except Exception:
            card = None
        if card:
            name_line = f"{card.get('key','—')} · {card.get('style','').strip()}"
            st.markdown(f"**{name_line}**")
            st.markdown("**Highlights:**")
            do_list = [d for d in (card.get("do") or []) if isinstance(d, str)]
            for d in do_list[:3]:
                st.write(f"• {d}")

    st.toggle(
        "Clear Chat on Persona Switch",
        key="clear_on_switch",
        help="If on, picking a different card clears the chat."
    )

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
