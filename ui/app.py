# Streamlit UI for GraphRAG Local QA Chat with Personas
# - WhatsApp-like chat with avatars
# - Per-persona logos and icons
# - Greeting once per persona
# - Clear-on-switch option
# - Export transcript as JSON (single-click)
# - Latency indicator rendered separately (doesn't break on next query)
# - Header chips auto-adapt to dark/light theme
# - Status chip reflects greeting lifecycle: Loading → Ready (or Error)
# - Immediate header update after greeting via st.rerun()
# - UPDATED: replace deprecated use_container_width with width="stretch"

import os
import time
import json
from datetime import datetime
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# -------------------- Config helpers --------------------
def _coord_url() -> str:
    return os.getenv("COORD_URL", "http://127.0.0.1:8000")

def _model_name() -> str:
    return os.getenv("PERSONA_MODEL", "llama3.1:8b")

COORD = _coord_url()
MODEL = _model_name()

st.set_page_config(
    page_title="EEVA Chat — Local",
    page_icon="💬",
    layout="wide"
)

# -------------------- Persona assets (env overrides allowed) --------------------
EEVA_LOGO = os.getenv("EEVA_LOGO", "")          # e.g., "images/eeva_logo.png"
CINDY_LOGO = os.getenv("CINDY_LOGO", "")        # e.g., "images/cindy_logo.png"
APP_LOGO   = os.getenv("APP_LOGO_PATH", "")     # optional app brand logo

EEVA_AVATAR = os.getenv("EEVA_AVATAR", "🧠")    # can be emoji or image path
CINDY_AVATAR = os.getenv("CINDY_AVATAR", "🛠️")
USER_AVATAR  = os.getenv("USER_AVATAR", "🧑")

def persona_assets(name: str):
    if "Cindy" in name:
        return {
            "logo": CINDY_LOGO if CINDY_LOGO else None,
            "avatar": CINDY_AVATAR,
            "tag": "Cindy — Pragmatic Builder"
        }
    # default Eeva
    return {
        "logo": EEVA_LOGO if EEVA_LOGO else None,
        "avatar": EEVA_AVATAR,
        "tag": "Eeva — Nerdy Charming"
    }

# -------------------- Sidebar: Persona + Settings --------------------
with st.sidebar:
    if APP_LOGO:
        # UPDATED: use width="stretch" instead of use_container_width
        st.image(APP_LOGO, width="stretch")

    st.markdown("### 🤖 Persona")
    persona = st.selectbox(
        "Choose a voice",
        ["Eeva (Nerdy Charming)", "Cindy (Pragmatic Builder)"],
        index=0
    )

    clear_on_switch = st.checkbox("Clear Chat on Persona Switch", value=False)

    # Optional mode (future wiring)
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    mode = st.radio(
        "Mode (future-ready):",
        ["Local (Chat-only)", "Local + MCP (soon)"],
        index=0,
        help="Keep Local for now. MCP mode will call RAG/KG tools later."
    )

    st.caption(f"Coordinator: {COORD}")

    # Persona bio card (short)
    pa = persona_assets(persona)
    if pa["logo"]:
        # UPDATED: use width="stretch" instead of use_container_width
        st.image(pa["logo"], width="stretch")
    if "Eeva" in persona:
        st.info("**Eeva** · nerdy, charming, concise\n\n"
                "• Clears up complex ideas\n"
                "• Adds small next-step suggestions\n"
                "• Light emojis only")
    else:
        st.info("**Cindy** · practical, hands-on, direct\n\n"
                "• Prefers step-by-step tasks\n"
                "• Calls out assumptions\n"
                "• No hype")

# -------------------- Session State --------------------
if "chat_history" not in st.session_state:
    # Each message: {"role": "user"|"assistant", "content": str, "latency_ms"?: int}
    st.session_state.chat_history = []

if "greeted_for_persona" not in st.session_state:
    # dict[str, bool]
    st.session_state.greeted_for_persona = {}

