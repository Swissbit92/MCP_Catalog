"""Interactive UI test for NEPHILIM website - Phase 8 validation"""
from playwright.sync_api import sync_playwright
import os

SCREENSHOTS = os.path.join(os.path.dirname(__file__), 'test-screenshots', 'interactive')
os.makedirs(SCREENSHOTS, exist_ok=True)

def shot(page, name):
    path = os.path.join(SCREENSHOTS, f'{name}.png')
    page.screenshot(path=path, full_page=False)
    print(f'  Screenshot: {name}.png')
    return path

def shot_full(page, name):
    path = os.path.join(SCREENSHOTS, f'{name}.png')
    page.screenshot(path=path, full_page=True)
    print(f'  Screenshot (full): {name}.png')
    return path

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()

    # Set up localStorage for authenticated user
    page.goto('http://localhost:3001')
    page.evaluate("""() => {
        localStorage.setItem('nephilim_user_id', 'default_seeker')
        localStorage.setItem('nephilim_user_name', 'TestSeeker')
        localStorage.setItem('nephilim_onboarding_complete', 'true')
    }""")

    # ==========================================
    # 1. LANDING PAGE
    # ==========================================
    print('\n=== 1. LANDING PAGE ===')
    page.goto('http://localhost:3001/', wait_until='networkidle')
    page.wait_for_timeout(2000)
    shot(page, '01-landing')

    # Look for "Enter the Realm" button
    enter_btn = page.locator('text=/enter.*realm/i').first
    if enter_btn.is_visible():
        print('  Found "Enter the Realm" button - clicking...')
        enter_btn.click()
        page.wait_for_timeout(2000)
        shot(page, '02-after-enter-realm')
    else:
        print('  "Enter the Realm" not found, checking page content...')
        shot(page, '02-landing-content')

    # ==========================================
    # 2. BROWSE ALL COMPANIONS -> /select
    # ==========================================
    print('\n=== 2. NAVIGATE TO COMPANIONS ===')
    browse_btn = page.locator('text=/browse.*companion/i').first
    if browse_btn.is_visible():
        print('  Found "Browse All Companions" - clicking...')
        browse_btn.click()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
    else:
        print('  Navigating directly to /select...')
        page.goto('http://localhost:3001/select', wait_until='networkidle')
        page.wait_for_timeout(2000)

    shot(page, '03-select-page')

    # Count visible cards
    cards = page.locator('[class*="CharacterCard_card"]').all()
    print(f'  Persona cards visible: {len(cards)}')

    # ==========================================
    # 3. TEST NEPHILIM FILTER
    # ==========================================
    print('\n=== 3. NEPHILIM FILTER ===')
    nephilim_filter = page.locator('button:has-text("Nephilim")').first
    if nephilim_filter.is_visible():
        nephilim_filter.click()
        page.wait_for_timeout(1000)
        shot(page, '04-nephilim-filter')
        filtered_cards = page.locator('[class*="CharacterCard_card"]').all()
        print(f'  Cards after NEPHILIM filter: {len(filtered_cards)}')

    # Switch back to All
    all_filter = page.locator('button:has-text("All")').first
    if all_filter.is_visible():
        all_filter.click()
        page.wait_for_timeout(500)

    # ==========================================
    # 4. CLICK A PERSONA CARD -> CHAT
    # ==========================================
    print('\n=== 4. CLICK PERSONA CARD ===')
    # Hover over first card to trigger overlay
    first_card = page.locator('[class*="CharacterCard_card"]').first
    if first_card.is_visible():
        first_card.hover()
        page.wait_for_timeout(500)
        shot(page, '05-card-hover')

        # Click the "Choose" button on the card overlay
        choose_btn = page.locator('[class*="card-choose"], button:has-text("Choose"), [class*="choose"]').first
        if choose_btn.is_visible():
            print('  Found Choose button - clicking...')
            choose_btn.click(force=True)
        else:
            # Try clicking the card directly
            print('  Clicking card directly...')
            first_card.click(force=True)

        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)
        shot(page, '06-chat-after-card')
        print(f'  Current URL: {page.url}')

    # ==========================================
    # 5. CHAT - SEND A MESSAGE
    # ==========================================
    print('\n=== 5. CHAT INTERACTION ===')

    # Check if we're on chat page with a greeting
    if '/chat' in page.url:
        # Wait for greeting to load
        page.wait_for_timeout(3000)
        shot(page, '07-chat-greeting')

        # Check for greeting message
        messages = page.locator('[class*="message"], [class*="Message"], [class*="bubble"]').all()
        print(f'  Message bubbles visible: {len(messages)}')

        # Find and fill chat input
        chat_input = page.locator('input[placeholder*="message"], textarea[placeholder*="message"]').first
        if chat_input.is_visible():
            print('  Typing message...')
            chat_input.fill('Hello, tell me about yourself')
            page.wait_for_timeout(500)
            shot(page, '08-chat-typed')

            # Click Send button
            send_btn = page.locator('button:has-text("Send")').first
            if send_btn.is_visible():
                print('  Clicking Send...')
                send_btn.click()

                # Wait for LLM response (up to 30s)
                print('  Waiting for LLM response...')
                page.wait_for_timeout(15000)
                shot(page, '09-chat-response')

                # Check for resonance toast
                toast = page.locator('text=/resonance/i').first
                if toast.is_visible():
                    print('  +5 Resonance toast VISIBLE!')
                    shot(page, '10-resonance-toast')
                else:
                    print('  Resonance toast not visible (may have already faded)')
                    # Take a screenshot anyway
                    shot(page, '10-after-send')
            else:
                print('  Send button not found')
        else:
            print('  Chat input not found - checking for empty state')
            shot(page, '07-chat-state')
    else:
        print(f'  Not on chat page, navigating directly...')
        page.goto('http://localhost:3001/chat', wait_until='networkidle')
        page.wait_for_timeout(2000)
        shot(page, '07-chat-empty')

    # ==========================================
    # 6. DASHBOARD - ALL TABS
    # ==========================================
    print('\n=== 6. DASHBOARD ===')

    # Navigate via header
    dashboard_link = page.locator('a:has-text("Dashboard")').first
    if dashboard_link.is_visible():
        print('  Clicking Dashboard in header...')
        dashboard_link.click()
    else:
        page.goto('http://localhost:3001/dashboard', wait_until='networkidle')

    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)
    shot_full(page, '11-dashboard-profile')

    # Check for Seeker Profile content
    rank_text = page.locator('text=/Initiate/i').first
    print(f'  Rank badge visible: {rank_text.is_visible() if rank_text else False}')

    # Click Bonds Forged tab
    print('\n  --- Bonds Forged Tab ---')
    bonds_tab = page.locator('button:has-text("Bonds")').first
    if bonds_tab.is_visible():
        bonds_tab.click()
        page.wait_for_timeout(1000)
        shot_full(page, '12-dashboard-bonds')

        # Check constellation SVG
        svg = page.locator('svg').first
        circles = page.locator('svg circle').all()
        print(f'  Constellation SVG visible: {svg.is_visible() if svg else False}')
        print(f'  SVG circles (nodes): {len(circles)}')

    # Click Chronicle tab
    print('\n  --- Invocation Chronicle Tab ---')
    chronicle_tab = page.locator('button:has-text("Chronicle")').first
    if chronicle_tab.is_visible():
        chronicle_tab.click()
        page.wait_for_timeout(1000)
        shot_full(page, '13-dashboard-chronicle')

        # Check for CTA button
        cta = page.locator('button:has-text("Begin your first Summoning")').first
        print(f'  "Begin your first Summoning" CTA visible: {cta.is_visible() if cta else False}')

        # Check stats
        stats = page.locator('text=/Invocation Stats/i').first
        print(f'  Invocation Stats section visible: {stats.is_visible() if stats else False}')

    # Click back to Profile tab
    profile_tab = page.locator('button:has-text("Profile"), button:has-text("Seeker")').first
    if profile_tab.is_visible():
        profile_tab.click()
        page.wait_for_timeout(500)

    # ==========================================
    # 7. HEADER RANK BADGE CLOSE-UP
    # ==========================================
    print('\n=== 7. HEADER RANK BADGE ===')
    header = page.locator('header').first
    if header.is_visible():
        header.screenshot(path=os.path.join(SCREENSHOTS, '14-header-closeup.png'))
        print('  Header screenshot captured')

        rank_badge = page.locator('text=/Initiate/').first
        print(f'  Rank "Initiate" in header: {rank_badge.is_visible() if rank_badge else False}')

        seeker_name = page.locator('text=TestSeeker').first
        print(f'  "TestSeeker" name in header: {seeker_name.is_visible() if seeker_name else False}')

    # ==========================================
    # 8. MOBILE VIEWPORT
    # ==========================================
    print('\n=== 8. MOBILE VIEWPORT (375x812) ===')
    mobile_context = browser.new_context(
        viewport={'width': 375, 'height': 812},
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    )
    mobile = mobile_context.new_page()

    # Navigate first, then set localStorage
    mobile.goto('http://localhost:3001/', wait_until='networkidle')
    mobile.evaluate("""() => {
        localStorage.setItem('nephilim_user_id', 'default_seeker')
        localStorage.setItem('nephilim_user_name', 'TestSeeker')
        localStorage.setItem('nephilim_onboarding_complete', 'true')
    }""")
    mobile.goto('http://localhost:3001/', wait_until='networkidle')
    mobile.wait_for_timeout(2000)
    shot(mobile, '15-mobile-landing')

    # Mobile select
    mobile.goto('http://localhost:3001/select', wait_until='networkidle')
    mobile.wait_for_timeout(2000)
    shot(mobile, '16-mobile-select')

    # Check bottom tab bar
    bottom_nav = mobile.locator('nav[aria-label="Mobile navigation"]').first
    if bottom_nav.is_visible():
        print('  Bottom tab bar: VISIBLE')
        bottom_nav.screenshot(path=os.path.join(SCREENSHOTS, '17-mobile-bottom-bar.png'))

        # Check tab labels
        tabs = mobile.locator('nav[aria-label="Mobile navigation"] a, nav[aria-label="Mobile navigation"] button').all()
        tab_texts = [t.text_content().strip() for t in tabs]
        # Encode safely for Windows console
        safe_texts = [t.encode('ascii', 'replace').decode() for t in tab_texts]
        print(f'  Tab items: {safe_texts}')
    else:
        print('  Bottom tab bar: NOT FOUND')

    # Mobile dashboard
    mobile.goto('http://localhost:3001/dashboard', wait_until='networkidle')
    mobile.wait_for_timeout(2000)
    shot(mobile, '18-mobile-dashboard')

    # Mobile chat
    mobile.goto('http://localhost:3001/chat', wait_until='networkidle')
    mobile.wait_for_timeout(1000)
    shot(mobile, '19-mobile-chat')

    mobile_context.close()

    # ==========================================
    # SUMMARY
    # ==========================================
    print('\n==========================================')
    print('         TEST COMPLETE')
    print('==========================================')
    screenshots = [f for f in os.listdir(SCREENSHOTS) if f.endswith('.png')]
    print(f'Total screenshots: {len(screenshots)}')
    for s in sorted(screenshots):
        print(f'  {s}')

    browser.close()
