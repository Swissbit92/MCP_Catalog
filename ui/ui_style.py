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
      button[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] * { color:#ffffff !important; }
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

    /* Persona Card — responsive (unchanged from your latest) */
    .card-outer {
      width: clamp(140px, 18vw, 240px);
      aspect-ratio: 2 / 3;
      height: auto;
      border-radius: 16px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 10px 18px rgba(0,0,0,0.25);
      background: linear-gradient(135deg, rgba(255,255,255,0.75), rgba(200,220,255,0.55), rgba(255,215,240,0.55));
      border: 1px solid rgba(255,255,255,0.6);
      transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
      backdrop-filter: blur(6px);
      margin-bottom: 8px;
      font-size: clamp(12px, 0.9vw, 16px);
    }
    @media (min-width: 1280px) {
      .card-outer { width: clamp(160px, 16vw, 260px); }
    }
    .card-outer:hover { transform: translateY(-3px) rotateZ(-0.35deg); box-shadow: 0 14px 24px rgba(0,0,0,0.3); filter: saturate(1.05); }
    .card-outer.revealed { box-shadow: 0 0 20px 3px rgba(80,200,255,0.85), inset 0 0 16px rgba(255,255,255,0.5); border-color: rgba(80,200,255,0.85); }
    .card-rarity { position:absolute; inset:0; background:conic-gradient(from 180deg at 50% 50%, rgba(255,255,255,0.12), rgba(0,0,0,0.12), rgba(255,255,255,0.12)); mix-blend-mode:soft-light; pointer-events:none; }
    .card-body { position: relative; height: 100%; display: flex; flex-direction: column; align-items: center; padding: 10px; box-sizing: border-box; gap: 4px; }
    .card-img { width: 100%; flex: 0 0 58%; object-fit: cover; border-radius: 12px; border: 1px solid rgba(0,0,0,0.05); }
    .card-name { flex: 0 0 14%; width: 100%; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; font-weight: 700; text-align: center; font-size: 1.05em; line-height: 1.15; }
    .card-tagline { flex: 0 0 12%; width: 100%; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; text-overflow: ellipsis; text-align: center; opacity: 0.95; font-size: 0.95em; line-height: 1.2; min-height: 2.1em; }

    .card-choose { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; opacity:0; transition:opacity 140ms ease, transform 140ms ease; pointer-events:none; }
    .card-outer:hover .card-choose { opacity:1; transform:scale(1.02); pointer-events:auto; }
    .choose-pill { padding:12px 18px; border-radius:999px; background:rgba(17,24,39,0.85); color:#fff; border:1px solid rgba(255,255,255,0.5); font-weight:700; box-shadow:0 8px 16px rgba(0,0,0,0.35); cursor:pointer; user-select:none; text-decoration:none !important; outline:none; border-width:1px; font-size: clamp(0.9rem, 1.5vw, 1rem); }
    .choose-pill:hover { filter:brightness(1.08); }
    @media (prefers-color-scheme: dark) {
      .card-outer { border-color:#2f3542; background:linear-gradient(135deg, rgba(23,30,45,0.85), rgba(32,40,60,0.7)); }
      .choose-pill { background:rgba(255,255,255,0.1); border-color:rgba(255,255,255,0.45); }
    }

    /* Chat Input — layout driven ONLY by left/right set from JS */
    [data-testid="stChatInput"] {
      position: fixed !important;
      bottom: max(0px, env(safe-area-inset-bottom)) !important;
      z-index: 1005 !important; /* higher than sidebar overlay */
      padding-top: 0.35rem; padding-bottom: 0.35rem;
      background: rgba(255,255,255,0.88);
      backdrop-filter: blur(6px);
      border-top: 1px solid rgba(0,0,0,0.08);
      left: var(--eeva-left, 0px) !important;
      right: var(--eeva-right, 0px) !important;
      width: auto !important; max-width: none !important; transform: none !important;
      border-radius: 14px 14px 0 0;
      margin: 0;
    }
    @media (prefers-color-scheme: dark) {
      [data-testid="stChatInput"] { background: rgba(17,24,39,0.88); border-top: 1px solid rgba(255,255,255,0.12); }
    }

    .persona-search-wrap { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
    .persona-search-wrap .stTextInput > div > div input { width: 520px !important; max-width: 90vw !important; min-width: 320px !important; }
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
          const url = new URL(parent.window.location);
          if (url.searchParams.get('tab') !== tab) {
            url.searchParams.set('tab', tab);
            parent.window.history.replaceState({}, '', url);
          }
        };
        setInterval(setTabParam, 400);
        setTimeout(setTabParam, 60);
        </script>
        """,
        height=0
    )

    # Responsive columns param (?cols=...)
    components.html(
        """
        <script>
        (function(){
          function pickCols(w){
            if (w < 560) return 2;        // phones
            if (w < 900) return 3;        // small tablets
            if (w < 1280) return 4;       // laptops
            return 5;                     // large desktops
          }
          function syncCols(){
            try{
              const w = parent.window.innerWidth || document.documentElement.clientWidth || 1200;
              const cols = pickCols(w);
              const url = new URL(parent.window.location);
              if (url.searchParams.get('cols') !== String(cols)) {
                url.searchParams.set('cols', String(cols));
                parent.window.history.replaceState({}, '', url);
              }
            }catch(e){}
          }
          parent.window.addEventListener('resize', syncCols);
          setInterval(syncCols, 600);
          setTimeout(syncCols, 40);
          setTimeout(syncCols, 200);
          setTimeout(syncCols, 800);
        })();
        </script>
        """,
        height=0
    )

    # Chat input layout: sidebar-aware (overlay or pinned) + bottom padding sync
    components.html(
        """
        <script>
        (function(){
          const px = (n)=>Math.max(0,Math.round(n))+'px';

          function layoutChat(){
            const doc = parent.document;
            const input = doc.querySelector('[data-testid="stChatInput"]');
            const main  = doc.querySelector('.block-container');
            if (!input || !main) return;

            const vw = parent.window.innerWidth || doc.documentElement.clientWidth || 1200;
            // Desired width when not constrained by sidebar/pins:
            let desired = 0.95 * vw;                  // phones
            if (vw >= 600) desired = 0.85 * vw;       // tablets
            if (vw >= 900) desired = 0.75 * vw;       // desktops
            desired = Math.max(360, Math.min(1100, Math.round(desired)));

            // Base content gutters from block container
            const rect = main.getBoundingClientRect();
            let leftEdge   = rect.left;                                    // content left
            const rightG   = (doc.documentElement.clientWidth - rect.right); // content right gutter

            // Sidebar rect (works for both pinned and overlay)
            const sb = doc.querySelector('aside[data-testid="stSidebar"]');
            if (sb) {
              const sbRect = sb.getBoundingClientRect();
              const sbVisible = (sbRect.width > 0) && (sbRect.left < (vw - 8));
              if (sbVisible) {
                // If overlay is open, its right edge can occlude content — push left edge to its right edge.
                leftEdge = Math.max(leftEdge, Math.round(sbRect.right));
              }
            }

            // Available width between leftEdge and right gutter
            const docW = doc.documentElement.clientWidth;
            const available = Math.max(0, docW - leftEdge - rightG);

            // Final width: centered INSIDE the available region
            const finalW = Math.min(desired, available);
            const sidePad = Math.max(0, (available - finalW) / 2);
            const finalLeft  = leftEdge + sidePad;
            const finalRight = docW - finalLeft - finalW;

            // Apply via CSS variables so we win specificity
            input.style.setProperty('--eeva-left',  px(finalLeft));
            input.style.setProperty('--eeva-right', px(finalRight));

            // Keep content clear of the bar
            const h = input.getBoundingClientRect().height || 96;
            main.style.paddingBottom = px(h + 24);
          }

          const doc = parent.document;
          const observe = (el) => { if (!el) return; new ResizeObserver(layoutChat).observe(el); };

          observe(doc.body);
          observe(doc.querySelector('.block-container'));
          observe(doc.querySelector('aside[data-testid="stSidebar"]'));

          parent.window.addEventListener('resize', layoutChat);
          parent.window.addEventListener('scroll', layoutChat);

          // staged runs to catch fonts/Streamlit reflows
          setTimeout(layoutChat, 40);
          setTimeout(layoutChat, 160);
          setTimeout(layoutChat, 360);
          setTimeout(layoutChat, 800);

          // React to the input itself changing height
          (function waitForInput(){
            const input = doc.querySelector('[data-testid="stChatInput"]');
            if (!input) { setTimeout(waitForInput, 120); return; }
            new ResizeObserver(layoutChat).observe(input);
            layoutChat();
          })();
        })();
        </script>
        """,
        height=0
    )

    # Define chooser (unchanged)
    components.html(
        """
        <script>
        (function(){
          try {
            if (!parent || !parent.window) return;
            parent.window.eevaChoose = function(key) {
              try {
                const url = new URL(parent.window.location);
                url.searchParams.set('tab', 'chat');
                url.searchParams.set('select', key);
                parent.window.history.replaceState({}, '', url);
                parent.window.location.href = url.toString();
              } catch (e) {
                console.error('eevaChoose error', e);
                parent.window.location.reload();
              }
            };
          } catch (e) {
            console.error('init eevaChoose failed', e);
          }
        })();
        </script>
        """,
        height=0
    )
