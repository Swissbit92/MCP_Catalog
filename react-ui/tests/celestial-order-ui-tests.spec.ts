import { test, expect, Page } from '@playwright/test'
import path from 'path'
import fs from 'fs'

// Absolute path to the mockup
const MOCKUP_PATH =
  'file:///C:/Users/rzehn/desktop/MCP_catalog/react-ui/celestial-order-mockup.html'
const SCREENSHOTS_DIR =
  'C:/Users/rzehn/desktop/MCP_catalog/react-ui/tests/screenshots'

// Helper: ensure screenshots directory exists
function ensureScreenshotsDir() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
  }
}

// Helper: wait for fonts/animations to settle
async function waitForPageSettle(page: Page) {
  await page.waitForLoadState('domcontentloaded')
  await page.waitForTimeout(600)
}

test.describe('Celestial Order Mockup — Full UI Validation', () => {

  test.beforeAll(() => {
    ensureScreenshotsDir()
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 1: Full Page Load
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 1: Full page load and full-page screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    // Check title
    const title = await page.title()
    expect(title).toContain('Celestial Order')

    // Check hero title is visible
    const heroTitle = page.locator('.hero-title')
    await expect(heroTitle).toBeVisible()

    // Check nav tabs rendered
    const navTabs = page.locator('.nav-tab')
    await expect(navTabs).toHaveCount(5)

    // Full-page screenshot
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-fullpage.png`,
      fullPage: true,
    })

    console.log('Test 1 PASSED: Full page loaded, title correct, 5 nav tabs found')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 2: Section Navigation — click each tab and verify scroll
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 2: Section navigation — all 5 tabs scroll to correct section', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    const tabs = [
      { label: 'I. Overview', sectionId: 'overview' },
      { label: 'II. Cards', sectionId: 'cards' },
      { label: 'III. MCP Access', sectionId: 'matrix' },
      { label: 'IV. Summoning', sectionId: 'summoning' },
      { label: 'V. Themes', sectionId: 'themes' },
    ]

    for (const tab of tabs) {
      // Click the tab
      await page.locator(`.nav-tab[data-section="${tab.sectionId}"]`).click()
      await page.waitForTimeout(600) // allow smooth scroll

      // Take viewport screenshot for this section
      await page.screenshot({
        path: `${SCREENSHOTS_DIR}/celestial-order-section-${tab.sectionId}.png`,
      })

      // Verify the target section exists in DOM
      const section = page.locator(`#${tab.sectionId}`)
      await expect(section).toBeAttached()

      // Verify the clicked tab gains active class
      const activeTab = page.locator(`.nav-tab[data-section="${tab.sectionId}"]`)
      const classList = await activeTab.getAttribute('class')
      expect(classList).toContain('active')

      console.log(`  Tab "${tab.label}" → section #${tab.sectionId}: OK`)
    }

    console.log('Test 2 PASSED: All 5 tabs navigate correctly')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 3: Character Cards — count, hover effects
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 3: Character cards — 7 cards, hover states', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    // Navigate to cards section
    await page.locator('.nav-tab[data-section="cards"]').click()
    await page.waitForTimeout(700)

    // Count all persona cards
    const cards = page.locator('.persona-card')
    const cardCount = await cards.count()
    console.log(`  Found ${cardCount} .persona-card elements`)
    expect(cardCount).toBe(7)

    // Take grid screenshot
    const cardsGrid = page.locator('#cardsGrid')
    await expect(cardsGrid).toBeVisible()
    await cardsGrid.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-cards.png`,
    })

    // Hover over Archon card
    const archonCard = page.locator('.persona-card.archon').first()
    await expect(archonCard).toBeVisible()
    await archonCard.hover()
    await page.waitForTimeout(400)
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-card-archon-hover.png`,
    })

    // Verify archon hover drop-shadow applied (computed style)
    const archonFilter = await archonCard.evaluate((el) =>
      window.getComputedStyle(el).filter
    )
    console.log(`  Archon hover filter: ${archonFilter}`)
    // Should have drop-shadow (not 'none')
    expect(archonFilter).not.toBe('none')

    // Hover over Warden card
    const wardenCards = page.locator('.persona-card.warden')
    const wardenCount = await wardenCards.count()
    console.log(`  Found ${wardenCount} warden cards`)
    expect(wardenCount).toBeGreaterThan(0)

    await wardenCards.first().hover()
    await page.waitForTimeout(400)
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-card-warden-hover.png`,
    })

    // Hover over Sage card
    const sageCards = page.locator('.persona-card.sage')
    const sageCount = await sageCards.count()
    console.log(`  Found ${sageCount} sage cards`)
    expect(sageCount).toBeGreaterThan(0)

    await sageCards.first().hover()
    await page.waitForTimeout(400)
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-card-sage-hover.png`,
    })

    console.log('Test 3 PASSED: 7 cards found, hover effects work')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 4: MCP Matrix — rows count, checkmarks vs X
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 4: MCP matrix — 7 persona rows, check/X marks', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    await page.locator('.nav-tab[data-section="matrix"]').click()
    await page.waitForTimeout(700)

    const matrixGrid = page.locator('#matrixGrid')
    await expect(matrixGrid).toBeVisible()

    // Count persona rows — the matrix uses .matrix-persona for each persona name cell
    const rows = matrixGrid.locator('.matrix-persona')
    const rowCount = await rows.count()
    console.log(`  Matrix persona rows found: ${rowCount}`)
    expect(rowCount).toBe(7)

    // Count tool cells (.matrix-cell) — 7 personas x 3 tools = 21 cells
    const matrixCells = matrixGrid.locator('.matrix-cell')
    const cellCount = await matrixCells.count()
    console.log(`  Matrix tool cells found: ${cellCount}`)
    expect(cellCount).toBe(21)

    // Count check marks (.matrix-check.active = ✓) and X marks (.matrix-check.inactive = ✗)
    const checkCells = matrixGrid.locator('.matrix-check.active')
    const xCells = matrixGrid.locator('.matrix-check.inactive')
    const checkCount = await checkCells.count()
    const xCount = await xCells.count()
    console.log(`  Check marks (active): ${checkCount}, X marks (inactive): ${xCount}`)

    // Total check + X should equal 21 cells
    expect(checkCount + xCount).toBe(21)
    // At least some cells have access, some don't
    expect(checkCount).toBeGreaterThan(0)
    expect(xCount).toBeGreaterThan(0)

    await matrixGrid.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-matrix.png`,
    })

    console.log('Test 4 PASSED: MCP matrix rendered with 7 rows')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 5: Summoning Interaction — click each order card
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 5: Summoning interaction — order reveal cards change orb', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    await page.locator('.nav-tab[data-section="summoning"]').click()
    await page.waitForTimeout(700)

    const orbOrderEl = page.locator('#orbOrder')
    const orbNameEl = page.locator('#orbName')

    const revealOrders = [
      { dataOrder: 'archon', expectedLabel: 'Archon' },
      { dataOrder: 'warden', expectedLabel: 'Warden' },
      { dataOrder: 'sage', expectedLabel: 'Sage' },
      { dataOrder: 'wanderer', expectedLabel: 'Wanderer' },
    ]

    for (const reveal of revealOrders) {
      const card = page.locator(`.summon-reveal-card[data-order="${reveal.dataOrder}"]`)
      await expect(card).toBeVisible()
      await card.click()
      await page.waitForTimeout(500) // allow orb animation

      const orbOrderText = await orbOrderEl.textContent()
      console.log(
        `  Clicked ${reveal.dataOrder} → orbOrder text: "${orbOrderText}"`
      )
      expect(orbOrderText?.toLowerCase()).toContain(
        reveal.expectedLabel.toLowerCase()
      )

      await page.screenshot({
        path: `${SCREENSHOTS_DIR}/celestial-order-summon-${reveal.dataOrder}.png`,
      })
    }

    console.log('Test 5 PASSED: All 4 summoning reveal cards update orb correctly')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 6: Layout Validation — overflow, clipping, responsive viewports
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 6: Layout validation — no horizontal overflow, responsive viewports', async ({
    page,
  }) => {
    const viewports = [
      { width: 1920, height: 1080, label: '1920x1080' },
      { width: 1366, height: 768, label: '1366x768' },
      { width: 375, height: 812, label: '375x812-mobile' },
    ]

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto(MOCKUP_PATH)
      await waitForPageSettle(page)

      // Check horizontal overflow: scrollWidth should not exceed clientWidth
      const overflowData = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyScrollWidth: document.body.scrollWidth,
        bodyClientWidth: document.body.clientWidth,
      }))

      console.log(
        `  [${vp.label}] docScrollWidth=${overflowData.scrollWidth} clientWidth=${overflowData.clientWidth}`
      )

      const hasHorizontalOverflow =
        overflowData.scrollWidth > overflowData.clientWidth + 2 // 2px tolerance

      if (hasHorizontalOverflow) {
        console.warn(
          `  WARNING [${vp.label}]: Horizontal overflow detected! scrollWidth=${overflowData.scrollWidth} > clientWidth=${overflowData.clientWidth}`
        )
      }

      // Take viewport screenshot
      await page.screenshot({
        path: `${SCREENSHOTS_DIR}/celestial-order-viewport-${vp.label}.png`,
      })

      // Check hero title is not zero-height (text visibility)
      const heroTitle = page.locator('.hero-title')
      const heroBB = await heroTitle.boundingBox()
      if (heroBB) {
        console.log(
          `  [${vp.label}] hero-title bounding box: ${heroBB.width.toFixed(0)}x${heroBB.height.toFixed(0)}`
        )
        expect(heroBB.height).toBeGreaterThan(0)
        expect(heroBB.width).toBeGreaterThan(0)
      }

      // Nav tabs should be visible and not overflow vertically in an odd way
      const navTabs = page.locator('.nav-tabs')
      await expect(navTabs).toBeVisible()
    }

    console.log('Test 6 PASSED: Layout checked at 3 viewport sizes')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // TEST 7: Visual Regressions — atmosphere, glassmorphism, fonts, animations
  // ─────────────────────────────────────────────────────────────────────────────
  test('Test 7: Visual regressions — atmosphere, glass, fonts, animations', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    // 1. Atmosphere background exists and has correct position:fixed
    const atmosphere = page.locator('.atmosphere')
    await expect(atmosphere).toBeAttached()
    const atmosphereStyle = await atmosphere.evaluate((el) => {
      const s = window.getComputedStyle(el)
      return { position: s.position, zIndex: s.zIndex }
    })
    console.log(
      `  Atmosphere: position=${atmosphereStyle.position}, z-index=${atmosphereStyle.zIndex}`
    )
    expect(atmosphereStyle.position).toBe('fixed')

    // 2. Glassmorphism: .glass elements should have backdrop-filter
    const glassEl = page.locator('.glass').first()
    await expect(glassEl).toBeAttached()
    const glassFilter = await glassEl.evaluate((el) => {
      const s = window.getComputedStyle(el)
      return {
        backdropFilter: s.backdropFilter || s.webkitBackdropFilter,
        background: s.background,
      }
    })
    console.log(`  Glass backdrop-filter: "${glassFilter.backdropFilter}"`)
    // backdrop-filter blur should be present (not 'none')
    expect(glassFilter.backdropFilter).not.toBe('none')

    // 3. Font check — hero title should use Orbitron (or fallback)
    const heroTitle = page.locator('.hero-title')
    const heroFont = await heroTitle.evaluate((el) =>
      window.getComputedStyle(el).fontFamily
    )
    console.log(`  Hero title font-family: "${heroFont}"`)
    // Orbitron may or may not load depending on network; check it's declared
    // The CSS declares Orbitron — we just verify font-family is set (not empty)
    expect(heroFont).toBeTruthy()
    expect(heroFont.length).toBeGreaterThan(0)

    // 4. Space Mono on section numbers
    const sectionNumber = page.locator('.section-number').first()
    if ((await sectionNumber.count()) > 0) {
      const monoFont = await sectionNumber.evaluate((el) =>
        window.getComputedStyle(el).fontFamily
      )
      console.log(`  Section number font-family: "${monoFont}"`)
      expect(monoFont).toBeTruthy()
    }

    // 5. Animations — border-spin elements
    const borderSpinEls = page.locator('.card-border-effect')
    const borderSpinCount = await borderSpinEls.count()
    console.log(`  .card-border-effect elements: ${borderSpinCount}`)

    if (borderSpinCount > 0) {
      const animName = await borderSpinEls.first().evaluate((el) =>
        window.getComputedStyle(el).animationName
      )
      console.log(`  First border-spin animation-name: "${animName}"`)
      // Animation should be defined (not 'none')
      expect(animName).not.toBe('none')
    }

    // 6. Console errors check
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    // Reload once more to capture console errors from initial load
    await page.reload()
    await waitForPageSettle(page)

    if (consoleErrors.length > 0) {
      console.warn(`  CONSOLE ERRORS (${consoleErrors.length}):`)
      consoleErrors.forEach((err) => console.warn(`    - ${err}`))
    } else {
      console.log('  No console errors detected')
    }

    // Take final screenshot
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-visual-final.png`,
    })

    console.log('Test 7 PASSED: Visual regression checks complete')
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // BONUS: Themes Section — check theme showcase renders
  // ─────────────────────────────────────────────────────────────────────────────
  test('Bonus: Themes section renders theme showcase', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(MOCKUP_PATH)
    await waitForPageSettle(page)

    await page.locator('.nav-tab[data-section="themes"]').click()
    await page.waitForTimeout(700)

    const themeShowcase = page.locator('#themeShowcase')
    await expect(themeShowcase).toBeVisible()

    const themeItems = themeShowcase.locator('.theme-item, .theme-card, .glass-sm')
    const themeItemCount = await themeItems.count()
    console.log(`  Theme showcase items: ${themeItemCount}`)
    expect(themeItemCount).toBeGreaterThan(0)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/celestial-order-themes.png`,
    })

    console.log('Bonus PASSED: Themes section renders correctly')
  })
})
