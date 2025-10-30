# ui/tabs/chat.py
# Chat tab: greeting-once, message loop, export; uses common header + assets.

import time
import threading
from datetime import datetime
import json  # added for export serialization

import streamlit as st

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import USER_AVATAR
    from ui.tabs.common import render_header, _assets_for_selected
    from ui.ui_net import post_async
except ImportError:
    from personas import USER_AVATAR  # type: ignore
    from tabs.common import render_header, _assets_for_selected  # type: ignore
    from ui_net import post_async  # type: ignore


def _maybe_greet_once(coord_url: str):
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


def render_chat_tab(coord_url: str, model_name: str):
    render_header(model_name)
    if not st.session_state.selected_persona:
        st.info("Pick a character on the **Characters** tab to unlock chat.")
        return

    _maybe_greet_once(coord_url)

    assistant_avatar = _assets_for_selected()["avatar"]
    user_avatar = USER_AVATAR

    # ---------- Icon-only toolbar (stable single row) ----------
    # Left: 🧹 clear (native st.button so it clears in-place)
    # Right: 📥 export (native st.download_button for a JSON file)
    col_clear, col_export, _spacer = st.columns([0.07, 0.07, 0.86], gap="small")

    with col_clear:
        if st.button("🧹", help="Clear chat", use_container_width=True, key="btn_clear_chat"):
            st.session_state.chat_history = []
            st.toast("Chat cleared.", icon="🧹")
            st.rerun()

    with col_export:
        export_obj = {
            "persona": st.session_state.selected_persona,
            "model": model_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "history": st.session_state.chat_history,
        }
        st.download_button(
            "📥",
            data=(json.dumps(export_obj, indent=2).encode("utf-8")),
            file_name="transcript.json",
            mime="application/json",
            help="Export transcript (.json)",
            use_container_width=True,
            key="btn_export_json",
        )

    st.markdown("---")

    # ---------- History ----------
    for m in st.session_state.chat_history:
        if m["role"] == "user":
            with st.chat_message("user", avatar=user_avatar):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar=assistant_avatar):
                st.markdown(m["content"])
                if "latency_ms" in m and isinstance(m["latency_ms"], int):
                    st.caption(f"⏱️ {m['latency_ms']} ms")

    # ---------- Input ----------
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
