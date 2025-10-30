# ui/tabs/bio.py
# Bio tab: responsive CV banner + cached LLM summary (styled paragraphs, no expander).

import threading
import time
from html import escape

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
    post_async(f"{coord_url}/persona/summary", {"persona": persona_label}, 120, out)


def _render_summary_paragraphs(summary: str | None) -> str:
    """Escape and format narrative into paragraphs; first gets a dropcap."""
    if not summary:
        return ""
    txt = summary.replace("\r\n", "\n").strip()
    blocks = [b.strip() for b in txt.split("\n\n") if b.strip()] or [txt]
    html = []
    for i, b in enumerate(blocks):
        safe = escape(b).replace("\n", "<br/>")
        cls = "cv-p cv-lead" if i == 0 else "cv-p"
        html.append(f"<p class='{cls}'>{safe}</p>")
    return "\n".join(html)


def _cv_banner_html(img_uri: str | None, summary_html: str) -> str:
    """CV banner HTML: avatar on the left, summary on the right (single grid)."""
    img = (
        f"<img class='cv-avatar' src='{img_uri}' alt='persona' />"
        if img_uri
        else "<div class='cv-avatar cv-avatar-fallback' aria-label='persona avatar'>🎴</div>"
    )
    return f"""
    <div class="cv-banner">
      <div class="cv-left">{img}</div>
      <div class="cv-right"><div class="cv-summary">{summary_html}</div></div>
    </div>
    """


def render_bio_tab():
    render_header(st.session_state.MODEL)
    if not st.session_state.get("selected_persona"):
        st.info("Pick a character on the **Characters** tab to view their bio.")
        return

    chosen = st.session_state.get("selected_key") or "Eeva"
    cards = load_persona_cards(st.session_state.P_DIR)
    card = next((c for c in cards if c.get("key", "").lower().startswith(chosen.lower())), None)
    if not card:
        st.warning("Persona card not found.")
        return

    # Resolve image: explicit card logo → selected assets logo → card image fallback
    assets = _assets_for_selected()
    logo_uri = _file_to_data_uri(card["logo"]) if isinstance(card.get("logo"), str) else None
    if not logo_uri and assets.get("logo"):
        logo_uri = _file_to_data_uri(assets["logo"])
    if not logo_uri:
        logo_uri = resolve_card_image(card, chosen)

    # Fetch LLM-built summary from Coordinator
    coord_url = st.session_state.get("COORD_URL") or st.session_state.get("coord_url") or "http://127.0.0.1:8000"
    persona_label = st.session_state["selected_persona"]

    res: dict = {}
    t = threading.Thread(target=_fetch_summary, args=(coord_url, persona_label, res), daemon=True)
    t.start()

    ph = st.empty()
    dots = 0
    while t.is_alive():
        ph.info("Building persona summary" + "." * (1 + (dots % 3)))
        dots += 1
        time.sleep(0.2)
    ph.empty()

    summary_text = None
    if res.get("ok"):
        data = res.get("json") or {}
        summary_text = (data.get("summary") or "").strip() or None

    if summary_text:
        st.markdown(_cv_banner_html(logo_uri, _render_summary_paragraphs(summary_text)), unsafe_allow_html=True)
        return

    # Fallback structured view if no summary available
    left, right = st.columns([1, 2], vertical_alignment="top")
    with left:
        if logo_uri:
            st.image(logo_uri, width=220)
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
