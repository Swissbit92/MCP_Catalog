import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const BACKEND_URL = 'http://localhost:8000'
const SCREENSHOT_DIR = 'test-screenshots/phase8-live'

test.describe('Phase 8 Final Gap Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'default_seeker')
      localStorage.setItem('nephilim_user_name', 'TestSeeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })
  })

  test('chat flow - select persona from card and verify greeting loads', async ({ page }) => {
    // Go to select page
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    // Find a clickable card - use the card's clickable area
    // From screenshots, cards show persona names like "Eeva - Bitcoin Expert"
    // Let's try clicking the first card image/container
    const cardContainers = page.locator('[class*="CardV2"], [class*="cardv2"], [class*="characterCard"]')
    const cardCount = await cardContainers.count()
    console.log(`CardV2 elements found: ${cardCount}`)

    // Try broader selector
    const allClickable = page.locator('img[alt], [class*="card"] img, [class*="Card"] img')
    const imgCount = await allClickable.count()
    console.log(`Card images found: ${imgCount}`)

    // Click the first card image
    if (imgCount > 0) {
      await allClickable.first().click()
      await page.waitForTimeout(8000) // Wait for chat + greeting from LLM
      await page.screenshot({ path: `${SCREENSHOT_DIR}/09-chat-from-select.png`, fullPage: true })
      console.log(`URL after card click: ${page.url()}`)

      // Check for greeting message
      const bodyText = await page.textContent('body')
      const hasGreeting = bodyText.includes('Hey') || bodyText.includes('Hello') || bodyText.includes('Welcome') || bodyText.includes('channeling')
      console.log(`Greeting content found: ${hasGreeting}`)
      console.log(`Body text preview (first 500): ${bodyText.slice(0, 500)}`)

      // Verify chat input
      const textarea = page.locator('textarea')
      const hasTextarea = await textarea.isVisible().catch(() => false)
      console.log(`Textarea visible: ${hasTextarea}`)

      // Check for Send button
      const sendBtn = page.getByText('Send')
      const sendVis = await sendBtn.isVisible().catch(() => false)
      console.log(`Send button visible: ${sendVis}`)

      // If we have a textarea, try sending a message
      if (hasTextarea) {
        await textarea.fill('Hello! Quick test message.')
        await page.screenshot({ path: `${SCREENSHOT_DIR}/09-chat-message-typed.png`, fullPage: true })

        // Send via button click
        if (sendVis) {
          await sendBtn.click()
        } else {
          await page.keyboard.press('Enter')
        }

        // Wait for response
        await page.waitForTimeout(15000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/09-chat-response-received.png`, fullPage: true })

        // Look for any response elements
        const messageEls = page.locator('[class*="message"], [class*="Message"], [class*="bubble"]')
        const msgCount = await messageEls.count()
        console.log(`Message elements after send: ${msgCount}`)

        // Check for ResonanceToast
        const toast = page.locator('[class*="resonance"], [class*="Resonance"], [class*="toast"], [class*="Toast"]')
        const toastCount = await toast.count()
        console.log(`Resonance/toast elements: ${toastCount}`)
      }
    } else {
      console.log('No card images found to click')
    }
  })

  test('chat URL with persona param - verify it loads persona correctly', async ({ page }) => {
    // Use direct backend API to create a session first
    const greetResp = await page.request.post(`${BACKEND_URL}/greet`, {
      data: { persona: 'nephilim_eeva' }
    })
    console.log(`Greet API status: ${greetResp.status()}`)

    if (greetResp.ok()) {
      const greetData = await greetResp.json()
      console.log(`Greet response: ${JSON.stringify(greetData).slice(0, 300)}`)
      const sessionId = greetData.session_id

      if (sessionId) {
        // Navigate to chat with this session
        await page.goto(`${BASE_URL}/chat/${sessionId}`)
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(5000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/09-chat-with-session.png`, fullPage: true })

        // Check for greeting
        const bodyText = await page.textContent('body')
        console.log(`Chat with session body: ${bodyText.slice(0, 500)}`)

        // Verify persona name
        const hasEeva = bodyText.includes('E.E.V.A') || bodyText.includes('Eeva') || bodyText.includes('eeva')
        console.log(`EEVA name visible: ${hasEeva}`)
      }
    }
  })

  test('onboarding - verify redirect and portal UI', async ({ page }) => {
    // Clear onboarding state
    await page.evaluate(() => localStorage.clear())

    // Visit root - should redirect to onboarding
    await page.goto(BASE_URL + '/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    const url = page.url()
    console.log(`After visiting / without onboarding: ${url}`)

    if (url.includes('/onboarding')) {
      console.log('PASS: Redirected to /onboarding correctly')

      await page.waitForTimeout(3000) // Typewriter effect
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10-onboarding-portal.png`, fullPage: true })

      // Check what's on the page
      const bodyText = await page.textContent('body')
      console.log(`Onboarding content: ${bodyText.slice(0, 400)}`)

      // Look for interactive elements
      const inputs = page.locator('input')
      const inputCount = await inputs.count()
      console.log(`Input fields: ${inputCount}`)

      const buttons = page.locator('button:visible')
      const btnCount = await buttons.count()
      console.log(`Visible buttons: ${btnCount}`)

      for (let i = 0; i < btnCount; i++) {
        const text = await buttons.nth(i).textContent()
        console.log(`  Button ${i}: "${text?.trim()}"`)
      }

      // Click "Enter the Realm" if present
      const enterBtn = page.getByText(/Enter.*Realm/i)
      const enterVis = await enterBtn.isVisible().catch(() => false)
      if (enterVis) {
        await enterBtn.click()
        await page.waitForTimeout(3000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/10-onboarding-after-enter.png`, fullPage: true })
        console.log(`After Enter the Realm: ${page.url()}`)

        // Check what we see now
        const newBody = await page.textContent('body')
        console.log(`After enter content: ${newBody.slice(0, 400)}`)

        // Look for name input
        const nameInput = page.locator('input')
        const nameVis = await nameInput.first().isVisible().catch(() => false)
        if (nameVis) {
          await nameInput.first().fill('QA_Tester')
          await page.waitForTimeout(500)
          await page.screenshot({ path: `${SCREENSHOT_DIR}/10-onboarding-name.png`, fullPage: true })
        }
      }
    }
  })

  test('dashboard codex tab - alternative lookup', async ({ page }) => {
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Get all tab button texts
    const tabBtns = page.locator('button, [role="tab"]')
    const btnCount = await tabBtns.count()
    console.log(`Dashboard tab/button count: ${btnCount}`)

    for (let i = 0; i < btnCount; i++) {
      const text = (await tabBtns.nth(i).textContent())?.trim()
      if (text && text.length < 60) {
        console.log(`  Tab ${i}: "${text}"`)
      }
    }

    // The tabs are "SEEKER PROFILE", "BONDS FORGED", "INVOCATION CHRONICLE"
    // The Codex may be nested or may be the third tab
    // Let me check each tab
    const thirdTab = page.locator('button').filter({ hasText: /INVOCATION|Chronicle/i }).first()
    const thirdVis = await thirdTab.isVisible().catch(() => false)
    if (thirdVis) {
      await thirdTab.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10-dashboard-invocation.png`, fullPage: true })

      const content = await page.textContent('body')
      console.log(`Invocation Chronicle content: ${content.slice(content.indexOf('INVOCATION'), content.indexOf('INVOCATION') + 300)}`)
    }

    // Check if there's a Lore Codex section within Seeker Profile
    const seekerTab = page.locator('button').filter({ hasText: /SEEKER|Profile/i }).first()
    if (await seekerTab.isVisible().catch(() => false)) {
      await seekerTab.click()
      await page.waitForTimeout(2000)

      // Scroll to bottom to see if Codex is below
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
      await page.waitForTimeout(500)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10-dashboard-seeker-scrolled.png`, fullPage: true })
    }
  })

  test('select page - Legacy filter and Wanderer badge check', async ({ page }) => {
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    // Click Wanderers filter
    const wandererBtn = page.locator('button').filter({ hasText: /Wanderer|Legacy/i }).first()
    const wandVis = await wandererBtn.isVisible().catch(() => false)
    console.log(`Wanderers/Legacy filter button: ${wandVis ? 'VISIBLE' : 'NOT FOUND'}`)

    if (wandVis) {
      await wandererBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/11-select-wanderers.png`, fullPage: true })

      // Check what cards are visible
      const bodyText = await page.textContent('body')
      const hasWanderer = bodyText.includes('Wanderer')
      console.log(`Wanderer label visible: ${hasWanderer}`)
    }

    // Check the filter counts in the toggle
    const allBtn = page.locator('button').filter({ hasText: /All.*\d/ }).first()
    const allText = await allBtn.textContent().catch(() => 'not found')
    console.log(`All filter text: "${allText}"`)

    const nephBtn = page.locator('button').filter({ hasText: /Nephilim.*\d/i }).first()
    const nephText = await nephBtn.textContent().catch(() => 'not found')
    console.log(`Nephilim filter text: "${nephText}"`)

    const wandBtn = page.locator('button').filter({ hasText: /Wanderer.*\d/i }).first()
    const wandText = await wandBtn.textContent().catch(() => 'not found')
    console.log(`Wanderers filter text: "${wandText}"`)
  })

  test('header rank badge fetches from live API', async ({ page }) => {
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Check the rank badge
    const rankBadge = page.getByText(/Initiate|Acolyte|Adept|Ascendant|Nephilim/)
    const badgeVis = await rankBadge.first().isVisible().catch(() => false)
    console.log(`Rank badge visible: ${badgeVis}`)

    if (badgeVis) {
      const badgeText = await rankBadge.first().textContent()
      console.log(`Rank badge text: "${badgeText}"`)

      // Verify it matches API
      const apiResp = await page.request.get(`${BACKEND_URL}/nephilim/seeker/default_seeker/rank`)
      if (apiResp.ok()) {
        const apiData = await apiResp.json()
        console.log(`API rank: ${JSON.stringify(apiData)}`)
      }
    }

    // Check seeker name
    const seekerName = page.getByText('TestSeeker')
    const nameVis = await seekerName.isVisible().catch(() => false)
    console.log(`Seeker name "TestSeeker" in header: ${nameVis}`)

    await page.screenshot({ path: `${SCREENSHOT_DIR}/12-header-rank.png` })
  })

  test('full navigation cycle with screenshots', async ({ page }) => {
    // 1. Landing -> Enter Realm -> Browse All -> Select
    await page.goto(BASE_URL + '/')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-01-landing.png` })

    const enterBtn = page.getByText('REALM')
    if (await enterBtn.isVisible().catch(() => false)) {
      await enterBtn.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-02-sixnephilim.png` })

      const browseBtn = page.getByText('Browse All Companions')
      if (await browseBtn.isVisible().catch(() => false)) {
        await browseBtn.click()
        await page.waitForTimeout(3000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-03-select.png` })
        expect(page.url()).toContain('/select')
      }
    }

    // 2. Select -> Click card -> Chat
    await page.goto(BASE_URL + '/select')
    await page.waitForTimeout(4000)
    const cards = page.locator('img[alt]')
    if (await cards.count() > 0) {
      await cards.first().click()
      await page.waitForTimeout(8000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-04-chat.png` })
      console.log(`After card click: ${page.url()}`)
    }

    // 3. Chat -> Header Dashboard link -> Dashboard
    const dashLink = page.locator('header').getByText('Dashboard')
    if (await dashLink.isVisible().catch(() => false)) {
      await dashLink.click()
      await page.waitForTimeout(3000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-05-dashboard.png` })
      expect(page.url()).toContain('/dashboard')
    }

    // 4. Dashboard -> Header Companions -> Select
    const compLink = page.locator('header').getByText('Companions')
    if (await compLink.isVisible().catch(() => false)) {
      await compLink.click()
      await page.waitForTimeout(3000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-06-back-select.png` })
      expect(page.url()).toContain('/select')
    }

    // 5. Header NEPHILIM wordmark -> Home
    const wordmark = page.locator('header').getByText('NEPHILIM')
    if (await wordmark.isVisible().catch(() => false)) {
      await wordmark.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13-nav-07-home.png` })
    }
  })

  test('check for text-white/40 in source CSS classes', async ({ page }) => {
    const pages = ['/select', '/dashboard', '/chat', '/']

    for (const route of pages) {
      await page.goto(BASE_URL + route)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(2000)

      // Check for low-opacity elements with actual text content
      const lowOpacity = await page.evaluate(() => {
        const results: { tag: string, text: string, opacity: string, color: string }[] = []
        document.querySelectorAll('*').forEach(el => {
          const style = window.getComputedStyle(el)
          const text = el.textContent?.trim()
          if (!text || text.length === 0) return

          // Check actual computed opacity and color alpha
          const color = style.color
          const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/)
          if (match) {
            const alpha = match[4] ? parseFloat(match[4]) : 1
            if (alpha < 0.5 && alpha > 0 && text.length < 100) {
              results.push({
                tag: el.tagName,
                text: text.slice(0, 50),
                opacity: style.opacity,
                color: color
              })
            }
          }
        })
        return results.slice(0, 10) // Limit
      })

      if (lowOpacity.length > 0) {
        console.log(`${route}: ${lowOpacity.length} elements with low alpha text color:`)
        for (const item of lowOpacity.slice(0, 3)) {
          console.log(`  <${item.tag}> "${item.text}" color=${item.color} opacity=${item.opacity}`)
        }
      } else {
        console.log(`${route}: No low-alpha text colors found - PASS`)
      }
    }
  })
})
