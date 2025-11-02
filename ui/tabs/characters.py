# ui/tabs/characters.py
# Characters tab: search + responsive columns + hover "Choose ✨" overlay
# Now with shiny rarity frames, foil glints, and a mint number plate.
# Adds rarity-themed glow for the selected/active card.

import streamlit as st

# --- dual-mode imports: absolute first, then local fallback ---
try:
    from ui.personas import load_persona_cards, resolve_card_image
except ImportError:
    from personas import load_persona_cards, resolve_card_image  # type: ignore


def _cols_from_query(default: int = 5) -> int:
    """Read ?cols=<int> set by ui_style.js; clamp to [1..6]."""
    try:
        qp = st.query_params
        raw = qp.get("cols", default)
        if isinstance(raw, list):
            raw = raw[0] if raw else default
        cols = int(raw)
        return max(1, min(6, cols))
    except Exception:
        return default


def _mint_number(key: str) -> int:
    """Stable-ish mint number based on the persona key (no Python hash salt)."""
    return (sum((i + 1) * ord(c) for i, c in enumerate(key)) % 999) + 1


def _rarity_for(card: dict, key: str) -> str:
    """
    Resolve rarity with sane defaults. If the card provides "rarity",
    we accept (legendary|epic|rare|common|mythic). Otherwise:
    - Eeva, Astra, Gwen => Legendary
    - Else => Epic
    """
    raw = str(card.get("rarity", "")).strip().lower()
    aliases = {
        "mythic": "legendary",
        "leg": "legendary",
        "ep": "epic",
        "r": "rare",
        "c": "common",
    }
    if raw in aliases:
        raw = aliases[raw]
    if raw in {"legendary", "epic", "rare", "common"}:
        return raw
    key_l = key.lower()
    if key_l in {"eeva", "astra", "gwen"}:
        return "legendary"
    return "epic"


def render_characters_tab():
    st.subheader("Characters")

    # --- style: make native st.button look like the translucent overlay pill inside .card-choose
    st.markdown(
        """
        <style>
        /* Only affect buttons inside our overlay container */
        .card-choose div[data-testid="stButton"] { display:inline-block; }
        .card-choose div[data-testid="stButton"] > button {
            all: unset;                /* strip default Streamlit styles */
            display: inline-block;
            font-weight: 600;
            padding: 0.3em 0.8em;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.4);
            background: rgba(255,255,255,0.2);
            cursor: pointer;
            user-select: none;
            -webkit-user-select: none;
            line-height: 1.1;
        }
        .card-choose div[data-testid="stButton"] > button:hover {
            background: rgba(255,255,255,0.3);
        }
        .card-choose {                /* keep your existing overlay behavior */
            position: absolute;
            bottom: 8%;
            width: 100%;
            text-align: center;
            opacity: 0;
            transition: opacity 0.25s;
        }
        .card-outer:hover .card-choose { opacity: 1; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Persona search (stable size; CSS sized in ui_style)
    with st.container():
        st.markdown('<div class="persona-search-wrap">', unsafe_allow_html=True)
        q = st.text_input(
            label="Search personas",
            value=st.session_state.get("persona_search", ""),
            placeholder="Search by name, style, traits…",
            key="persona_search",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Pick your assistant. Cards keep a **2:3** ratio and scale with the screen. "
        "Hover & click **Choose ✨** to select and unlock Chat & Bio."
    )

    cards = load_persona_cards(st.session_state.P_DIR)

    # Filter by query
    if q:
        ql = q.strip().lower()

        def match(card):
            fields = [
                str(card.get("key", "")),
                str(card.get("display_name", "")),
                str(card.get("style", "")),
            ]
            fields += [d for d in (card.get("do") or []) if isinstance(d, str)]
            fields += [d for d in (card.get("dont") or []) if isinstance(d, str)]
            return any(ql in f.lower() for f in fields)

        cards = [c for c in cards if match(c)]

    # Responsive columns count from ?cols= (2/3/4/5/..)
    MAX_COLS = _cols_from_query(default=5)

    # Render in rows with hover overlay
    idx = 0
    while idx < len(cards):
        row_cards = cards[idx : idx + MAX_COLS]
        cols = st.columns(len(row_cards), gap="small")
        for col, card in zip(cols, row_cards):
            with col:
                key = (card.get("key") or "Eeva").split()[0].capitalize()
                disp = card.get("display_name", f"{key} — Nerdy Charming")
                tagline = card.get("style", "curious & kind")
                rarity = _rarity_for(card, key)  # legendary|epic|rare|common
                mint_no = _mint_number(key)
                img_src = resolve_card_image(card, key)

                # Mark selection/active visually
                is_selected = (st.session_state.get("selected_key") or "") == key
                selected_cls = " selected" if is_selected else ""

                # Also keep reveal effect (set in app.py on selection once)
                is_revealed = (st.session_state.get("reveal_key") or "") == key
                revealed_cls = " revealed" if is_revealed else ""

                html_img = (
                    f"<img class='card-img' src='{img_src}' />"
                    if img_src
                    else "<div class='card-img card-img-fallback'>🎴</div>"
                )

                # Rarity label text
                rarity_label = {
                    "legendary": "Legendary ✨",
                    "epic": "Epic ✨",
                    "rare": "Rare ★",
                    "common": "Common",
                }.get(rarity, "Epic ✨")

                # --- Card markup (unchanged body; overlay now contains native st.button)
                st.markdown(
                    f"""
                    <div class="card-outer rarity-{rarity}{selected_cls}{revealed_cls}">
                      <!-- Gold/Holo frame layers -->
                      <div class="card-frame"></div>
                      <div class="card-foil"></div>
                      <div class="card-glint"></div>

                      <!-- Rarity badge & mint plate -->
                      <div class="rarity-badge" title="{rarity_label}">{rarity_label}</div>
                      <div class="mint-plate" title="Mint number">No. {mint_no:03d}</div>

                      <!-- Body -->
                      <div class="card-body">
                        {html_img}
                        <div class="card-name" title="{disp}">{disp}</div>
                        <div class="card-tagline" title="{tagline}">{tagline}</div>
                        <div class="card-choose">
                          <!-- Streamlit button gets injected below inside this container -->
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Place the native Streamlit button directly after the container so it renders inside it.
                # We use a unique key per persona card.
                # On click: update query params to ?tab=chat&select=<Key> (app.py handles selection + chat focusing/creation)
                btn_key = f"choose_{key}"
                clicked = st.button("Choose ✨", key=btn_key, help="Select this persona")
                if clicked:
                    try:
                        qp = st.query_params
                        qp["tab"] = "chat"
                        qp["select"] = key
                    except Exception:
                        # best-effort fallback: set both and continue
                        try:
                            st.query_params.clear()
                            st.query_params["tab"] = "chat"
                            st.query_params["select"] = key
                        except Exception:
                            pass
                    st.rerun()
        idx += MAX_COLS
