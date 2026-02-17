"""Deep chat UI testing - bubble positioning, loading states, multi-turn conversations"""
from playwright.sync_api import sync_playwright
import os, time

SCREENSHOTS = os.path.join(os.path.dirname(__file__), 'test-screenshots', 'chat-deep')
os.makedirs(SCREENSHOTS, exist_ok=True)

def shot(page, name):
    path = os.path.join(SCREENSHOTS, f'{name}.png')
    page.screenshot(path=path, full_page=False)
    print(f'  >> {name}.png')

def shot_full(page, name):
    path = os.path.join(SCREENSHOTS, f'{name}.png')
    page.screenshot(path=path, full_page=True)
    print(f'  >> {name}.png (full)')

def send_message(page, text, wait_ms=20000):
    """Type a message, capture the loading state, then wait for response"""
    chat_input = page.locator('input[placeholder*="message"], textarea[placeholder*="message"]').first
    if not chat_input.is_visible():
        print(f'  [WARN] Chat input not visible')
        return False

    chat_input.fill(text)
    page.wait_for_timeout(300)

    send_btn = page.locator('button:has-text("Send")').first
    if send_btn.is_visible():
        send_btn.click()
        # Capture loading/typing indicator immediately
        page.wait_for_timeout(800)
        return True
    return False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ==========================================
    # DESKTOP CHAT TEST (1440x900)
    # ==========================================
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()

    # Collect console errors
    console_errors = []
    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)

    # Set up user state
    page.goto('http://localhost:3001/')
    page.evaluate("""() => {
        localStorage.setItem('nephilim_user_id', 'default_seeker')
        localStorage.setItem('nephilim_user_name', 'TestSeeker')
        localStorage.setItem('nephilim_onboarding_complete', 'true')
    }""")

    # ==========================================
    # TEST 1: Select a NEPHILIM persona and start chat
    # ==========================================
    print('\n=== TEST 1: START CHAT WITH NEPHILIM PERSONA ===')
    page.goto('http://localhost:3001/select', wait_until='networkidle')
    page.wait_for_timeout(2000)

    # Click NEPHILIM filter first
    neph_filter = page.locator('button:has-text("Nephilim")').first
    if neph_filter.is_visible():
        neph_filter.click()
        page.wait_for_timeout(500)

    # Find and click the first card's Choose button
    first_card = page.locator('[class*="CharacterCard_card"]').first
    if first_card.is_visible():
        first_card.hover()
        page.wait_for_timeout(500)
        choose = page.locator('[class*="card-choose"], button:has-text("Choose")').first
        if choose.is_visible():
            choose.click(force=True)
        else:
            first_card.click(force=True)

        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

    shot(page, '01-chat-initial-greeting')
    print(f'  URL: {page.url}')

    # ==========================================
    # TEST 2: Examine greeting message bubble
    # ==========================================
    print('\n=== TEST 2: GREETING MESSAGE BUBBLE ===')
    page.wait_for_timeout(2000)

    # Check for persona name in chat header or message
    persona_label = page.locator('[class*="persona"], [class*="Persona"], [class*="sender"], [class*="name"]').first
    if persona_label.is_visible():
        label_text = persona_label.text_content()
        print(f'  Persona label: {label_text[:50] if label_text else "empty"}')

    # Check message bubble positioning - assistant messages should be left-aligned
    all_messages = page.locator('[class*="message"], [class*="Message"], [class*="bubble"], [class*="Bubble"]').all()
    print(f'  Total message elements: {len(all_messages)}')

    shot(page, '02-greeting-bubble-detail')

    # ==========================================
    # TEST 3: Send first message and capture typing indicator
    # ==========================================
    print('\n=== TEST 3: SEND MESSAGE + TYPING INDICATOR ===')

    if send_message(page, 'Hello! What can you help me with?', wait_ms=0):
        # Quick screenshot to catch typing/loading indicator
        shot(page, '03a-typing-indicator')

        # Check for typing indicator
        typing_css = page.locator('[class*="typing"], [class*="Typing"], [class*="channeling"]').first
        typing_text = page.locator('text=/channeling|typing|thinking/i').first
        typing_visible = False
        try:
            typing_visible = typing_css.is_visible(timeout=1000) if typing_css else False
        except:
            pass
        if not typing_visible:
            try:
                typing_visible = typing_text.is_visible(timeout=1000) if typing_text else False
            except:
                pass
        if typing_visible:
            print('  Typing indicator: VISIBLE')
            shot(page, '03b-typing-indicator-visible')
        else:
            print('  Typing indicator: not caught (may have been too fast)')

        # Wait for full response
        print('  Waiting for LLM response...')
        page.wait_for_timeout(20000)
        shot(page, '03c-first-response')

        messages_after = page.locator('[class*="message"], [class*="Message"], [class*="bubble"], [class*="Bubble"]').all()
        print(f'  Messages after send: {len(messages_after)}')

    # ==========================================
    # TEST 4: Check bubble alignment (user=right, assistant=left)
    # ==========================================
    print('\n=== TEST 4: BUBBLE ALIGNMENT ===')

    # Evaluate bubble positions in the DOM
    alignment_info = page.evaluate("""() => {
        const msgs = document.querySelectorAll('[class*="message"], [class*="Message"]')
        const results = []
        for (const msg of msgs) {
            const rect = msg.getBoundingClientRect()
            const style = window.getComputedStyle(msg)
            const text = msg.textContent?.slice(0, 60) || ''
            const classes = msg.className?.toString() || ''
            results.push({
                text: text,
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width),
                classes: classes.slice(0, 100),
                justify: style.justifyContent || style.textAlign || 'unknown'
            })
        }
        return results
    }""")

    for info in alignment_info[:6]:
        text_preview = info.get('text', '')[:40].encode('ascii', 'replace').decode()
        print(f'  Bubble: left={info["left"]}px right={info["right"]}px | {text_preview}')

    # ==========================================
    # TEST 5: Send second message for multi-turn
    # ==========================================
    print('\n=== TEST 5: MULTI-TURN CONVERSATION ===')

    if send_message(page, 'Tell me something interesting about yourself'):
        page.wait_for_timeout(800)
        shot(page, '04a-second-msg-typing')

        print('  Waiting for second response...')
        page.wait_for_timeout(20000)
        shot(page, '04b-second-response')

        messages_count = page.locator('[class*="message"], [class*="Message"], [class*="bubble"], [class*="Bubble"]').all()
        print(f'  Total messages now: {len(messages_count)}')

    # ==========================================
    # TEST 6: Send third message to test scrolling
    # ==========================================
    print('\n=== TEST 6: SCROLL BEHAVIOR ===')

    if send_message(page, 'Can you explain that in more detail? I want to understand better.'):
        page.wait_for_timeout(800)
        shot(page, '05a-third-msg-sent')

        print('  Waiting for third response...')
        page.wait_for_timeout(20000)
        shot(page, '05b-third-response')

    # Check if chat auto-scrolled to bottom
    scroll_info = page.evaluate("""() => {
        const containers = document.querySelectorAll('[class*="message"], [class*="list"], [class*="chat"], [class*="scroll"]')
        for (const c of containers) {
            if (c.scrollHeight > c.clientHeight) {
                return {
                    scrollTop: Math.round(c.scrollTop),
                    scrollHeight: Math.round(c.scrollHeight),
                    clientHeight: Math.round(c.clientHeight),
                    atBottom: Math.abs((c.scrollTop + c.clientHeight) - c.scrollHeight) < 50,
                    tag: c.tagName,
                    class: c.className?.toString().slice(0, 60)
                }
            }
        }
        return { note: 'No scrollable container found or content fits' }
    }""")
    print(f'  Scroll state: {scroll_info}')

    # ==========================================
    # TEST 7: Check resonance toast appearance
    # ==========================================
    print('\n=== TEST 7: RESONANCE TOAST CHECK ===')

    # Send one more message and check immediately for toast
    if send_message(page, 'Thanks!'):
        # Check very quickly for the toast (it appears right after send)
        page.wait_for_timeout(500)

        toast = page.locator('text=/resonance/i').first
        toast_visible = toast.is_visible() if toast else False
        print(f'  Resonance toast at 0.5s: {toast_visible}')
        if toast_visible:
            shot(page, '06a-resonance-toast-visible')

        page.wait_for_timeout(1000)
        toast2 = page.locator('text=/resonance/i').first
        toast_visible2 = toast2.is_visible() if toast2 else False
        print(f'  Resonance toast at 1.5s: {toast_visible2}')
        if toast_visible2:
            shot(page, '06b-resonance-toast-still')

        # Wait for it to fade
        page.wait_for_timeout(3500)
        toast3 = page.locator('text=/resonance/i').first
        toast_visible3 = toast3.is_visible() if toast3 else False
        print(f'  Resonance toast at 5s (should be gone): {toast_visible3}')

        # Wait for response
        page.wait_for_timeout(15000)
        shot(page, '06c-after-thanks')

    # ==========================================
    # TEST 8: Session sidebar
    # ==========================================
    print('\n=== TEST 8: SESSION SIDEBAR ===')

    sidebar_css = page.locator('[class*="session"], [class*="Session"], [class*="sidebar"], [class*="Sidebar"]').first
    sidebar_text = page.locator('text=/memory archive/i').first
    sidebar_visible = False
    try:
        sidebar_visible = sidebar_css.is_visible(timeout=2000)
    except:
        pass
    if not sidebar_visible:
        try:
            sidebar_visible = sidebar_text.is_visible(timeout=1000)
        except:
            pass
    if sidebar_visible:
        print('  Session sidebar: VISIBLE')
        shot(page, '07-session-sidebar')
    else:
        print('  Session sidebar: not visible (may need to scroll or toggle)')

    # Check for session list items
    sessions = page.locator('[class*="session-item"], [class*="SessionItem"], [class*="sessionCard"]').all()
    print(f'  Session items visible: {len(sessions)}')

    # ==========================================
    # TEST 9: Source indicators on messages
    # ==========================================
    print('\n=== TEST 9: SOURCE INDICATORS ===')

    sources = page.locator('text=/Pure LLM|Brave|MongoDB|Archives|Crystal/i').all()
    print(f'  Source indicator badges: {len(sources)}')
    for s in sources[:3]:
        txt = s.text_content()
        if txt:
            safe = txt.strip()[:50].encode('ascii', 'replace').decode()
            print(f'    - {safe}')

    # ==========================================
    # TEST 10: Message timestamps
    # ==========================================
    print('\n=== TEST 10: TIMESTAMPS ===')

    timestamps = page.locator('text=/\\d{1,2}:\\d{2}\\s?(AM|PM|am|pm)/').all()
    print(f'  Timestamp elements: {len(timestamps)}')

    # Final full-page screenshot of the conversation
    shot_full(page, '08-full-conversation')

    # ==========================================
    # TEST 11: MOBILE CHAT (375x812)
    # ==========================================
    print('\n=== TEST 11: MOBILE CHAT ===')
    context.close()

    mobile_ctx = browser.new_context(
        viewport={'width': 375, 'height': 812},
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    )
    mobile = mobile_ctx.new_page()
    mobile.goto('http://localhost:3001/')
    mobile.evaluate("""() => {
        localStorage.setItem('nephilim_user_id', 'default_seeker')
        localStorage.setItem('nephilim_user_name', 'TestSeeker')
        localStorage.setItem('nephilim_onboarding_complete', 'true')
    }""")

    # Go to select, pick a persona
    mobile.goto('http://localhost:3001/select', wait_until='networkidle')
    mobile.wait_for_timeout(2000)

    mobile_card = mobile.locator('[class*="CharacterCard_card"]').first
    if mobile_card.is_visible():
        mobile_card.click(force=True)
        mobile.wait_for_timeout(500)
        # Try to find and click choose
        mobile_choose = mobile.locator('[class*="card-choose"], button:has-text("Choose")').first
        if mobile_choose.is_visible():
            mobile_choose.click(force=True)
        else:
            mobile_card.click(force=True)

        mobile.wait_for_load_state('networkidle')
        mobile.wait_for_timeout(3000)

    shot(mobile, '09-mobile-chat-greeting')

    # Send a message on mobile
    mobile_input = mobile.locator('input[placeholder*="message"], textarea[placeholder*="message"]').first
    if mobile_input.is_visible():
        mobile_input.fill('Hi there! Testing on mobile')
        mobile.wait_for_timeout(300)
        shot(mobile, '10-mobile-chat-typing')

        mobile_send = mobile.locator('button:has-text("Send")').first
        if mobile_send.is_visible():
            mobile_send.click()
            mobile.wait_for_timeout(1000)
            shot(mobile, '11-mobile-chat-loading')

            print('  Waiting for mobile LLM response...')
            mobile.wait_for_timeout(20000)
            shot(mobile, '12-mobile-chat-response')

            # Check bubble layout on mobile
            mobile_bubbles = mobile.evaluate("""() => {
                const viewport = window.innerWidth
                const msgs = document.querySelectorAll('[class*="message"], [class*="Message"]')
                const results = []
                for (const msg of msgs) {
                    const rect = msg.getBoundingClientRect()
                    results.push({
                        left: Math.round(rect.left),
                        right: Math.round(rect.right),
                        width: Math.round(rect.width),
                        pctWidth: Math.round(rect.width / viewport * 100),
                        text: msg.textContent?.slice(0, 30) || ''
                    })
                }
                return { viewport, messages: results }
            }""")
            print(f'  Mobile viewport: {mobile_bubbles.get("viewport")}px')
            for mb in mobile_bubbles.get('messages', [])[:4]:
                txt = mb.get('text', '')[:25].encode('ascii', 'replace').decode()
                print(f'    Bubble: {mb["pctWidth"]}% width, left={mb["left"]}px | {txt}')

    # Check bottom nav doesn't overlap chat input
    shot(mobile, '13-mobile-chat-bottom')

    # Check if input is above bottom nav
    input_pos = mobile.evaluate("""() => {
        const input = document.querySelector('input[placeholder*="message"], textarea[placeholder*="message"]')
        const nav = document.querySelector('nav[aria-label="Mobile navigation"]')
        if (input && nav) {
            const inputRect = input.getBoundingClientRect()
            const navRect = nav.getBoundingClientRect()
            return {
                inputBottom: Math.round(inputRect.bottom),
                navTop: Math.round(navRect.top),
                overlap: inputRect.bottom > navRect.top,
                gap: Math.round(navRect.top - inputRect.bottom)
            }
        }
        return { note: 'Could not find input or nav' }
    }""")
    print(f'  Input/Nav overlap check: {input_pos}')

    mobile_ctx.close()

    # ==========================================
    # TEST 12: LEGACY PERSONA CHAT (no resonance toast)
    # ==========================================
    print('\n=== TEST 12: LEGACY (WANDERER) PERSONA CHAT ===')

    legacy_ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    legacy_page = legacy_ctx.new_page()
    legacy_page.goto('http://localhost:3001/')
    legacy_page.evaluate("""() => {
        localStorage.setItem('nephilim_user_id', 'default_seeker')
        localStorage.setItem('nephilim_user_name', 'TestSeeker')
        localStorage.setItem('nephilim_onboarding_complete', 'true')
    }""")

    # Filter to Wanderers only
    legacy_page.goto('http://localhost:3001/select', wait_until='networkidle')
    legacy_page.wait_for_timeout(2000)

    wanderer_filter = legacy_page.locator('button:has-text("Wanderers")').first
    if wanderer_filter.is_visible():
        wanderer_filter.click()
        legacy_page.wait_for_timeout(500)

    shot(legacy_page, '14-wanderer-select')

    # Click first wanderer card
    wanderer_card = legacy_page.locator('[class*="CharacterCard_card"]').first
    if wanderer_card.is_visible():
        wanderer_card.hover()
        legacy_page.wait_for_timeout(300)
        w_choose = legacy_page.locator('[class*="card-choose"], button:has-text("Choose")').first
        if w_choose.is_visible():
            w_choose.click(force=True)
        else:
            wanderer_card.click(force=True)

        legacy_page.wait_for_load_state('networkidle')
        legacy_page.wait_for_timeout(3000)
        shot(legacy_page, '15-wanderer-chat-greeting')

        # Send message to wanderer
        if send_message(legacy_page, 'Hello! Tell me about yourself'):
            legacy_page.wait_for_timeout(1000)

            # Check that resonance toast does NOT appear for wanderer
            w_toast = legacy_page.locator('text=/resonance/i').first
            w_toast_visible = w_toast.is_visible() if w_toast else False
            print(f'  Resonance toast for Wanderer (should be false): {w_toast_visible}')

            print('  Waiting for Wanderer response...')
            legacy_page.wait_for_timeout(20000)
            shot(legacy_page, '16-wanderer-chat-response')

    legacy_ctx.close()

    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print('\n==========================================')
    print('       CHAT DEEP TEST COMPLETE')
    print('==========================================')

    screenshots = sorted([f for f in os.listdir(SCREENSHOTS) if f.endswith('.png')])
    print(f'Total screenshots: {len(screenshots)}')
    for s in screenshots:
        print(f'  {s}')

    if console_errors:
        print(f'\nConsole errors captured: {len(console_errors)}')
        for e in console_errors[:5]:
            safe = e[:100].encode('ascii', 'replace').decode()
            print(f'  {safe}')

    browser.close()
