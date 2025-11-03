# ui/app.py
# Orchestrator for GraphRAG Coordinator UI — server-side router (single-panel render)

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
    # Tabs (modular; rendered lazily by router)
    from ui.tabs.characters import render_characters_tab
    from ui.tabs.chat import render_chat_tab
    from ui.tabs.bio import render_bio_tab
    from ui.tabs.common import _resolve_persona_logo_for_sidebar
except ImportError:
    from personas import (  # type: ignore
        coord_url, persona_model, persona_dir, APP_LOGO,
        load_persona_cards, build_coordinator_label
    )
    from ui_style import inject_global_css_js  # type: ignore
    from tabs.characters import render_characters_tab  # type: ignore
    from tabs.chat import render_chat_tab  # type: ignore
    from tabs.bio import render_bio_tab  # type: ignore
    from tabs.common import _resolve_persona_logo_for_sidebar  # type: ignore

# ---------- page config ----------
st.set_page_config(page_title="EEVA — GraphRAG Personas", page_icon="🃏", layout="wide")

# ---------- globals ----------
COORD = coord_url()
MODEL = persona_model()
P_DIR = persona_dir()

# ---------- session defaults ----------
ss = st.session_state
ss.setdefault("P_DIR", P_DIR)
ss.setdefault("MODEL", MODEL)
ss.setdefault("coord_url", COORD)  # expose to tabs (Bio uses it)

# persona selection / greeting state
ss.setdefault("selected_persona", None)   # pretty label (for greeter + header)
ss.setdefault("selected_key", None)       # short key (e.g., "Eeva")
ss.setdefault("reveal_key", None)
ss.setdefault("chat_history", [])
ss.setdefault("greeted_for_persona", {})     # keyed by pretty label
ss.setdefault("greeting_inflight", {})       # keyed by pretty label
ss.setdefault("greeting_error", {})          # keyed by pretty label
ss.setdefault("greet_done", {})              # keyed by pretty label
ss.setdefault("last_latency_ms", None)

# router state
ss.setdefault("active_tab", "characters")    # authoritative: "characters" | "chat" | "bio"
ss.setdefault("mode_radio", "Local (Chat-only)")

# chats (session-only MVP)
ss.setdefault("chats", {})                    # id -> {persona_key,title,messages,created_at}
ss.setdefault("active_chat_id", None)
ss.setdefault("persona_chat_counters", {})    # persona_key -> next index (int)

def _now_ms() -> int:
    return int(time.time() * 1000)

def _new_chat_id() -> str:
    base = str(len(ss.chats) + 1)
    return f"c{base.zfill(3)}"

def _default_title(persona_key: str) -> str:
    ctr = ss.persona_chat_counters.get(persona_key, 1)
    title = f"{persona_key}: chat {ctr:02d}"
    ss.persona_chat_counters[persona_key] = ctr + 1
    return title

def _find_card_for_key(key: str):
    cards = load_persona_cards(P_DIR)
    return next((c for c in cards if str(c.get("key","")).lower().startswith(str(key).lower())), None)

def _ensure_greet_keys_for_label(label: str):
    if label not in ss.greeted_for_persona:
        ss.greeted_for_persona[label] = False
    if label not in ss.greet_done:
        ss.greet_done[label] = False
    if label not in ss.greeting_inflight:
        ss.greeting_inflight[label] = False
    if label not in ss.greeting_error:
        ss.greeting_error[label] = False

def _fallback_welcome(card: dict, persona_key: str) -> str:
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
    chat = ss.chats.get(chat_id)
    if not chat:
        return
    if chat.get("messages"):
        return
    pkey = chat.get("persona_key","")
    card = _find_card_for_key(pkey) or {}
    first = _fallback_welcome(card, pkey)
    chat["messages"] = [{"role": "assistant", "content": first}]
    if ss.active_chat_id == chat_id:
        ss.chat_history = list(chat["messages"])
    label = build_coordinator_label(card, pkey) if card else pkey
    _ensure_greet_keys_for_label(label)
    ss.greeted_for_persona[label] = True
    ss.greet_done[label] = True

def create_chat_for_persona(persona_key: str) -> str:
    chat_id = _new_chat_id()
    ss.chats[chat_id] = {
        "persona_key": persona_key,
        "title": _default_title(persona_key),
        "messages": [],
        "created_at": _now_ms(),
    }
    ss.active_chat_id = chat_id
    card = _find_card_for_key(persona_key)
    label = build_coordinator_label(card, persona_key) if card else persona_key
    ss.selected_key = persona_key
    ss.selected_persona = label
    ss.reveal_key = persona_key
    _ensure_greet_keys_for_label(label)
    _inject_first_message_if_empty(chat_id)
    # router intent: go to chat for brand-new chats
    ss.active_tab = "chat"
    try:
        st.query_params["tab"] = "chat"
    except Exception:
        pass
    st.rerun()

# ---------- assets & CSS/JS ----------
inject_global_css_js()

