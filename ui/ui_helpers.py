# ui/ui_helpers.py
# Streamlit UI rendering, CSS/JS, async HTTP, and chat/greet logic.

import time
import threading
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import (
        APP_LOGO, USER_AVATAR, persona_assets_by_key,
        load_persona_cards, build_coordinator_label, resolve_card_image,
        display_name_to_tag, _file_to_data_uri
    )
except ImportError:
    from personas import (  # type: ignore
        APP_LOGO, USER_AVATAR, persona_assets_by_key,
        load_persona_cards, build_coordinator_label, resolve_card_image,
        display_name_to_tag, _file_to_data_uri
    )

# ---------- CSS + JS injection ----------
def inject_global_css_js():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.0rem; padding-bottom: 7.5rem; }
    div[data-testid="column"] { padding-left: 4px !important; padding-right: 4px !important; }

    button[role="tab"], button[role="tab"] * { color: #1f2937 !important; }
    button[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] * {
      color: #111827 !important; font-weight: 700 !important;
    }
    @media (prefers-color-scheme: dark) {
      button[role="tab"], button[role="tab"] * { color: #e5e7eb !important; }
      button[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] * { color: #ffffff !important; }
    }

    .eeva-header { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:8px 0 4px 0; }
    .eeva-title { font-size:22px; font-weight:600; }
    .chip { padding:2px 10px; border-radius:12px; background:#f7f7f9; border:1px solid #d0d0d6; color:#222; font-size:0.85rem; }
    .chip-success { background:#e6ffe6; border:1px solid #b3ffb3; color:#155e2b; }
    .chip-soft  { background:#eef; border:1px solid #ccd; color:#1f2a44; }
    .chip-warn  { background:#fff7e6; border:1px solid #ffd699; color:#8a6100; }
    .chip-error { background:#ffe6e6; border:1px solid #ffb3b3; color:#7a1f1f; }
    @media (prefers-color-scheme: dark) {
      .chip { background:#1f2937; border:1px solid #374151; color:#e5e7eb; }
      .chip-success { background:#064e3b; border:1px solid #10b981; color:#d1fae5; }
      .chip-soft { background:#1e293b; border:1px solid #334155; color:#e2e8f0; }
      .chip-warn { background:#4a3b13; border:1px solid #f59e0b; color:#fde68a; }
      .chip-error { background:#4c1d1d; border:1px solid #f87171; color:#fecaca; }
    }
    .eeva-subtle { color:#6b6b6b; margin-bottom:10px; }
    @media (prefers-color-scheme: dark) { .eeva-subtle { color:#a3a3a3; } }

    .card-outer { width:192px; height:288px; border-radius:16px; position:relative; overflow:hidden;
      box-shadow:0 10px 18px rgba(0,0,0,0.25);
      background:linear-gradient(135deg, rgba(255,255,255,0.75), rgba(200,220,255,0.55), rgba(255,215,240,0.55));
      border:1px solid rgba(255,255,255,0.6); transition:transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
      backdrop-filter:blur(6px); margin-bottom:8px;
    }
    .card-outer:hover { transform:translateY(-3px) rotateZ(-0.35deg); box-shadow:0 14px 24px rgba(0,0,0,0.3); filter:saturate(1.05); }
    .card-outer.revealed { box-shadow:0 0 20px 3px rgba(80,200,255,0.85), inset 0 0 16px rgba(255,255,255,0.5); border-color:rgba(80,200,255,0.85); }
    .card-rarity { position:absolute; inset:0; background:conic-gradient(from 180deg at 50% 50%, rgba(255,255,255,0.12), rgba(0,0,0,0.12), rgba(255,255,255,0.12)); mix-blend-mode:soft-light; pointer-events:none; }
    .card-body { position:relative; height:100%; display:flex; flex-direction:column; align-items:center; padding:10px; }
    .card-img { width:100%; height:60%; object-fit:cover; border-radius:12px; border:1px solid rgba(0,0,0,0.05); }
    .card-name { margin-top:8px; font-weight:700; font-size:0.98rem; text-align:center; }
    .card-tagline { font-size:0.82rem; opacity:0.95; text-align:center; min-height: 2.1em; }

    @media (prefers-color-scheme: dark) {
      .card-outer { border-color:#2f3542; background:linear-gradient(135deg, rgba(23,30,45,0.85), rgba(32,40,60,0.7)); }
    }

    [data-testid="stChatInput"] {
      position: fixed !important; bottom: 0 !important; z-index: 999 !important;
      padding-top: 0.35rem; padding-bottom: 0.35rem;
      background: rgba(255,255,255,0.88); backdrop-filter: blur(6px);
      border-top: 1px solid rgba(0,0,0,0.08);
    }
    @media (prefers-color-scheme: dark) {
      [data-testid="stChatInput"] {
        background: rgba(17,24,39,0.88);
        border-top: 1px solid rgba(255,255,255,0.12);
      }
    }
    </style>
    """, unsafe_allow_html=True)

    components.html(
        """
        <script>
        const fitChatInput = () => {
          const input = parent.document.querySelector('[data-testid="stChatInput"]');
          const main  = parent.document.querySelector('.block-container');
          if (!input || !main) return;
          const rect = main.getBoundingClientRect();
          input.style.left = rect.left + 'px';
          input.style.width = rect.width + 'px';
        };
        new ResizeObserver(fitChatInput).observe(parent.document.body);
        window.addEventListener('resize', fitChatInput);
        setTimeout(fitChatInput, 60);
        setTimeout(fitChatInput, 300);
        </script>
        """,
        height=0
    )

# ---------- HTTP helper ----------
def post_async(url: str, payload: dict, timeout: int, out_dict: dict):
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        try:
            out_dict["json"] = resp.json()
        except Exception:
            out_dict["json"] = None
        out_dict["text"] = resp.text
        out_dict["ok"] = resp.ok
        out_dict["status_code"] = resp.status_code
    except Exception as e:
        out_dict["error"] = str(e)
        out_dict["ok"] = False

def _assets_for_selected():
    key = st.session_state.selected_key
    if not key:
        return {"logo": None, "avatar": "🤖", "tag": "—"}
    return persona_assets_by_key(key)

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
    st.caption("Pick your assistant. Cards are 2:3 — click **Choose** to select and unlock Chat & Bio.")

    cards = load_persona_cards(st.session_state.P_DIR)
    idx = 0
    while idx < len(cards):
        row_cards = cards[idx:idx+3]
        cols = st.columns(3, gap="small")
        positions = [0] if len(row_cards) == 1 else ([0,1] if len(row_cards) == 2 else [0,1,2])
        for rpos, card in zip(positions, row_cards):
            with cols[rpos]:
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
        idx += 3

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
        logo_uri = resolve_card_image(card, chosen) or _file_to_data_uri(assets["logo"] or "")
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
