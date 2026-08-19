---
title: Persona image generation — model + architecture research and decision
status: active
created: 2026-08-19
last_reviewed_on: 2026-08-19
review_in: 6 months
applies_to: nephilim
---

# Persona image generation — research + decision (park record)

On-demand, in-character image generation for the NEPHILIM personas. This note records the
**decided direction**, the **parked option**, the **durable findings**, and the **open
questions** from a 2026-08-19 research + sparring session. **Nothing is built yet** — this is a
decision/park record, not an implementation. A formal ADR is written at build time, not before.

Research inputs: a 17-agent web sweep (runtimes, SFW/NSFW models, character consistency,
Apple-Silicon performance, licensing, integration, quantization, 2026 frontier scan incl.
Ideogram 4 / WAN) plus a `/crucible:spar-with-me` pass, reconciled against the actual persona
art in the repo.

## Decided direction (local, on-Mac, occasional/exclusive-mode)

Generation is an **occasional, ad-hoc action** invoked by persona behavior and/or user prompt —
not an always-on service. It therefore runs in **exclusive mode**: the resident ~17 GB companion
LLM may be briefly unloaded during a generation session, freeing the full 48 GB. This removes the
memory pressure that would otherwise force small models and cheap sampling.

- **Serving runtime:** **ComfyUI**, run headless as a launchd-style local HTTP/WebSocket server,
  driven by the FastAPI coordinator (templated workflow-JSON per persona; submit → poll/`/ws` →
  fetch PNG; async job, never a synchronous route — a single quality-pipeline image is tens of
  seconds).
- **SFW personas (Japanese-anime look):** **Illustrious-XL / NoobAI-XL** (SDXL-family anime
  specialists) — native fit for the gacha-anime persona art.
- **gwen (NSFW, Western-cartoon look):** **Pony Diffusion V6 XL** — *not* an Illustrious-lineage
  NSFW checkpoint. Pony is the native base for Western-cartoon / painted / NSFW art; the style
  match outweighs the convenience of a single shared model family. This deliberately **overturns**
  the initial web-research recommendation (WAI-NSFW-illustrious for lineage uniformity).
- **Per-persona consistency:** one trained **character LoRA per persona**, trained **on-device via
  Draw Things** (Metal-native SDXL trainer, ~10 GB at 512px / ~20 GB at 768px — comfortable in
  exclusive mode). This is the load-bearing mechanism.
- **Quality pipeline:** because exclusive mode frees memory and speed is explicitly deprioritized
  (quality > speed), run the full pipeline — high-res generation → upscale pass → refiner pass →
  dedicated face-fix (ADetailer-style). For this art, this is a larger quality gain than swapping
  to a bigger base model.

**First step when building:** a **single-persona pilot** — bootstrap ~20–30 varied reference
images of one persona (current art is too thin to train on directly), train her LoRA, generate
~30 test images, eyeball consistency — *before* committing the recipe to all six. The
"recognizably herself across many generations" bar is unproven for this art until this pilot runs.

## Parked option (revisit later) — cloud-trained big-model quality

Explicitly deferred, not rejected. The **one-time cloud-GPU LoRA training** step (~$5–20/persona,
one-time) would unlock the higher-quality frontier bases whose LoRA training is unreliable on
Apple Silicon:

- **SFW:** Qwen-Image (20B, Apache-2.0, Q8 ≈ 22 GB) — strongest coherence/prompt-adherence of the
  Mac-runnable anime-capable frontier models; large adapter ecosystem.
- **NSFW:** Chroma1-HD (FLUX-class, Apache-2.0, uncensored-by-design) — highest raw fidelity for
  the NSFW persona, but weakest Mac tooling today (MPS-only, no MLX port) → slow inference.

**Revisit triggers:** (a) the on-Mac SDXL + quality-pipeline output proves insufficient in
practice; (b) willingness to spend the one-time cloud-training cost; or (c) a Mac-native LoRA
trainer for FLUX/Qwen matures. The operator declined the cloud step for now (2026-08-19).

