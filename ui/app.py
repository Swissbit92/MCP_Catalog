# ui/app.py
# Orchestrator for GraphRAG Coordinator UI — imports styles, tabs, personas.

import os
import time
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
st.session_state.setdefault("selected_persona", None)  # pretty label used by greeter
st.session_state.setdefault("selected_key", None)      # short key (e.g., "Eeva")
st.session_state.setdefault("reveal_key", None)
st.session_state.setdefault("jump_to_chat", False)
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("greeted_for_persona", {})   # keyed by pretty label
st.session_state.setdefault("greeting_inflight", {})     # keyed by pretty label
st.session_state.setdefault("greeting_error", {})        # keyed by pretty label
st.session_state.setdefault("last_latency_ms", None)
st.session_state.setdefault("greet_done", {})            # keyed by pretty label
st.session_state.setdefault("clear_on_switch", True)
st.session_state.setdefault("active_tab", "characters")  # characters | chat | bio
st.session_state.setdefault("mode_radio", "Local (Chat-only)")

# --- session-only chats (MVP) ---
st.session_state.setdefault("chats", {})                    # id -> {persona_key,title,messages,created_at}
st.session_state.setdefault("active_chat_id", None)         # current chat id
st.session_state.setdefault("persona_chat_counters", {})    # persona_key -> next index (int)

def _now_ms() -> int:
    return int(time.time() * 1000)

def _new_chat_id() -> str:
    base = str(len(st.session_state.chats) + 1)
    return f"c{base.zfill(3)}"

def _default_title(persona_key: str) -> str:
    ctr = st.session_state.persona_chat_counters.get(persona_key, 1)
    title = f"{persona_key}: chat {ctr:02d}"
    st.session_state.persona_chat_counters[persona_key] = ctr + 1
    return title

def _find_card_for_key(key: str):
    cards = load_persona_cards(P_DIR)
    return next((c for c in cards if str(c.get("key","")).lower().startswith(str(key).lower())), None)

def _ensure_greet_keys_for_label(label: str):
    """Make sure greeter dicts have an entry for the pretty persona label."""
    if label not in st.session_state.greeted_for_persona:
        st.session_state.greeted_for_persona[label] = False
    if label not in st.session_state.greet_done:
        st.session_state.greet_done[label] = False
    if label not in st.session_state.greeting_inflight:
        st.session_state.greeting_inflight[label] = False
    if label not in st.session_state.greeting_error:
        st.session_state.greeting_error[label] = False

def _fallback_welcome(card: dict, persona_key: str) -> str:
    """Build a safe first-line welcome from card fields."""
    name = (card.get("key") or persona_key).strip()
    emoji = (card.get("emoji") or "✨") if isinstance(card.get("emoji"), str) else "✨"
    welcome = ""
    for k in ("welcome", "greeting", "intro", "tagline"):
        val = card.get(k)
        if isinstance(val, str) and val.strip():
            welcome = val.strip()
            break
    if not welcome:
        welcome = "Ready to help with crypto research, GraphRAG queries, and MCP tools."
    return f"{emoji} **{name}** here — {welcome}"

def _inject_first_message_if_empty(chat_id: str):
    """Ensure a welcome message exists when a chat is brand-new (fallback path)."""
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        return
    if chat.get("messages"):
        return  # already has content
    pkey = chat.get("persona_key","")
    card = _find_card_for_key(pkey) or {}
    first = _fallback_welcome(card, pkey)
    chat["messages"] = [{"role": "assistant", "content": first}]
    # mirror into chat_history for current render if this is the active chat
    if st.session_state.active_chat_id == chat_id:
        st.session_state.chat_history = list(chat["messages"])
    # mark greeted flags for the pretty label (so we don't double-greet)
    label = build_coordinator_label(card, pkey) if card else pkey
    _ensure_greet_keys_for_label(label)
    st.session_state.greeted_for_persona[label] = True
    st.session_state.greet_done[label] = True

