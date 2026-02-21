#!/usr/bin/env python3
"""
Post-startup smoke test for Docker deployment.

Polls the /ready endpoint, verifies MCP subsystems match .env.docker config,
and sends lightweight test queries to confirm end-to-end functionality.

Usage:
    python scripts/docker/verify_startup.py          # default localhost:8000
    python scripts/docker/verify_startup.py --port 8001
    python scripts/docker/verify_startup.py --timeout 120

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_BASE = "http://localhost:8000"
READY_POLL_INTERVAL = 3  # seconds between /ready polls
ENV_FILE = ".env.docker"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def cprint(color: str, msg: str) -> None:
    print(f"{color}{msg}{Colors.RESET}")


def http_get(url: str, timeout: int = 10) -> tuple[int, dict | str]:
    """GET request returning (status_code, parsed_json_or_text)."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body)
        except (json.JSONDecodeError, Exception):
            return e.code, body
    except Exception as e:
        return 0, str(e)


def http_post_json(url: str, payload: dict, timeout: int = 30) -> tuple[int, dict | str]:
    """POST JSON request returning (status_code, parsed_json_or_text)."""
    data = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body)
        except (json.JSONDecodeError, Exception):
            return e.code, body
    except Exception as e:
        return 0, str(e)


def load_env_file(path: str) -> dict[str, str]:
    """Parse a .env file into a dict (ignores comments and blank lines)."""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


# ---------------------------------------------------------------------------
# Phase 1: Poll /ready
# ---------------------------------------------------------------------------
def wait_for_ready(base_url: str, timeout: int) -> dict | None:
    """Poll /ready until 200 or timeout. Returns checks dict or None."""
    cprint(Colors.CYAN, f"\n[1/3] Waiting for {base_url}/ready (timeout {timeout}s)...")

    deadline = time.time() + timeout
    last_error = ""
    attempts = 0

    while time.time() < deadline:
        attempts += 1
        status, body = http_get(f"{base_url}/ready", timeout=5)

        if status == 200 and isinstance(body, dict):
            cprint(Colors.GREEN, f"      /ready returned 200 after {attempts} attempt(s)")
            return body.get("checks", body)

        if isinstance(body, dict):
            last_error = json.dumps(body.get("checks", body), indent=2)
        else:
            last_error = str(body)[:200]

        remaining = int(deadline - time.time())
        print(f"      Attempt {attempts}: status={status}, retrying... ({remaining}s left)")
        time.sleep(READY_POLL_INTERVAL)

    cprint(Colors.RED, f"      TIMEOUT after {timeout}s. Last response: {last_error}")
    return None


# ---------------------------------------------------------------------------
# Phase 2: Verify subsystems against .env.docker
# ---------------------------------------------------------------------------
def verify_subsystems(checks: dict, env: dict) -> list[tuple[str, bool, str]]:
    """Compare /ready checks against .env.docker expectations.

    Returns list of (name, passed, detail).
    """
    cprint(Colors.CYAN, "\n[2/3] Verifying subsystem status against .env.docker...")

    results = []

    # Database — always required
    db_ok = checks.get("database") == "ok"
    results.append(("database", db_ok, checks.get("database", "missing")))

    # Ollama — always required
    ollama_ok = checks.get("ollama") == "ok"
    results.append(("ollama", ollama_ok, checks.get("ollama", "missing")))

    # Brave MCP — expected enabled if BRAVE_API_KEY is non-empty
    brave_key = env.get("BRAVE_API_KEY", "")
    brave_status = checks.get("brave_mcp", "unknown")
    if brave_key:
        brave_ok = brave_status == "enabled"
        results.append(("brave_mcp", brave_ok,
                        f"expected=enabled, got={brave_status}" if not brave_ok else "enabled"))
    else:
        results.append(("brave_mcp", True, f"disabled (no API key) — got={brave_status}"))

    # MongoDB MCP — expected enabled if MONGODB_ENABLED=true and MONGODB_URI is non-empty
    mongo_enabled = env.get("MONGODB_ENABLED", "false").lower() == "true"
    mongo_uri = env.get("MONGODB_URI", "")
    mongo_status = checks.get("mongodb_mcp", "unknown")
    if mongo_enabled and mongo_uri:
        mongo_ok = mongo_status == "enabled"
        results.append(("mongodb_mcp", mongo_ok,
                        f"expected=enabled, got={mongo_status}" if not mongo_ok else "enabled"))
    else:
        results.append(("mongodb_mcp", True, f"disabled (config) — got={mongo_status}"))

    for name, passed, detail in results:
        icon = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"      [{icon}] {name}: {detail}")

    return results


