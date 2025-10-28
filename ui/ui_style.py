# ui/ui_style.py
# Global CSS/JS injection + query param sync helpers

import streamlit as st
import streamlit.components.v1 as components

def inject_global_css_js():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.0rem; padding-bottom: 7.5rem; }
    div[data-testid="column"] { padding-left: 2px !important; padding-right: 2px !important; } /* tighter */

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

    /* Chat input stays full width relative to content */
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

    /* Persona search bar sizing (consistent width) */
    .persona-search-wrap { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
    .persona-search-wrap .stTextInput > div > div input {
      width: 520px !important; max-width: 90vw !important; min-width: 320px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Track active tab in query params (?tab=characters|chat|bio)
    components.html(
        """
        <script>
        const setTabParam = () => {
          const active = Array.from(parent.document.querySelectorAll('button[role="tab"]'))
            .find(b => b.getAttribute('aria-selected') === 'true');
          if (!active) return;
          const txt = (active.innerText || '').trim().toLowerCase();
          let tab = 'characters';
          if (txt.startsWith('💬')) tab = 'chat';
          else if (txt.startsWith('📜')) tab = 'bio';
          const url = new URL(window.location);
          if (url.searchParams.get('tab') !== tab) {
            url.searchParams.set('tab', tab);
            window.history.replaceState({}, '', url);
          }
        };
        setInterval(setTabParam, 400);
        setTimeout(setTabParam, 60);
        </script>
        """,
        height=0
    )

    # Make chat input width follow the main container
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
