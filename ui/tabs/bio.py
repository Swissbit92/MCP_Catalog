# ui/tabs/bio.py
# Bio tab: responsive CV banner + cached LLM summary (no structured-details expander).

import threading
import time

import streamlit as st

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import load_persona_cards, resolve_card_image, _file_to_data_uri
    from ui.tabs.common import render_header, _assets_for_selected
    from ui.ui_net import post_async
except ImportError:
    from personas import load_persona_cards, resolve_card_image, _file_to_data_uri  # type: ignore
    from tabs.common import render_header, _assets_for_selected  # type: ignore
    from ui_net import post_async  # type: ignore


def _fetch_summary(coord_url: str, persona_label: str, out: dict):
    payload = {"persona": persona_label}
    post_async(f"{coord_url}/persona/summary", payload, 120, out)


def _cv_banner_html(img_uri: str | None, summary: str) -> str:
    img = (
        f"<img class='cv-avatar' src='{img_uri}' alt='persona' />"
        if img_uri
        else "<div class='cv-avatar cv-avatar-fallback'>🎴</div>"
    )
    # Summary paragraph is rendered below in markdown to ensure proper wrapping
    return f"""
    <div class="cv-banner">
      <div class="cv-left">{img}</div>
      <div class="cv-right">
        <div class="cv-summary">{summary}</div>
      </div>
    </div>
    """


def render_bio_tab():
    render_header(st.session_state.MODEL)
    if not st.session_state.selected_persona:
        st.info("Pick a character on the **Characters** tab to view their bio.")
        return

    chosen = st.session_state.selected_key or "Eeva"
    cards = load_persona_cards(st.session_state.P_DIR)
    card = next((c for c in cards if c.get("key", "").lower().startswith(chosen.lower())), None)
    if not card:
        st.warning("Persona card not found.")
        return

    # Resolve a clean image: logo → env logo → card image
    assets = _assets_for_selected()
    logo_uri = None
    if isinstance(card.get("logo"), str):
        logo_uri = _file_to_data_uri(card["logo"])
    if not logo_uri and assets.get("logo"):
        logo_uri = _file_to_data_uri(assets["logo"])
    if not logo_uri:
        logo_uri = resolve_card_image(card, chosen)

    # --- Fetch or build CV-style summary from Coordinator ---
    coord_url = st.session_state.get("COORD_URL") or st.session_state.get("coord_url") or "http://127.0.0.1:8000"
    persona_label = st.session_state.selected_persona

    res: dict = {}
    t = threading.Thread(target=_fetch_summary, args=(coord_url, persona_label, res), daemon=True)
    t.start()

    # tiny spinner while we fetch
    ph = st.empty()
    dots = 0
    while t.is_alive():
        ph.info("Building persona summary" + "." * (1 + (dots % 3)))
        dots += 1
        time.sleep(0.2)

    ph.empty()
    if not res.get("ok"):
        st.warning("Could not load summary. Showing structured details instead.")
        summary_text = None
    else:
        data = res.get("json") or {}
        summary_text = (data.get("summary") or "").strip() or None

    # --- CV banner (narrative) or fallback structured details ---
    if summary_text:
        # Render banner shell (image + right column)
        st.markdown(_cv_banner_html(logo_uri, ""), unsafe_allow_html=True)
        # Put the paragraph as markdown so it wraps properly
        with st.container():
            st.markdown(f"<div class='cv-summary-md'>{summary_text}</div>", unsafe_allow_html=True)
    else:
        # Fallback to structured details if summary missing
        left, right = st.columns([1, 2], vertical_alignment="top")
        with left:
            if logo_uri:
                st.image(logo_uri, width=240)
            st.markdown(f"**Persona:** {card.get('display_name','—')}")
            st.markdown(f"**Style:** {card.get('style','—')}")
            st.markdown("**Personality tics:**")
            for t_ in (card.get("voice", {}) or {}).get("tics", []):
                st.markdown(f"- {t_}")
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
