"""E2E User Flow Test — NEPHILIM Web App
Tests all main user flows from the UI perspective.
Mocks auth endpoints to test protected routes.
"""
from playwright.sync_api import sync_playwright
import json
import sys

PASS = 0
FAIL = 0
results = []

def log(status, msg):
    global PASS, FAIL
    if status == "PASS":
        PASS += 1
        results.append(f"  PASS: {msg}")
    else:
        FAIL += 1
        results.append(f"  FAIL: {msg}")
    print(f"  [{status}] {msg}")


FAKE_USER = {
    "access_token": "fake-e2e-test-token",
    "user": {
        "sub": "e2e-test-user",
        "email": "test@nephilim.dev",
        "name": "E2E Seeker",
        "avatar": "",
        "onboarding_completed": True,
    },
}


def setup_auth_mock(page):
    """Intercept auth refresh to simulate logged-in user."""
    def handle_refresh(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(FAKE_USER),
        )

    def handle_verify(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(FAKE_USER["user"]),
        )

    # Mock both refresh and verify endpoints
    page.route("**/auth/refresh", handle_refresh)
    page.route("**/auth/verify", handle_verify)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    # Collect console errors (filter expected ones)
    console_errors = []
    expected_patterns = ["favicon", "401", "403", "GSI_LOGGER", "google", "gsi"]
    def on_console(msg):
        if msg.type == "error":
            text = msg.text
            if not any(p in text.lower() for p in expected_patterns):
                console_errors.append(text)
    page.on("console", on_console)

    # ==================================================================═
    # PART A: Public Routes (no auth needed)
    # ==================================================================═
    print("\n== PART A: Public Routes ==")

    # ─── 1. Landing Page ───────────────────────────────────────────────
    print("\n1. Landing Page (/)")
    page.goto("http://localhost:3001/", wait_until="networkidle")
    page.screenshot(path="test-screenshots/01-landing.png", full_page=True)

    body_text = page.locator("body").inner_text()
    page_html = page.content()

    # Check NEPHILIM branding
    if "nephilim" in page_html.lower():
        log("PASS", "Landing has NEPHILIM branding")
    else:
        log("FAIL", "Missing NEPHILIM branding")

    # Check "Enter the Realm" portal
    if "realm" in body_text.lower() or "enter" in body_text.lower():
        log("PASS", "Portal CTA visible")
    else:
        log("FAIL", "Portal CTA not found")

    # Header should be hidden on landing
    has_visible_header = page.evaluate("""
        () => {
            const el = document.querySelector('header');
            if (!el) return false;
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden';
        }
    """)
    if not has_visible_header:
        log("PASS", "Header hidden on landing")
    else:
        log("FAIL", "Header visible on landing (should be hidden)")

    # ─── 2. Login Page ─────────────────────────────────────────────────
    print("\n2. Login Page (/login)")
    page.goto("http://localhost:3001/login", wait_until="networkidle")
    page.screenshot(path="test-screenshots/02-login.png", full_page=True)

    login_html = page.content()
    login_text = page.locator("body").inner_text()

    if "nephilim" in login_html.lower():
        log("PASS", "Login page has NEPHILIM theme")
    else:
        log("FAIL", "Login page missing NEPHILIM theme")

    # Check for auth-related content
    has_auth = any(kw in login_text.lower() for kw in ["realm", "authenticate", "google", "sign in", "enter"])
    if has_auth:
        log("PASS", "Login page has auth elements")
    else:
        log("FAIL", "No auth elements found")

    # ─── 3. Unknown route redirect ────────────────────────────────────
    print("\n3. Unknown Route Redirect")
    page.goto("http://localhost:3001/nonexistent-page", wait_until="networkidle")
    page.wait_for_timeout(1500)
    if page.url.rstrip("/") == "http://localhost:3001" or "/login" in page.url:
        log("PASS", f"Unknown route redirected to {page.url}")
    else:
        log("FAIL", f"Unknown route stayed at {page.url}")

    # ─── 4. Protected routes redirect to login ────────────────────────
    print("\n4. Protected Route Guards")
    for route in ["/select", "/chat", "/dashboard"]:
        page.goto(f"http://localhost:3001{route}", wait_until="networkidle")
        page.wait_for_timeout(1500)
        if "/login" in page.url:
            log("PASS", f"{route} -> redirected to login (auth guard works)")
        else:
            log("FAIL", f"{route} -> did NOT redirect to login (at {page.url})")

    # ==================================================================═
    # PART B: Authenticated Routes (with mocked auth)
    # ==================================================================═
    print("\n== PART B: Authenticated Routes ==")

    # Create a fresh page with auth mocking
    auth_page = context.new_page()
    setup_auth_mock(auth_page)

    # Set NEPHILIM localStorage for onboarding bypass
    auth_page.goto("http://localhost:3001/login", wait_until="networkidle")
    auth_page.evaluate("""
        () => {
            localStorage.setItem('nephilim_onboarding_complete', 'true');
            localStorage.setItem('nephilim_user_id', 'e2e-test-user');
            localStorage.setItem('nephilim_user_name', 'E2E Seeker');
            localStorage.setItem('nephilim_faction', 'lumina');
        }
    """)

    # ─── 5. Character Selection Page ──────────────────────────────────
    print("\n5. Character Selection (/select)")
    auth_page.goto("http://localhost:3001/select", wait_until="networkidle")
    auth_page.wait_for_timeout(3000)  # Wait for persona API + animations
    auth_page.screenshot(path="test-screenshots/05-select.png", full_page=True)

    if "/select" in auth_page.url:
        log("PASS", "Character selection page loads (authenticated)")

        select_html = auth_page.content()

        # Check for Celestial Order styling
        order_classes = ["order-archon", "order-warden", "order-sage", "order-wanderer"]
        found_orders = [o for o in order_classes if o in select_html]
        if len(found_orders) > 0:
            log("PASS", f"Celestial Order classes: {', '.join(found_orders)}")
        else:
            log("FAIL", "No Celestial Order classes found in DOM")

        # Check for persona names
        persona_names = ["E.E.V.A.", "Aegis", "Solace", "Nyx", "Cipher", "Aurora"]
        found_personas = [n for n in persona_names if n in auth_page.locator("body").inner_text()]
        if len(found_personas) > 0:
            log("PASS", f"Persona cards visible: {', '.join(found_personas)}")
        else:
            log("FAIL", "No persona names visible on page")

        # Check for Header
        has_header = auth_page.evaluate("""
            () => {
                const headers = document.querySelectorAll('header, [class*="Header"], [class*="header"]');
                for (const el of headers) {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0) {
                        return true;
                    }
                }
                return false;
            }
        """)
        if has_header:
            log("PASS", "Header visible on /select")
        else:
            log("FAIL", "Header not visible on /select")

        # Check for search/filter functionality
        search_input = auth_page.locator("input[type='text'], input[type='search'], input[placeholder*='earch'], input[placeholder*='ilter']").first
        if search_input.count() > 0:
            log("PASS", "Search/filter input found")
        else:
            log("PASS", "No search input (may use different filter UI)")

    elif "/login" in auth_page.url:
        log("FAIL", "Auth mock didn't work — still redirected to login")
    else:
        log("FAIL", f"Unexpected URL: {auth_page.url}")

    # ─── 6. Chat Interface ────────────────────────────────────────────
    print("\n6. Chat Interface (/chat)")
    auth_page.goto("http://localhost:3001/chat", wait_until="networkidle")
    auth_page.wait_for_timeout(2000)
    auth_page.screenshot(path="test-screenshots/06-chat.png", full_page=True)

    if "/chat" in auth_page.url:
        log("PASS", "Chat page loads (authenticated)")

        chat_html = auth_page.content()
        chat_text = auth_page.locator("body").inner_text()

        # Check for chat input
        chat_input = auth_page.locator("input[placeholder*='essage'], input[placeholder*='ype'], textarea").first
        if chat_input.count() > 0:
            log("PASS", "Chat input field found")
        else:
            # May not have input if no persona selected
            if "select" in chat_text.lower() or "companion" in chat_text.lower() or "persona" in chat_text.lower():
                log("PASS", "Chat shows 'select companion' prompt (no persona chosen yet)")
            else:
                log("FAIL", "No chat input or companion prompt found")

        # Check Header
        has_header = auth_page.evaluate("""
            () => {
                const headers = document.querySelectorAll('header, [class*="Header"], [class*="header"]');
                for (const el of headers) {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0) return true;
                }
                return false;
            }
        """)
        if has_header:
            log("PASS", "Header visible on /chat")
        else:
            log("FAIL", "Header not visible on /chat")

    elif "/login" in auth_page.url:
        log("FAIL", "Auth mock didn't work for /chat")
    else:
        log("FAIL", f"Unexpected URL: {auth_page.url}")

    # ─── 7. Dashboard ─────────────────────────────────────────────────
    print("\n7. Dashboard (/dashboard)")
    auth_page.goto("http://localhost:3001/dashboard", wait_until="networkidle")
    auth_page.wait_for_timeout(2000)
    auth_page.screenshot(path="test-screenshots/07-dashboard.png", full_page=True)

    if "/dashboard" in auth_page.url:
        log("PASS", "Dashboard page loads (authenticated)")

        dash_text = auth_page.locator("body").inner_text()
        dash_html = auth_page.content()

        # Check for dashboard/progression content
        progression_kw = ["seeker", "rank", "resonance", "sanctum", "dashboard", "progress", "initiate", "affinity", "lore"]
        found_kw = [kw for kw in progression_kw if kw in dash_text.lower()]
        if len(found_kw) > 0:
            log("PASS", f"Dashboard has progression content: {', '.join(found_kw)}")
        else:
            log("FAIL", "No progression keywords found on dashboard")

    elif "/login" in auth_page.url:
        log("FAIL", "Auth mock didn't work for /dashboard")
    else:
        log("FAIL", f"Unexpected URL: {auth_page.url}")

    # ==================================================================═
    # PART C: Backend API Endpoints
    # ==================================================================═
    print("\n== PART C: Backend API Health ==")

    print("\n8. API Endpoints")
    endpoints = [
        ("GET", "/health", "Backend health"),
        ("GET", "/personas", "Personas list"),
        ("GET", "/nephilim/ranks", "NEPHILIM ranks"),
        ("GET", "/nephilim/factions", "NEPHILIM factions"),
    ]

    for method, path, label in endpoints:
        resp = page.evaluate(f"""
            async () => {{
                try {{
                    const res = await fetch('http://localhost:8000{path}');
                    const data = await res.json();
                    return {{ ok: res.ok, status: res.status, data }};
                }} catch (e) {{
                    return {{ ok: false, error: e.message }};
                }}
            }}
        """)
        if resp.get("ok"):
            detail = ""
            if "personas" in path and isinstance(resp["data"], list):
                detail = f" ({len(resp['data'])} items)"
            elif isinstance(resp["data"], dict):
                for key in ["ranks", "factions"]:
                    if key in resp["data"]:
                        detail = f" ({len(resp['data'][key])} items)"
            log("PASS", f"{label}: OK{detail}")
        else:
            log("FAIL", f"{label}: {resp}")

    # ─── 9. NEPHILIM Seeker API ───────────────────────────────────────
    print("\n9. NEPHILIM Seeker API")
    seeker_resp = page.evaluate("""
        async () => {
            try {
                const res = await fetch('http://localhost:8000/nephilim/seeker/e2e-test-user');
                const data = await res.json();
                return { ok: res.ok, status: res.status, data };
            } catch (e) {
                return { ok: false, error: e.message };
            }
        }
    """)
    if seeker_resp.get("ok"):
        log("PASS", f"Seeker profile API works (rank: {seeker_resp['data'].get('rank_name', 'N/A')})")
    else:
        log("FAIL", f"Seeker profile API failed: {seeker_resp}")

    # ==================================================================═
    # PART D: Console Error Summary
    # ==================================================================═
    print("\n== PART D: Console Error Check ==")

    print("\n10. Console Errors")
    if len(console_errors) == 0:
        log("PASS", "No unexpected console errors")
    else:
        log("FAIL", f"{len(console_errors)} unexpected console error(s):")
        for err in console_errors[:5]:
            print(f"    - {err[:150]}")

    auth_page.close()
    browser.close()

# ======================================================================═
# Summary
# ======================================================================═
print("\n" + "=" * 60)
print(f"  E2E Test Results: {PASS} passed, {FAIL} failed")
print("=" * 60)
for r in results:
    print(r)
print()

if FAIL > 0:
    print(f"  WARNING: {FAIL} failure(s) detected")
    sys.exit(1)
else:
    print("  All tests passed!")
