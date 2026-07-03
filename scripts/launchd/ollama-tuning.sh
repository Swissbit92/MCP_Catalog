#!/bin/bash
# Durable Ollama tuning for the always-on desktop station.
#
# WHY: nephilim is single-user, but Ollama defaults to multiple parallel slots.
# When two /api/generate requests overlap (e.g. a background job + a chat turn),
# Ollama splits the single GPU AND splits num_ctx across slots, and the 2nd slot
# is cold (no cached prefix). The result is a ~16x slowdown — this is what caused
# the 2026-06-21 "161.9s response" incident (server.log showed two concurrent
# generations at ~2m44s each). OLLAMA_NUM_PARALLEL=1 serializes requests so each
# runs alone at full speed (~16 tok/s) instead of contending.
#
# Ollama.app passes OLLAMA_NUM_PARALLEL through from the launchd GUI env (unlike
# OLLAMA_KEEP_ALIVE, which the app overrides from its own setting — so we don't
# set that here; the chat model stays warm via the app's per-request keep_alive=-1).
#
# Idempotent: only restarts Ollama if the running server isn't already on
# NUM_PARALLEL:1, so it's safe to run at every login.

LOG="$HOME/.ollama/logs/nephilim-tuning.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

echo "[$(date)] ollama-tuning: setenv OLLAMA_NUM_PARALLEL=1"
launchctl setenv OLLAMA_NUM_PARALLEL 1

# Already serialized? (latest server-config line)
if grep -E "server config" "$HOME/.ollama/logs/server.log" 2>/dev/null | tail -1 | grep -q "OLLAMA_NUM_PARALLEL:1"; then
  echo "[$(date)] server already on NUM_PARALLEL:1 — no restart needed"
  exit 0
fi

echo "[$(date)] restarting Ollama to apply NUM_PARALLEL=1"
kill "$(pgrep -f 'Ollama.app/Contents/MacOS/Ollama' | head -1)" 2>/dev/null
pkill -f 'Resources/ollama serve' 2>/dev/null
sleep 4
open -a Ollama
echo "[$(date)] Ollama relaunched"
