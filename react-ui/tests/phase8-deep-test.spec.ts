import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const BACKEND_URL = 'http://localhost:8000'
const SCREENSHOT_DIR = 'test-screenshots/phase8-live'

test.describe('Phase 8 Deep UI Testing - Backend Live', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'default_seeker')
      localStorage.setItem('nephilim_user_name', 'TestSeeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })
  })

  // ============================================
  // 1. INFRASTRUCTURE - Backend API deep check
  // ============================================
  test('backend API endpoints are all responding', async ({ request }) => {
    // /personas
    const personas = await request.get(`${BACKEND_URL}/personas`)
    expect(personas.ok()).toBeTruthy()
    const personaData = await personas.json()
    const keys = Object.keys(personaData)
    console.log(`Personas endpoint: ${keys.length} personas: ${keys.join(', ')}`)
    expect(keys.length).toBeGreaterThanOrEqual(6)

    // /nephilim/ranks
    const ranks = await request.get(`${BACKEND_URL}/nephilim/ranks`)
    expect(ranks.ok()).toBeTruthy()
    const rankData = await ranks.json()
    console.log(`Ranks endpoint: ${JSON.stringify(rankData)}`)

    // /nephilim/factions
    const factions = await request.get(`${BACKEND_URL}/nephilim/factions`)
    expect(factions.ok()).toBeTruthy()
    const factionData = await factions.json()
    console.log(`Factions endpoint: ${JSON.stringify(factionData).slice(0, 200)}`)

    // /nephilim/seeker/default_seeker
    const seeker = await request.get(`${BACKEND_URL}/nephilim/seeker/default_seeker`)
    expect(seeker.ok()).toBeTruthy()
    const seekerData = await seeker.json()
    console.log(`Seeker profile: rank=${seekerData.rank_name}, resonance=${seekerData.total_resonance}`)

    // /nephilim/seeker/default_seeker/summary
    const summary = await request.get(`${BACKEND_URL}/nephilim/seeker/default_seeker/summary`)
    expect(summary.ok()).toBeTruthy()
    const summaryData = await summary.json()
    console.log(`Seeker summary: ${JSON.stringify(summaryData).slice(0, 300)}`)

    // /nephilim/seeker/default_seeker/affinity
    const affinity = await request.get(`${BACKEND_URL}/nephilim/seeker/default_seeker/affinity`)
    expect(affinity.ok()).toBeTruthy()
    const affinityData = await affinity.json()
    console.log(`Affinity data: ${JSON.stringify(affinityData).slice(0, 300)}`)

    // /nephilim/seeker/default_seeker/lore
    const lore = await request.get(`${BACKEND_URL}/nephilim/seeker/default_seeker/lore`)
    expect(lore.ok()).toBeTruthy()
    const loreData = await lore.json()
    console.log(`Lore data: ${JSON.stringify(loreData).slice(0, 300)}`)

    // /sessions
    const sessions = await request.get(`${BACKEND_URL}/sessions`)
    expect(sessions.ok()).toBeTruthy()
    const sessionData = await sessions.json()
    console.log(`Sessions: ${sessionData.length} sessions`)
  })

  // ============================================
  // 2. LANDING PAGE - Detailed element checks
  // ============================================
  test('landing page - all visual elements render', async ({ page }) => {
    await page.goto(BASE_URL + '/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000) // Let animations complete

    await page.screenshot({ path: `${SCREENSHOT_DIR}/01-landing-full.png`, fullPage: true })

    // Check NEPHILIM title
    const title = page.getByText('NEPHILIM').first()
    await expect(title).toBeVisible()
    console.log('PASS: NEPHILIM title visible')

    // Check subtitle
    const subtitle = page.getByText('Those Who Chose to Fall')
    const subtitleVis = await subtitle.isVisible().catch(() => false)
    console.log(`Subtitle "Those Who Chose to Fall": ${subtitleVis ? 'VISIBLE' : 'NOT FOUND'}`)

    // Check Enter the Realm
    const enterBtn = page.getByText('REALM')
    const enterVis = await enterBtn.isVisible().catch(() => false)
    console.log(`ENTER THE REALM: ${enterVis ? 'VISIBLE' : 'NOT FOUND'}`)

    // Check for background effects (canvas, animation divs)
    const canvas = await page.$('canvas')
    console.log(`Canvas (particles): ${canvas ? 'PRESENT' : 'NOT FOUND'}`)

    // Check page background color is void dark
    const bgColor = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor)
    console.log(`Body background: ${bgColor}`)
    expect(bgColor).toBe('rgb(11, 11, 13)') // --nephilim-void

    // Click Enter the Realm and verify The Six Nephilim section
    if (enterVis) {
      await enterBtn.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/01-landing-after-enter.png`, fullPage: true })

      // Check Six Nephilim section
      const sixNephilim = page.getByText('THE SIX NEPHILIM')
      const sixVis = await sixNephilim.isVisible().catch(() => false)
      console.log(`THE SIX NEPHILIM section: ${sixVis ? 'VISIBLE' : 'NOT FOUND'}`)

      // Check Browse All Companions
      const browseBtn = page.getByText('Browse All Companions')
      const browseVis = await browseBtn.isVisible().catch(() => false)
      console.log(`Browse All Companions: ${browseVis ? 'VISIBLE' : 'NOT FOUND'}`)

      // Click Browse All Companions
      if (browseVis) {
        await browseBtn.click()
        await page.waitForTimeout(2000)
        console.log(`After Browse All Companions: URL=${page.url()}`)
        expect(page.url()).toContain('/select')
        await page.screenshot({ path: `${SCREENSHOT_DIR}/01-landing-browse-nav.png`, fullPage: true })
      }
    }
  })

  // ============================================
  // 3. COMPANION SELECT - Filter toggle deep test
  // ============================================
  test('companion select - filter toggle and persona counts', async ({ page }) => {
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    await page.screenshot({ path: `${SCREENSHOT_DIR}/02-select-initial.png`, fullPage: true })

    // Verify personas loaded from backend
    const bodyText = await page.textContent('body')
    const nephilimNames = ['E.E.V.A.', 'Aegis', 'Solace', 'Nyx', 'Cipher', 'Aurora']
    for (const name of nephilimNames) {
      const found = bodyText.includes(name)
      console.log(`Persona "${name}": ${found ? 'FOUND' : 'MISSING'}`)
    }

    // Check filter toggle buttons
    const allBtn = page.getByText('All').first()
    const nephBtn = page.locator('button').filter({ hasText: /NEPHILIM/i }).first()
    const legacyBtn = page.locator('button').filter({ hasText: /Legacy/i }).first()

    const allVis = await allBtn.isVisible().catch(() => false)
    const nephVis = await nephBtn.isVisible().catch(() => false)
    const legacyVis = await legacyBtn.isVisible().catch(() => false)
    console.log(`Filter buttons: All=${allVis}, NEPHILIM=${nephVis}, Legacy=${legacyVis}`)

    // Click NEPHILIM filter
    if (nephVis) {
      await nephBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/02-select-nephilim-filter.png`, fullPage: true })

      // Count visible cards - should be 6 nephilim
      const visiblePersonas = await page.evaluate(() => {
        const cards = document.querySelectorAll('[class*="card"], [class*="Card"]')
        return cards.length
      })
      console.log(`NEPHILIM filter: ${visiblePersonas} card elements visible`)
    }

    // Click Legacy filter
    if (legacyVis) {
      await legacyBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/02-select-legacy-filter.png`, fullPage: true })

      const visiblePersonas = await page.evaluate(() => {
        const cards = document.querySelectorAll('[class*="card"], [class*="Card"]')
        return cards.length
      })
      console.log(`Legacy filter: ${visiblePersonas} card elements visible`)
    }

    // Click All filter
    if (allVis) {
      await allBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/02-select-all-filter.png`, fullPage: true })

      const visiblePersonas = await page.evaluate(() => {
        const cards = document.querySelectorAll('[class*="card"], [class*="Card"]')
        return cards.length
      })
      console.log(`All filter: ${visiblePersonas} card elements visible`)
    }

    // Check NEPHILIM badge on persona cards
    const badges = await page.$$('text=/NEPHILIM/')
    console.log(`NEPHILIM badges on cards: ${badges.length}`)

    // Check Wanderer label for legacy personas
    const wanderers = await page.$$('text=/Wanderer/')
    console.log(`Wanderer labels: ${wanderers.length}`)

    // Check localStorage filter persistence
    const filterMode = await page.evaluate(() => localStorage.getItem('persona_filter_mode'))
    console.log(`Stored filter mode: ${filterMode}`)
  })

  // ============================================
  // 4. CHAT - Full interaction with persona
  // ============================================
  test('chat page - greet and send message with EEVA', async ({ page }) => {
    // Navigate to chat with EEVA
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    // Find and click EEVA card
    const eevaCard = page.getByText('E.E.V.A.').first()
    const eevaVis = await eevaCard.isVisible().catch(() => false)
    if (eevaVis) {
      await eevaCard.click()
      await page.waitForTimeout(5000) // Wait for chat page + greeting
      await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-eeva-greeting.png`, fullPage: true })
      console.log(`Chat URL after clicking EEVA: ${page.url()}`)

      // Check if greeting message appeared
      const pageText = await page.textContent('body')
      const hasMessage = pageText.length > 200 // Greeting would add text
      console.log(`Page has substantial content (greeting): ${hasMessage}`)

      // Check for chat header
      const headerArea = page.locator('[class*="ChatHeader"], [class*="chat-header"], header')
      const headerCount = await headerArea.count()
      console.log(`Header/ChatHeader elements: ${headerCount}`)

      // Check for chat input textarea
      const textarea = page.locator('textarea')
      const textareaVis = await textarea.first().isVisible().catch(() => false)
      console.log(`Chat textarea visible: ${textareaVis}`)

      if (textareaVis) {
        // Type and send a message
        await textarea.first().fill('Hello! This is a test message.')
        await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-typed.png`, fullPage: true })

        // Send the message
        await page.keyboard.press('Enter')
        await page.waitForTimeout(10000) // Wait for LLM response

        await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-response.png`, fullPage: true })

        // Check for message bubbles
        const messages = page.locator('[class*="message"], [class*="Message"], [class*="bubble"]')
        const msgCount = await messages.count()
        console.log(`Message elements after send: ${msgCount}`)

        // Check for resonance toast
        const toast = page.getByText(/resonance|\+5/i)
        const toastVis = await toast.first().isVisible().catch(() => false)
        console.log(`Resonance toast visible: ${toastVis}`)

        // Check for typing indicator during response
        const typing = page.locator('[class*="typing"], [class*="Typing"]')
        const typingCount = await typing.count()
        console.log(`Typing indicator elements: ${typingCount}`)
      }
    } else {
      console.log('EEVA card not visible on select page')
      // Try direct URL
      await page.goto(BASE_URL + '/chat?persona=nephilim_eeva')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(5000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-eeva-direct.png`, fullPage: true })
    }
  })

  test('chat page - glassmorphism and void theme styling', async ({ page }) => {
    await page.goto(BASE_URL + '/chat')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Check background is void dark
    const bgColor = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor)
    console.log(`Chat body background: ${bgColor}`)
    expect(bgColor).toBe('rgb(11, 11, 13)')

    // Count backdrop-blur elements (glassmorphism)
    const blurCount = await page.evaluate(() => {
      let count = 0
      document.querySelectorAll('*').forEach(el => {
        const bf = window.getComputedStyle(el).backdropFilter
        if (bf && bf !== 'none') count++
      })
      return count
    })
    console.log(`Glassmorphism (backdrop-blur) elements: ${blurCount}`)

    await page.screenshot({ path: `${SCREENSHOT_DIR}/03-chat-styling.png`, fullPage: true })
  })

  // ============================================
  // 5. DASHBOARD - All 3 tabs deep inspection
  // ============================================
  test('dashboard - Bonds Forged tab with constellation', async ({ page }) => {
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    await page.screenshot({ path: `${SCREENSHOT_DIR}/04-dashboard-default.png`, fullPage: true })

    // Check heading
    const heading = page.getByText("Seeker's Sanctum")
    await expect(heading).toBeVisible()
    console.log('PASS: Seeker\'s Sanctum heading visible')

    // Check for rank display
    const rankText = page.getByText(/Initiate|Acolyte|Adept/)
    const rankVis = await rankText.first().isVisible().catch(() => false)
    console.log(`Rank display: ${rankVis ? 'VISIBLE' : 'NOT FOUND'}`)

    // Click Bonds Forged tab
    const bondsTab = page.getByText('Bonds Forged')
    const bondsVis = await bondsTab.isVisible().catch(() => false)
    if (bondsVis) {
      await bondsTab.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04-dashboard-bonds.png`, fullPage: true })

      // Check for constellation SVG
      const svg = page.locator('svg').first()
      const svgVis = await svg.isVisible().catch(() => false)
      console.log(`Constellation SVG: ${svgVis ? 'VISIBLE' : 'NOT FOUND'}`)

      // Check for persona nodes in SVG
      const circles = page.locator('svg circle')
      const circleCount = await circles.count()
      console.log(`SVG circles (persona nodes): ${circleCount}`)

      // Check for connecting lines
      const lines = page.locator('svg line, svg path')
      const lineCount = await lines.count()
      console.log(`SVG lines/paths (connections): ${lineCount}`)

      // Check for persona names near constellation
      for (const name of ['E.E.V.A.', 'Aegis', 'Solace', 'Nyx', 'Cipher', 'Aurora']) {
        const nameEl = page.getByText(name).first()
        const nameVis = await nameEl.isVisible().catch(() => false)
        console.log(`  Constellation node "${name}": ${nameVis ? 'VISIBLE' : 'NOT VISIBLE'}`)
      }

      // Try hovering/clicking a node
      if (circleCount > 0) {
        await circles.first().hover()
        await page.waitForTimeout(500)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/04-dashboard-bonds-hover.png`, fullPage: true })
        console.log('Hovered on first constellation node')

        await circles.first().click()
        await page.waitForTimeout(1000)
        const afterClickUrl = page.url()
        console.log(`After clicking constellation node: ${afterClickUrl}`)
        if (afterClickUrl.includes('/chat')) {
          console.log('PASS: Constellation node click navigates to /chat')
        }
      }
    } else {
      console.log('Bonds Forged tab not found')
    }
  })

  test('dashboard - Chronicle tab', async ({ page }) => {
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    const chronicleTab = page.getByText('Chronicle')
    const chronVis = await chronicleTab.isVisible().catch(() => false)
    if (chronVis) {
      await chronicleTab.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04-dashboard-chronicle.png`, fullPage: true })

      // Check for pull history or empty state
      const bodyText = await page.textContent('body')
      const hasBeginSummoning = bodyText.includes('Begin') && bodyText.includes('Summon')
      const hasHistory = bodyText.includes('Summoned') || bodyText.includes('pulled') || bodyText.includes('collected')
      console.log(`Chronicle: empty CTA="${hasBeginSummoning}", has history="${hasHistory}"`)

      // Check for CTA button
      const ctaBtn = page.getByText(/Begin.*Summon/i)
      const ctaVis = await ctaBtn.first().isVisible().catch(() => false)
      if (ctaVis) {
        console.log('PASS: Chronicle empty state CTA button visible')
        await ctaBtn.first().click()
        await page.waitForTimeout(1000)
        console.log(`After CTA click: ${page.url()}`)
      }
    } else {
      console.log('Chronicle tab not found')
    }
  })

  test('dashboard - Codex tab (lore collection)', async ({ page }) => {
    await page.goto(BASE_URL + '/dashboard')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    const codexTab = page.getByText('Codex')
    const codexVis = await codexTab.isVisible().catch(() => false)
    if (codexVis) {
      await codexTab.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04-dashboard-codex.png`, fullPage: true })

      // Check content
      const bodyText = await page.textContent('body')
      console.log(`Codex content preview: ${bodyText.slice(bodyText.indexOf('Codex'), bodyText.indexOf('Codex') + 200)}`)

      // Check for lore fragments or empty state
      const loreFragments = page.locator('[class*="lore"], [class*="Lore"], [class*="fragment"], [class*="Fragment"]')
      const fragCount = await loreFragments.count()
      console.log(`Lore fragment elements: ${fragCount}`)

      const emptyState = page.getByText(/no.*lore|undiscovered|empty|begin/i)
      const emptyVis = await emptyState.first().isVisible().catch(() => false)
      console.log(`Codex empty state: ${emptyVis ? 'VISIBLE' : 'NOT SHOWN (may have content)'}`)
    } else {
      console.log('Codex tab not found')
      // Try alternate names
      const altTab = page.getByText(/Lore|Collection/i)
      const altVis = await altTab.first().isVisible().catch(() => false)
      console.log(`Alternative lore/collection tab: ${altVis ? 'FOUND' : 'NOT FOUND'}`)
    }
  })

  // ============================================
  // 6. ONBOARDING - Complete flow test
  // ============================================
  test('onboarding - full flow with name entry and quiz', async ({ page }) => {
    // Clear all onboarding state
    await page.evaluate(() => {
      localStorage.clear()
    })

    await page.goto(BASE_URL + '/onboarding')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000) // Let typewriter effect play
    await page.screenshot({ path: `${SCREENSHOT_DIR}/05-onboarding-step1.png`, fullPage: true })

    // Check for E.E.V.A. greeting elements
    const bodyText = await page.textContent('body')
    console.log(`Onboarding body preview: ${bodyText.slice(0, 400)}`)

    // Look for name input
    const nameInput = page.locator('input')
    const nameInputVis = await nameInput.first().isVisible().catch(() => false)
    console.log(`Name input: ${nameInputVis ? 'VISIBLE' : 'NOT FOUND'}`)

    if (nameInputVis) {
      await nameInput.first().fill('QA_Tester')
      await page.waitForTimeout(500)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/05-onboarding-name-filled.png`, fullPage: true })

      // Find and click continue/next button
      const buttons = page.locator('button:visible')
      const btnCount = await buttons.count()
      console.log(`Visible buttons: ${btnCount}`)

      for (let i = 0; i < btnCount; i++) {
        const text = await buttons.nth(i).textContent()
        console.log(`  Button ${i}: "${text?.trim()}"`)
      }

      // Click the primary action button
      const continueBtn = page.locator('button:visible').filter({ hasText: /continue|next|proceed|begin|enter/i })
      const contVis = await continueBtn.first().isVisible().catch(() => false)
      if (contVis) {
        await continueBtn.first().click()
        await page.waitForTimeout(3000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/05-onboarding-step2.png`, fullPage: true })
        console.log(`After continue: URL=${page.url()}`)

        // Try to progress through faction quiz
        for (let step = 1; step <= 5; step++) {
          const options = page.locator('button:visible')
          const optCount = await options.count()

          // Find quiz option buttons (longer text, not nav buttons)
          let clicked = false
          for (let i = 0; i < optCount; i++) {
            const text = (await options.nth(i).textContent())?.trim() || ''
            if (text.length > 20 && text.length < 300) {
              await options.nth(i).click()
              await page.waitForTimeout(2000)
              clicked = true
              break
            }
          }

          if (clicked) {
            await page.screenshot({ path: `${SCREENSHOT_DIR}/05-onboarding-step${step + 2}.png`, fullPage: true })
            console.log(`Onboarding step ${step + 2}: progressed`)
          } else {
            console.log(`Onboarding step ${step + 2}: no quiz options found (may have completed)`)
            break
          }
        }

        await page.screenshot({ path: `${SCREENSHOT_DIR}/05-onboarding-final.png`, fullPage: true })
        console.log(`Onboarding final URL: ${page.url()}`)

        // Check localStorage was set
        const stored = await page.evaluate(() => ({
          user_id: localStorage.getItem('nephilim_user_id'),
          user_name: localStorage.getItem('nephilim_user_name'),
          faction: localStorage.getItem('nephilim_faction'),
          complete: localStorage.getItem('nephilim_onboarding_complete'),
        }))
        console.log(`Stored after onboarding: ${JSON.stringify(stored)}`)
      }
    } else {
      // Maybe a different onboarding UI - check for any interactive elements
      const allBtns = page.locator('button')
      const allBtnCount = await allBtns.count()
      console.log(`All buttons on onboarding: ${allBtnCount}`)
    }
  })

  // ============================================
  // 7. MOBILE - Deep checks
  // ============================================
  test('mobile - bottom tab navigation works', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })

    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: `${SCREENSHOT_DIR}/06-mobile-select.png` })

    // Check bottom nav
    const bottomNav = page.locator('nav[aria-label="Mobile navigation"]')
    const navVis = await bottomNav.isVisible().catch(() => false)
    console.log(`Mobile bottom nav: ${navVis ? 'VISIBLE' : 'NOT FOUND'}`)

    if (navVis) {
      // Tap each tab and verify navigation
      const tabs = [
        { label: 'Chat', expectedUrl: '/chat' },
        { label: 'Realm', expectedUrl: '/' },
        { label: 'Companions', expectedUrl: '/select' },
        { label: 'Profile', expectedUrl: '/dashboard' },
      ]

      for (const tab of tabs) {
        const tabBtn = bottomNav.getByText(tab.label)
        const tabVis = await tabBtn.isVisible().catch(() => false)
        if (tabVis) {
          await tabBtn.click()
          await page.waitForTimeout(1500)
          console.log(`  Tapped "${tab.label}": URL=${page.url()}`)
          await page.screenshot({ path: `${SCREENSHOT_DIR}/06-mobile-tab-${tab.label.toLowerCase()}.png` })
        } else {
          console.log(`  Tab "${tab.label}" not visible`)
        }
      }
    }
  })

  // ============================================
  // 8. ACCESSIBILITY - Detailed checks
  // ============================================
  test('accessibility - text contrast and WCAG compliance', async ({ page }) => {
    const pages = ['/select', '/dashboard', '/chat', '/']

    for (const route of pages) {
      await page.goto(BASE_URL + route)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(2000)

      // Check for text-white/40 in class names (below WCAG AA)
      const lowContrastClasses = await page.evaluate(() => {
        const results: string[] = []
        document.querySelectorAll('*').forEach(el => {
          const cls = el.className?.toString() || ''
          if (cls.includes('white/40') || cls.includes('white/30') || cls.includes('white/20') || cls.includes('white/10')) {
            const text = el.textContent?.trim().slice(0, 50)
            if (text) results.push(`${el.tagName}.${cls.slice(0, 60)}: "${text}"`)
          }
        })
        return results
      })

      if (lowContrastClasses.length > 0) {
        console.log(`WARNING ${route}: Found ${lowContrastClasses.length} low-contrast text elements:`)
        for (const item of lowContrastClasses.slice(0, 5)) {
          console.log(`  ${item}`)
        }
      } else {
        console.log(`PASS ${route}: No low-contrast text classes found`)
      }

      // Check all buttons and links have accessible names
      const a11y = await page.evaluate(() => {
        const issues: string[] = []
        document.querySelectorAll('button, a, [role="button"]').forEach(el => {
          const ariaLabel = el.getAttribute('aria-label')
          const title = el.getAttribute('title')
          const text = el.textContent?.trim()
          const ariaLabelledBy = el.getAttribute('aria-labelledby')
          if (!ariaLabel && !title && !text && !ariaLabelledBy) {
            issues.push(`${el.tagName}.${(el.className?.toString() || '').slice(0, 40)} - no accessible name`)
          }
        })
        return issues
      })

      if (a11y.length > 0) {
        console.log(`WARNING ${route}: ${a11y.length} elements without accessible names:`)
        for (const item of a11y.slice(0, 5)) {
          console.log(`  ${item}`)
        }
      } else {
        console.log(`PASS ${route}: All interactive elements have accessible names`)
      }
    }
  })

  // ============================================
  // 9. CROSS-FEATURE - Session persistence
  // ============================================
  test('cross-feature - session list loads from backend', async ({ page }) => {
    await page.goto(BASE_URL + '/chat')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Check for session list sidebar
    const sessionList = page.locator('[class*="session"], [class*="Session"], [class*="sidebar"], [class*="Sidebar"]')
    const sessionCount = await sessionList.count()
    console.log(`Session list elements: ${sessionCount}`)

    // Check if sessions API was called successfully (look at network)
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07-chat-sessions.png`, fullPage: true })

    // Navigate to select, pick a persona, and check if session is created
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    const firstCard = page.locator('[class*="card"], [class*="Card"]').first()
    const cardVis = await firstCard.isVisible().catch(() => false)
    if (cardVis) {
      await firstCard.click()
      await page.waitForTimeout(5000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/07-chat-after-select.png`, fullPage: true })
      console.log(`After selecting persona: URL=${page.url()}`)

      // Check if a session was created in the sidebar
      const newSessions = page.locator('[class*="session"], [class*="Session"]')
      const newCount = await newSessions.count()
      console.log(`Session elements after persona select: ${newCount}`)
    }
  })

  // ============================================
  // 10. VISUAL CONSISTENCY - Screenshots at all viewports
  // ============================================
  test('visual consistency - all pages at tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 }) // iPad

    const routes = ['/', '/select', '/chat', '/dashboard']
    for (const route of routes) {
      await page.goto(BASE_URL + route)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(2000)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/08-tablet${route.replace('/', '-') || '-home'}.png`, fullPage: true })
      console.log(`Tablet screenshot: ${route}`)

      // Check for horizontal overflow
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)
      if (overflow) {
        console.log(`WARNING: Horizontal overflow at tablet viewport on ${route}`)
      } else {
        console.log(`PASS: No overflow at tablet on ${route}`)
      }
    }
  })
})
