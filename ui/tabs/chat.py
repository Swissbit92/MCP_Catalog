# ui/tabs/chat.py
# Chat tab: greeting-once (model, per-chat), message loop, export; uses common header + assets.

import time
import threading
from datetime import datetime
import json  # export serialization

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


# ---------------------------
# Model greet state (per-chat)
# ---------------------------

def _ensure_model_greet_dicts_for_chat(chat_id: str):
    """
    Ensure dedicated flags for the *model-generated* greeting exist for this chat.
    This is per-chat so new chats always get a fresh model greet.
    """
    st.session_state.setdefault("model_greet_done_by_chat", {})
    st.session_state.setdefault("model_greet_inflight_by_chat", {})
    st.session_state.setdefault("model_greet_error_by_chat", {})

    if chat_id not in st.session_state.model_greet_done_by_chat:
        st.session_state.model_greet_done_by_chat[chat_id] = False
    if chat_id not in st.session_state.model_greet_inflight_by_chat:
        st.session_state.model_greet_inflight_by_chat[chat_id] = False
    if chat_id not in st.session_state.model_greet_error_by_chat:
        st.session_state.model_greet_error_by_chat[chat_id] = False


def _replace_fallback_if_present(greet_text: str, elapsed_ms: int):
    """
    If the chat currently contains exactly one assistant message *without* latency_ms,
    treat it as a placeholder/fallback and replace it with the model greet.
    Otherwise, append the greet as a new assistant message.
    """
    hist = st.session_state.chat_history or []
    if (
        len(hist) == 1
        and isinstance(hist[0], dict)
        and hist[0].get("role") == "assistant"
        and "latency_ms" not in hist[0]
    ):
        # Replace fallback content in-place
        hist[0]["content"] = greet_text
        hist[0]["latency_ms"] = elapsed_ms
        st.session_state.chat_history = hist
        return

    # Otherwise append
    st.session_state.chat_history.append(
        {"role": "assistant", "content": greet_text, "latency_ms": elapsed_ms}
    )


def _maybe_greet_once(coord_url: str):
    """
    Kick off a *model-generated* greet exactly once per *chat*.
    - Uses active chat id for gating, so every new chat gets a model greet.
    - Still uses the selected_persona label when calling the coordinator.
    """
    persona_label = st.session_state.selected_persona
    chat_id = st.session_state.active_chat_id

    if not persona_label or not chat_id:
        return

    _ensure_model_greet_dicts_for_chat(chat_id)

    if st.session_state.model_greet_done_by_chat.get(chat_id, False):
        return
    if st.session_state.model_greet_inflight_by_chat.get(chat_id, False):
        return

    # Mark inflight
    st.session_state.model_greet_inflight_by_chat[chat_id] = True
    st.session_state.model_greet_error_by_chat[chat_id] = False

    assistant_avatar = _assets_for_selected()["avatar"]
    msg_placeholder = st.empty()

    result: dict = {}
    t0 = time.perf_counter()
    thread = threading.Thread(
        target=post_async,
        args=(f"{coord_url}/persona/greet", {"persona": persona_label}, 120, result),
        daemon=True,
    )
    thread.start()

    # Typing animation
    frame_i = 0
    while thread.is_alive():
        with msg_placeholder.container():
            with st.chat_message("assistant", avatar=assistant_avatar):
                inner = st.empty()
                frames = ["_typing_", "_typing._", "_typing.._", "_typing..._"]
                inner.markdown(frames[frame_i % len(frames)])
                frame_i += 1
        time.sleep(0.25)

    # Done waiting
    st.session_state.model_greet_inflight_by_chat[chat_id] = False
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    st.session_state.last_latency_ms = elapsed_ms

    if result.get("ok"):
        data = result.get("json") or {}
        greet_text = (data.get("answer") or "").strip()
        if greet_text:
            _replace_fallback_if_present(greet_text, elapsed_ms)
            st.session_state.model_greet_done_by_chat[chat_id] = True
            st.toast("Model is ready ✅", icon="✅")
        else:
            st.session_state.chat_history.append(
                {"role": "assistant", "content": "(Greeting error: empty response)"}
            )
            st.session_state.model_greet_error_by_chat[chat_id] = True
            st.session_state.model_greet_done_by_chat[chat_id] = True
    else:
        err = result.get("error") or f"HTTP {result.get('status_code')} {result.get('text')}"
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"(Greeting error) {err}"}
        )
        st.session_state.model_greet_error_by_chat[chat_id] = True
        st.session_state.model_greet_done_by_chat[chat_id] = True
        st.toast("Greeting failed", icon="⚠️")

    # Persist change into the active chat immediately
    st.rerun()


def render_chat_tab(coord_url: str, model_name: str):
    render_header(model_name)
    if not st.session_state.selected_persona:
        st.info("Pick a character on the **Characters** tab to unlock chat.")
        return

    # Always attempt model greet exactly-once per *chat id*
    _maybe_greet_once(coord_url)

    assistant_avatar = _assets_for_selected()["avatar"]
    user_avatar = USER_AVATAR

    # ---------- Icon-only toolbar (stable single row) ----------
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
        if m.get("role") == "user":
            with st.chat_message("user", avatar=user_avatar):
                st.markdown(m.get("content", ""))
        else:
            with st.chat_message("assistant", avatar=assistant_avatar):
                st.markdown(m.get("content", ""))
                if isinstance(m.get("latency_ms"), int):
                    st.caption(f"⏱️ {m['latency_ms']} ms")

    # ---------- Input ----------
    user_in = st.chat_input("Type a message…")
    if user_in:
        st.session_state.chat_history.append({"role": "user", "content": user_in})
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(user_in)

        payload = {
            "persona": st.session_state.selected_persona,
            "history": [h for h in st.session_state.chat_history[:-1]],
            "message": user_in,
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
            st.session_state.chat_history.append(
                {"role": "assistant", "content": ans if ans else "(No answer)", "latency_ms": elapsed_ms}
            )
        else:
            err = result.get("error") or f"HTTP {result.get('status_code')} {result.get('text')}"
            with msg_placeholder.container():
                with st.chat_message("assistant", avatar=assistant_avatar):
                    st.markdown(f"Error: {err}")
            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {err}"})
            st.toast("Answer failed", icon="⚠️")
