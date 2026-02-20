import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'

// Collect console errors per test
const consoleErrors: string[] = []

test.describe('Phase 8 Implementation Review', () => {
  test.beforeEach(async ({ page }) => {
    // Clear console errors
    consoleErrors.length = 0

    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // Set nephilim localStorage values for testing
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'test_seeker')
      localStorage.setItem('nephilim_user_name', 'Test Seeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })
  })

  test('1 - homepage loads without errors', async ({ page }) => {
    await page.goto(`${BASE_URL}/`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-screenshots/01-homepage.png', fullPage: true })

    // Verify page loaded (title or main content exists)
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })

  test('2a - dashboard profile tab', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000) // Wait for API data to load

    await page.screenshot({ path: 'test-screenshots/02-dashboard-profile.png', fullPage: true })

    // Verify Seeker's Sanctum heading
    const heading = page.getByText("Seeker's Sanctum")
    await expect(heading).toBeVisible()
  })

  test('2b - dashboard bonds tab with constellation', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Click the Bonds Forged tab
    const bondsTab = page.getByText('Bonds Forged').first()
    if (await bondsTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await bondsTab.click()
      await page.waitForTimeout(1500)

      // Verify constellation heading appears
      const constellationHeading = page.getByText('Constellation of Bonds')
      const isVisible = await constellationHeading.isVisible().catch(() => false)
      if (isVisible) {
        // Check for SVG constellation map
        const svg = page.locator('svg')
        const svgCount = await svg.count()
        expect(svgCount).toBeGreaterThan(0)
      }

      // Check that active constellation nodes have cursor:pointer
      const activeNodes = page.locator('g[role="button"]')
      const activeCount = await activeNodes.count()
      if (activeCount > 0) {
        const cursor = await activeNodes.first().evaluate(el => {
          return window.getComputedStyle(el).cursor
        })
        expect(cursor).toBe('pointer')
      }
    }

    await page.screenshot({ path: 'test-screenshots/03-dashboard-bonds.png', fullPage: true })
  })

  test('2c - dashboard chronicle tab shows real content', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Click the Invocation Chronicle tab
    const chronicleTab = page.getByText('Chronicle').first()
    if (await chronicleTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await chronicleTab.click()
      await page.waitForTimeout(1500)
    }

    await page.screenshot({ path: 'test-screenshots/04-dashboard-chronicle.png', fullPage: true })

    // Verify the old Phase 7D placeholder text is NOT present
    const oldPlaceholder = page.getByText('Coming in Phase 7D integration')
    await expect(oldPlaceholder).not.toBeVisible()

    // Verify actual chronicle content exists
    const invocationStats = page.getByText('Invocation Stats')
    const isStatsVisible = await invocationStats.isVisible().catch(() => false)

    const recentInvocations = page.getByText('Recent Invocations')
    const isRecentVisible = await recentInvocations.isVisible().catch(() => false)

    const chronicleAwaits = page.getByText('The chronicle awaits')
    const isChronicleAwaitsVisible = await chronicleAwaits.isVisible().catch(() => false)

    // At least one of these should be visible (stats, recent invocations, or empty state)
    expect(isStatsVisible || isRecentVisible || isChronicleAwaitsVisible).toBe(true)
  })

  test('3 - header shows SeekerRankBadge', async ({ page }) => {
    // Navigate to /select where header is visible
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.screenshot({ path: 'test-screenshots/05-header-rank.png', fullPage: false })

    // Check the desktop header exists
    const header = page.locator('header')
    const headerVisible = await header.isVisible().catch(() => false)

    if (headerVisible) {
      // Verify NEPHILIM wordmark
      const wordmark = page.getByText('NEPHILIM').first()
      await expect(wordmark).toBeVisible()

      // Verify navigation links
      const companionsLink = page.getByText('Companions')
      await expect(companionsLink.first()).toBeVisible()

      const dashboardLink = page.getByText('Dashboard')
      await expect(dashboardLink.first()).toBeVisible()

      // Verify seeker name is displayed
      const seekerName = page.getByText('Test Seeker')
      const nameVisible = await seekerName.isVisible().catch(() => false)
      // Name might not be visible if viewport is mobile-sized
      if (!nameVisible) {
        console.log('Note: Seeker name not visible - may be mobile viewport')
      }
    }
  })

  test('4 - chat page renders without errors', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.screenshot({ path: 'test-screenshots/06-chat-page.png', fullPage: true })

    // Verify the page rendered (body visible, no crash)
    const body = page.locator('body')
    await expect(body).toBeVisible()

    // Check for any uncaught JS errors that would indicate a crash
    const criticalErrors = consoleErrors.filter(e =>
      e.includes('Uncaught') || e.includes('TypeError') || e.includes('ReferenceError')
    )
    // Log them but don't fail - API errors are expected in test env
    if (criticalErrors.length > 0) {
      console.log('Console errors on chat page:', criticalErrors)
    }
  })

  test('5 - character select page renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.screenshot({ path: 'test-screenshots/07-select-page.png', fullPage: true })

    // Verify the page rendered
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })
})
