# ui/tabs/bio.py
# Bio tab: logo + style + voice tics + lore/do/don't

import streamlit as st

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import load_persona_cards, resolve_card_image, _file_to_data_uri
    from ui.tabs.common import render_header, _assets_for_selected
except ImportError:
    from personas import load_persona_cards, resolve_card_image, _file_to_data_uri  # type: ignore
    from tabs.common import render_header, _assets_for_selected  # type: ignore

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
