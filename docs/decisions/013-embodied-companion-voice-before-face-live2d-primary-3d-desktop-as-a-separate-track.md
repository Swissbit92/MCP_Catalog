---
title: Embodied companion: voice before face, Live2D primary, 3D desktop as a separate track
status: Accepted
created: 2026-08-02
last_reviewed_on: 2026-08-02
review_in: 24 months
applies_to: docs
---

# ADR-013: Embodied companion: voice before face, Live2D primary, 3D desktop as a separate track

## Context

NEPHILIM is a companion platform, but its personas have no body and no voice. They are static PNG portraits (`react-ui/public/images/personas/<key>/`) rendered as 48px chat-bubble avatars and gacha cards. Twelve ADRs exist and **none address embodiment, voice, or multimodality**; `docs/ROADMAP.md` is silent on all three. The only historical trace is a superseded line in `archive/phase7/PHASE7_TRANSITION_PLAN.md` ("Phase 11: Voice Integration"), pointing at nothing.

An embodied face is a **product requirement**, not an enhancement — a companion the user meets on their phone daily should have a presence, not a portrait. This ADR exists so that requirement is recorded rather than living only in conversation.

The investigation began with `github.com/xikhar/persona` (MIT, React 19 + `@react-three/fiber` + `@pixiv/three-vrm`), an Electron overlay that renders a VRM avatar. Analysis established several constraints that shape the decision:

**The repo ships zero 3D models, by design.** `public/assets/models/` and `animations/` contain only `.gitkeep`; `manifest.json` is `"assets": []` with `distributionAllowed: false`; no `.vrm` blob exists anywhere in its git history. Its `LICENSES.md` states: *"No character models or animations are currently licensed for distribution as part of this repository."* This generalises — **VRM character models are always bring-your-own**, because VRM licences forbid redistribution by default. Character art is the dominant cost of any avatar project and no upstream project can supply it.

**Persona's architecture solves a problem NEPHILIM does not have.** Roughly 7,200 lines of Electron and native code exist to tap *another application's* audio output (the default process pattern matches `chatgpt|codex|openai`) and derive a speaking signal from its RMS level. NEPHILIM *produces* the speech, so it holds the audio directly. Further, the tap is per-*process*, not per-*stream* — aimed at a browser it would lip-sync to any other tab playing sound — and process audio taps do not exist on iOS or Android at all.

**Rendering happens on the client, not the Mac Mini.** NEPHILIM's backend (Ollama, TTS, FastAPI, SQLite) runs on the always-on Mac Mini M4 Pro, which has ample headroom (GPU measured at 0% utilisation, no contention with inference). But the browser draws every avatar frame on the *device* — for a phone-primary product, that means a phone GPU and a phone battery. Desktop-class performance measurements do not transfer.

**Mobile is the primary surface.** The intended daily use is from a phone, with desktop secondary. Two blockers follow directly:

- `scripts/serve_frontend.py:99` binds `HTTPServer(("127.0.0.1", PORT))` — the React UI is **not reachable from a phone today**. NEPHILIM's current mobile channel is the Telegram gateway, which by protocol can never render an avatar. Requiring a face forces the React app to become the primary phone surface.
- iOS Safari requires a user gesture before audio may play, which constrains any design where the companion speaks proactively.

The responsive groundwork is real, not hypothetical: 84 Tailwind responsive utilities, `isMobile` breakpoints at 768px, correct viewport meta, and `LegendaryParticles.tsx:178` already disables particle effects below 768px — the phone-GPU budget was already being respected.

## Decision

**Voice ships before the face, and the face is Live2D.**

**1. Sequencing is mandatory, not preferential.** Lip-sync, expression timing, and the entire perception of aliveness derive from audio. An avatar built before voice exists is a static image that animates to silence. The order is:

1. **TTS** on the Mac Mini
2. **Sentence-chunked streaming**, so first audio arrives in well under a second
3. **Phone access** — Tailscale plus PWA install
4. **Then the face** — one persona, behind a feature flag

Steps 1–3 deliver value independently of whether an avatar ever ships; step 2 additionally closes the open Telegram-gateway token-streaming item in `docs/ROADMAP.md`. The format decision therefore blocks nothing and may be revisited during steps 1–3.

**2. Live2D Cubism is the primary embodiment format.** Five independent factors converge:

- It rigs **the persona art NEPHILIM already owns** (~73 MB across six personas), so each persona stays recognisably herself. VRM requires recreating all six in 3D, and they will not match the established portraits — replacing a visual identity already built.
- Substantially lighter per frame on a phone GPU: deformed 2D layers versus a skinned 3D mesh with spring-bone physics and PBR lighting.
- Roughly 3 MB per character versus 10–40 MB for a typical VRM — material over cellular.
- It is the exact idiom of mobile gacha character screens, which NEPHILIM's rarity tiers, summon ceremonies, and holographic cards already evoke.
- **No third-party licence entanglement**: the rig is applied to art already owned. VRM models carry embedded `VRMC_vrm` metadata where `allowRedistribution` and `allowExcessivelySexualUsage` both default to `false`, which would constrain both this repository and the uncensored-companion posture recorded in `WEB_SAFESEARCH_DEFAULT`.