if "greeting_inflight" not in st.session_state:
    # dict[str, bool]
    st.session_state.greeting_inflight = {}

if "greeting_error" not in st.session_state:
    # dict[str, bool]
    st.session_state.greeting_error = {}

if "prev_persona" not in st.session_state:
    st.session_state.prev_persona = persona

if "last_latency_ms" not in st.session_state:
    st.session_state.last_latency_ms = None

# One-shot rerun flag (used to refresh header right after greeting finishes)
if "needs_header_rerun" not in st.session_state:
    st.session_state.needs_header_rerun = False
else:
    # Clear the flag at the start of a run so we don't loop
    st.session_state.needs_header_rerun = False

# Handle persona switch behavior
if persona != st.session_state.prev_persona:
    if clear_on_switch:
        st.session_state.chat_history = []
        st.toast("Chat cleared due to persona switch.", icon="🧹")
    # Reset status for the new persona
    st.session_state.prev_persona = persona
    st.session_state.greeting_error[persona] = False
    st.session_state.greeted_for_persona[persona] = st.session_state.greeted_for_persona.get(persona, False)
    # inflight will be set when we actually start the greeting request

# -------------------- Header / Status (compact and visible) --------------------
# Dark/Light adaptive chips via prefers-color-scheme
st.markdown(
    """
    <style>
      .eeva-header { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px; }
      .eeva-title { font-size:22px; font-weight:600; }

      /* Base (light) */
      .chip { padding:2px 10px; border-radius:12px; background:#f7f7f9; border:1px solid #d0d0d6; color:#222; font-size:0.85rem; }
      .chip-success { background:#e6ffe6; border:1px solid #b3ffb3; color:#155e2b; }
      .chip-soft  { background:#eef; border:1px solid #ccd; color:#1f2a44; }
      .chip-warn  { background:#fff7e6; border:1px solid #ffd699; color:#8a6100; } /* loading */
      .chip-error { background:#ffe6e6; border:1px solid #ffb3b3; color:#7a1f1f; }

      /* Dark mode overrides */
      @media (prefers-color-scheme: dark) {
        .chip { background:#1f2937; border:1px solid #374151; color:#e5e7eb; }
        .chip-success { background:#064e3b; border:1px solid #10b981; color:#d1fae5; }
        .chip-soft { background:#1e293b; border:1px solid #334155; color:#e2e8f0; }
        .chip-warn { background:#4a3b13; border:1px solid #f59e0b; color:#fde68a; }
        .chip-error { background:#4c1d1d; border:1px solid #f87171; color:#fecaca; }
      }

      .eeva-subtle { color:#6b6b6b; margin-bottom:10px; }
      @media (prefers-color-scheme: dark) {
        .eeva-subtle { color:#a3a3a3; }
      }
    </style>
    """,
    unsafe_allow_html=True
)

assets = persona_assets(persona)

# Compute status based on greeting lifecycle
greeted = st.session_state.greeted_for_persona.get(persona, False)
inflight = st.session_state.greeting_inflight.get(persona, False)
had_error = st.session_state.greeting_error.get(persona, False)

if had_error:
    status_chip = "<span class='chip chip-error'>Status: ⚠️ Error</span>"
elif inflight or not greeted:
    status_chip = "<span class='chip chip-warn'>Status: ⏳ Loading</span>"
else:
    status_chip = "<span class='chip chip-success'>Status: ✅ Ready</span>"

lat = st.session_state.last_latency_ms
lat_chip = (
    f"<span class='chip'>Latency: {lat} ms</span>"
    if isinstance(lat, int) else
    "<span class='chip'>Latency: —</span>"
)

model_chip = f"<span class='chip'>Model: {MODEL}</span>"
persona_chip = f"<span class='chip chip-soft'>{assets['tag']}</span>"

st.markdown(
    f"""
    <div class="eeva-header">
      <span class="eeva-title">EEVA Chat</span>
      {persona_chip}
      {model_chip}
      {status_chip}
      {lat_chip}
    </div>
    <div class="eeva-subtle">Enter to send · Shift+Enter for newline</div>
    """,
    unsafe_allow_html=True
)

