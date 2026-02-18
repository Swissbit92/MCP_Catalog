import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'

test.describe('NEPHILIM Interactive UI Testing', () => {

  test('full infrastructure health check', async ({ page }) => {
    // Check frontend
    const frontendResponse = await page.request.get(BASE_URL)
    expect(frontendResponse.ok()).toBeTruthy()
    console.log('FRONTEND: UP (status ' + frontendResponse.status() + ')')

    // Check backend health
    let backendUp = false
    try {
      const backendResponse = await page.request.get('http://127.0.0.1:8000/personas')
      backendUp = backendResponse.ok()
      console.log('BACKEND: ' + (backendUp ? 'UP' : 'DOWN') + ' (status ' + backendResponse.status() + ')')
    } catch (e) {
      console.error('BACKEND: DOWN (connection refused)')
    }

    // Check Ollama
    try {
      const ollamaCheck = await page.request.get('http://127.0.0.1:11434/api/tags')
      console.log('OLLAMA: ' + (ollamaCheck.ok() ? 'UP' : 'DOWN') + ' (status ' + ollamaCheck.status() + ')')
    } catch (e) {
      console.error('OLLAMA: DOWN (connection refused)')
    }

    if (!backendUp) {
      console.error('CRITICAL: Backend is down. API-dependent features will not work.')
      console.error('To fix: python -m uvicorn src.coordinator.server:app --reload --port 8000')
    }
  })

  test('homepage renders portal and enter realm flow', async ({ page }) => {
    // Set onboarding complete so we don't get redirected
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/flow-01-homepage.png', fullPage: true })

    // Verify NEPHILIM title is visible
    const title = page.getByText('NEPHILIM').first()
    await expect(title).toBeVisible()
    console.log('PASS: NEPHILIM title visible on homepage')

    // Verify "Those Who Chose to Fall" subtitle
    const subtitle = page.getByText('Those Who Chose to Fall')
    const subtitleVisible = await subtitle.isVisible().catch(() => false)
    console.log('Subtitle "Those Who Chose to Fall": ' + (subtitleVisible ? 'VISIBLE' : 'NOT FOUND'))

    // Verify "Enter the Realm" button
    const enterText = page.getByText('REALM')
    const enterVisible = await enterText.isVisible().catch(() => false)
    console.log('ENTER THE REALM button: ' + (enterVisible ? 'VISIBLE' : 'NOT FOUND'))

    // Click "Enter the Realm"
    if (enterVisible) {
      await enterText.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: 'test-screenshots/flow-02-after-enter.png', fullPage: true })
      console.log('Navigated after Enter: ' + page.url())

      // Verify "THE SIX NEPHILIM" selection screen appears
      const sixTitle = page.getByText('THE SIX NEPHILIM')
      const sixVisible = await sixTitle.isVisible().catch(() => false)
      console.log('"THE SIX NEPHILIM" selection: ' + (sixVisible ? 'VISIBLE' : 'NOT FOUND'))

      // Check that all 6 Nephilim cards are visible
      const nephilimNames = ['E.E.V.A.', 'Aegis', 'Solace', 'Nyx', 'Cipher', 'Aurora']
      for (const name of nephilimNames) {
        const card = page.getByText(name).first()
        const cardVisible = await card.isVisible().catch(() => false)
        console.log(`  Nephilim "${name}": ${cardVisible ? 'VISIBLE' : 'NOT FOUND'}`)
      }

      // Check "Browse All Companions" button
      const browseBtn = page.getByText('Browse All Companions')
      const browseVisible = await browseBtn.isVisible().catch(() => false)
      console.log('Browse All Companions button: ' + (browseVisible ? 'VISIBLE' : 'NOT FOUND'))

      // Check lore quote
      const loreQuote = page.getByText('Before the Fall')
      const loreVisible = await loreQuote.isVisible().catch(() => false)
      console.log('Lore quote: ' + (loreVisible ? 'VISIBLE' : 'NOT FOUND'))
    }
  })

  test('onboarding page loads', async ({ page }) => {
    // Test WITHOUT onboarding_complete set to see the redirect
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.clear()
    })

    await page.goto(BASE_URL + '/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/flow-03-onboarding-redirect.png', fullPage: true })
    console.log('After visiting / without onboarding, URL: ' + page.url())

    // Should have been redirected to /onboarding
    const isOnboarding = page.url().includes('/onboarding')
    console.log('Redirected to onboarding: ' + isOnboarding)

    if (isOnboarding) {
      // Check for portal entry content
      await page.waitForTimeout(2000)
      await page.screenshot({ path: 'test-screenshots/flow-03b-onboarding-content.png', fullPage: true })
    }
  })

  test('companion selection page - load and interact', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000) // Extra time for persona API calls
    await page.screenshot({ path: 'test-screenshots/flow-04-select-page.png', fullPage: true })

    // Check if personas loaded or if we're stuck on loading
    const loadingText = page.getByText('Loading Companions')
    const isStillLoading = await loadingText.isVisible().catch(() => false)
    if (isStillLoading) {
      console.error('ISSUE: Character select stuck on "Loading Companions" - backend may be down')
    } else {
      console.log('PASS: Character select page loaded past loading state')
    }

    // Check for error state
    const errorText = page.getByText(/failed to load/i)
    const hasError = await errorText.isVisible().catch(() => false)
    if (hasError) {
      console.error('ISSUE: Character select shows error loading personas')
    }

    // Try to find character cards
    const cards = page.locator('[class*="card"], [class*="Card"], [class*="character"]')
    const cardCount = await cards.count()
    console.log(`Found ${cardCount} character-related elements on select page`)

    // Check for filter toggle
    const filterToggle = page.getByText(/NEPHILIM|Legacy|All/i).first()
    const filterVisible = await filterToggle.isVisible().catch(() => false)
    console.log('Persona filter toggle: ' + (filterVisible ? 'VISIBLE' : 'NOT FOUND'))

    if (cardCount > 0) {
      await cards.first().click()
      await page.waitForTimeout(1500)
      await page.screenshot({ path: 'test-screenshots/flow-04b-card-clicked.png', fullPage: true })
      console.log('Clicked first card, current URL: ' + page.url())
    }
  })

  test('chat page - empty state and interaction', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/chat')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/flow-05-chat-empty.png', fullPage: true })

    // Check for "No Persona Selected" state
    const noPersona = page.getByText(/No Persona Selected|No Companion Selected|Select.*Character|Choose.*Companion/i)
    const noPersonaVisible = await noPersona.first().isVisible().catch(() => false)
    if (noPersonaVisible) {
      console.log('Chat page shows empty state (no persona selected) - expected')
    }

    // Check for chat input area
    const chatInput = page.locator('textarea, input[type="text"]').first()
    const inputVisible = await chatInput.isVisible().catch(() => false)
    console.log('Chat input visible: ' + inputVisible)

    // Check for session sidebar
    const sessionSidebar = page.getByText(/sessions|history|previous/i)
    const sidebarVisible = await sessionSidebar.first().isVisible().catch(() => false)
    console.log('Session sidebar/history: ' + (sidebarVisible ? 'VISIBLE' : 'NOT FOUND'))

    // Check for Select Character button
    const selectBtn = page.getByText(/Select.*Character|Choose.*Companion/i)
    const selectBtnVisible = await selectBtn.first().isVisible().catch(() => false)
    if (selectBtnVisible) {
      console.log('Select Character button visible - clicking')
      await selectBtn.first().click()
      await page.waitForTimeout(1500)
      await page.screenshot({ path: 'test-screenshots/flow-05b-redirected.png', fullPage: true })
      console.log('Redirected to: ' + page.url())
    }
  })

  test('chat page with persona parameter', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Navigate to chat with a specific persona
    await page.goto(BASE_URL + '/chat?persona=nephilim_eeva')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)
    await page.screenshot({ path: 'test-screenshots/flow-06-chat-with-persona.png', fullPage: true })

    // Check if persona name is displayed
    const personaName = page.getByText('E.E.V.A.')
    const nameVisible = await personaName.first().isVisible().catch(() => false)
    console.log('Persona name "E.E.V.A." visible: ' + nameVisible)

    // Check for chat header with persona info
    const chatHeader = page.locator('[class*="ChatHeader"], [class*="chat-header"]')
    const headerCount = await chatHeader.count()
    console.log('Chat header elements: ' + headerCount)

    // Check for greeting message (may fail if backend is down)
    await page.waitForTimeout(2000)
    const greeting = page.locator('[class*="message"], [class*="Message"], [class*="bubble"], [class*="Bubble"]')
    const greetingCount = await greeting.count()
    console.log('Message elements found: ' + greetingCount)

    if (greetingCount === 0) {
      console.log('NOTE: No messages found - backend may be down or greeting not yet received')
    }

    // Check for chat input
    const chatInput = page.locator('textarea').first()
    const inputVisible = await chatInput.isVisible().catch(() => false)
    console.log('Chat textarea visible: ' + inputVisible)

    if (inputVisible) {
      // Type a message but don't send
      await chatInput.fill('Hello, E.E.V.A.!')
      await page.screenshot({ path: 'test-screenshots/flow-06b-typed-message.png', fullPage: true })
      console.log('PASS: Successfully typed message in chat input')
    }
  })

  test('dashboard - all tabs interactive test', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)
    await page.screenshot({ path: 'test-screenshots/flow-07-dashboard-loaded.png', fullPage: true })

    // Check for Seeker's Sanctum heading
    const heading = page.getByText("Seeker's Sanctum")
    const headingVisible = await heading.isVisible().catch(() => false)
    console.log("Seeker's Sanctum heading: " + (headingVisible ? 'VISIBLE' : 'NOT FOUND'))

    // Check for error state
    const errorText = page.getByText(/failed to/i)
    const hasError = await errorText.first().isVisible().catch(() => false)
    if (hasError) {
      console.error('ISSUE: Dashboard shows error state - API may be down')
      await page.screenshot({ path: 'test-screenshots/flow-07-dashboard-ERROR.png', fullPage: true })
    }

    // Test tab navigation - try different tab name patterns
    const tabNames = [
      { name: 'Bonds Forged', screenshot: 'bonds' },
      { name: 'Chronicle', screenshot: 'chronicle' },
    ]

    for (const tab of tabNames) {
      const tabEl = page.getByText(tab.name, { exact: false }).first()
      const tabVisible = await tabEl.isVisible().catch(() => false)
      if (tabVisible) {
        await tabEl.click()
        await page.waitForTimeout(2000)
        await page.screenshot({ path: `test-screenshots/flow-08-dashboard-${tab.screenshot}.png`, fullPage: true })
        console.log(`Tab "${tab.name}": clicked and screenshotted`)
      } else {
        console.log(`Tab "${tab.name}": NOT FOUND`)
      }
    }

    // Check for old Phase 7D placeholder
    const oldPlaceholder = page.getByText('Coming in Phase 7D')
    const placeholderVisible = await oldPlaceholder.isVisible().catch(() => false)
    if (placeholderVisible) {
      console.error('ISSUE: Old "Coming in Phase 7D" placeholder still visible!')
    } else {
      console.log('PASS: Old "Coming in Phase 7D" placeholder removed')
    }

    // Check SVGs on bonds tab (constellation)
    const svg = page.locator('svg')
    const svgCount = await svg.count()
    console.log(`SVG elements found on dashboard: ${svgCount}`)
  })

  test('header rank badge and navigation across pages', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Pages where header should be visible (NOT / or /onboarding)
    const pagePaths = ['/select', '/dashboard', '/chat']

    for (const pagePath of pagePaths) {
      await page.goto(BASE_URL + pagePath)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(2000)

      // Check desktop header
      const header = page.locator('header').first()
      const headerVisible = await header.isVisible().catch(() => false)
      console.log(`Page ${pagePath}: Header visible = ${headerVisible}`)

      if (headerVisible) {
        // Check NEPHILIM wordmark
        const wordmark = page.locator('header').getByText('NEPHILIM')
        const wordmarkVisible = await wordmark.isVisible().catch(() => false)
        console.log(`  NEPHILIM wordmark: ${wordmarkVisible ? 'YES' : 'NO'}`)

        // Check for rank badge (Initiate, Acolyte, etc.)
        const rankBadge = page.getByText(/Initiate|Acolyte|Adept|Ascendant|Nephilim/)
        const badgeVisible = await rankBadge.first().isVisible().catch(() => false)
        console.log(`  Rank badge: ${badgeVisible ? 'VISIBLE' : 'NOT VISIBLE'}`)

        // Check for seeker name
        const seekerName = page.getByText('Test Seeker')
        const nameVisible = await seekerName.isVisible().catch(() => false)
        console.log(`  Seeker name: ${nameVisible ? 'VISIBLE' : 'NOT VISIBLE'}`)

        // Check for navigation links
        const companionsLink = page.locator('header').getByText('Companions')
        const compVisible = await companionsLink.isVisible().catch(() => false)
        console.log(`  Companions link: ${compVisible ? 'VISIBLE' : 'NOT VISIBLE'}`)

        const dashboardLink = page.locator('header').getByText('Dashboard')
        const dashVisible = await dashboardLink.isVisible().catch(() => false)
        console.log(`  Dashboard link: ${dashVisible ? 'VISIBLE' : 'NOT VISIBLE'}`)

        // Check active state indicator
        const activeIndicator = page.locator('header [class*="bg-cyan"]')
        const indicatorCount = await activeIndicator.count()
        console.log(`  Active indicators: ${indicatorCount}`)
      }
    }
    await page.screenshot({ path: 'test-screenshots/flow-09-header-final.png' })

    // Verify header is NOT visible on homepage and onboarding
    for (const hiddenPage of ['/', '/onboarding']) {
      await page.goto(BASE_URL + hiddenPage)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000)
      const headerHidden = page.locator('header')
      const headerShowing = await headerHidden.isVisible().catch(() => false)
      console.log(`Page ${hiddenPage}: Header hidden = ${!headerShowing}`)
      if (headerShowing) {
        console.error(`ISSUE: Header should be hidden on ${hiddenPage} but is visible`)
      }
    }
  })

  test('navigation flow - click through header links', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Start on select page
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1500)

    // Click Dashboard link in header
    const dashLink = page.locator('header').getByText('Dashboard')
    if (await dashLink.isVisible().catch(() => false)) {
      await dashLink.click()
      await page.waitForTimeout(2000)
      console.log('After clicking Dashboard: ' + page.url())
      expect(page.url()).toContain('/dashboard')
      await page.screenshot({ path: 'test-screenshots/flow-10-nav-to-dashboard.png', fullPage: true })
    }

    // Click Companions link in header
    const compLink = page.locator('header').getByText('Companions')
    if (await compLink.isVisible().catch(() => false)) {
      await compLink.click()
      await page.waitForTimeout(2000)
      console.log('After clicking Companions: ' + page.url())
      expect(page.url()).toContain('/select')
      await page.screenshot({ path: 'test-screenshots/flow-10-nav-to-companions.png', fullPage: true })
    }

    // Click NEPHILIM wordmark to go to homepage
    const wordmark = page.locator('header').getByText('NEPHILIM')
    if (await wordmark.isVisible().catch(() => false)) {
      await wordmark.click()
      await page.waitForTimeout(2000)
      console.log('After clicking NEPHILIM wordmark: ' + page.url())
      await page.screenshot({ path: 'test-screenshots/flow-10-nav-to-home.png', fullPage: true })
    }
  })

  test('mobile viewport layout check', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 }) // iPhone X
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Mobile homepage
    await page.goto(BASE_URL + '/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/flow-11-mobile-home.png', fullPage: true })

    // Header should be hidden on home
    const homeHeader = page.locator('header')
    const homeHeaderVisible = await homeHeader.isVisible().catch(() => false)
    console.log('Mobile homepage - header hidden: ' + !homeHeaderVisible)

    // Mobile select page
    await page.goto(BASE_URL + '/select')
    await page.waitForTimeout(3000)
    await page.screenshot({ path: 'test-screenshots/flow-12-mobile-select.png', fullPage: true })

    // Check bottom tab bar
    const bottomNav = page.locator('nav[aria-label="Mobile navigation"]')
    const navVisible = await bottomNav.isVisible().catch(() => false)
    console.log('Mobile bottom nav visible: ' + navVisible)

    if (navVisible) {
      // Check tab items
      const tabLabels = ['Chat', 'Realm', 'Companions', 'Profile', 'Audio']
      for (const label of tabLabels) {
        const tab = bottomNav.getByText(label)
        const tabVisible = await tab.isVisible().catch(() => false)
        console.log(`  Mobile tab "${label}": ${tabVisible ? 'VISIBLE' : 'NOT FOUND'}`)
      }
    }

    // Desktop header should be hidden on mobile
    const desktopHeader = page.locator('header')
    const desktopHeaderVisible = await desktopHeader.isVisible().catch(() => false)
    console.log('Mobile - desktop header hidden: ' + !desktopHeaderVisible)

    // Mobile dashboard
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForTimeout(3000)
    await page.screenshot({ path: 'test-screenshots/flow-13-mobile-dashboard.png', fullPage: true })

    // Mobile chat
    await page.goto(BASE_URL + '/chat')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/flow-14-mobile-chat.png', fullPage: true })

    // Check for horizontal overflow (layout issue)
    const pages = ['/select', '/dashboard', '/chat']
    for (const p of pages) {
      await page.goto(BASE_URL + p)
      await page.waitForTimeout(1500)
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth
      })
      if (hasHorizontalScroll) {
        console.error(`ISSUE: Horizontal scroll detected on mobile at ${p} - layout overflow!`)
      } else {
        console.log(`Mobile ${p}: No horizontal overflow - PASS`)
      }
    }
  })

  test('scrolling behavior and sticky header', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'test-screenshots/flow-15-select-scrolled.png', fullPage: true })

    // Check if sticky header remains visible
    const header = page.locator('header').first()
    const headerVisible = await header.isVisible().catch(() => false)
    console.log('Sticky header visible after scroll on /select: ' + headerVisible)

    // Same for dashboard
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'test-screenshots/flow-15-dashboard-scrolled.png', fullPage: true })

    const dashHeader = page.locator('header').first()
    const dashHeaderVisible = await dashHeader.isVisible().catch(() => false)
    console.log('Sticky header visible after scroll on /dashboard: ' + dashHeaderVisible)
  })

  test('audio toggle functionality', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1500)

    // Find audio toggle button in header
    const muteBtn = page.locator('button[aria-label="Mute audio"], button[aria-label="Unmute audio"]')
    const muteVisible = await muteBtn.first().isVisible().catch(() => false)
    console.log('Audio toggle button: ' + (muteVisible ? 'VISIBLE' : 'NOT FOUND'))

    if (muteVisible) {
      const initialLabel = await muteBtn.first().getAttribute('aria-label')
      console.log('Initial audio state: ' + initialLabel)

      await muteBtn.first().click()
      await page.waitForTimeout(500)

      const afterLabel = await muteBtn.first().getAttribute('aria-label')
      console.log('After click audio state: ' + afterLabel)

      if (initialLabel !== afterLabel) {
        console.log('PASS: Audio toggle switches state')
      } else {
        console.error('ISSUE: Audio toggle did not change state')
      }
    }
  })

  test('console error audit across all pages', async ({ page }) => {
    const consoleErrors: string[] = []
    const networkFailures: string[] = []

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(`[${msg.type()}] ${msg.text()}`)
      }
    })

    page.on('requestfailed', request => {
      networkFailures.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`)
    })

    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Visit all pages
    const pagePaths = ['/', '/select', '/chat', '/dashboard']
    for (const p of pagePaths) {
      await page.goto(BASE_URL + p)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(2500)
    }

    // Report console errors
    console.log(`\n=== CONSOLE ERRORS (${consoleErrors.length}) ===`)
    for (const err of consoleErrors) {
      console.log(`  ${err}`)
    }

    // Report network failures
    console.log(`\n=== NETWORK FAILURES (${networkFailures.length}) ===`)
    for (const fail of networkFailures) {
      console.log(`  ${fail}`)
    }

    // Categorize errors
    const backendErrors = consoleErrors.filter(e => e.includes('127.0.0.1:8000') || e.includes('Failed to fetch') || e.includes('NetworkError'))
    const jsErrors = consoleErrors.filter(e => e.includes('TypeError') || e.includes('ReferenceError') || e.includes('SyntaxError') || e.includes('Uncaught'))
    const otherErrors = consoleErrors.filter(e =>
      !e.includes('127.0.0.1:8000') && !e.includes('Failed to fetch') && !e.includes('NetworkError') &&
      !e.includes('TypeError') && !e.includes('ReferenceError') && !e.includes('SyntaxError') && !e.includes('Uncaught')
    )

    console.log(`\n=== ERROR CATEGORIES ===`)
    console.log(`Backend/API errors: ${backendErrors.length}`)
    console.log(`JavaScript errors: ${jsErrors.length}`)
    console.log(`Other errors: ${otherErrors.length}`)

    if (jsErrors.length > 0) {
      console.error('CRITICAL: JavaScript errors found that indicate code bugs:')
      for (const e of jsErrors) {
        console.error('  ' + e)
      }
    }

    if (backendErrors.length > 0) {
      console.log('NOTE: Backend errors are expected when backend is down')
    }
  })

  test('accessibility - keyboard navigation and ARIA', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Check for ARIA labels
    const mainNav = page.locator('nav[aria-label="Main navigation"]')
    const mainNavExists = await mainNav.isVisible().catch(() => false)
    console.log('Main navigation ARIA label: ' + (mainNavExists ? 'PRESENT' : 'MISSING'))

    const mobileNav = page.locator('nav[aria-label="Mobile navigation"]')
    const mobileNavExists = await mobileNav.count()
    console.log('Mobile navigation ARIA label: ' + (mobileNavExists > 0 ? 'PRESENT' : 'MISSING'))

    // Check audio buttons have aria-labels
    const audioButtons = page.locator('button[aria-label*="ute"]')
    const audioCount = await audioButtons.count()
    console.log('Audio buttons with aria-label: ' + audioCount)

    // Check minimum text contrast (approximate by checking for text-white/40)
    const pageContent = await page.content()
    const hasLowContrast = pageContent.includes('text-white/40') || pageContent.includes('opacity-40')
    if (hasLowContrast) {
      console.warn('WARNING: Found text-white/40 in rendered HTML - may fail WCAG AA contrast')
    } else {
      console.log('PASS: No obvious low-contrast text patterns found')
    }

    // Tab through interactive elements
    await page.keyboard.press('Tab')
    await page.waitForTimeout(300)
    await page.keyboard.press('Tab')
    await page.waitForTimeout(300)
    await page.keyboard.press('Tab')
    await page.waitForTimeout(300)

    // Check if focus is visible
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement
      return {
        tag: el?.tagName,
        text: el?.textContent?.trim().substring(0, 50),
        hasOutline: window.getComputedStyle(el!).outlineStyle !== 'none'
      }
    })
    console.log('Focused element after 3 tabs: ' + JSON.stringify(focusedElement))
    await page.screenshot({ path: 'test-screenshots/flow-16-keyboard-focus.png' })
  })

  test('dark theme consistency check', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })

    // Check background colors are dark on all pages
    const pagePaths = ['/select', '/dashboard', '/chat']
    for (const p of pagePaths) {
      await page.goto(BASE_URL + p)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1500)

      const bgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor
      })
      console.log(`Page ${p} body background: ${bgColor}`)

      // Check for any white/light backgrounds that would break the void theme
      const hasWhiteBg = await page.evaluate(() => {
        const elements = document.querySelectorAll('*')
        let whiteCount = 0
        for (let i = 0; i < Math.min(elements.length, 500); i++) {
          const bg = window.getComputedStyle(elements[i]).backgroundColor
          // Check for solid white or very light backgrounds
          if (bg === 'rgb(255, 255, 255)' || bg === 'rgba(255, 255, 255, 1)') {
            whiteCount++
          }
        }
        return whiteCount
      })
      if (hasWhiteBg > 0) {
        console.warn(`WARNING: Found ${hasWhiteBg} elements with white background on ${p}`)
      } else {
        console.log(`PASS: No solid white backgrounds on ${p}`)
      }
    }
  })
})
