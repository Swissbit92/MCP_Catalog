# ui/tabs/characters.py
# Characters tab: search + 5-per-row cards + hover "Choose ✨" overlay (same window)

import streamlit as st

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import load_persona_cards, resolve_card_image
except ImportError:
    from personas import load_persona_cards, resolve_card_image  # type: ignore

def render_characters_tab():
    st.subheader("Characters")

    # Persona search (stable size; CSS sized in ui_style)
    with st.container():
        st.markdown('<div class="persona-search-wrap">', unsafe_allow_html=True)
        q = st.text_input(
            label="Search personas",
            value=st.session_state.get("persona_search",""),
            placeholder="Search by name, style, traits…",
            key="persona_search"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.caption("Pick your assistant. Cards are 2:3 — hover & click **Choose ✨** to select and unlock Chat & Bio.")

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

    # Render in rows of up to 5 with hover overlay (no st.button)
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

                # Same-window navigation: write query params (?tab=chat&select=<Key>)
                choose_href = f"?tab=chat&select={key}"

                st.markdown(
                    f"""
                    <div class="card-outer{revealed}">
                      <div class="card-rarity"></div>
                      <div class="card-body">
                        {html_img}
                        <div class="card-name">{disp}</div>
                        <div class="card-tagline">{tagline}</div>
                        <div class="card-choose">
                          <a class="choose-pill" href="{choose_href}">Choose ✨</a>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        idx += MAX_COLS
