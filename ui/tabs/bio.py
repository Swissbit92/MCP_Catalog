# ui/tabs/bio.py
# Bio tab: cyberpunk gacha banner + cached LLM summary (text stays right of the image).

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


def _inject_tabbar_css_once():
    """
    Minimal, safe CSS polish for the top radio "tab bar".
    Targets Streamlit's radio group generically; idempotent.
    """
    if st.session_state.get("_eeva_tabbar_css_done"):
        return
    st.session_state["_eeva_tabbar_css_done"] = True
    st.markdown(
        """
        <style>
          /* Tab bar container spacing */
          div[role="radiogroup"] {
            gap: 8px !important;
          }
          /* Each label as a pill */
          div[role="radiogroup"] > label {
            border-radius: 999px;
            padding: 4px 8px;
            border: 1px solid rgba(255,255,255,0.25);
            background: rgba(255,255,255,0.06);
            transition: background 120ms ease, transform 120ms ease, border-color 120ms ease;
          }
          div[role="radiogroup"] > label:hover {
            background: rgba(255,255,255,0.12);
            transform: translateY(-1px);
          }
          /* Selected state: Streamlit renders an <input> preceding content inside label */
          div[role="radiogroup"] > label:has(input:checked) {
            border-color: rgba(255,255,255,0.45);
            background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08));
            box-shadow: 0 0 0 1px rgba(255,255,255,0.15) inset, 0 6px 18px rgba(0,0,0,0.25);
          }
          /* Focus ring for keyboard nav */
          div[role="radiogroup"] > label:has(input:focus-visible) {
            outline: 2px solid rgba(0, 200, 255, 0.55);
            outline-offset: 2px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fetch_summary(coord_url: str, persona_label: str, out: dict):
    payload = {"persona": persona_label}
    post_async(f"{coord_url}/persona/summary", payload, 120, out)


def _mint_number(key: str) -> int:
    """Stable-ish mint number based on the persona key (no Python hash salt)."""
    return (sum((i + 1) * ord(c) for i, c in enumerate(key)) % 999) + 1


def _rarity_for(card: dict, key: str) -> str:
    """
    Resolve rarity with sane defaults. Matches Characters tab logic.
    Accepts (legendary|epic|rare|common|mythic). 'mythic' maps to 'legendary'.
    """
    raw = str(card.get("rarity", "")).strip().lower()
    aliases = {"mythic": "legendary", "leg": "legendary", "ep": "epic", "r": "rare", "c": "common"}
    if raw in aliases:
        raw = aliases[raw]
    if raw in {"legendary", "epic", "rare", "common"}:
        return raw
    key_l = (key or "").lower()
    if key_l in {"eeva", "astra", "gwen"}:
        return "legendary"
    return "epic"


def _format_summary_to_html(summary_text: str) -> str:
    """
    Turn plaintext summary into styled HTML paragraphs inside the banner.
    First paragraph gets a 'cv-lead' class for a neon dropcap badge effect.
    """
    safe = escape(summary_text or "")
    paras = [p.strip() for p in safe.split("\n\n") if p.strip()]
    if not paras:
        return "<div class='cv-summary'></div>"
    out = []
    for i, p in enumerate(paras):
        cls = "cv-p cv-lead" if i == 0 else "cv-p"
        p = p.replace("\n", "<br/>")  # preserve single line-breaks softly
        out.append(f"<p class='{cls}'>{p}</p>")
    return f"<div class='cv-summary'>{''.join(out)}</div>"


def _cv_banner_html(img_uri: str | None, rarity: str, mint_no: int, summary_html: str) -> str:
    """
    Gacha-style banner with animated foil/glint frame layers.
    Structured so TEXT stays in the right column of a 2-col grid.
    """
    img = (
        f"<img class='cv-avatar' src='{img_uri}' alt='persona' />"
        if img_uri
        else "<div class='cv-avatar cv-avatar-fallback'>🎴</div>"
    )
    rarity_label = {
        "legendary": "Legendary ✨",
        "epic": "Epic ✨",
        "rare": "Rare ★",
        "common": "Common",
    }.get(rarity, "Epic ✨")

    return f"""
    <div class="cv-banner rarity-{rarity}">
      <!-- Decorative frame layers -->
      <div class="cv-frame"></div>
      <div class="cv-foil"></div>
      <div class="cv-glint"></div>
      <div class="cv-sheen"></div>

      <!-- Badges -->
      <div class="cv-rarity-badge" title="{rarity_label}">{rarity_label}</div>
      <div class="cv-mint-plate" title="Mint number">No. {mint_no:03d}</div>

      <!-- Content grid -->
      <div class="cv-left">{img}</div>
      <div class="cv-right">
        {summary_html}
      </div>
    </div>
    """


def render_bio_tab():
    _inject_tabbar_css_once()
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

    # Determine rarity & mint number (matches Characters tab vibe)
    rarity = _rarity_for(card, chosen)
    mint_no = _mint_number(chosen)

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
    summary_text = None
    if res.get("ok"):
        data = res.get("json") or {}
        summary_text = (data.get("summary") or "").strip() or None
    else:
        st.warning("Could not load summary. Showing structured details instead.")

    # --- CV banner (narrative) or fallback structured details ---
    if summary_text:
        summary_html = _format_summary_to_html(summary_text)
        st.markdown(_cv_banner_html(logo_uri, rarity, mint_no, summary_html), unsafe_allow_html=True)
    else:
        # Fallback (kept as-is): structured details in two columns
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