# -------------------- Controls row --------------------
c1, c2, c3 = st.columns([1, 1, 6])
with c1:
    if st.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.toast("Chat cleared.", icon="🧹")

with c2:
    # Single-click export as JSON
    export_obj = {
        "persona": persona,
        "model": MODEL,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "history": st.session_state.chat_history,
    }
    data = json.dumps(export_obj, indent=2).encode("utf-8")
    st.download_button(
        "📥 Export (.json)",
        data=data,
        file_name="transcript.json",
        mime="application/json",
        help="Download your conversation as JSON"
    )

st.markdown("---")

# -------------------- Greeting (one-time per persona) --------------------
# Only start greeting if not greeted and not already in-flight
if not greeted and not inflight:
    st.session_state.greeting_inflight[persona] = True
    st.session_state.greeting_error[persona] = False
    try:
        t0 = time.perf_counter()
        r = requests.post(f"{COORD}/persona/greet", json={"persona": persona}, timeout=120)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        st.session_state.last_latency_ms = elapsed_ms  # reflect in header
        if r.ok:
            greet_text = (r.json() or {}).get("answer", "").strip()
            if greet_text:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": greet_text,
                    "latency_ms": elapsed_ms
                })
                st.session_state.greeted_for_persona[persona] = True
                st.toast("Model is ready ✅", icon="✅")
            else:
                # no text — treat as error-ish so status doesn't show ready
                st.session_state.greeting_error[persona] = True
        else:
            st.session_state.greeting_error[persona] = True
            msg = f"(Greeting error: {r.status_code} {r.text})"
            st.session_state.chat_history.append({"role": "assistant", "content": msg})
            st.toast("Greeting failed", icon="⚠️")
    except Exception as e:
        st.session_state.greeting_error[persona] = True
        st.session_state.chat_history.append({"role": "assistant", "content": f"(Greeting error: {e})"})
        st.toast("Could not contact Coordinator", icon="⚠️")
    finally:
        st.session_state.greeting_inflight[persona] = False
        # Trigger an immediate rerun so the header chip flips to Ready/Error now
        st.session_state.needs_header_rerun = True
        st.rerun()

# -------------------- Render history (WhatsApp-like: avatars + neat bubbles) --------------------
assistant_avatar = assets["avatar"]
user_avatar = USER_AVATAR

for m in st.session_state.chat_history:
    if m["role"] == "user":
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(m["content"])
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.markdown(m["content"])
            if "latency_ms" in m and isinstance(m["latency_ms"], int):
                st.caption(f"⏱️ {m['latency_ms']} ms")

# -------------------- Chat input & send --------------------
user_in = st.chat_input("Type a message…")
if user_in:
    st.session_state.chat_history.append({"role": "user", "content": user_in})
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(user_in)

    payload = {
        "persona": persona,
        "history": [h for h in st.session_state.chat_history[:-1]],  # exclude current user turn
        "message": user_in
    }

    t0 = time.perf_counter()
    try:
        r = requests.post(f"{COORD}/persona/chat", json=payload, timeout=180)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        st.session_state.last_latency_ms = elapsed_ms  # keep a headline metric fresh

        data = r.json()
        if r.ok:
            ans = data.get("answer", "").strip()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": ans,
                "latency_ms": elapsed_ms
            })
            with st.chat_message("assistant", avatar=assistant_avatar):
                st.markdown(ans)
                st.caption(f"⏱️ {elapsed_ms} ms")
        else:
            err = f"Error: {data}"
            st.session_state.chat_history.append({"role": "assistant", "content": err})
            with st.chat_message("assistant", avatar=assistant_avatar):
                st.markdown(err)
            st.toast("Answer failed", icon="⚠️")
    except Exception as e:
        err = f"Coordinator error: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": err})
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.markdown(err)
        st.toast("Coordinator error", icon="⚠️")
