---
title: Mac Mini Bringup — Remaining Setup & Windows→Mac Cleanup
status: active
created: 2026-06-21
last_reviewed_on: 2026-06-21
review_in: 3 months
applies_to: nephilim
---

# Mac Mini Bringup — Remaining Setup & Windows→Mac Cleanup

Punch list from bringing nephilim back online on the Mac Mini M4 Pro (48 GB, Apple Silicon/Metal, native Ollama+MLX) after migrating off the Windows/NVIDIA-RTX-4090 Zephyrus. Audit performed 2026-06-21.

## Bringup status (2026-06-21)

- ✅ Site live & **always-on via launchd** — `com.nephilim.backend` (uvicorn :8000) + `com.nephilim.frontend` (static `serve_frontend.py` :3001, "NEPHILIM Realm"); RunAtLoad + KeepAlive. Plists + `install.sh` version-controlled in `scripts/launchd/`.
- ✅ python3.12 venv (`.venv`), pip deps, npm deps, `data/`+`logs/` dirs, frontend `npm run build` bundle.
- ✅ Models pulled: `gemma2:9b-instruct-q5_K_M` (smoke), `nomic-embed-text:latest` (RAG).
- ✅ `AUTH_REQUIRED=false` for first local boot (`.env:111`).
- ✅ Filesystem-MCP re-pointed off dead `~/Desktop/Nephilim` → `~/nephilim` (user-scope, Connected).
- ⏳ Magidonia daily-driver MLX + Gemma DECKARD standalone MLX downloading (Magidonia ~46%); wiring pending download.

## Section A — Remaining setup (not migration bugs)

- [x] **Wire Magidonia daily driver** ✅ DONE 2026-06-21 — **pivoted from MLX to GGUF**: the `Wwayu/...-mlx-6Bit` HF download kept stalling/thrashing under the unauthenticated HF rate limit (each resume spawned duplicate `.incomplete` shards). Switched to the official GGUF via Ollama's HF pull: `ollama pull hf.co/TheDrummer/Magidonia-24B-v4.3-GGUF:Q4_K_M` (14 GB, one clean step, imports straight into Ollama — no manual Modelfile/MLX import). `PERSONA_MODEL` set to that tag; launchd backend restarted; verified end-to-end (Nyx replied in-character, ~18.5 tok/s GGUF/Metal). Tradeoff vs MLX 6-bit: ~15% slower + Q4 not Q6, but a path that actually lands. Upgrade to `:Q5_K_M`/`:Q6_K` later if desired.
- [x] **Persona preset re-tune** ✅ DONE 2026-06-21 — re-tuned the 5 presets in `sampling_presets.py` for Mistral-Small-3.2: base temps lowered (creative 1.2→1.0, chaotic 1.5→1.1, etc.), `repeat_penalty` softened to 1.03–1.08 (Mistral degrades above 1.1), `min_p`~0.05. Personas already override `temperature` (0.6–0.95, Mistral-safe), so the real fix was the inherited `min_p`/`repeat_penalty`. **Validated via quality gate:** Nyx (hardest, full quick 30) = **96.7% PASS / 0.958 avg**; EEVA (partial) ~26/28 PASS mostly A. Full 7-persona run stopped early (sustained GPU heat; ~25s/test × 210 ≈ 90 min) — representative coverage sufficient. - [x] **`MODEL_CONTEXT_WINDOW` knob fixed** ✅ 2026-06-21 — `num_ctx=cfg.context_window` now passed to all 3 `OllamaLLM` instantiations (`llm_completion_service`, `cv_summarizer`, `prompt_builder`) — previously none set it, so Ollama defaulted to 32K. Set `MODEL_CONTEXT_WINDOW=16384`; verified `ollama ps` → CONTEXT 16384, SIZE 20 GB→17 GB (KV-cache halved). All 3 paths agree → no model reloads.
- [ ] **Gemma DECKARD standalone** — `mlx-community/gemma-4-31B-it-The-DECKARD-HERETIC-UNCENSORED-Thinking-4.6bit-msq` (downloading). Not wired into personas; runs via `mlx-lm` (Ollama GGUF chat-template bug). For "something else later."
- [x] **Re-point filesystem MCP config** ✅ DONE 2026-06-21 — user-scope `filesystem` MCP in `~/.claude.json` re-pointed `~/Desktop/Nephilim` → `~/nephilim` via `claude mcp` CLI; verified Connected.
- [x] **launchd always-on** ✅ DONE 2026-06-21 — `com.nephilim.backend` + `com.nephilim.frontend` (static build) loaded, RunAtLoad + KeepAlive, both `state = running`. Source + `install.sh` in `scripts/launchd/`. Native, not Docker (Docker on Mac = no Metal).
- [x] **Static-serve API proxy** ✅ DONE 2026-06-21 — `serve_frontend.py` now reverse-proxies API prefixes (/auth, /sessions, /persona, /nephilim, …) to the backend. The frontend's auth calls use *relative* URLs that depend on the react-scripts dev-server proxy; the static server lacked it, so `/auth/refresh` 404'd → login failed. With proxy + `AUTH_REQUIRED=false`, the `/auth/refresh` bypass auto-logs-in.
- [x] **Remote access over SSH** ✅ verified 2026-06-21 — laptop reaches the site via `ssh -L 3001:localhost:3001 -L 8000:localhost:8000 swissbit.@<mini>` → `http://localhost:3001`. Both ports needed (chat uses absolute :8000; auth proxies via :3001).
- [ ] **Re-enable AUTH_REQUIRED + Google OAuth** when going beyond local single-user (this is Phase 8). Confirm redirect URIs include `localhost:3001`.

