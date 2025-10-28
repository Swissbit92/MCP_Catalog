# ui/ui_tabs.py
# Header + Characters/Chat/Bio tabs + greeting + sidebar logo resolver

import time
import threading
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components  # for maybe_jump_to_chat animation

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import (
        USER_AVATAR, persona_assets_by_key, load_persona_cards,
        build_coordinator_label, resolve_card_image,
        display_name_to_tag, _file_to_data_uri
    )
except ImportError:
    from personas import (  # type: ignore
        USER_AVATAR, persona_assets_by_key, load_persona_cards,
        build_coordinator_label, resolve_card_image,
        display_name_to_tag, _file_to_data_uri
    )

try:
    from ui.ui_net import post_async
except ImportError:
    from ui_net import post_async  # type: ignore

# ---------- helpers ----------
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

# ---------- Header ----------
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

# ---------- Characters tab ----------
def render_characters_tab():
    st.subheader("Characters")

    # Persona search (stable size)
    with st.container():
        st.markdown('<div class="persona-search-wrap">', unsafe_allow_html=True)
        q = st.text_input(
            label="Search personas",
            value=st.session_state.get("persona_search",""),
            placeholder="Search by name, style, traits…",
            key="persona_search"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.caption("Pick your assistant. Cards are 2:3 — click **Choose** to select and unlock Chat & Bio.")
    cards = load_persona_cards(st.session_state.P_DIR)

    # Filter by query
    if q:
        ql = q.strip().lower()
        def match(card):
            fields = [
                str(card.get("key","")),
                str(card.get("display_name","")),
                str(card.get("style","")),
            ]
            fields += [d for d in (card.get("do") or []) if isinstance(d, str)]
            fields += [d for d in (card.get("dont") or []) if isinstance(d, str)]
            return any(ql in f.lower() for f in fields)
        cards = [c for c in cards if match(c)]

    # Render in rows of up to 5
    idx = 0
    MAX_COLS = 5
    while idx < len(cards):
        row_cards = cards[idx:idx+MAX_COLS]
        cols = st.columns(len(row_cards), gap="small")
        for col, card in zip(cols, row_cards):
            with col:
                key = (card.get("key") or "Eeva").split()[0].capitalize()
                disp = card.get("display_name", f"{key} — Nerdy Charming")
                tagline = card.get("style", "curious & kind")
                img_src = resolve_card_image(card, key)
                revealed = " revealed" if st.session_state.reveal_key == key else ""
                html_img = f"<img class='card-img' src='{img_src}' />" if img_src else (
                    "<div class='card-img' style='display:flex;align-items:center;justify-content:center;font-size:2rem;'>🎴</div>"
                )
                st.markdown(
                    f"""
                    <div class="card-outer{revealed}">
                      <div class="card-rarity"></div>
                      <div class="card-body">{html_img}
                        <div class="card-name">{disp}</div>
                        <div class="card-tagline">{tagline}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                choose = st.button("✨ Choose", key=f"choose-{key}", help=f"Select {disp}", type="secondary")
                if choose:
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

                    st.session_state.jump_to_chat = True
                    st.balloons()
                    st.rerun()
        idx += MAX_COLS

# ---------- Greeting (strictly once per persona) ----------
def maybe_greet_once(coord_url: str):
    persona = st.session_state.selected_persona
    if not persona:
        return
    if st.session_state.greet_done.get(persona, False):
        return
    greeted = st.session_state.greeted_for_persona.get(persona, False)
    inflight = st.session_state.greeting_inflight.get(persona, False)
    if greeted or inflight:
        return

    st.session_state.greeting_inflight[persona] = True
    st.session_state.greeting_error[persona] = False

    assistant_avatar = _assets_for_selected()["avatar"]
    msg_placeholder = st.empty()

    result: dict = {}
    t0 = time.perf_counter()
    thread = threading.Thread(
        target=post_async,
        args=(f"{coord_url}/persona/greet", {"persona": persona}, 120, result),
        daemon=True,
    )
    thread.start()

    frame_i = 0
    while thread.is_alive():
        with msg_placeholder.container():
            with st.chat_message("assistant", avatar=assistant_avatar):
                inner = st.empty()
                frames = ["_typing_", "_typing._", "_typing.._", "_typing..._"]
                inner.markdown(frames[frame_i % len(frames)])
                frame_i += 1
        time.sleep(0.25)

    st.session_state.greeting_inflight[persona] = False
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    st.session_state.last_latency_ms = elapsed_ms

    if result.get("ok"):
        data = result.get("json") or {}
        greet_text = (data.get("answer") or "").strip()
        if greet_text:
            st.session_state.chat_history.append({"role":"assistant","content":greet_text,"latency_ms":elapsed_ms})
            st.session_state.greeted_for_persona[persona] = True
            st.session_state.greet_done[persona] = True
            st.toast("Model is ready ✅", icon="✅")
        else:
            st.session_state.chat_history.append({"role":"assistant","content":"(Greeting error: empty response)"})
            st.session_state.greeting_error[persona] = True
            st.session_state.greet_done[persona] = True
    else:
        err = result.get("error") or f"HTTP {result.get('status_code')} {result.get('text')}"
        st.session_state.chat_history.append({"role":"assistant","content":f"(Greeting error) {err}"})
        st.session_state.greeting_error[persona] = True
        st.session_state.greet_done[persona] = True
        st.toast("Greeting failed", "⚠️")

    st.rerun()

# ---------- Chat tab ----------
def render_chat_tab(coord_url: str, model_name: str):
    render_header(model_name)
    if not st.session_state.selected_persona:
        st.info("Pick a character on the **Characters** tab to unlock chat.")
        return

    maybe_greet_once(coord_url)

    assistant_avatar = _assets_for_selected()["avatar"]
    user_avatar = USER_AVATAR

    c1, c2, _ = st.columns([1,1,6])
    with c1:
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []
            st.toast("Chat cleared.", icon="🧹")
    with c2:
        export_obj = {
            "persona": st.session_state.selected_persona,
            "model": model_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "history": st.session_state.chat_history,
        }
        st.download_button(
            "📥 Export (.json)",
            data=(__import__("json").dumps(export_obj, indent=2).encode("utf-8")),
            file_name="transcript.json",
            mime="application/json"
        )

    st.markdown("---")

    for m in st.session_state.chat_history:
        if m["role"] == "user":
            with st.chat_message("user", avatar=user_avatar):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar=assistant_avatar):
                st.markdown(m["content"])
                if "latency_ms" in m and isinstance(m["latency_ms"], int):
                    st.caption(f"⏱️ {m['latency_ms']} ms")

    user_in = st.chat_input("Type a message…")
    if user_in:
        st.session_state.chat_history.append({"role":"user","content":user_in})
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(user_in)

        payload = {
            "persona": st.session_state.selected_persona,
            "history": [h for h in st.session_state.chat_history[:-1]],
            "message": user_in
        }

        msg_placeholder = st.empty()
        result: dict = {}
        t0 = time.perf_counter()
        thread = threading.Thread(
            target=post_async,
            args=(f"{coord_url}/persona/chat", payload, 180, result),
            daemon=True,
        )
        thread.start()

        frame_i = 0
        while thread.is_alive():
            with msg_placeholder.container():
                with st.chat_message("assistant", avatar=assistant_avatar):
                    inner = st.empty()
                    frames = ["_typing_", "_typing._", "_typing.._", "_typing..._"]
                    inner.markdown(frames[frame_i % len(frames)])
                    frame_i += 1
            import time as _t; _t.sleep(0.25)

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        st.session_state.last_latency_ms = elapsed_ms

        if result.get("ok"):
            data = result.get("json") or {}
            ans = (data.get("answer") or "").strip()
            with msg_placeholder.container():
                with st.chat_message("assistant", avatar=assistant_avatar):
                    st.markdown(ans if ans else "(No answer)")
                    st.caption(f"⏱️ {elapsed_ms} ms")
            st.session_state.chat_history.append({"role":"assistant","content":ans if ans else "(No answer)","latency_ms":elapsed_ms})
        else:
            err = result.get("error") or f"HTTP {result.get('status_code')} {result.get('text')}"
            with msg_placeholder.container():
                with st.chat_message("assistant", avatar=assistant_avatar):
                    st.markdown(f"Error: {err}")
            st.session_state.chat_history.append({"role":"assistant","content":f"Error: {err}"})
            st.toast("Answer failed", icon="⚠️")

# ---------- Bio tab ----------
def render_bio_tab():
    render_header(st.session_state.MODEL)
    if not st.session_state.selected_persona:
        st.info("Pick a character on the **Characters** tab to view their bio.")
        return

    chosen = st.session_state.selected_key or "Eeva"
    cards = load_persona_cards(st.session_state.P_DIR)
    card = next((c for c in cards if c.get("key","").lower().startswith(chosen.lower())), None)
    if not card:
        st.warning("Persona card not found.")
        return

    assets = _assets_for_selected()
    left, right = st.columns([1,2], vertical_alignment="top")
    with left:
        # Prefer persona 'logo' → env logo → fallback to card image
        logo_uri = None
        if isinstance(card.get("logo"), str):
            logo_uri = _file_to_data_uri(card["logo"])
        if not logo_uri:
            env_logo = assets.get("logo")
            logo_uri = _file_to_data_uri(env_logo) if env_logo else None
        if not logo_uri:
            logo_uri = resolve_card_image(card, chosen)
        if logo_uri:
            st.image(logo_uri, width=240)

        st.markdown(f"**Persona:** {card.get('display_name','—')}")
        st.markdown(f"**Style:** {card.get('style','—')}")
        st.markdown("**Personality tics:**")
        for t in (card.get("voice",{}) or {}).get("tics", []):
            st.markdown(f"- {t}")
    with right:
        st.markdown("**Lore:**")
        for line in card.get("lore", []):
            st.markdown(f"- {line}")
        st.markdown("**Do:**")
        for d in card.get("do", []):
            st.markdown(f"- {d}")
        st.markdown("**Don’t:**")
        for d in card.get("dont", []):
            st.markdown(f"- {d}")

# ---------- After-select auto-jump to Chat ----------
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
