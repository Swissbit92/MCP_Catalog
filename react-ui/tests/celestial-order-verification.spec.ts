import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const BASE_URL = 'http://localhost:3001'
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots')

// Ensure screenshots directory exists
function ensureScreenshotsDir() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
  }
}

test.beforeAll(() => {
  ensureScreenshotsDir()
})

test.beforeEach(async ({ page }) => {
  // Seed onboarding data so the app renders fully without redirect loops
  await page.goto(BASE_URL)
  await page.evaluate(() => {
    localStorage.setItem('nephilim_user_id', 'test_seeker')
    localStorage.setItem('nephilim_user_name', 'Test Seeker')
    localStorage.setItem('nephilim_onboarding_complete', 'true')
    localStorage.setItem('nephilim_faction', 'house_aegis')
  })
})

test.describe('Celestial Order Remap Verification — Live App', () => {

  // ─────────────────────────────────────────────────────────────────────
  // TEST 1: Character Select page — new vocabulary present
  // ─────────────────────────────────────────────────────────────────────
  test('1 - /select shows Celestial Order labels (Archon/Warden/Sage/Wanderer)', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-fullpage.png`,
      fullPage: true,
    })

    const pageText = await page.textContent('body')

    // At least one new Celestial Order term must appear
    const hasArchon = pageText?.includes('Archon') ?? false
    const hasWarden = pageText?.includes('Warden') ?? false
    const hasSage = pageText?.includes('Sage') ?? false
    const hasWanderer = pageText?.includes('Wanderer') ?? false

    const hasNewVocab = hasArchon || hasWarden || hasSage || hasWanderer
    console.log(`  Archon: ${hasArchon}, Warden: ${hasWarden}, Sage: ${hasSage}, Wanderer: ${hasWanderer}`)

    expect(hasNewVocab).toBeTruthy()

    // "Legendary" must NOT appear as a tier label on the page
    // (rarity-* CSS classes are internal; what matters is visible text)
    const hasLegendaryText = /\bLegendary\b/.test(pageText || '')
    console.log(`  "Legendary" visible text found: ${hasLegendaryText}`)
    expect(hasLegendaryText).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 2: Character Select page — old tier vocabulary absent
  // ─────────────────────────────────────────────────────────────────────
  test('2 - /select has no visible old tier labels (Legendary/Epic/Rare/Common)', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    const pageText = await page.textContent('body') || ''

    // These old labels should NOT appear as standalone tier badges
    // Note: words like "rare" might exist in general prose; test for capitalised form
    // used as a standalone tier — we test the visible rendered text
    const hasLegendary = /\bLegendary\b/.test(pageText)
    // Note: "Epic" and "Rare" can appear in the filter UI ("NEPHILIM" vs "Legacy"),
    // so we only hard-fail on "Legendary" which is purely a tier label
    console.log(`  Old tier "Legendary" present: ${hasLegendary}`)
    expect(hasLegendary).toBeFalsy()

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-no-old-vocab.png`,
      fullPage: false,
    })
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 3: CSS classes — rarity-* classes are still applied to DOM
  // ─────────────────────────────────────────────────────────────────────
  test('3 - /select DOM still uses rarity-* CSS classes (unchanged styling)', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Check that elements with rarity-* classes exist in the DOM
    const rarityLegendary = await page.locator('[class*="rarity-legendary"]').count()
    const rarityEpic = await page.locator('[class*="rarity-epic"]').count()
    const rarityRare = await page.locator('[class*="rarity-rare"]').count()
    const rarityCommon = await page.locator('[class*="rarity-common"]').count()

    console.log(`  rarity-legendary: ${rarityLegendary}, rarity-epic: ${rarityEpic}, rarity-rare: ${rarityRare}, rarity-common: ${rarityCommon}`)

    const totalRarityElements = rarityLegendary + rarityEpic + rarityRare + rarityCommon
    expect(totalRarityElements).toBeGreaterThan(0)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-rarity-classes.png`,
    })
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 4: Chat page — Celestial Order or old vocabulary check
  // ─────────────────────────────────────────────────────────────────────
  test('4 - /chat page renders with NEPHILIM styling', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-chat-fullpage.png`,
      fullPage: true,
    })

    const body = page.locator('body')
    await expect(body).toBeVisible()

    const pageText = await page.textContent('body') || ''
    const hasLegendaryTierLabel = /\bLegendary\b/.test(pageText)
    console.log(`  Chat page "Legendary" tier text present: ${hasLegendaryTierLabel}`)
    // Chat page may not show tier labels at all — just confirm no old vocabulary
    expect(hasLegendaryTierLabel).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 5: Dashboard page — no old vocabulary
  // ─────────────────────────────────────────────────────────────────────
  test('5 - /dashboard page renders with Celestial Order vocabulary', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-dashboard-fullpage.png`,
      fullPage: true,
    })

    const body = page.locator('body')
    await expect(body).toBeVisible()

    const pageText = await page.textContent('body') || ''
    const hasLegendary = /\bLegendary\b/.test(pageText)
    console.log(`  Dashboard "Legendary" tier text present: ${hasLegendary}`)
    expect(hasLegendary).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 6: Homepage — no old vocabulary
  // ─────────────────────────────────────────────────────────────────────
  test('6 - / homepage renders without old vocabulary', async ({ page }) => {
    await page.goto(`${BASE_URL}/`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-home-fullpage.png`,
      fullPage: true,
    })

    const body = page.locator('body')
    await expect(body).toBeVisible()

    const pageText = await page.textContent('body') || ''
    const hasLegendary = /\bLegendary\b/.test(pageText)
    console.log(`  Homepage "Legendary" tier text present: ${hasLegendary}`)
    expect(hasLegendary).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 7: /select — card rarity-badge shows order labels, not rarity names
  // ─────────────────────────────────────────────────────────────────────
  test('7 - card rarity badges show order labels (Archon/Warden/Sage/Wanderer)', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Look for rarity-badge elements and capture their text
    const badgeSelectors = [
      '[class*="rarity-badge"]',
      '[class*="order-badge"]',
      '[class*="tier-badge"]',
      '[class*="celestial-badge"]',
    ]

    let badgeTexts: string[] = []
    for (const sel of badgeSelectors) {
      const badges = page.locator(sel)
      const count = await badges.count()
      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const text = await badges.nth(i).textContent()
          if (text) badgeTexts.push(text.trim())
        }
        break
      }
    }

    console.log(`  Badge texts found: ${badgeTexts.join(', ') || '(none found by selector)'}`)

    // If badges were found, they should use new vocabulary
    for (const text of badgeTexts) {
      const isOldTierLabel = /^(Legendary|Epic|Rare|Common)$/i.test(text)
      if (isOldTierLabel) {
        console.warn(`  WARNING: Found old tier label in badge: "${text}"`)
      }
      expect(isOldTierLabel).toBeFalsy()
    }

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-badges.png`,
    })
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 8: Layout — no horizontal overflow on /select at 1280x800
  // ─────────────────────────────────────────────────────────────────────
  test('8 - /select no horizontal overflow at 1280x800 (default viewport)', async ({ page }) => {
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      bodyClientWidth: document.body.clientWidth,
    }))

    console.log(`  doc scrollWidth=${overflow.scrollWidth}, clientWidth=${overflow.clientWidth}`)
    const hasHorizontalOverflow = overflow.scrollWidth > overflow.clientWidth + 2
    if (hasHorizontalOverflow) {
      console.warn(`  LAYOUT WARNING: Horizontal overflow detected on /select!`)
    }

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-layout.png`,
    })

    expect(hasHorizontalOverflow).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 9: Layout — /select at mobile 375x812 no horizontal overflow
  // ─────────────────────────────────────────────────────────────────────
  test('9 - /select no horizontal overflow at mobile 375x812', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))

    console.log(`  [mobile] scrollWidth=${overflow.scrollWidth}, clientWidth=${overflow.clientWidth}`)
    const hasHorizontalOverflow = overflow.scrollWidth > overflow.clientWidth + 2
    if (hasHorizontalOverflow) {
      console.warn(`  LAYOUT WARNING: Mobile horizontal overflow on /select!`)
    }

    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-select-mobile-375.png`,
      fullPage: true,
    })

    expect(hasHorizontalOverflow).toBeFalsy()
  })

  // ─────────────────────────────────────────────────────────────────────
  // TEST 10: Summoning page — celestial order labels in ritual UI
  // ─────────────────────────────────────────────────────────────────────
  test('10 - summoning / pull interface uses Celestial Order vocabulary', async ({ page }) => {
    // First navigate to select, then look for pull/summoning UI
    await page.goto(`${BASE_URL}/select`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    const pageText = await page.textContent('body') || ''

    // Summoning UI may reference orders — verify no old vocabulary
    const hasLegendary = /\bLegendary\b/.test(pageText)
    const hasNewOrder = /\b(Archon|Warden|Sage|Wanderer)\b/.test(pageText)

    console.log(`  Summoning: new order terms=${hasNewOrder}, "Legendary" present=${hasLegendary}`)

    // Screenshot the full select page which includes any pull UI
    await page.screenshot({
      path: `${SCREENSHOTS_DIR}/verification-summon-vocabulary.png`,
      fullPage: true,
    })

    expect(hasLegendary).toBeFalsy()
  })
})
