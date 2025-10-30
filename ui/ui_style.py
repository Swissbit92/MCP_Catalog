# ui/ui_style.py
# Global CSS/JS injection + query param sync helpers (Cyberpunk CV banner, shine on image only, resized & fixed grid)

import streamlit as st
import streamlit.components.v1 as components

def inject_global_css_js():
    st.markdown("""
    <style>
    .block-container{padding-top:1rem;padding-bottom:7rem}
    div[data-testid="column"]{padding-left:2px!important;padding-right:2px!important}

    button[role="tab"],button[role="tab"] *{color:#1f2937!important}
    button[role="tab"][aria-selected="true"],button[role="tab"][aria-selected="true"] *{color:#111827!important;font-weight:700!important}
    @media (prefers-color-scheme:dark){
      button[role="tab"],button[role="tab"] *{color:#e5e7eb!important}
      button[role="tab"][aria-selected="true"],button[role="tab"][aria-selected="true"] *{color:#fff!important}
    }

    .eeva-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:8px 0 4px}
    .eeva-title{font-size:22px;font-weight:600}
    .chip{padding:2px 10px;border-radius:12px;background:#f7f7f9;border:1px solid #d0d0d6;color:#222;font-size:.85rem}
    .chip-success{background:#e6ffe6;border-color:#b3ffb3;color:#155e2b}
    .chip-soft{background:#eef;border-color:#ccd;color:#1f2a44}
    .chip-warn{background:#fff7e6;border-color:#ffd699;color:#8a6100}
    .chip-error{background:#ffe6e6;border-color:#ffb3b3;color:#7a1f1f}
    @media (prefers-color-scheme:dark){
      .chip{background:#1f2937;border-color:#374151;color:#e5e7eb}
      .chip-success{background:#064e3b;border-color:#10b981;color:#d1fae5}
      .chip-soft{background:#1e293b;border-color:#334155;color:#e2e8f0}
      .chip-warn{background:#4a3b13;border-color:#f59e0b;color:#fde68a}
      .chip-error{background:#4c1d1d;border-color:#f87171;color:#fecaca}
    }
    .eeva-subtle{color:#6b6b6b;margin-bottom:10px}
    @media (prefers-color-scheme:dark){.eeva-subtle{color:#a3a3a3}}

    /* Persona cards (core unchanged) */
    .card-outer{width:clamp(140px,18vw,240px);aspect-ratio:2/3;border-radius:16px;position:relative;overflow:hidden;box-shadow:0 8px 14px rgba(0,0,0,.22);background:linear-gradient(135deg,rgba(255,255,255,.75),rgba(200,220,255,.55),rgba(255,215,240,.55));border:1px solid rgba(255,255,255,.6);transition:.18s;backdrop-filter:blur(6px);margin-bottom:8px;font-size:clamp(12px,.9vw,16px)}
    @media (min-width:1280px){.card-outer{width:clamp(160px,16vw,260px)}}
    .card-outer:hover{transform:translateY(-3px) rotateZ(-.35deg);box-shadow:0 12px 20px rgba(0,0,0,.28);filter:saturate(1.05)}
    .card-outer.revealed{box-shadow:0 0 18px 2px rgba(80,200,255,.75),inset 0 0 12px rgba(255,255,255,.45);border-color:rgba(80,200,255,.8)}
    .card-rarity{position:absolute;inset:0;background:conic-gradient(from 180deg at 50% 50%,rgba(255,255,255,.12),rgba(0,0,0,.12),rgba(255,255,255,.12));mix-blend-mode:soft-light;pointer-events:none}
    .card-body{position:relative;height:100%;display:flex;flex-direction:column;align-items:center;padding:10px;box-sizing:border-box;gap:4px}
    .card-img{width:100%;flex:0 0 58%;object-fit:cover;border-radius:12px;border:1px solid rgba(0,0,0,.05)}
    .card-name{flex:0 0 14%;width:100%;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;text-overflow:ellipsis;margin-top:4px;font-weight:700;text-align:center;font-size:1.05em;line-height:1.15}
    .card-tagline{flex:0 0 12%;width:100%;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;text-overflow:ellipsis;text-align:center;opacity:.95;font-size:.95em;line-height:1.2;min-height:2.1em}
    .card-choose{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:.14s;pointer-events:none}
    .card-outer:hover .card-choose{opacity:1;transform:scale(1.02);pointer-events:auto}
    .choose-pill{padding:12px 18px;border-radius:999px;background:rgba(17,24,39,.85);color:#fff;border:1px solid rgba(255,255,255,.5);font-weight:700;box-shadow:0 8px 16px rgba(0,0,0,.35);cursor:pointer;text-decoration:none!important;font-size:clamp(.9rem,1.5vw,1rem)}
    @media (prefers-color-scheme:dark){
      .card-outer{border-color:#2f3542;background:linear-gradient(135deg,rgba(23,30,45,.85),rgba(32,40,60,.7))}
      .choose-pill{background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.45)}
    }

    /* Chat input */
    [data-testid="stChatInput"]{position:fixed!important;bottom:max(0px,env(safe-area-inset-bottom))!important;z-index:1005!important;padding:.35rem 0;background:rgba(255,255,255,.88);backdrop-filter:blur(6px);border-top:1px solid rgba(0,0,0,.08);left:var(--eeva-left,0)!important;right:var(--eeva-right,0)!important;width:auto!important;max-width:none!important;border-radius:14px 14px 0 0;margin:0}
    @media (prefers-color-scheme:dark){[data-testid="stChatInput"]{background:rgba(17,24,39,.88);border-top:1px solid rgba(255,255,255,.12)}}

    /* Toolbar */
    .chat-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:nowrap;margin-bottom:8px;user-select:none}
    .chat-toolbar .icon-btn{display:inline-flex;align-items:center;justify-content:center;width:clamp(36px,4.5vw,42px);height:clamp(36px,4.5vw,42px);border-radius:10px;border:1px solid rgba(0,0,0,.15);background:rgba(255,255,255,.6);box-shadow:0 1px 2px rgba(0,0,0,.06);text-decoration:none!important;font-size:clamp(18px,2.2vw,22px);line-height:1;cursor:pointer;transition:.12s;padding:0;color:#111827}
    .chat-toolbar .icon-btn:hover{transform:translateY(-1px);background:rgba(255,255,255,.85);box-shadow:0 3px 8px rgba(0,0,0,.08)}
    @media (prefers-color-scheme:dark){
      .chat-toolbar .icon-btn{border-color:rgba(255,255,255,.18);background:rgba(255,255,255,.07);color:#e5e7eb}
      .chat-toolbar .icon-btn:hover{background:rgba(255,255,255,.12)}
    }

    /* ================== Cyberpunk CV Banner (resized & fixed) ================== */
    /* Force grid even inside Streamlit's markdown wrapper */
    .stMarkdown .cv-banner{display:grid!important}

    .cv-banner{
      --panel-bg:rgba(10,18,30,.86);--panel-fg:#e8f0ff;--grid-a:rgba(150,200,255,.08);--grid-b:rgba(255,120,220,.06);
      position:relative;display:grid;grid-template-columns:180px 1fr;gap:18px;align-items:start;padding:18px;border-radius:16px;
      border:1px solid rgba(255,255,255,.08);
      background:
        radial-gradient(240px 160px at 0% 0%,rgba(66,245,255,.10),transparent 60%),
        radial-gradient(220px 140px at 100% 100%,rgba(255,100,246,.10),transparent 60%),
        linear-gradient(135deg,rgba(66,245,255,.10),rgba(154,107,255,.12) 40%,rgba(255,100,246,.10)),
        var(--panel-bg);
      color:var(--panel-fg);
      width:min(95vw, 880px);
      margin:6px auto 16px;
      overflow:hidden;backdrop-filter:blur(10px) saturate(110%);
      clip-path:polygon(10px 0%,calc(100% - 24px) 0%,100% 16px,100% calc(100% - 10px),calc(100% - 10px) 100%,20px 100%,0% calc(100% - 20px),0% 10px);
      box-shadow:0 16px 30px rgba(0,0,0,.40),0 0 0 1px rgba(255,255,255,.04) inset,0 0 18px rgba(66,245,255,.10),0 0 20px rgba(255,100,246,.10);
    }
    .cv-banner::before{content:"";position:absolute;inset:0;background:linear-gradient(to right,var(--grid-a) 1px,transparent 1px),linear-gradient(to bottom,var(--grid-b) 1px,transparent 1px);background-size:20px 20px,20px 20px;opacity:.42;mix-blend-mode:soft-light;pointer-events:none}

    .cv-left{position:relative;border-radius:12px;overflow:hidden}
    .cv-right{min-width:0} /* allow wrapping so grid stays side-by-side */

    /* IMAGE + animated shine (image only) */
    .cv-avatar{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:12px;border:1px solid rgba(255,255,255,.14);display:block;box-shadow:0 6px 12px rgba(0,0,0,.4),0 0 16px rgba(66,245,255,.16),0 0 18px rgba(255,100,246,.12)}
    .cv-avatar-fallback{display:flex;align-items:center;justify-content:center;font-size:44px;background:rgba(255,255,255,.06);width:100%;aspect-ratio:1/1;border-radius:12px;border:1px solid rgba(255,255,255,.14);box-shadow:0 6px 12px rgba(0,0,0,.4),0 0 16px rgba(66,245,255,.16),0 0 18px rgba(255,100,246,.12);color:#cde8ff}
    .cv-left::after{
      content:"";position:absolute;inset:0;pointer-events:none;
      background:linear-gradient(120deg,rgba(255,255,255,0) 20%,rgba(255,255,255,.32) 45%,rgba(255,255,255,0) 65%);
      transform:translateX(-70%);mix-blend-mode:screen;animation:imgSheen 4.8s infinite ease-in-out;
    }
    @keyframes imgSheen{0%{transform:translateX(-75%)}55%{transform:translateX(70%)}100%{transform:translateX(110%)}}

    /* Summary typography */
    .cv-summary{font-size:clamp(14px,1vw,17px);line-height:1.64;color:#e8f1ff;letter-spacing:.02em;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;hyphens:auto;hanging-punctuation:first;text-wrap:pretty;text-shadow:0 0 2px rgba(66,245,255,.22),0 0 6px rgba(154,107,255,.10)}
    .cv-summary .cv-p{margin:0 0 9px}
    .cv-summary .cv-p:last-child{margin-bottom:4px}
    .cv-summary .cv-lead::first-letter{float:left;font-size:2.4em;line-height:.9;padding:4px 8px 2px 6px;margin:2px 8px 0 0;border-radius:6px 10px 6px 6px;background:linear-gradient(135deg,rgba(66,245,255,.28),rgba(255,100,246,.26));color:#0a0f18;box-shadow:inset 0 0 0 1px rgba(255,255,255,.14),0 0 12px rgba(66,245,255,.30),0 0 16px rgba(255,100,246,.24)}

    /* Light scheme tweaks */
    @media (prefers-color-scheme:light){
      .cv-banner{--panel-bg:rgba(240,245,255,.82);--panel-fg:#0f172a;color:var(--panel-fg);box-shadow:0 10px 20px rgba(0,0,0,.12),0 0 0 1px rgba(0,0,0,.04) inset,0 0 14px rgba(66,245,255,.10),0 0 16px rgba(255,100,246,.08)}
      .cv-summary{color:#0f172a;text-shadow:none}
      .cv-avatar{border-color:rgba(0,0,0,.08)}
    }

    /* Responsive */
    @media (max-width:1100px){.cv-banner{grid-template-columns:170px 1fr}}
    @media (max-width:900px){.cv-banner{grid-template-columns:160px 1fr}}
    @media (max-width:740px){.cv-banner{grid-template-columns:150px 1fr}}
    @media (max-width:640px){
      .cv-banner{
        width:min(96vw, 620px);
        grid-template-columns:1fr;gap:12px;padding:16px;
        clip-path:polygon(10px 0%,calc(100% - 20px) 0%,100% 16px,100% calc(100% - 10px),calc(100% - 10px) 100%,18px 100%,0% calc(100% - 18px),0% 10px)
      }
      .cv-left{margin-bottom:2px}
    }
    </style>
    """, unsafe_allow_html=True)

    # Active tab → ?tab=
    components.html("""
    <script>
    const tick=()=>{const a=[...parent.document.querySelectorAll('button[role="tab"]')].find(b=>b.getAttribute('aria-selected')==='true');if(!a)return;
      const t=(a.innerText||'').trim().toLowerCase();let tab='characters';if(t.startsWith('💬'))tab='chat';else if(t.startsWith('📜'))tab='bio';
      const u=new URL(parent.window.location);if(u.searchParams.get('tab')!==tab){u.searchParams.set('tab',tab);parent.window.history.replaceState({},'',u)}};
    setInterval(tick,400);setTimeout(tick,60);
    </script>
    """, height=0)

    # Characters tab: ?cols=
    components.html("""
    <script>
    (function(){function c(w){if(w<560)return 2;if(w<900)return 3;if(w<1280)return 4;return 5}
      function s(){try{const w=parent.window.innerWidth||1200,m=c(w),u=new URL(parent.window.location);
        if(u.searchParams.get('cols')!==String(m)){u.searchParams.set('cols',String(m));parent.window.history.replaceState({},'',u)}}catch(e){}}
      parent.window.addEventListener('resize',s);setInterval(s,600);setTimeout(s,40);setTimeout(s,200);setTimeout(s,800);
    })();
    </script>
    """, height=0)

    # Chat input layout (sidebar-aware) + padding; cap width to match banner feel
    components.html("""
    <script>
    (function(){
      const px=n=>Math.max(0,Math.round(n))+'px';
      function layout(){
        const d=parent.document,i=d.querySelector('[data-testid="stChatInput"]'),m=d.querySelector('.block-container');if(!i||!m)return;
        const vw=parent.window.innerWidth||1200;let want=.95*vw;if(vw>=600)want=.85*vw;if(vw>=900)want=.72*vw;want=Math.max(360,Math.min(960,Math.round(want)));
        const r=m.getBoundingClientRect();let L=r.left;const R=(d.documentElement.clientWidth-r.right);
        const sb=d.querySelector('aside[data-testid="stSidebar"]');if(sb){const sbr=sb.getBoundingClientRect();const vis=(sbr.width>0)&&(sbr.left<(vw-8));if(vis)L=Math.max(L,Math.round(sbr.right))}
        const W=d.documentElement.clientWidth,avail=Math.max(0,W-L-R),w=Math.min(want,avail),pad=Math.max(0,(avail-w)/2),l=L+pad,ri=W-l-w;
        i.style.setProperty('--eeva-left',px(l));i.style.setProperty('--eeva-right',px(ri));m.style.paddingBottom=px((i.getBoundingClientRect().height||96)+24);
      }
      const d=parent.document,obs=e=>{if(!e)return;new ResizeObserver(layout).observe(e)};
      obs(d.body);obs(d.querySelector('.block-container'));obs(d.querySelector('aside[data-testid="stSidebar"]'));
      parent.window.addEventListener('resize',layout);parent.window.addEventListener('scroll',layout);
      setTimeout(layout,40);setTimeout(layout,160);setTimeout(layout,360);setTimeout(layout,800);
      (function wait(){const i=d.querySelector('[data-testid="stChatInput"]');if(!i){setTimeout(wait,120);return}new ResizeObserver(layout).observe(i);layout()})();
    })();
    </script>
    """, height=0)

    # Global chooser helper
    components.html("""
    <script>
    (function(){try{if(!parent||!parent.window)return;parent.window.eevaChoose=function(key){
      try{const u=new URL(parent.window.location);u.searchParams.set('tab','chat');u.searchParams.set('select',key);
        parent.window.history.replaceState({},'',u);parent.window.location.href=u.toString()}catch(e){parent.window.location.reload()}}
    }catch(e){}})();
    </script>
    """, height=0)