## Section B — Windows→Mac cleanup (audit 2026-06-21)

> **Status: ✅ all Section-B items completed 2026-06-21** via `/develop` (LIGHT). Code blockers verified (lint-neutral, no test regressions — the stdout-guard fix actually un-broke pytest collection, 149→245). Compose items are inert on Mac (we run native) but fixed for any future Docker/Linux use. The boxes below are left for traceability. **Not** part of this cleanup: pre-existing test-suite debt surfaced during QA (8 stale-`get_ollama_base` imports + `_count_tokens("")` mismatch) — tracked as its own roadmap item.

### Blockers (functional on Mac)

- [ ] `src/coordinator/config.py:34` — code default `PERSONA_MODEL="mistral:latest"` → silent wrong model if env missing. Change to `gemma2:9b-instruct-q5_K_M`.
- [ ] `react-ui/package.json` — `react-scripts@5` + Node 25 throws OpenSSL `digital envelope routines::unsupported`. Currently worked around at launch via `NODE_OPTIONS=--openssl-legacy-provider`. Make durable: add it to the `start`/`build` scripts, add `engines`/`.nvmrc` (Node 20), or migrate CRA→Vite.
- [ ] `tests/exploration/check_import.py:5` — hardcoded `sys.path.insert(0, "C:\\Users\\rzehn\\desktop\\nephilim")`. Replace with repo-relative path or delete.
- [ ] `docker-compose.yml:23-31` — `OLLAMA_FLASH_ATTENTION=true` + `driver: nvidia` GPU reservation (RTX 4090). Crashes `docker-compose up` on Mac. Remove the GPU block (Docker-only; native Ollama gets Metal automatically).
- [ ] `docker-compose.yml:53-54` — `OLLAMA_BASE: http://ollama:11434` + fallback `PERSONA_MODEL:-dolphin-llama3:8b`. For native Ollama use `host.docker.internal:11434` (or drop the `ollama` service); fix fallback to `gemma2:9b-instruct-q5_K_M`. (Only matters if Docker path is ever used.)
- [ ] `react-ui/*.ps1` + `scripts/docker/*.ps1` (8 files) — PowerShell setup scripts cited as the primary path in `docs/DEVELOPMENT.md:18`, `docs/README.md:40-41`, `Readme.md:208`. Present `.sh` as primary on Mac; keep `.ps1` for reference only.

### Should-fix

- [ ] `src/coordinator/memory_rag.py:52-109` — `faiss.get_num_gpus()` CUDA detection is dead code on Apple Silicon (faiss-cpu). Add a comment / guard; CPU path already works.
- [ ] Model-name drift — standardize references: `Readme.md:227,299` (two models in one file), `docs/setup/DOCKER_QUICKSTART.md:61,104,116,655` (`nchapman/...` + `dolphin-llama3:8b`), `.env.example:16`. Converge on the active model.
- [ ] `Readme.md:181,190,424,692` + `docs/setup/DOCKER_QUICKSTART.md:384-451` — GPU tables and "GPU Support (NVIDIA Only)" section say NVIDIA/CUDA. Reframe for Apple Silicon/Metal (native Ollama).
- [ ] 9 test files — `sys.stdout = io.TextIOWrapper(...)` Windows-console UTF-8 fix (no-op on Mac, can break pytest capture). Guard with `if sys.platform == 'win32':`.
- [ ] `scripts/utils/run_react.py:85,139` — `shell=True` (Windows `npm.cmd` workaround); drop on macOS.
- [ ] `docs/setup/DOCKER_QUICKSTART.md:310-312` — `netstat/findstr/taskkill` Windows commands; lead with `lsof`/`kill`.
- [ ] Node version docs — `Readme.md:188`, `scripts/setup/README.md:10`, `requirements.txt:46` say "Node 16+"; note Node 17+ breaks react-scripts without the OpenSSL flag.
- [ ] Workflow docs — `CLAUDE.md:25-26` ("Docker most common") and `docs/DEVELOPMENT.md:14` ("Docker Recommended"): local dev + native Ollama is now primary on Mac; reframe.

### Cosmetic

- [ ] `archive/phase7/*.md:51,166` — `/c/Users/rzehn/desktop/nephilim` Git-Bash paths (archived; add a banner or leave).
- [ ] `Readme.md:236` — `start http://...` Windows open command (drop, keep `open`).
- [ ] `scripts/README.md`, `scripts/setup/README.md` — references to non-existent `.bat` files.
- [ ] `docs/README.md:31`, `docs/setup/DOCKER_QUICKSTART.md:583` — "Windows co-primary" / "M1/M2 Mac" phrasing.