# ---------- Query params sync & selection logic (TOP, before rendering) ----------
try:
    qp = st.query_params  # new API

    # Sync router from ?tab=
    tab_q = qp.get("tab", ss.active_tab)
    if isinstance(tab_q, list):
        tab_q = tab_q[0] if tab_q else ss.active_tab
    if tab_q in ("characters", "chat", "bio"):
        ss.active_tab = tab_q

    # Handle persona selection from ?select=<Key>
    sel_q = qp.get("select", None)
    if isinstance(sel_q, list):
        sel_q = sel_q[0] if sel_q else None
    if sel_q:
        key = str(sel_q).strip()
        card = _find_card_for_key(key)
        if card:
            new_persona = build_coordinator_label(card, key)
            ss.selected_persona = new_persona
            ss.selected_key = key
            ss.reveal_key = key
            _ensure_greet_keys_for_label(new_persona)

            # Focus logic matching your requirement:
            # If persona has existing chats -> activate most recent, STAY on Characters.
            # If none -> create a new chat and route to Chat.
            chats = ss.chats or {}
            persona_chats = [(cid, c) for cid, c in chats.items() if c.get("persona_key") == key]
            if persona_chats:
                cid, _c = max(persona_chats, key=lambda kv: kv[1].get("created_at", 0))
                ss.active_chat_id = cid
                _inject_first_message_if_empty(cid)
                # stay on Characters (no router change)
            else:
                create_chat_for_persona(key)  # will set active_tab='chat' and rerun

        # Clean select once consumed (keep tab intact)
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
        chat = ss.chats.get(chat_id)
        if chat:
            ss.active_chat_id = chat_id
            key = chat.get("persona_key")
            card = _find_card_for_key(key) if key else None
            if card:
                label = build_coordinator_label(card, key)
                ss.selected_persona = label
                ss.selected_key = key
                ss.reveal_key = key
                _ensure_greet_keys_for_label(label)
            _inject_first_message_if_empty(chat_id)
            ss.active_tab = "chat"
            try:
                st.query_params["tab"] = "chat"
            except Exception:
                pass
            st.rerun()

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
        if ss.selected_key:
            create_chat_for_persona(ss.selected_key)  # will route & rerun
        else:
            st.info("Pick a persona in the Characters tab first.", icon="🃏")

    chats = ss.chats
    if chats:
        try:
            cards = load_persona_cards(P_DIR)
            card_map = {str(c.get("key","")): c for c in cards}
        except Exception:
            card_map = {}

        active_id = ss.active_chat_id
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
                # Route deterministically to Chat and make this chat active
                ss.active_chat_id = cid
                ss.selected_key = pkey
                pretty = build_coordinator_label(card, pkey) if card else pkey
                ss.selected_persona = pretty
                ss.reveal_key = pkey
                _ensure_greet_keys_for_label(pretty)
                _inject_first_message_if_empty(cid)
                ss.active_tab = "chat"
                try:
                    st.query_params["tab"] = "chat"
                except Exception:
                    pass
                st.rerun()
        if active_id is None and ss.selected_key:
            # If a persona is selected but no chat exists, create one lazily
            create_chat_for_persona(ss.selected_key)  # will route & rerun
    else:
        st.caption("No chats yet — create one or select a persona to start.")

    st.markdown("### ⚙️ Settings")
    ss.mode_radio = st.radio(
        "Mode (future-ready):",
        options=["Local (Chat-only)", "Local + MCP (soon)"],
        index=0 if ss.mode_radio.startswith("Local (Chat-only)") else 1,
        help="UI only for now. MCP routing to be enabled in a later update."
    )

    st.caption(f"Coordinator: {COORD}")
    st.caption(f"Model: {MODEL}")

    # Persona summary + logo (only if selected; only visual here)
    sel_key = ss.selected_key
    sel_label = ss.selected_persona
    if sel_key and sel_label:
        if ss.active_tab == "chat":
            logo_uri = _resolve_persona_logo_for_sidebar()
            if logo_uri:
                st.image(logo_uri, width=160)
            else:
                # emoji fallback
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

# ---------- Top navigation (server-side router control) ----------
# Use a compact horizontal radio (segmented control look) to pick the active panel.
tab_label_map = {
    "characters": "🃏 Characters",
    "chat": "💬 Chat",
    "bio": "📜 Bio",
}
current_label = tab_label_map.get(ss.active_tab, "🃏 Characters")

choice = st.radio(
    "Navigation",
    options=["🃏 Characters", "💬 Chat", "📜 Bio"],
    index=["🃏 Characters", "💬 Chat", "📜 Bio"].index(current_label),
    horizontal=True,
    label_visibility="collapsed",
)

# Map back to key
rev_map = {v: k for k, v in tab_label_map.items()}
new_active = rev_map.get(choice, "characters")
if new_active != ss.active_tab:
    ss.active_tab = new_active
    try:
        st.query_params["tab"] = new_active
    except Exception:
        pass
    st.rerun()

# ---------- Render ONE panel per rerun (no eager multi-tab rendering) ----------
def _sync_into_chat_history():
    chat_id = ss.active_chat_id
    if not chat_id:
        return
    chat = ss.chats.get(chat_id)
    if not chat:
        return
    ss.chat_history = list(chat.get("messages", []))

def _sync_back_from_chat_history():
    chat_id = ss.active_chat_id
    if not chat_id:
        return
    chat = ss.chats.get(chat_id)
    if not chat:
        return
    chat["messages"] = list(ss.chat_history or [])

if ss.active_tab == "characters":
    render_characters_tab()

elif ss.active_tab == "chat":
    # Small header for active chat (emoji + title)
    cards = []
    try:
        cards = load_persona_cards(P_DIR)
    except Exception:
        pass
    card_map = {str(c.get("key","")): c for c in (cards or [])}
    chat_id = ss.active_chat_id
    chat = ss.chats.get(chat_id) if chat_id else None
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

elif ss.active_tab == "bio":
    # Bio does work ONLY when active (no race with Chat)
    render_bio_tab()
