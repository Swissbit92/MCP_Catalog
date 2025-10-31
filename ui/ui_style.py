# ui/ui_style.py
# Global CSS/JS injection + query param sync helpers
# Includes: Gacha gold cards + Cyberpunk CV banner with rarity palettes

import streamlit as st
import streamlit.components.v1 as components

def inject_global_css_js():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.0rem; padding-bottom: 7.5rem; }
    div[data-testid="column"] { padding-left: 2px !important; padding-right: 2px !important; }

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

    /* ======================= Gacha-style Persona Cards ======================= */
    .card-outer {
      width: clamp(140px, 18vw, 240px);
      aspect-ratio: 2 / 3;
      height: auto;
      border-radius: 20px;
      position: relative;
      overflow: hidden;
      margin-bottom: 10px;
      font-size: clamp(12px, 0.9vw, 16px);
      background: linear-gradient(160deg, rgba(15,20,35,0.85), rgba(20,28,48,0.78));
      box-shadow: 0 14px 24px rgba(0,0,0,0.35);
      backdrop-filter: blur(6px) saturate(110%);
      transform: translateZ(0);
      transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
      isolation: isolate;
    }
    .card-outer:hover {
      transform: translateY(-3px) rotateZ(-0.35deg);
      box-shadow: 0 18px 32px rgba(0,0,0,0.45);
      filter: saturate(1.05);
    }

    /* Rarity glow variables for selected state */
    .rarity-legendary { --glow: rgba(255,208,80,0.90);  --glow2: rgba(255,240,166,0.70); }
    .rarity-epic      { --glow: rgba(186,120,255,0.85); --glow2: rgba(246,212,255,0.65); }
    .rarity-rare      { --glow: rgba( 66,245,255,0.85); --glow2: rgba(212,246,255,0.65); }
    .rarity-common    { --glow: rgba(230,230,230,0.85); --glow2: rgba(250,250,250,0.60); }

    /* Selected/active card state — pulsing halo + boosted frame glow */
    .card-outer.selected {
      transform: translateY(-4px) scale(1.01);
      filter: saturate(1.12) brightness(1.03);
      box-shadow:
        0 20px 40px rgba(0,0,0,0.50),
        0 0 0 1px rgba(255,255,255,0.22),
        0 0 24px var(--glow);
    }
    .card-outer.selected::before{
      content:"";
      position:absolute; inset:-8px;
      border-radius: 26px;
      background:
        radial-gradient(60% 50% at 50% 6%, var(--glow2), transparent 60%),
        radial-gradient(70% 60% at 50% 100%, var(--glow), transparent 70%);
      filter: blur(14px);
      opacity: 0.85;
      z-index: 0; pointer-events:none;
      animation: haloPulse 2.2s ease-in-out infinite;
    }
    .card-outer.selected .card-frame{
      box-shadow:
        0 0 28px var(--glow),
        inset 0 0 14px var(--glow2),
        0 0 0 1px rgba(255,255,255,0.25);
    }
    .card-outer.selected .card-choose{
      opacity: 1; pointer-events:auto; /* keep the CTA visible when selected */
    }

    @keyframes haloPulse {
      0%   { opacity: 0.70; transform: scale(0.995); }
      50%  { opacity: 1.00; transform: scale(1.010); }
      100% { opacity: 0.70; transform: scale(0.995); }
    }

    .card-frame{
      position: absolute; inset: 0;
      border-radius: inherit;
      padding: 2px;
      background:
        conic-gradient(from 180deg,
          #fff7cc 0deg, #ffd86b 70deg, #ffb13b 120deg, #ffd86b 220deg,
          #fff7cc 260deg, #ffe89a 320deg, #fff7cc 360deg);
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      pointer-events: none;
      opacity: 0.95;
      box-shadow: 0 0 22px rgba(255,216,107,0.35), inset 0 0 10px rgba(255,216,107,0.25);
      z-index: 1;
    }
    .card-foil{
      position: absolute; inset: 0;
      border-radius: inherit;
      background:
        radial-gradient(120% 120% at 0% 0%, rgba(255,255,255,0.10), transparent 45%),
        radial-gradient(120% 120% at 100% 100%, rgba(255,255,255,0.10), transparent 45%),
        linear-gradient(135deg, rgba(255,210,130,0.12), rgba(100,200,255,0.10) 50%, rgba(255,120,220,0.12)),
        repeating-conic-gradient(from 0deg, rgba(255,255,255,0.08) 0deg 6deg, rgba(255,255,255,0.02) 6deg 12deg);
      mix-blend-mode: overlay;
      pointer-events: none;
      animation: foilSpin 8s linear infinite;
      z-index: 0;
    }
    @keyframes foilSpin { 0% { filter: hue-rotate(0deg) brightness(1); } 50% { filter: hue-rotate(30deg) brightness(1.05); } 100% { filter: hue-rotate(0deg) brightness(1); } }
    .card-glint{
      position: absolute; inset: -20%;
      background: linear-gradient(120deg, rgba(255,255,255,0.0) 35%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.0) 65%);
      transform: translateX(-60%);
      animation: glintSweep 4.6s ease-in-out infinite;
      mix-blend-mode: screen;
      pointer-events: none;
      z-index: 2;
    }
    @keyframes glintSweep { 0% { transform: translateX(-70%) rotate(0.2deg); } 55% { transform: translateX(60%) rotate(0.2deg); } 100% { transform: translateX(110%) rotate(0.2deg); } }
    .rarity-legendary .card-frame{
      background: conic-gradient(from 180deg, #fff8d6 0deg, #ffe07a 60deg, #ffbf4a 130deg, #ffd36e 190deg, #fff0a6 260deg, #ffe07a 320deg, #fff8d6 360deg);
      box-shadow: 0 0 26px rgba(255,208,80,0.45), inset 0 0 12px rgba(255,208,80,0.35);
    }
    .rarity-epic .card-frame{
      background: conic-gradient(from 180deg, #f6d4ff 0deg, #d09aff 90deg, #b974ff 170deg, #ff64f6 230deg, #f6d4ff 360deg);
      box-shadow: 0 0 24px rgba(186,120,255,0.40), inset 0 0 10px rgba(186,120,255,0.30);
    }
    .rarity-rare .card-frame{
      background: conic-gradient(from 180deg, #d4f6ff 0deg, #9fe3ff 90deg, #6fd6ff 170deg, #42f5ff 230deg, #d4f6ff 360deg);
      box-shadow: 0 0 22px rgba(66,245,255,0.35), inset 0 0 10px rgba(66,245,255,0.25);
    }
    .rarity-common .card-frame{
      background: conic-gradient(from 180deg, #f2f2f2 0deg, #dddddd 90deg, #cccccc 170deg, #eeeeee 230deg, #f2f2f2 360deg);
      box-shadow: 0 0 18px rgba(220,220,220,0.25), inset 0 0 8px rgba(230,230,230,0.20);
    }
    .card-body { position: relative; height: 100%; display: flex; flex-direction: column; align-items: center; padding: 10px; box-sizing: border-box; gap: 4px; z-index: 3; }
    .card-img { width: 100%; flex: 0 0 58%; object-fit: cover; border-radius: 14px; border: 1px solid rgba(0,0,0,0.25); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); }
    .card-img-fallback{ display:flex; align-items:center; justify-content:center; font-size:2rem; color:#fef3c7; text-shadow: 0 0 10px rgba(255,220,120,0.6); }
    .card-name { flex: 0 0 14%; width: 100%; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; font-weight: 800; text-align: center; font-size: 1.06em; line-height: 1.15; letter-spacing: .02em; color: #fff8e7; text-shadow: 0 0 6px rgba(255,220,120,0.4), 0 1px 0 rgba(0,0,0,0.6); }
    .rarity-epic .card-name { text-shadow: 0 0 6px rgba(186,120,255,0.45), 0 1px 0 rgba(0,0,0,0.6); }
    .rarity-rare .card-name { text-shadow: 0 0 6px rgba(66,245,255,0.45), 0 1px 0 rgba(0,0,0,0.6); }
    .rarity-common .card-name { text-shadow: 0 0 6px rgba(220,220,220,0.4), 0 1px 0 rgba(0,0,0,0.6); }
    .card-tagline { flex: 0 0 12%; width: 100%; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; text-overflow: ellipsis; text-align: center; opacity: 0.96; font-size: 0.95em; line-height: 1.2; min-height: 2.1em; color:#fefce8; }
    .card-choose { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; opacity:0; transition:opacity 140ms ease, transform 140ms ease; pointer-events:none; }
    .card-outer:hover .card-choose { opacity:1; transform:scale(1.02); pointer-events:auto; }
    .choose-pill { padding:12px 18px; border-radius:999px; background:rgba(17,24,39,0.85); color:#fff; border:1px solid rgba(255,255,255,0.5); font-weight:700; box-shadow:0 8px 16px rgba(0,0,0,0.35); cursor:pointer; user-select:none; text-decoration:none !important; outline:none; border-width:1px; font-size: clamp(0.9rem, 1.5vw, 1rem); }
    .choose-pill:hover { filter:brightness(1.08); }
    .rarity-badge{
      position: absolute; top: 8px; left: 10px; z-index: 4;
      padding: 4px 10px; font-weight: 800; font-size: 0.78rem; border-radius: 999px; letter-spacing: .02em;
      color: #111827; background: linear-gradient(135deg, #ffe9a6, #ffd36e, #ffbf4a);
      border: 1px solid rgba(0,0,0,0.25); box-shadow: 0 2px 8px rgba(0,0,0,0.25), inset 0 0 6px rgba(255,255,255,0.45);
      text-shadow: 0 1px 0 rgba(255,255,255,0.6); backdrop-filter: blur(2px);
    }
    .rarity-epic .rarity-badge{ background: linear-gradient(135deg, #f6d4ff, #d09aff, #b974ff); color:#1a0b2e; }
    .rarity-rare .rarity-badge{ background: linear-gradient(135deg, #d4f6ff, #9fe3ff, #42f5ff); color:#06222a; }
    .rarity-common .rarity-badge{ background: linear-gradient(135deg, #f4f4f4, #dfdfdf, #cfcfcf); color:#1f2937; }
    .mint-plate{
      position: absolute; top: 8px; right: 10px; z-index: 4;
      padding: 4px 10px; font-weight: 700; font-size: 0.78rem; border-radius: 8px; letter-spacing: .02em;
      color: #fff6d4; background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(45,55,72,0.85));
      border: 1px solid rgba(255,255,255,0.18); box-shadow: 0 2px 8px rgba(0,0,0,0.25), inset 0 0 6px rgba(255,255,255,0.08);
      text-shadow: 0 1px 0 rgba(0,0,0,0.6); backdrop-filter: blur(2px);
    }

    /* ===================== Chat Input ===================== */
    [data-testid="stChatInput"] {
      position: fixed !important;
      bottom: max(0px, env(safe-area-inset-bottom)) !important;
      z-index: 1005 !important;
      padding-top: 0.35rem; padding-bottom: 0.35rem;
      background: rgba(255,255,255,0.88);
      backdrop-filter: blur(6px);
      border-top: 1px solid rgba(0,0,0,0.08);
      left: var(--eeva-left, 0px) !important;
      right: var(--eeva-right, 0px) !important;
      width: auto !important; max-width: none !important; transform: none !important;
      border-radius: 14px 14px 0 0; margin: 0;
    }
    @media (prefers-color-scheme: dark) {
      [data-testid="stChatInput"] { background: rgba(17,24,39,0.88); border-top: 1px solid rgba(255,255,255,0.12); }
    }

    .chat-toolbar{
      display:flex; align-items:center; gap: 10px; flex-wrap: nowrap; justify-content: flex-start;
      margin-bottom: 8px; user-select: none;
    }
    .chat-toolbar .icon-btn{
      display:inline-flex; align-items:center; justify-content:center;
      width: clamp(36px, 4.5vw, 42px); height: clamp(36px, 4.5vw, 42px);
      border-radius: 10px; border: 1px solid rgba(0,0,0,0.15);
      background: rgba(255,255,255,0.6); box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      text-decoration: none !important; font-size: clamp(18px, 2.2vw, 22px);
      line-height: 1; cursor: pointer; transition: transform 120ms ease, background 120ms ease, box-shadow 120ms ease;
      padding: 0; color: #111827;
    }
    .chat-toolbar .icon-btn:hover{ transform: translateY(-1px); background: rgba(255,255,255,0.85); box-shadow: 0 3px 8px rgba(0,0,0,0.08); }
    @media (prefers-color-scheme: dark) {
      .chat-toolbar .icon-btn{ border-color: rgba(255,255,255,0.18); background: rgba(255,255,255,0.07); color: #e5e7eb; }
      .chat-toolbar .icon-btn:hover{ background: rgba(255,255,255,0.12); }
    }

    /* ===================== Cyberpunk CV Gacha Banner ===================== */
    .cv-banner{
      --panel-bg:    rgba(10, 18, 30, 0.86);
      --panel-fg:    #e8f0ff;
      position: relative;
      display: grid;
      grid-template-columns: 200px 1fr; /* IMAGE | TEXT */
      gap: 22px;
      align-items: start;
      padding: 20px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.06);
      background: var(--panel-bg);
      color: var(--panel-fg);
      max-width: 1200px;
      margin: 10px auto 22px auto;
      overflow: hidden;
      backdrop-filter: blur(10px) saturate(110%);
      clip-path: polygon(12px 0%, calc(100% - 28px) 0%, 100% 18px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 24px 100%, 0% calc(100% - 24px), 0% 12px);
      box-shadow: 0 20px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.04) inset;
      isolation: isolate;
    }

    /* Decorative frame layers (rarity-driven) */
    .cv-frame{
      position:absolute; inset:0; border-radius: inherit;
      padding: 3px;
      background: conic-gradient(from 180deg, #fff7cc, #ffd86b, #ffb13b, #ffd86b, #fff7cc);
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      box-shadow: 0 0 24px rgba(255,216,107,0.30), inset 0 0 10px rgba(255,216,107,0.18);
      pointer-events:none; z-index:1; opacity:0.95;
    }
    .cv-foil{
      position:absolute; inset:0; border-radius: inherit; z-index:0;
      background:
        radial-gradient(120% 120% at 0% 0%, rgba(255,255,255,0.08), transparent 45%),
        radial-gradient(120% 120% at 100% 100%, rgba(255,255,255,0.08), transparent 45%),
        linear-gradient(135deg, rgba(255,210,130,0.10), rgba(100,200,255,0.08) 50%, rgba(255,120,220,0.10)),
        repeating-conic-gradient(from 0deg, rgba(255,255,255,0.06) 0deg 6deg, rgba(255,255,255,0.02) 6deg 12deg);
      mix-blend-mode: overlay; animation: foilSpin 8s linear infinite;
    }
    .cv-glint{
      position:absolute; inset:-20%;
      background: linear-gradient(120deg, rgba(255,255,255,0.0) 35%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.0) 65%);
      transform: translateX(-60%); animation: glintSweep 5.0s ease-in-out infinite;
      mix-blend-mode: screen; pointer-events:none; z-index:2;
    }
    .cv-sheen{
      position:absolute; inset:0;
      background:
        radial-gradient(280px 180px at 0% 0%, rgba(66,245,255,0.10), transparent 60%),
        radial-gradient(240px 160px at 100% 100%, rgba(255,100,246,0.10), transparent 60%),
        linear-gradient(135deg, rgba(66,245,255,0.10), rgba(154,107,255,0.12) 40%, rgba(255,100,246,0.10));
      mix-blend-mode: soft-light; pointer-events:none; z-index:0;
    }

    /* Rarity palettes for CV frame */
    .rarity-legendary .cv-frame{
      background: conic-gradient(from 180deg, #fff8d6, #ffe07a, #ffbf4a, #ffd36e, #fff0a6, #ffe07a, #fff8d6);
      box-shadow: 0 0 26px rgba(255,208,80,0.45), inset 0 0 12px rgba(255,208,80,0.35);
    }
    .rarity-epic .cv-frame{
      background: conic-gradient(from 180deg, #f6d4ff, #d09aff, #b974ff, #ff64f6, #f6d4ff);
      box-shadow: 0 0 24px rgba(186,120,255,0.40), inset 0 0 10px rgba(186,120,255,0.30);
    }
    .rarity-rare .cv-frame{
      background: conic-gradient(from 180deg, #d4f6ff, #9fe3ff, #6fd6ff, #42f5ff, #d4f6ff);
      box-shadow: 0 0 22px rgba(66,245,255,0.35), inset 0 0 10px rgba(66,245,255,0.25);
    }
    .rarity-common .cv-frame{
      background: conic-gradient(from 180deg, #f2f2f2, #dddddd, #cccccc, #eeeeee, #f2f2f2);
      box-shadow: 0 0 18px rgba(220,220,220,0.25), inset 0 0 8px rgba(230,230,230,0.20);
    }

    /* Badges for banner */
    .cv-rarity-badge{
      position: absolute; top: 10px; left: 12px; z-index: 4;
      padding: 6px 12px; font-weight: 800; font-size: 0.84rem; border-radius: 999px; letter-spacing:.02em;
      color: #111827; background: linear-gradient(135deg, #ffe9a6, #ffd36e, #ffbf4a);
      border: 1px solid rgba(0,0,0,0.25); box-shadow: 0 2px 8px rgba(0,0,0,0.25), inset 0 0 6px rgba(255,255,255,0.45);
      text-shadow: 0 1px 0 rgba(255,255,255,0.6); backdrop-filter: blur(2px);
    }
    .rarity-epic .cv-rarity-badge{ background: linear-gradient(135deg, #f6d4ff, #d09aff, #b974ff); color:#1a0b2e; }
    .rarity-rare .cv-rarity-badge{ background: linear-gradient(135deg, #d4f6ff, #9fe3ff, #42f5ff); color:#06222a; }
    .rarity-common .cv-rarity-badge{ background: linear-gradient(135deg, #f4f4f4, #dfdfdf, #cfcfcf); color:#1f2937; }

    .cv-mint-plate{
      position: absolute; top: 10px; right: 12px; z-index: 4;
      padding: 6px 12px; font-weight: 700; font-size: 0.84rem; border-radius: 10px; letter-spacing:.02em;
      color: #fff6d4; background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(45,55,72,0.85));
      border: 1px solid rgba(255,255,255,0.18); box-shadow: 0 2px 8px rgba(0,0,0,0.25), inset 0 0 6px rgba(255,255,255,0.08);
      text-shadow: 0 1px 0 rgba(0,0,0,0.6); backdrop-filter: blur(2px);
    }

    /* Image and text (keep text on the right side!) */
    .cv-left {}
    .cv-right {}

    .cv-avatar{
      width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.14);
      box-shadow: 0 8px 16px rgba(0,0,0,0.45), 0 0 22px rgba(66,245,255,0.18), 0 0 26px rgba(255,100,246,0.14);
      display:block;
    }
    .cv-avatar-fallback{
      display:flex; align-items:center; justify-content:center; font-size: 48px;
      background: rgba(255,255,255,0.06); width:100%; aspect-ratio:1/1; border-radius:12px;
      border: 1px solid rgba(255,255,255,0.14); color:#cde8ff;
      box-shadow: 0 8px 16px rgba(0,0,0,0.45), 0 0 22px rgba(66,245,255,0.18), 0 0 26px rgba(255,100,246,0.14);
    }

    .cv-summary{
      font-size: clamp(14px, 1.05vw, 18px);
      line-height: 1.68;
      color: #e8f1ff;
      letter-spacing: 0.02em;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
      hyphens: auto;
      hanging-punctuation: first;
      text-wrap: pretty;
      text-shadow: 0 0 2px rgba(66,245,255,0.25), 0 0 8px rgba(154,107,255,0.12);
    }
    .cv-summary .cv-p{ margin: 0 0 10px 0; }
    .cv-summary .cv-p:last-child{ margin-bottom: 4px; }

    /* Neon dropcap badge for first paragraph */
    .cv-summary .cv-lead::first-letter{
      float:left; font-size: 2.6em; line-height: 0.9;
      padding: 4px 8px 2px 6px; margin: 4px 8px 0 0;
      border-radius: 6px 10px 6px 6px;
      background: linear-gradient(135deg, rgba(66,245,255,0.30), rgba(255,100,246,0.28));
      color: #0a0f18;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14), 0 0 14px rgba(66,245,255,0.35), 0 0 18px rgba(255,100,246,0.28);
    }

    /* Light theme fallback */
    @media (prefers-color-scheme: light){
      .cv-banner{ --panel-bg: rgba(240, 245, 255, 0.82); --panel-fg: #0f172a; color: var(--panel-fg);
        box-shadow: 0 10px 24px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04) inset; }
      .cv-summary{ color: #0f172a; text-shadow: none; }
      .cv-summary .cv-lead::first-letter{ color: #0a0f18; }
      .cv-avatar{ border-color: rgba(0,0,0,0.08); }
    }

    /* Responsive grid tweaks — keep text on the right until we must stack */
    @media (max-width: 1000px){ .cv-banner{ grid-template-columns: 170px 1fr; } }
    @media (max-width: 740px){ .cv-banner{ grid-template-columns: 140px 1fr; } }
    @media (max-width: 640px){
      .cv-banner{
        grid-template-columns: 1fr;
        gap: 14px;
        padding: 16px;
        clip-path: polygon(10px 0%, calc(100% - 20px) 0%, 100% 16px, 100% calc(100% - 10px),
                           calc(100% - 10px) 100%, 18px 100%, 0% calc(100% - 18px), 0% 10px);
      }
      .cv-left{ margin-bottom: 2px; }
    }

    /* Reuse animations */
    @keyframes foilSpin { 0% { filter: hue-rotate(0deg) brightness(1); } 50% { filter: hue-rotate(30deg) brightness(1.05); } 100% { filter: hue-rotate(0deg) brightness(1); } }
    @keyframes glintSweep { 0% { transform: translateX(-70%) rotate(0.2deg); } 55% { transform: translateX(60%) rotate(0.2deg); } 100% { transform: translateX(110%) rotate(0.2deg); } }

    /* ===================== Query Param Sync / Chat Layout JS placeholders ===================== */
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

    # Responsive columns: compute ?cols= based on viewport width (characters tab)
    components.html(
        """
        <script>
        (function(){
          function pickCols(w){
            if (w < 560) return 2;
            if (w < 900) return 3;
            if (w < 1280) return 4;
            return 5;
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

    # Chat input layout: sidebar-aware + bottom padding sync
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
            let desired = 0.95 * vw; if (vw >= 600) desired = 0.85 * vw; if (vw >= 900) desired = 0.75 * vw;
            desired = Math.max(360, Math.min(1100, Math.round(desired)));
            const rect = main.getBoundingClientRect();
            let leftEdge   = rect.left;
            const rightG   = (doc.documentElement.clientWidth - rect.right);
            const sb = doc.querySelector('aside[data-testid="stSidebar"]');
            if (sb) {
              const sbRect = sb.getBoundingClientRect();
              const sbVisible = (sbRect.width > 0) && (sbRect.left < (vw - 8));
              if (sbVisible) leftEdge = Math.max(leftEdge, Math.round(sbRect.right));
            }
            const docW = doc.documentElement.clientWidth;
            const available = Math.max(0, docW - leftEdge - rightG);
            const finalW = Math.min(desired, available);
            const sidePad = Math.max(0, (available - finalW) / 2);
            const finalLeft  = leftEdge + sidePad;
            const finalRight = docW - finalLeft - finalW;
            input.style.setProperty('--eeva-left',  px(finalLeft));
            input.style.setProperty('--eeva-right', px(finalRight));
            const h = input.getBoundingClientRect().height || 96;
            main.style.paddingBottom = px(h + 24);
          }
          const doc = parent.document;
          const observe = (el) => { if (!el) return; new ResizeObserver(layoutChat).observe(el); };
          observe(doc.body); observe(doc.querySelector('.block-container')); observe(doc.querySelector('aside[data-testid="stSidebar"]'));
          parent.window.addEventListener('resize', layoutChat);
          parent.window.addEventListener('scroll', layoutChat);
          setTimeout(layoutChat, 40); setTimeout(layoutChat, 160); setTimeout(layoutChat, 360); setTimeout(layoutChat, 800);
          (function waitForInput(){
            const input = doc.querySelector('[data-testid="stChatInput"]');
            if (!input) { setTimeout(waitForInput, 120); return; }
            new ResizeObserver(layoutChat).observe(input); layoutChat();
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