# ---------------------------------------------------------------------------
# Phase 3: Test queries
# ---------------------------------------------------------------------------
def run_test_queries(base_url: str, checks: dict) -> list[tuple[str, bool, str]]:
    """Send lightweight test queries per MCP path. Returns (name, passed, detail)."""
    cprint(Colors.CYAN, "\n[3/3] Running test queries...")

    results = []

    # Test: persona list loads
    status, body = http_get(f"{base_url}/personas", timeout=10)
    if status == 200 and isinstance(body, list) and len(body) > 0:
        results.append(("persona_load", True, f"{len(body)} personas loaded"))
    else:
        results.append(("persona_load", False, f"status={status}, body={str(body)[:100]}"))

    # Pick a persona with MCP access for testing (nephilim_eeva has brave + mongodb)
    persona_key = "nephilim_eeva"
    if isinstance(body, list):
        keys = [p.get("key") for p in body if isinstance(p, dict) and p.get("key")]
        if persona_key not in keys and keys:
            persona_key = keys[0]

    # Create a session for test queries
    status, session_body = http_post_json(
        f"{base_url}/sessions",
        {"persona_key": persona_key, "title": "verify_startup"},
        timeout=15,
    )
    session_id = (session_body or {}).get("session_id") or (session_body or {}).get("id") if isinstance(session_body, dict) else None
    if status == 200 and session_id:
        results.append(("create_session", True, f"session={session_id[:8]}..."))
    else:
        results.append(("create_session", False, f"status={status}, body={str(session_body)[:120]}"))
        _print_results(results)
        return results

    # Test: LLM greet (pure LLM, no MCP)
    status, greet_body = http_post_json(
        f"{base_url}/persona/greet",
        {"persona": persona_key},
        timeout=120,
    )
    greet_ok = status == 200 and isinstance(greet_body, dict) and greet_body.get("answer")
    if greet_ok:
        answer_preview = str(greet_body["answer"])[:60].replace("\n", " ")
        results.append(("llm_greet", True, f'"{answer_preview}..."'))
    else:
        results.append(("llm_greet", False, f"status={status}, body={str(greet_body)[:120]}"))

    # Test: Brave search query (only if enabled)
    if checks.get("brave_mcp") == "enabled":
        print("      ... testing Brave MCP (web search)...")
        status, chat_body = http_post_json(
            f"{base_url}/sessions/{session_id}/chat",
            {"persona": persona_key, "message": "Search the web: what is the weather in London today?"},
            timeout=120,
        )
        reply = chat_body.get("reply") or chat_body.get("answer", "") if isinstance(chat_body, dict) else ""
        reply_text = reply if isinstance(reply, str) else " ".join(reply) if isinstance(reply, list) else str(reply)
        brave_ok = status == 200 and len(reply_text) > 0
        detail = f"got reply ({len(reply_text)} chars)" if brave_ok else f"status={status}, body={str(chat_body)[:120]}"
        results.append(("brave_query", brave_ok, detail))

    # Test: MongoDB query (only if enabled)
    if checks.get("mongodb_mcp") == "enabled":
        print("      ... testing MongoDB MCP (trading data)...")
        status, chat_body = http_post_json(
            f"{base_url}/sessions/{session_id}/chat",
            {"persona": persona_key, "message": "Show me the latest Bitcoin trading data from the database"},
            timeout=120,
        )
        reply = chat_body.get("reply") or chat_body.get("answer", "") if isinstance(chat_body, dict) else ""
        reply_text = reply if isinstance(reply, str) else " ".join(reply) if isinstance(reply, list) else str(reply)
        mongo_ok = status == 200 and len(reply_text) > 0
        detail = f"got reply ({len(reply_text)} chars)" if mongo_ok else f"status={status}, body={str(chat_body)[:120]}"
        results.append(("mongodb_query", mongo_ok, detail))

    _print_results(results)
    return results


def _safe_print(text: str) -> None:
    """Print with fallback for Windows cp1252 encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _print_results(results: list[tuple[str, bool, str]]) -> None:
    for name, passed, detail in results:
        icon = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        _safe_print(f"      [{icon}] {name}: {detail}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Post-startup verification for Docker deployment")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--timeout", type=int, default=90, help="Max seconds to wait for /ready (default: 90)")
    parser.add_argument("--skip-queries", action="store_true", help="Skip test query phase (faster)")
    args = parser.parse_args()

    base_url = f"http://localhost:{args.port}"

    cprint(Colors.BOLD, "\n========================================")
    cprint(Colors.BOLD, "  Docker Startup Verification")
    cprint(Colors.BOLD, "========================================")

    # Load .env.docker for expected config
    env = load_env_file(ENV_FILE)
    if not env:
        cprint(Colors.YELLOW, f"  Warning: {ENV_FILE} not found or empty — subsystem checks will be lenient")

    # Phase 1: Poll /ready
    checks = wait_for_ready(base_url, args.timeout)
    if checks is None:
        cprint(Colors.RED, "\nFAILED: Backend never became ready.")
        return 1

    # Phase 2: Verify subsystems
    subsystem_results = verify_subsystems(checks, env)

    # Phase 3: Test queries (optional)
    query_results = []
    if not args.skip_queries:
        query_results = run_test_queries(base_url, checks)
    else:
        cprint(Colors.YELLOW, "\n[3/3] Skipping test queries (--skip-queries)")

    # Summary
    all_results = subsystem_results + query_results
    passed = sum(1 for _, ok, _ in all_results if ok)
    failed = sum(1 for _, ok, _ in all_results if not ok)
    total = len(all_results)

    print()
    cprint(Colors.BOLD, "========================================")
    if failed == 0:
        cprint(Colors.GREEN, f"  ALL CHECKS PASSED ({passed}/{total})")
    else:
        cprint(Colors.RED, f"  {failed} CHECK(S) FAILED ({passed}/{total} passed)")
    cprint(Colors.BOLD, "========================================\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