## Durable findings

- **The personas span TWO art styles, not one.** SFW personas (e.g. nyx) are Japanese-anime /
  gacha style; gwen is a Western-cartoon / painted (NSFW) style from a different source. **No
  single base model natively serves both** — this is the core reason the SFW and NSFW paths use
  different model families, and it is invisible to any web research that assumes "6 anime personas".
- **Model size ≠ anime/cartoon quality.** SDXL (~2.6B) anime/cartoon specialists beat much larger
  general models (FLUX 12–32B, Qwen 20B) at *this* aesthetic, because the big models spent their
  capacity on photoreal coherence and prompt-following. Quality here comes from **specialization +
  a refinement pipeline**, not base-model parameter count.
- **On-Mac LoRA training is SDXL-only in practice.** Draw Things trains SDXL LoRAs on-device
  reliably; FLUX/Qwen LoRA training on Apple Silicon (MPS) is documented as unreliable
  (ai-toolkit self-labels Mac support experimental; FLUX convergence failures on MPS). Big-model
  character consistency therefore *implies* cloud training — hence the park.
- **Face-lock adapters are a dead end for this art.** InstantID / IP-Adapter FaceID / PuLID all
  depend on InsightFace/ArcFace embeddings trained on photoreal human faces, which do not map onto
  anime/cartoon proportions (acknowledged upstream). Plain (non-face) IP-Adapter is usable only as
  a loose pose/composition helper, not an identity lock. Identity = the LoRA.
- **Frontier scan — mostly not Mac-actionable today.** Ideogram 4 did surprise-release open
  weights (June 2026) but is **non-commercial + likely CUDA-blocked** (nf4/bitsandbytes) — stays a
  cloud/curiosity option, never for the NSFW persona (cloud ToS forbids it). **WAN (Wan2.1/2.2) is
  CUDA-only and video-first** — ruled out for local stills; noted only as a *future animated-clip*
  angle for the [ADR-013](../decisions/013-embodied-companion-voice-before-face-live2d-primary-3d-desktop-as-a-separate-track.md)
  embodiment/Live2D track if a Mac port ever appears.
- **Licensing flags to remember** (fine for personal use, would bite on any future monetization):
  NoobAI-XL bans all commercialization; SD3.5 forbids NSFW even self-hosted; FLUX.1-dev / Ideogram 4
  are non-commercial. Cleanest: Animagine XL, Pony V6 (personal-use free), Qwen-Image/Chroma
  (Apache-2.0). Read the exact checkpoint license at download time — Illustrious's terms changed
  between versions.

## Open questions (not yet decided)

- **Distinct vs unified style:** keep each persona's current distinct look (nyx anime / gwen
  cartoon → the two-base plan above), or unify toward one house style (one base + restyle). Leaning
  keep-distinct, which validates the two-base plan; a quick pilot could test whether a single
  Pony-based anime merge renders *both* looks well enough via per-persona LoRAs.
- **Exact checkpoints/merges** for each family (settle at build time).
- **Trigger + surface wiring:** how a persona decides to generate an image (tool/intent —
  candidate home is the ADR-008 tool brain surface + ADR-009 registry, alongside `image_search`),
  and how the result renders in the React UI and the Telegram gateway.

## Key sources

Runtimes/perf: Draw Things engineering blog (on-device SDXL LoRA trainer), ComfyUI API docs.
Models: OnomaAIResearch/Illustrious-XL-v2.0, Laxhar/noobai-XL-Vpred-1.0, Pony Diffusion V6 XL,
lodestones/Chroma1-HD, Qwen/Qwen-Image (+ mflux, mlx-community quants), circlestone-labs/Anima.
Consistency: InstantID GitHub #203 (anime face-ID failure), AnimeAdapter (arXiv 2605.20237).
Frontier: bfl.ai FLUX.2/FLUX 3, Tongyi-MAI/Z-Image-Turbo, ideogram-ai HF org, Wan-Video/Wan2.2.
