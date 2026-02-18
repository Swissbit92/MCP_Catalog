/**
 * Celestial Order Mockup — Playwright Visual & Functional Tests
 *
 * Tests the static HTML mockup at react-ui/celestial-order-mockup.html
 * using the file:// protocol so no dev server is required.
 */

import { test, expect, Page } from '@playwright/test'
import path from 'path'

// Resolve the absolute path to the HTML file and convert to file:// URL
const HTML_FILE = path.resolve(
  __dirname,
  '..',
  'celestial-order-mockup.html'
)
// Playwright expects forward slashes even on Windows for file:// URLs
const FILE_URL = 'file:///' + HTML_FILE.replace(/\\/g, '/')

// ─────────────────────────────────────────────────────
// HELPER: wait for the page JS to finish rendering cards
// ─────────────────────────────────────────────────────
async function openMockup(page: Page) {
  await page.goto(FILE_URL, { waitUntil: 'domcontentloaded' })
  // The page renders cards via renderCards() called on DOMContentLoaded.
  // Wait until at least one persona-card exists in the DOM.
  await page.waitForSelector('.persona-card', { timeout: 10000 })
}

// ─────────────────────────────────────────────────────
// SUITE 1 — FULL-PAGE SCREENSHOTS
// ─────────────────────────────────────────────────────
test.describe('Full-Page Screenshots', () => {
  test('desktop 1920x1080 full-page screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    await page.screenshot({
      path: 'tests/screenshots/celestial-order-desktop-1920x1080.png',
      fullPage: true,
    })

    // Verify the screenshot was taken by checking page title
    const title = await page.title()
    expect(title).toBe('Celestial Order System — NEPHILIM Classification')
  })

  test('mobile 375x812 full-page screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await openMockup(page)

    await page.screenshot({
      path: 'tests/screenshots/celestial-order-mobile-375x812.png',
      fullPage: true,
    })

    const title = await page.title()
    expect(title).toBe('Celestial Order System — NEPHILIM Classification')
  })
})

// ─────────────────────────────────────────────────────
// SUITE 2 — PERSONA CARD COUNT
// ─────────────────────────────────────────────────────
test.describe('Persona Card Count', () => {
  test('renders exactly 7 persona cards', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const cardCount = await page.locator('.persona-card').count()
    console.log(`  Persona cards found: ${cardCount}`)
    expect(cardCount).toBe(7)
  })

  test('cards section exists and contains the card grid', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const grid = page.locator('#cardsGrid')
    await expect(grid).toBeVisible()

    const wrapperCount = await page.locator('.card-wrapper').count()
    console.log(`  Card wrappers found: ${wrapperCount}`)
    expect(wrapperCount).toBe(7)
  })

  test('each persona card has a name element', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const nameElements = await page.locator('.card-name').allTextContents()
    console.log(`  Card names: ${nameElements.join(', ')}`)
    expect(nameElements.length).toBe(7)

    // Spot-check that known persona names are present
    const knownNames = ['E.E.V.A.', 'Aegis', 'Aurora', 'Solace', 'Cipher', 'Nyx', 'Wanderer']
    for (const name of knownNames) {
      expect(nameElements).toContain(name)
    }
  })
})

// ─────────────────────────────────────────────────────
// SUITE 3 — MCP ACCESS MATRIX ROWS
// ─────────────────────────────────────────────────────
test.describe('MCP Access Matrix', () => {
  test('matrix section exists and is in the DOM', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const matrix = page.locator('#matrixGrid')
    await expect(matrix).toBeAttached()
  })

  test('matrix contains one persona row per persona (7 rows)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    // Each persona row is represented by a .matrix-persona cell
    const rowCount = await page.locator('.matrix-persona').count()
    console.log(`  Matrix persona rows found: ${rowCount}`)
    expect(rowCount).toBe(7)
  })

  test('matrix has exactly 4 header columns', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const headers = await page.locator('.matrix-header').allTextContents()
    console.log(`  Matrix headers: ${headers.join(' | ')}`)
    expect(headers.length).toBe(4)
    expect(headers[0]).toContain('Persona')
    expect(headers[1]).toContain('Brave Search')
    expect(headers[2]).toContain('MongoDB')
    expect(headers[3]).toContain('Meta')
  })

  test('matrix section screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const matrixSection = page.locator('#matrix')
    await matrixSection.scrollIntoViewIfNeeded()
    await page.waitForTimeout(300)

    await matrixSection.screenshot({
      path: 'tests/screenshots/celestial-order-matrix.png',
    })

    await expect(matrixSection).toBeAttached()
  })
})