The Live2D Cubism SDK for Web is free to publish below ¥10M/yr revenue, so cost is rigging commissions only.

**3. One format everywhere; fidelity scales by device.** A per-device split — 3D on desktop, 2D on mobile — is **explicitly rejected**. It doubles the dominant cost (twelve character assets instead of six), doubles every downstream feature (each expression and reaction implemented twice), and fractures the companion's identity across devices, which is precisely the continuity a companion product exists to provide. Desktop instead receives the same rig at higher fidelity: fuller framing, richer stage, more idle variety.

**4. A 3D desktop companion is a separate, later track.** Not a parallel workstream and not a per-device variant, but a deliberate second incarnation — an always-on-top desktop presence — to be undertaken only once the Live2D companion exists and its value is proven. Should it proceed, `xikhar/persona` becomes genuinely useful for the first time: its MIT `main.cjs` window configuration (transparent, frameless, `alwaysOnTop` at `"floating"` level, re-asserting `setVisibleOnAllWorkspaces` on every show because macOS drops it across Space switches) is hard-won, and roughly 1,500 lines of its `src/` renderer are portable — `App.tsx` already codes a no-Electron fallback path.

**5. Audio drives the face via WebAudio, never an OS audio tap.** An `AnalyserNode` attached to the TTS audio node is sample-accurate, requires no permissions or native binaries, works identically on every platform including mobile, and is structurally incapable of picking up unrelated audio.

**6. `xikhar/persona` is rejected as a vehicle.** It contains no models, its audio-tap subsystem is inapplicable, and it is not an AI companion. Closer references for the LLM-driven avatar problem are `semperai/amica` (React + three-vrm, Ollama-friendly, 14-emotion engine), `tegnike/aituber-kit` (provider-swapping patterns), and `pixiv/ChatVRM` (archived, but the canonical `[happy]`-style bracket-tag emotion pattern).

## Status

Accepted

Format choice (Live2D) is revisitable during steps 1–3 at no cost, since no avatar work begins until step 4. It would be reconsidered if seeing the personas in genuine 3D — real depth, turnaround, camera freedom — proves to matter more than fidelity to the existing portrait art.

## Consequences

**Easier**

- The requirement is recorded. Embodiment stops being tacit and gains an anchor for future work.
- Steps 1–3 are independently valuable, so the programme cannot strand on the avatar.
- Streaming closes an existing ROADMAP item as a side effect.
- One format means one renderer, one expression mapping, one lip-sync path.
- Rigging owned art removes the licence-compatibility question entirely.
- Existing per-turn `EmotionalState` (`current_mood`, `mood_intensity`, `trust_level`, `rapport`, exposed at `GET /sessions/{id}/emotional-state`) is already close to what an expression system consumes.

**Harder**

- Phone access must be built (Tailscale + PWA). Loopback-only binding is a hard prerequisite, not a refinement.
- Telegram's role needs deciding: lightweight text channel alongside a richer React PWA, or retired.
- Rigging is a commission skill; Live2D Cubism Editor PRO is a paid tool, unlike the free VRoid Studio.
- iOS audio-unlock requires a deliberate "tap to wake" interaction before proactive speech.
- Battery obliges a render policy — animate during speech, idle low-FPS or static otherwise — extending the precedent in `LegendaryParticles.tsx`.
- Choosing Live2D forgoes true 3D on the primary surface. Deliberate, and the reason the desktop track is kept open.

**Follow-up**

- ROADMAP entries for TTS, sentence-chunked streaming, and phone access.
- TTS engine selection. Kokoro-82M (Apache-2.0) via `mlx-audio` is the current front-runner: MLX-native for Apple Silicon and OpenAI-compatible REST, so it drops into FastAPI. **Avoid XTTS-v2** — permanently non-commercial since Coqui dissolved — and note Piper's maintained fork is now GPL-3.0.
- Decide the expression signal: the existing keyword-heuristic `EmotionalState`, LLM-emitted bracket tags (cheapest, and improves text chat independently), or implementing the PAD triplet designed in [ADR-006](006-companion-memory-and-continuity-eval-first.md) Phase 2 and still unbuilt.
- If phone rendering fidelity ever becomes the binding constraint, server-side rendering on the Mac Mini streamed as WebRTC video is the escape hatch — the phone would only hardware-decode video. High complexity; recorded as an option, not a plan.
