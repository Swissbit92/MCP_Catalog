# ui/tabs/common.py
# Shared helpers: header, jump-to-chat, sidebar logo resolver, selected assets.

import streamlit as st
import streamlit.components.v1 as components

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import (
        persona_assets_by_key, load_persona_cards,
        resolve_card_image, display_name_to_tag, _file_to_data_uri
    )
except ImportError:
    from personas import (  # type: ignore
        persona_assets_by_key, load_persona_cards,
        resolve_card_image, display_name_to_tag, _file_to_data_uri
    )

def _assets_for_selected():
    key = st.session_state.selected_key
    if not key:
        return {"logo": None, "avatar": "🤖", "tag": "—"}
    return persona_assets_by_key(key)

def _resolve_persona_logo_for_sidebar() -> str | None:
    """
    Resolve a clean logo for sidebar (prefer JSON logo → JSON image → env logo → card image → None).
    Returns data URI if resolvable.
    """
    key = st.session_state.selected_key
    if not key:
        return None
    cards = load_persona_cards(st.session_state.P_DIR)
    card = next((c for c in cards if str(c.get("key","")).lower().startswith(key.lower())), None)

    # 1) Persona JSON explicit logo
    if card and isinstance(card.get("logo"), str):
        uri = _file_to_data_uri(card["logo"])
        if uri:
            return uri
    # 2) Persona JSON image (card art)
    if card and isinstance(card.get("image"), str):
        uri = _file_to_data_uri(card["image"])
        if uri:
            return uri
    # 3) Env-based fallback
    assets = persona_assets_by_key(key)
    if assets.get("logo"):
        uri = _file_to_data_uri(assets["logo"])
        if uri:
            return uri
    # 4) As a last resort, try derived card image resolver
    if card:
        img = resolve_card_image(card, key)
        if img:
            return img
    return None

def render_header(model_name: str):
    assets = _assets_for_selected()
    greeted = st.session_state.greeted_for_persona.get(st.session_state.selected_persona or "", False)
    inflight = st.session_state.greeting_inflight.get(st.session_state.selected_persona or "", False)
    had_error = st.session_state.greeting_error.get(st.session_state.selected_persona or "", False)

    if had_error:
        status_chip = "<span class='chip chip-error'>Status: ⚠️ Error</span>"
    elif (st.session_state.selected_persona and (inflight or not greeted)):
        status_chip = "<span class='chip chip-warn'>Status: ⏳ Loading</span>"
    elif st.session_state.selected_persona:
        status_chip = "<span class='chip chip-success'>Status: ✅ Ready</span>"
    else:
        status_chip = "<span class='chip'>Status: —</span>"

    lat = st.session_state.last_latency_ms
    lat_chip = f"<span class='chip'>Latency: {lat} ms</span>" if isinstance(lat, int) else "<span class='chip'>Latency: —</span>"

    if st.session_state.selected_persona and st.session_state.selected_key:
        cards = load_persona_cards(st.session_state.P_DIR)
        disp = None
        for c in cards:
            if c.get("key","").lower().startswith(st.session_state.selected_key.lower()):
                disp = c.get("display_name")
                break
        tag_text = display_name_to_tag(disp, st.session_state.selected_key) if disp else assets["tag"]
        who_chip = f"<span class='chip chip-soft'>{tag_text}</span>"
    else:
        who_chip = ""

    st.markdown(
        f"""
        <div class="eeva-header">
          <span class="eeva-title">EEVA Persona Chat</span>
          {who_chip}<span class='chip'>Model: {model_name}</span>{status_chip}{lat_chip}
        </div>
        <div class="eeva-subtle">Enter to send · Shift+Enter for newline</div>
        """,
        unsafe_allow_html=True
    )

def maybe_jump_to_chat():
    if not st.session_state.jump_to_chat:
        return
    components.html(
        """
        <script>
        const goChat = () => {
          const tabs = Array.from(parent.document.querySelectorAll('button[role="tab"]'));
          const chat = tabs.find(btn => btn.innerText.trim().startsWith("💬"));
          if (chat) chat.click();
        };
        setTimeout(goChat, 60);
        </script>
        """,
        height=0
    )
    st.session_state.jump_to_chat = False
