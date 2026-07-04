#!/usr/bin/env bash
# Smoke test — live end-to-end check of the eeva-telegram gateway.
#
# Unlike eeva-dca's smoke test, NOTHING here spends money. It runs the bot in
# the foreground so you can exercise it by hand from the Telegram app, then
# verify the manual checklist below.
#
# Prerequisites:
#   1. .env populated (TG_BOT_TOKEN from @BotFather, TG_ALLOWED_CHAT_IDS = your id)
#   2. nephilim backend up on NEPHILIM_BASE_URL (default http://127.0.0.1:8000)
#   3. A SECOND Telegram account (or a friend) NOT on the allowlist, to prove
#      the silent-rejection path.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

echo "============================================================"
echo "  eeva-telegram SMOKE TEST — live, no money at risk"
echo "============================================================"
echo ""

if [[ ! -f .env ]]; then
    echo "ERROR: .env does not exist. Copy .env.example to .env and populate." >&2
    exit 1
fi

if grep -qE '^TG_BOT_TOKEN=YOUR_' .env; then
    echo "ERROR: TG_BOT_TOKEN still has the placeholder value in .env." >&2
    exit 1
fi

# Pre-flight: is the nephilim backend reachable?
BASE_URL="$(grep -E '^NEPHILIM_BASE_URL=' .env | cut -d= -f2- || true)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
echo "Checking nephilim backend at ${BASE_URL}/health ..."
if curl -sf "${BASE_URL}/health" >/dev/null; then
    echo "  backend OK"
else
    echo "  WARNING: ${BASE_URL}/health not reachable. Start the nephilim backend first." >&2
    read -r -p "Proceed anyway? [y/N] " confirm
    [[ "${confirm}" == "y" ]] || exit 1
fi

echo ""
echo "Starting the bot in the FOREGROUND. Leave this running and switch to Telegram."
echo "Press Ctrl-C here when you're done."
echo ""
echo "MANUAL CHECKLIST — verify each from the Telegram app:"
echo "  1. From your ALLOWLISTED account, send /start   -> an in-character greeting arrives."
echo "  2. Send a normal message (e.g. 'hey, how are you?')"
echo "       -> the 'typing…' indicator shows, then a reply arrives."
echo "  3. Send a very long prompt that yields a >4096-char reply"
echo "       -> the reply arrives as multiple messages, none truncated."
echo "  4. FORWARD any message from another chat to the bot"
echo "       -> it refuses ('I only read messages you write to me directly…'),"
echo "          and NO reply from the persona is generated."
echo "  5. From a NON-allowlisted account, send anything -> COMPLETE SILENCE (no reply)."
echo "  6. Send /reset -> 'history is wiped' confirmation; then a new message"
echo "       shows the persona no longer remembers the earlier turns."
echo "  7. Stop the nephilim backend, send a message"
echo "       -> a graceful 'having trouble connecting' reply, and this process"
echo "          does NOT crash (it keeps polling)."
echo ""

exec "${PROJECT_DIR}/venv/bin/python" "${PROJECT_DIR}/bin/run_telegram_bot.py"