def create_chat_for_persona(persona_key: str) -> str:
    """Create a new empty chat for persona_key and make it active."""
    chat_id = _new_chat_id()
    st.session_state.chats[chat_id] = {
        "persona_key": persona_key,
        "title": _default_title(persona_key),
        "messages": [],
        "created_at": _now_ms(),
    }
    st.session_state.active_chat_id = chat_id

    # Set selected persona + label and ensure greeter flags under the pretty label
    card = _find_card_for_key(persona_key)
    label = build_coordinator_label(card, persona_key) if card else persona_key
    st.session_state.selected_key = persona_key
    st.session_state.selected_persona = label
    st.session_state.reveal_key = persona_key
    _ensure_greet_keys_for_label(label)

    # Guaranteed welcome line (fallback) — keeps UX snappy even if router greet is delayed
    _inject_first_message_if_empty(chat_id)

    # Make sure UI jumps to Chat so the greeter logic can run
    st.session_state.active_tab = "chat"
    st.session_state.jump_to_chat = True
    return chat_id

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
        card = _find_card_for_key(key)
        if card:
            new_persona = build_coordinator_label(card, key)  # pretty label
            if st.session_state.selected_persona != new_persona and st.session_state.clear_on_switch:
                st.session_state.chat_history = []
                st.toast("Chat cleared due to persona switch.", icon="🧹")

            st.session_state.selected_persona = new_persona
            st.session_state.selected_key = key
            st.session_state.reveal_key = key
            _ensure_greet_keys_for_label(new_persona)

            # Ensure a chat exists for this persona and jump to chat
            active = st.session_state.chats.get(st.session_state.active_chat_id) if st.session_state.active_chat_id else None
            if (not active) or active.get("persona_key") != key:
                cid = create_chat_for_persona(key)
                _inject_first_message_if_empty(cid)
            else:
                _inject_first_message_if_empty(st.session_state.active_chat_id)
                st.session_state.active_tab = "chat"
                st.session_state.jump_to_chat = True

        # Clean URL (remove select param after consumption)
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

    # Handle ?chat=<id> (compat)
    chat_q = qp.get("chat", None)
    if isinstance(chat_q, list):
        chat_q = chat_q[0] if chat_q else None
    if chat_q:
        chat_id = str(chat_q).strip()
        chat = st.session_state.chats.get(chat_id)
        if chat:
            st.session_state.active_chat_id = chat_id
            key = chat.get("persona_key")
            card = _find_card_for_key(key) if key else None
            if card:
                label = build_coordinator_label(card, key)
                st.session_state.selected_persona = label
                st.session_state.selected_key = key
                st.session_state.reveal_key = key
                _ensure_greet_keys_for_label(label)
            _inject_first_message_if_empty(chat_id)
            st.session_state.active_tab = "chat"
            st.session_state.jump_to_chat = True

        # Clean chat param
        try:
            current = dict(st.query_params)
            if "chat" in current:
                del current["chat"]
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

    # --- simple chat list (session-only) ---
    st.markdown("### 💬 Chats")
    if st.button("＋ New Chat", use_container_width=True, help="Create a chat for the selected persona"):
        if st.session_state.selected_key:
            create_chat_for_persona(st.session_state.selected_key)
            st.rerun()
        else:
            st.info("Pick a persona in the Characters tab first.", icon="🃏")

    chats = st.session_state.chats
    if chats:
        # load persona cards for emoji/rarity display
        try:
            cards = load_persona_cards(P_DIR)
            card_map = {str(c.get("key","")): c for c in cards}
        except Exception:
            card_map = {}

        active_id = st.session_state.active_chat_id
        # Render as real buttons; highlight the active one via type="primary"
        for cid, cdata in sorted(chats.items(), key=lambda kv: kv[1].get("created_at", 0)):
            pkey = cdata.get("persona_key","")
            card = card_map.get(pkey) or {}
            emoji = (card.get("emoji") or "💬") if isinstance(card.get("emoji"), str) else "💬"
            title = cdata.get("title") or f"{pkey}: chat"
            label = f"{emoji}  {title}"
            is_active = (cid == active_id)
            if st.button(
                label,
                key=f"chatbtn_{cid}",
                use_container_width=True,
                type=("primary" if is_active else "secondary")
            ):
                # Update selected chat + persona, jump to chat, ensure greeter keys
                st.session_state.active_chat_id = cid
                st.session_state.selected_key = pkey
                pretty = build_coordinator_label(card, pkey) if card else pkey
                st.session_state.selected_persona = pretty
                st.session_state.reveal_key = pkey
                _ensure_greet_keys_for_label(pretty)
                _inject_first_message_if_empty(cid)
                st.session_state.active_tab = "chat"
                st.session_state.jump_to_chat = True
                st.rerun()
        if active_id is None and st.session_state.selected_key:
            # If a persona is selected but no chat exists, create one lazily
            cid = create_chat_for_persona(st.session_state.selected_key)
            _inject_first_message_if_empty(cid)
            st.rerun()
    else:
        st.caption("No chats yet — create one or select a persona to start.")

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
        if st.session_state.active_tab == "chat":
            logo_uri = _resolve_persona_logo_for_sidebar()
            if logo_uri:
                st.image(logo_uri, width=160)
            else:
                emoji = "🧠"
                try:
                    cards = load_persona_cards(P_DIR)
                    card = next((c for c in cards if str(c.get("key","")).lower().startswith(sel_key.lower())), None)
                    if card and isinstance(card.get("emoji"), str) and card["emoji"].strip():
                        emoji = card["emoji"].strip()
                except Exception:
                    pass
                st.markdown(f"<div style='font-size:42px;line-height:1;'>{emoji}</div>", unsafe_allow_html=True)

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

# Auto-jump if a persona was selected or a chat was chosen
maybe_jump_to_chat()

# ---- Sync active chat <-> chat_history (session-only MVP) ----
def _sync_into_chat_history():
    chat_id = st.session_state.active_chat_id
    if not chat_id:
        return
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        return
    st.session_state.chat_history = list(chat.get("messages", []))

def _sync_back_from_chat_history():
    chat_id = st.session_state.active_chat_id
    if not chat_id:
        return
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        return
    chat["messages"] = list(st.session_state.chat_history or [])

with tab_chars:
    render_characters_tab()

with tab_chat:
    # --- Header showing active chat title + persona emoji ---
    cards = []
    try:
        cards = load_persona_cards(P_DIR)
    except Exception:
        pass
    card_map = {str(c.get("key","")): c for c in (cards or [])}
    chat_id = st.session_state.active_chat_id
    chat = st.session_state.chats.get(chat_id) if chat_id else None
    if chat:
        pkey = chat.get("persona_key","")
        card = card_map.get(pkey) or {}
        emoji = (card.get("emoji") or "💬") if isinstance(card.get("emoji"), str) else "💬"
        title = chat.get("title") or f"{pkey}: chat"
        st.markdown(
            f"""
            <div class="eeva-header">
              <div class="chip">{emoji}</div>
              <div class="eeva-title">{title}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    _sync_into_chat_history()
    render_chat_tab(COORD, MODEL)
    _sync_back_from_chat_history()

with tab_bio:
    render_bio_tab()
