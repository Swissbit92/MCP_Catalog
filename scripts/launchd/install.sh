#!/usr/bin/env bash
# Install/reload the nephilim always-on launchd agents (backend + static frontend).
# Idempotent: safe to re-run after a code change or reboot.
#
#   backend  -> uvicorn src.coordinator.server:app on 127.0.0.1:8000  (KeepAlive)
#   frontend -> scripts/serve_frontend.py serving react-ui/build on 127.0.0.1:3001
#
# Rebuild the frontend bundle after UI changes:  cd react-ui && npm run build
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/LaunchAgents"
UID_="$(id -u)"
AGENTS=(com.nephilim.backend com.nephilim.frontend)

mkdir -p "$DEST"
# Free the ports in case ad-hoc dev servers are holding them.
lsof -ti:8000 2>/dev/null | xargs kill 2>/dev/null || true
lsof -ti:3001 2>/dev/null | xargs kill 2>/dev/null || true

for a in "${AGENTS[@]}"; do
    cp "$HERE/$a.plist" "$DEST/$a.plist"
    launchctl bootout "gui/$UID_/$a" 2>/dev/null || true
    launchctl bootstrap "gui/$UID_" "$DEST/$a.plist"
    echo "loaded $a"
done

echo "Done. Verify:  curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/ready"
echo "               curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3001/"
echo "Uninstall:     launchctl bootout gui/$UID_/com.nephilim.backend; launchctl bootout gui/$UID_/com.nephilim.frontend"