// ─────────────────────────────────────────────────────
// SUITE 4 — TAB NAVIGATION
// ─────────────────────────────────────────────────────
test.describe('Tab Navigation', () => {
  const TAB_SECTIONS = [
    { label: 'I. Overview', section: 'overview' },
    { label: 'II. Cards', section: 'cards' },
    { label: 'III. MCP Access', section: 'matrix' },
    { label: 'IV. Summoning', section: 'summoning' },
    { label: 'V. Themes', section: 'themes' },
  ]

  test('nav bar renders all 5 tabs', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const tabs = await page.locator('.nav-tab').count()
    console.log(`  Nav tabs found: ${tabs}`)
    expect(tabs).toBe(5)
  })

  test('first tab (Overview) is active on load', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const activeTab = page.locator('.nav-tab.active')
    const activeCount = await activeTab.count()
    expect(activeCount).toBeGreaterThanOrEqual(1)

    const activeText = await activeTab.first().textContent()
    console.log(`  Active tab on load: "${activeText}"`)
    expect(activeText).toContain('Overview')
  })

  for (const { label, section } of TAB_SECTIONS) {
    test(`clicking tab "${label}" navigates to section #${section}`, async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 })
      await openMockup(page)

      const tab = page.locator(`.nav-tab[data-section="${section}"]`)
      await expect(tab).toBeVisible()

      await tab.click()
      await page.waitForTimeout(600) // allow scroll/transition

      // Verify the tab received the active class
      await expect(tab).toHaveClass(/active/)

      // Take a screenshot to record the state
      await page.screenshot({
        path: `tests/screenshots/celestial-order-tab-${section}.png`,
        fullPage: false,
      })

      console.log(`  Clicked tab "${label}" — section #${section} activated`)
    })
  }
})

// ─────────────────────────────────────────────────────
// SUITE 5 — SUMMONING REVEAL CARDS
// ─────────────────────────────────────────────────────
test.describe('Summoning Reveal Cards', () => {
  const ORDERS = ['archon', 'warden', 'sage', 'wanderer']

  test('summoning section contains 4 reveal cards', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const revealCards = await page.locator('.summon-reveal-card').count()
    console.log(`  Reveal cards found: ${revealCards}`)
    expect(revealCards).toBe(4)
  })

  for (const order of ORDERS) {
    test(`reveal card for order "${order}" is clickable`, async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 })
      await openMockup(page)

      // Navigate to summoning section first
      const summoningTab = page.locator('.nav-tab[data-section="summoning"]')
      await summoningTab.click()
      await page.waitForTimeout(400)

      const revealCard = page.locator(`.summon-reveal-card[data-order="${order}"]`)
      await expect(revealCard).toBeAttached()

      // Scroll it into view before clicking
      await revealCard.scrollIntoViewIfNeeded()
      await page.waitForTimeout(200)

      // Click the reveal card
      await revealCard.click()
      await page.waitForTimeout(500) // allow animation/state update

      // Capture the orb state after click
      const orbOrder = await page.locator('#orbOrder').textContent()
      const orbName = await page.locator('#orbName').textContent()
      console.log(`  After clicking "${order}" card — orb shows: "${orbOrder}" / "${orbName}"`)

      // The orb should update to reflect the selected order
      const orderCapitalized = order.charAt(0).toUpperCase() + order.slice(1)
      expect(orbOrder).toContain(orderCapitalized)

      await page.screenshot({
        path: `tests/screenshots/celestial-order-reveal-${order}.png`,
        fullPage: false,
      })
    })
  }

  test('summoning demo section screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const summoningTab = page.locator('.nav-tab[data-section="summoning"]')
    await summoningTab.click()
    await page.waitForTimeout(600)

    const summoningSection = page.locator('#summoning')
    await summoningSection.screenshot({
      path: 'tests/screenshots/celestial-order-summoning.png',
    })

    await expect(summoningSection).toBeAttached()
  })
})

// ─────────────────────────────────────────────────────
// SUITE 6 — ACCESSIBILITY & STRUCTURE
// ─────────────────────────────────────────────────────
test.describe('Accessibility and Structure', () => {
  test('nav tablist has correct ARIA role', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const navTabs = page.locator('#navTabs')
    await expect(navTabs).toHaveAttribute('role', 'tablist')
  })

  test('each nav tab has an aria-label', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const tabs = page.locator('.nav-tab')
    const count = await tabs.count()
    for (let i = 0; i < count; i++) {
      const ariaLabel = await tabs.nth(i).getAttribute('aria-label')
      expect(ariaLabel).toBeTruthy()
      console.log(`  Tab ${i + 1} aria-label: "${ariaLabel}"`)
    }
  })

  test('each reveal card has an aria-label', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const revealCards = page.locator('.summon-reveal-card')
    const count = await revealCards.count()
    for (let i = 0; i < count; i++) {
      const ariaLabel = await revealCards.nth(i).getAttribute('aria-label')
      expect(ariaLabel).toBeTruthy()
      console.log(`  Reveal card ${i + 1} aria-label: "${ariaLabel}"`)
    }
  })

  test('page has a descriptive title', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const title = await page.title()
    expect(title).toBe('Celestial Order System — NEPHILIM Classification')
  })

  test('atmosphere background element is present', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await openMockup(page)

    const atmosphere = page.locator('.atmosphere')
    await expect(atmosphere).toBeAttached()
  })
})
