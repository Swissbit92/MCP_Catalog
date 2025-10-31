# ui/ui_style.py
# Global CSS/JS injection + query param sync helpers (compact edition)

import re
import streamlit as st
import streamlit.components.v1 as components

def _minify(css: str) -> str:
    # conservative minifier: strip comments and excess blank lines, keep newlines for safety
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"[ \t]+\n", "\n", css)
    css = re.sub(r"\n{3,}", "\n\n", css)
    return css.strip()

def inject_global_css_js():
    BASE = """
    .block-container{padding-top:1rem;padding-bottom:7.5rem}
    div[data-testid="column"]{padding-left:2px!important;padding-right:2px!important}
    button[role=tab],button[role=tab]*{color:#1f2937!important}
    button[role=tab][aria-selected=true],button[role=tab][aria-selected=true]*{color:#111827!important;font-weight:700!important}
    @media (prefers-color-scheme:dark){
      button[role=tab],button[role=tab]*{color:#e5e7eb!important}
      button[role=tab][aria-selected=true],button[role=tab][aria-selected=true]*{color:#fff!important}
    }
    .eeva-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:8px 0 4px}
    .eeva-title{font-size:22px;font-weight:600}
    .chip{padding:2px 10px;border-radius:12px;background:#f7f7f9;border:1px solid #d0d0d6;color:#222;font-size:.85rem}
    .chip-success{background:#e6ffe6;border:1px solid #b3ffb3;color:#155e2b}
    .chip-soft{background:#eef;border:1px solid #ccd;color:#1f2a44}
    .chip-warn{background:#fff7e6;border:1px solid #ffd699;color:#8a6100}
    .chip-error{background:#ffe6e6;border:1px solid #ffb3b3;color:#7a1f1f}
    @media (prefers-color-scheme:dark){
      .chip{background:#1f2937;border:1px solid #374151;color:#e5e7eb}
      .chip-success{background:#064e3b;border:1px solid #10b981;color:#d1fae5}
      .chip-soft{background:#1e293b;border:1px solid #334155;color:#e2e8f0}
      .chip-warn{background:#4a3b13;border:1px solid #f59e0b;color:#fde68a}
      .chip-error{background:#4c1d1d;border:1px solid #f87171;color:#fecaca}
    }
    .eeva-subtle{color:#6b6b6b;margin-bottom:10px}
    @media (prefers-color-scheme:dark){.eeva-subtle{color:#a3a3a3}}
    """

    # Persona cards + rarity glow + GRID container
    CARDS = """
    /* GRID wrapper: smooth, one-by-one wrapping */
    .cards-grid{
      display:grid;
      grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));
      gap:10px;
      align-items:start;
      justify-items:center; /* center cards within each grid cell */
    }

    /* Cards now fill their grid cell up to a max width (keeps 2:3 ratio) */
    .card-outer{
      width:100%;
      max-width:360px; min-width:140px;
      aspect-ratio:2/3;
      border-radius:20px; position:relative; overflow:hidden; margin:0;
      font-size:clamp(12px,.9vw,16px);
      background:linear-gradient(160deg,rgba(15,20,35,.85),rgba(20,28,48,.78));
      box-shadow:0 14px 24px rgba(0,0,0,.35); backdrop-filter:blur(6px) saturate(110%);
      transform:translateZ(0);
      transition:transform .18s,box-shadow .18s,filter .18s;
      isolation:isolate;
    }
    .card-outer:hover{transform:translateY(-3px) rotateZ(-.35deg);box-shadow:0 18px 32px rgba(0,0,0,.45);filter:saturate(1.05)}

    .rarity-legendary{--glow:rgba(255,208,80,.9);--glow2:rgba(255,240,166,.7)}
    .rarity-epic{--glow:rgba(186,120,255,.85);--glow2:rgba(246,212,255,.65)}
    .rarity-rare{--glow:rgba(66,245,255,.85);--glow2:rgba(212,246,255,.65)}
    .rarity-common{--glow:rgba(230,230,230,.85);--glow2:rgba(250,250,250,.6)}

    .card-outer.selected{transform:translateY(-4px) scale(1.01);filter:saturate(1.12) brightness(1.03);box-shadow:0 20px 40px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.22),0 0 24px var(--glow)}
    .card-outer.selected::before{content:"";position:absolute;inset:-8px;border-radius:26px;background:radial-gradient(60% 50% at 50% 6%,var(--glow2),transparent 60%),radial-gradient(70% 60% at 50% 100%,var(--glow),transparent 70%);filter:blur(14px);opacity:.85;z-index:0;pointer-events:none;animation:haloPulse 2.2s ease-in-out infinite}
    .card-outer.selected .card-frame{box-shadow:0 0 28px var(--glow),inset 0 0 14px var(--glow2),0 0 0 1px rgba(255,255,255,.25)}
    .card-outer.selected .card-choose{opacity:1;pointer-events:auto}
    @keyframes haloPulse{0%{opacity:.7;transform:scale(.995)}50%{opacity:1;transform:scale(1.01)}100%{opacity:.7;transform:scale(.995)}}

    .card-frame{position:absolute;inset:0;border-radius:inherit;padding:2px;background:conic-gradient(from 180deg,#fff7cc 0deg,#ffd86b 70deg,#ffb13b 120deg,#ffd86b 220deg,#fff7cc 260deg,#ffe89a 320deg,#fff7cc 360deg);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;opacity:.95;box-shadow:0 0 22px rgba(255,216,107,.35),inset 0 0 10px rgba(255,216,107,.25);z-index:1}
    .card-foil{position:absolute;inset:0;border-radius:inherit;background:radial-gradient(120% 120% at 0% 0%,rgba(255,255,255,.1),transparent 45%),radial-gradient(120% 120% at 100% 100%,rgba(255,255,255,.1),transparent 45%),linear-gradient(135deg,rgba(255,210,130,.12),rgba(100,200,255,.1) 50%,rgba(255,120,220,.12)),repeating-conic-gradient(from 0deg,rgba(255,255,255,.08) 0deg 6deg,rgba(255,255,255,.02) 6deg 12deg);mix-blend-mode:overlay;pointer-events:none;animation:foilSpin 8s linear infinite;z-index:0}
    .card-glint{position:absolute;inset:-20%;background:linear-gradient(120deg,rgba(255,255,255,0) 35%,rgba(255,255,255,.18) 50%,rgba(255,255,255,0) 65%);transform:translateX(-60%);animation:glintSweep 4.6s ease-in-out infinite;mix-blend-mode:screen;pointer-events:none;z-index:2}
    @keyframes foilSpin{0%{filter:hue-rotate(0) brightness(1)}50%{filter:hue-rotate(30deg) brightness(1.05)}100%{filter:hue-rotate(0) brightness(1)}}
    @keyframes glintSweep{0%{transform:translateX(-70%) rotate(.2deg)}55%{transform:translateX(60%) rotate(.2deg)}100%{transform:translateX(110%) rotate(.2deg)}}
    .rarity-legendary .card-frame{background:conic-gradient(from 180deg,#fff8d6,#ffe07a,#ffbf4a,#ffd36e,#fff0a6,#ffe07a,#fff8d6);box-shadow:0 0 26px rgba(255,208,80,.45),inset 0 0 12px rgba(255,208,80,.35)}
    .rarity-epic .card-frame{background:conic-gradient(from 180deg,#f6d4ff,#d09aff,#b974ff,#ff64f6,#f6d4ff);box-shadow:0 0 24px rgba(186,120,255,.4),inset 0 0 10px rgba(186,120,255,.3)}
    .rarity-rare .card-frame{background:conic-gradient(from 180deg,#d4f6ff,#9fe3ff,#6fd6ff,#42f5ff,#d4f6ff);box-shadow:0 0 22px rgba(66,245,255,.35),inset 0 0 10px rgba(66,245,255,.25)}
    .rarity-common .card-frame{background:conic-gradient(from 180deg,#f2f2f2,#ddd,#ccc,#eee,#f2f2f2);box-shadow:0 0 18px rgba(220,220,220,.25),inset 0 0 8px rgba(230,230,230,.2)}
    .card-body{position:relative;height:100%;display:flex;flex-direction:column;align-items:center;padding:10px;box-sizing:border-box;gap:4px;z-index:3}
    .card-img{width:100%;flex:0 0 58%;object-fit:cover;border-radius:14px;border:1px solid rgba(0,0,0,.25);box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);background:rgba(255,255,255,.03)}
    .card-img-fallback{display:flex;align-items:center;justify-content:center;font-size:2rem;color:#fef3c7;text-shadow:0 0 10px rgba(255,220,120,.6)}
    .card-name{flex:0 0 14%;width:100%;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;text-overflow:ellipsis;margin-top:4px;font-weight:800;text-align:center;font-size:1.06em;line-height:1.15;letter-spacing:.02em;color:#fff8e7;text-shadow:0 0 6px rgba(255,220,120,.4),0 1px 0 rgba(0,0,0,.6)}
    .rarity-epic .card-name{text-shadow:0 0 6px rgba(186,120,255,.45),0 1px 0 rgba(0,0,0,.6)}
    .rarity-rare .card-name{text-shadow:0 0 6px rgba(66,245,255,.45),0 1px 0 rgba(0,0,0,.6)}
    .rarity-common .card-name{text-shadow:0 0 6px rgba(220,220,220,.4),0 1px 0 rgba(0,0,0,.6)}
    .card-tagline{flex:0 0 12%;width:100%;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;text-overflow:ellipsis;text-align:center;opacity:.96;font-size:.95em;line-height:1.2;min-height:2.1em;color:#fefce8}
    .card-choose{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .14s,transform .14s;pointer-events:none}
    .card-outer:hover .card-choose{opacity:1;transform:scale(1.02);pointer-events:auto}
    .choose-pill{padding:12px 18px;border-radius:999px;background:rgba(17,24,39,.85);color:#fff;border:1px solid rgba(255,255,255,.5);font-weight:700;box-shadow:0 8px 16px rgba(0,0,0,.35);cursor:pointer;user-select:none;text-decoration:none!important;outline:none;border-width:1px;font-size:clamp(.9rem,1.5vw,1rem)}
    .rarity-badge{position:absolute;top:8px;left:10px;z-index:4;padding:4px 10px;font-weight:800;font-size:.78rem;border-radius:999px;letter-spacing:.02em;color:#111827;background:linear-gradient(135deg,#ffe9a6,#ffd36e,#ffbf4a);border:1px solid rgba(0,0,0,.25);box-shadow:0 2px 8px rgba(0,0,0,.25),inset 0 0 6px rgba(255,255,255,.45);text-shadow:0 1px 0 rgba(255,255,255,.6);backdrop-filter:blur(2px)}
    .rarity-epic .rarity-badge{background:linear-gradient(135deg,#f6d4ff,#d09aff,#b974ff);color:#1a0b2e}
    .rarity-rare .rarity-badge{background:linear-gradient(135deg,#d4f6ff,#9fe3ff,#42f5ff);color:#06222a}
    .rarity-common .rarity-badge{background:linear-gradient(135deg,#f4f4f4,#dfdfdf,#cfcfcf);color:#1f2937}
    .mint-plate{position:absolute;top:8px;right:10px;z-index:4;padding:4px 10px;font-weight:700;font-size:.78rem;border-radius:8px;letter-spacing:.02em;color:#fff6d4;background:linear-gradient(135deg,rgba(17,24,39,.9),rgba(45,55,72,.85));border:1px solid rgba(255,255,255,.18);box-shadow:0 2px 8px rgba(0,0,0,.25),inset 0 0 6px rgba(255,255,255,.08);text-shadow:0 1px 0 rgba(0,0,0,.6);backdrop-filter:blur(2px)}
    """

    # Chat input & toolbar (compact)
    CHAT = """
    [data-testid="stChatInput"]{position:fixed!important;bottom:max(0px,env(safe-area-inset-bottom))!important;z-index:1005!important;padding-top:.35rem;padding-bottom:.35rem;background:rgba(255,255,255,.88);backdrop-filter:blur(6px);border-top:1px solid rgba(0,0,0,.08);left:var(--eeva-left,0)!important;right:var(--eeva-right,0)!important;width:auto!important;max-width:none!important;transform:none!important;border-radius:14px 14px 0 0;margin:0}
    @media (prefers-color-scheme:dark){[data-testid="stChatInput"]{background:rgba(17,24,39,.88);border-top:1px solid rgba(255,255,255,.12)}}
    .chat-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:nowrap;justify-content:flex-start;margin-bottom:8px;user-select:none}
    .chat-toolbar .icon-btn{display:inline-flex;align-items:center;justify-content:center;width:clamp(36px,4.5vw,42px);height:clamp(36px,4.5vw,42px);border-radius:10px;border:1px solid rgba(0,0,0,.15);background:rgba(255,255,255,.6);box-shadow:0 1px 2px rgba(0,0,0,.06);text-decoration:none!important;font-size:clamp(18px,2.2vw,22px);line-height:1;cursor:pointer;transition:transform .12s,background .12s,box-shadow .12s;padding:0;color:#111827}
    @media (prefers-color-scheme:dark){.chat-toolbar .icon-btn{border-color:rgba(255,255,255,.18);background:rgba(255,255,255,.07);color:#e5e7eb}}
    """

    # CV banner (compact, unchanged functionality)
    CV = """
    .cv-banner{--panel-bg:rgba(10,18,30,.86);--panel-fg:#e8f0ff;position:relative;display:grid;grid-template-columns:200px 1fr;gap:22px;align-items:start;padding:20px;border-radius:22px;border:1px solid rgba(255,255,255,.06);background:var(--panel-bg);color:var(--panel-fg);max-width:1200px;margin:10px auto 22px;overflow:hidden;backdrop-filter:blur(10px) saturate(110%);clip-path:polygon(12px 0%,calc(100% - 28px) 0%,100% 18px,100% calc(100% - 12px),calc(100% - 12px) 100%,24px 100%,0% calc(100% - 24px),0% 12px);box-shadow:0 20px 40px rgba(0,0,0,.45),0 0 0 1px rgba(255,255,255,.04) inset;isolation:isolate}
    .cv-frame{position:absolute;inset:0;border-radius:inherit;padding:3px;background:conic-gradient(from 180deg,#fff7cc,#ffd86b,#ffb13b,#ffd86b,#fff7cc);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;box-shadow:0 0 24px rgba(255,216,107,.3),inset 0 0 10px rgba(255,216,107,.18);pointer-events:none;z-index:1;opacity:.95}
    .cv-foil{position:absolute;inset:0;border-radius:inherit;z-index:0;background:radial-gradient(120% 120% at 0% 0%,rgba(255,255,255,.08),transparent 45%),radial-gradient(120% 120% at 100% 100%,rgba(255,255,255,.08),transparent 45%),linear-gradient(135deg,rgba(255,210,130,.10),rgba(100,200,255,.08) 50%,rgba(255,120,220,.10)),repeating-conic-gradient(from 0deg,rgba(255,255,255,.06) 0deg 6deg,rgba(255,255,255,.02) 6deg 12deg);mix-blend-mode:overlay;animation:foilSpin 8s linear infinite}
    .cv-glint{position:absolute;inset:-20%;background:linear-gradient(120deg,rgba(255,255,255,0) 35%,rgba(255,255,255,.18) 50%,rgba(255,255,255,0) 65%);transform:translateX(-60%);animation:glintSweep 5s ease-in-out infinite;mix-blend-mode:screen;pointer-events:none;z-index:2}
    .cv-sheen{position:absolute;inset:0;background:radial-gradient(280px 180px at 0% 0%,rgba(66,245,255,.10),transparent 60%),radial-gradient(240px 160px at 100% 100%,rgba(255,100,246,.10),transparent 60%),linear-gradient(135deg,rgba(66,245,255,.10),rgba(154,107,255,.12) 40%,rgba(255,100,246,.10));mix-blend-mode:soft-light;pointer-events:none;z-index:0}
    .rarity-legendary .cv-frame{background:conic-gradient(from 180deg,#fff8d6,#ffe07a,#ffbf4a,#ffd36e,#fff0a6,#ffe07a,#fff8d6);box-shadow:0 0 26px rgba(255,208,80,.45),inset 0 0 12px rgba(255,208,80,.35)}
    .rarity-epic .cv-frame{background:conic-gradient(from 180deg,#f6d4ff,#d09aff,#b974ff,#ff64f6,#f6d4ff);box-shadow:0 0 24px rgba(186,120,255,.4),inset 0 0 10px rgba(186,120,255,.3)}
    .rarity-rare .cv-frame{background:conic-gradient(from 180deg,#d4f6ff,#9fe3ff,#6fd6ff,#42f5ff,#d4f6ff);box-shadow:0 0 22px rgba(66,245,255,.35),inset 0 0 10px rgba(66,245,255,.25)}
    .rarity-common .cv-frame{background:conic-gradient(from 180deg,#f2f2f2,#ddd,#ccc,#eee,#f2f2f2);box-shadow:0 0 18px rgba(220,220,220,.25),inset 0 0 8px rgba(230,230,230,.2)}
    .cv-rarity-badge{position:absolute;top:10px;left:12px;z-index:4;padding:6px 12px;font-weight:800;font-size:.84rem;border-radius:999px;letter-spacing:.02em;color:#111827;background:linear-gradient(135deg,#ffe9a6,#ffd36e,#ffbf4a);border:1px solid rgba(0,0,0,.25);box-shadow:0 2px 8px rgba(0,0,0,.25),inset 0 0 6px rgba(255,255,255,.45);text-shadow:0 1px 0 rgba(255,255,255,.6);backdrop-filter:blur(2px)}
    .rarity-epic .cv-rarity-badge{background:linear-gradient(135deg,#f6d4ff,#d09aff,#b974ff);color:#1a0b2e}
    .rarity-rare .cv-rarity-badge{background:linear-gradient(135deg,#d4f6ff,#9fe3ff,#42f5ff);color:#06222a}
    .rarity-common .cv-rarity-badge{background:linear-gradient(135deg,#f4f4f4,#dfdfdf,#cfcfcf);color:#1f2937}
    .cv-mint-plate{position:absolute;top:10px;right:12px;z-index:4;padding:6px 12px;font-weight:700;font-size:.84rem;border-radius:10px;letter-spacing:.02em;color:#fff6d4;background:linear-gradient(135deg,rgba(17,24,39,.9),rgba(45,55,72,.85));border:1px solid rgba(255,255,255,.18);box-shadow:0 2px 8px rgba(0,0,0,.25),inset 0 0 6px rgba(255,255,255,.08);text-shadow:0 1px 0 rgba(0,0,0,.6);backdrop-filter:blur(2px)}
    .cv-avatar{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:14px;border:1px solid rgba(255,255,255,.14);box-shadow:0 8px 16px rgba(0,0,0,.45),0 0 22px rgba(66,245,255,.18),0 0 26px rgba(255,100,246,.14);display:block}
    .cv-avatar-fallback{display:flex;align-items:center;justify-content:center;font-size:48px;background:rgba(255,255,255,.06);width:100%;aspect-ratio:1/1;border-radius:12px;border:1px solid rgba(255,255,255,.14);color:#cde8ff;box-shadow:0 8px 16px rgba(0,0,0,.45),0 0 22px rgba(66,245,255,.18),0 0 26px rgba(255,100,246,.14)}
    .cv-summary{font-size:clamp(14px,1.05vw,18px);line-height:1.68;color:#e8f1ff;letter-spacing:.02em;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;hyphens:auto;hanging-punctuation:first;text-wrap:pretty;text-shadow:0 0 2px rgba(66,245,255,.25),0 0 8px rgba(154,107,255,.12)}
    .cv-summary .cv-p{margin:0 0 10px}
    .cv-summary .cv-p:last-child{margin-bottom:4px}
    .cv-summary .cv-lead::first-letter{float:left;font-size:2.6em;line-height:.9;padding:4px 8px 2px 6px;margin:4px 8px 0 0;border-radius:6px 10px 6px 6px;background:linear-gradient(135deg,rgba(66,245,255,.30),rgba(255,100,246,.28));color:#0a0f18;box-shadow:inset 0 0 0 1px rgba(255,255,255,.14),0 0 14px rgba(66,245,255,.35),0 0 18px rgba(255,100,246,.28)}
    @media (prefers-color-scheme:light){
      .cv-banner{--panel-bg:rgba(240,245,255,.82);--panel-fg:#0f172a;color:var(--panel-fg);box-shadow:0 10px 24px rgba(0,0,0,.12),0 0 0 1px rgba(0,0,0,.04) inset}
      .cv-summary{color:#0f172a;text-shadow:none}
      .cv-summary .cv-lead::first-letter{color:#0a0f18}
      .cv-avatar{border-color:rgba(0,0,0,.08)}
    }
    @media (max-width:1000px){.cv-banner{grid-template-columns:170px 1fr}}
    @media (max-width:740px){.cv-banner{grid-template-columns:140px 1fr}}
    @media (max-width:640px){
      .cv-banner{grid-template-columns:1fr;gap:14px;padding:16px;clip-path:polygon(10px 0%,calc(100% - 20px) 0%,100% 16px,100% calc(100% - 10px),calc(100% - 10px) 100%,18px 100%,0% calc(100% - 18px),0% 10px)}
      .cv-left{margin-bottom:2px}
    }
    """

    ALL_CSS = _minify(BASE + "\n\n" + CARDS + "\n\n" + CHAT + "\n\n" + CV)

    st.markdown(f"<style>{ALL_CSS}</style>", unsafe_allow_html=True)

    # ---- JS helpers (kept short) ----

    # Track active tab (?tab=characters|chat|bio)
    components.html(
        """
        <script>
        const syncTab=()=>{const b=[...parent.document.querySelectorAll('button[role="tab"]')]
          .find(x=>x.getAttribute('aria-selected')==='true'); if(!b)return;
          const t=(b.innerText||'').trim().toLowerCase().startsWith('💬')?'chat':
                   (b.innerText||'').trim().toLowerCase().startsWith('📜')?'bio':'characters';
          const u=new URL(parent.window.location); if(u.searchParams.get('tab')!==t){u.searchParams.set('tab',t);parent.window.history.replaceState({},'',u);}
        }; setInterval(syncTab,400); setTimeout(syncTab,60);
        </script>
        """,
        height=0
    )

    # Responsive columns (?cols=2/3/4/5) — retained for backward compatibility (no longer used by grid)
    components.html(
        """
        <script>
        (function(){
          const pick=w=>w<560?2:w<900?3:w<1280?4:5;
          const sync=()=>{try{const w=parent.window.innerWidth||1200;const c=String(pick(w));
            const u=new URL(parent.window.location); if(u.searchParams.get('cols')!==c){u.searchParams.set('cols',c);parent.window.history.replaceState({},'',u);}}catch(e){}};
          parent.window.addEventListener('resize',sync);
          setInterval(sync,600); setTimeout(sync,40); setTimeout(sync,200); setTimeout(sync,800);
        })();
        </script>
        """,
        height=0
    )

    # Chat input layout (sidebar-aware) + bottom padding sync
    components.html(
        """
        <script>
        (function(){
          const px=n=>Math.max(0,Math.round(n))+'px';
          function layout(){
            const d=parent.document, input=d.querySelector('[data-testid="stChatInput"]'), main=d.querySelector('.block-container');
            if(!input||!main) return;
            const vw=parent.window.innerWidth||1200;
            let want=vw>=900?0.75*vw:vw>=600?0.85*vw:0.95*vw; want=Math.max(360,Math.min(1100,Math.round(want)));
            const r=main.getBoundingClientRect(); let L=r.left, R=(d.documentElement.clientWidth-r.right);
            const sb=d.querySelector('aside[data-testid="stSidebar"]'); if(sb){const sr=sb.getBoundingClientRect(); if(sr.width>0&&sr.left<(vw-8)) L=Math.max(L,Math.round(sr.right));}
            const W=d.documentElement.clientWidth, avail=Math.max(0,W-L-R), finW=Math.min(want,avail), pad=Math.max(0,(avail-finW)/2);
            const left=L+pad, right=W-left-finW;
            input.style.setProperty('--eeva-left',px(left)); input.style.setProperty('--eeva-right',px(right));
            const h=input.getBoundingClientRect().height||96; main.style.paddingBottom=px(h+24);
          }
          const d=parent.document, obs=el=>{if(!el)return; new ResizeObserver(layout).observe(el);};
          obs(d.body); obs(d.querySelector('.block-container')); obs(d.querySelector('aside[data-testid="stSidebar"]'));
          parent.window.addEventListener('resize',layout); parent.window.addEventListener('scroll',layout);
          setTimeout(layout,40); setTimeout(layout,160); setTimeout(layout,360); setTimeout(layout,800);
          (function wait(){const i=d.querySelector('[data-testid="stChatInput"]'); if(!i){setTimeout(wait,120);return;} new ResizeObserver(layout).observe(i); layout();})();
        })();
        </script>
        """,
        height=0
    )

    # Chooser: switch to chat & select persona (kept)
    components.html(
        """
        <script>
        (function(){
          try{
            if(!parent||!parent.window) return;
            parent.window.eevaChoose=function(key){
              try{
                const u=new URL(parent.window.location);
                u.searchParams.set('tab','chat'); u.searchParams.set('select',key);
                parent.window.history.replaceState({},'',u); parent.window.location.href=String(u);
              }catch(e){console.error('eevaChoose',e); parent.window.location.reload();}
            };
          }catch(e){console.error('init eevaChoose',e);}
        })();
        </script>
        """,
        height=0
    )
