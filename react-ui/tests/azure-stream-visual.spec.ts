/**
 * Azure Stream Visual Verification - Playwright Tests
 *
 * Visually verifies the Azure Stream (Sage-tier) card effects on the
 * /select character selection page. Takes screenshots of:
 *   - Full page with all cards
 *   - Individual Sage-tier cards (Cipher, Nyx)
 *   - Sage card hover state
 *   - Non-Sage card (Archon or Warden) for comparison
 *
 * Screenshots saved to: tests/screenshots/azure-stream/
 */

import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const BASE_URL = 'http://localhost:3001'
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots', 'azure-stream')

function ensureDir() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
  }
}

test.beforeAll(() => {
  ensureDir()
})

test.beforeEach(async ({ page }) => {
  await page.goto(BASE_URL)
  await page.evaluate(() => {
    localStorage.setItem('nephilim_user_id', 'azure_test_seeker')
    localStorage.setItem('nephilim_user_name', 'Azure Test Seeker')
    localStorage.setItem('nephilim_onboarding_complete', 'true')
    localStorage.setItem('nephilim_faction', 'house_cipher')
    localStorage.setItem('persona_filter_mode', 'all')
  })
})
test.describe('Azure Stream - Sage Card Visual Tests', () => {

  test('1 - Full page screenshot of /select with all cards', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const cardElements = page.locator('[class*="card-outer"]')
    const cardCount = await cardElements.count()
    console.log('  Total cards rendered: ' + cardCount)
    expect(cardCount).toBeGreaterThan(0)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/01-full-page-all-cards.png',
      fullPage: true,
    })

    console.log('  Test 1 PASSED: Full page screenshot captured')
  })

  test('2 - Sage-tier cards (Cipher, Nyx) present with rarity-rare CSS class', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const sageCards = page.locator('[class*="rarity-rare"]')
    const sageCount = await sageCards.count()
    console.log('  Sage-tier cards found (rarity-rare): ' + sageCount)
    expect(sageCount).toBeGreaterThanOrEqual(2)

    const bodyText = await page.textContent('body') || ''
    const hasSageLabel = bodyText.includes('Sage')
    console.log('  Sage label visible on page: ' + hasSageLabel)
    expect(hasSageLabel).toBeTruthy()

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/02-sage-cards-identified.png',
      fullPage: false,
    })

    console.log('  Test 2 PASSED: Sage-tier cards identified')
  })
  test('3 - Close-up screenshot of Cipher (Sage card)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const cipherCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Cipher' }).first()
    const cipherVisible = await cipherCard.isVisible()
    console.log('  Cipher card visible: ' + cipherVisible)
    expect(cipherVisible).toBeTruthy()

    await cipherCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await cipherCard.screenshot({
      path: SCREENSHOTS_DIR + '/03-cipher-sage-closeup.png',
    })

    const classes = await cipherCard.getAttribute('class') || ''
    const hasSageClass = classes.includes('rarity-rare')
    console.log('  Cipher card classes contain rarity-rare: ' + hasSageClass)
    expect(hasSageClass).toBeTruthy()

    console.log('  Test 3 PASSED: Cipher close-up captured')
  })

  test('4 - Close-up screenshot of Nyx (Sage card)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const nyxCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Nyx' }).first()
    const nyxVisible = await nyxCard.isVisible()
    console.log('  Nyx card visible: ' + nyxVisible)
    expect(nyxVisible).toBeTruthy()

    await nyxCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await nyxCard.screenshot({
      path: SCREENSHOTS_DIR + '/04-nyx-sage-closeup.png',
    })

    const classes = await nyxCard.getAttribute('class') || ''
    const hasSageClass = classes.includes('rarity-rare')
    console.log('  Nyx card classes contain rarity-rare: ' + hasSageClass)
    expect(hasSageClass).toBeTruthy()

    console.log('  Test 4 PASSED: Nyx close-up captured')
  })
  test('5 - Hover over Cipher Sage card captures Azure Stream effect', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const cipherCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Cipher' }).first()
    await cipherCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await cipherCard.hover()
    await page.waitForTimeout(1500)

    await cipherCard.screenshot({
      path: SCREENSHOTS_DIR + '/05-cipher-sage-hover.png',
    })

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/05b-cipher-sage-hover-wide.png',
      fullPage: false,
    })

    const computedStyle = await cipherCard.evaluate((el) => {
      const cs = window.getComputedStyle(el)
      return {
        boxShadow: cs.boxShadow,
        filter: cs.filter,
        animationName: cs.animationName,
      }
    })
    console.log('  Cipher hover box-shadow: ' + computedStyle.boxShadow)
    console.log('  Cipher hover filter: ' + computedStyle.filter)
    console.log('  Cipher hover animation: ' + computedStyle.animationName)

    expect(computedStyle.boxShadow).not.toBe('none')

    console.log('  Test 5 PASSED: Cipher hover with Azure Stream captured')
  })

  test('6 - Hover over Nyx Sage card captures Azure Stream effect', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const nyxCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Nyx' }).first()
    await nyxCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await nyxCard.hover()
    await page.waitForTimeout(1500)

    await nyxCard.screenshot({
      path: SCREENSHOTS_DIR + '/06-nyx-sage-hover.png',
    })

    console.log('  Test 6 PASSED: Nyx hover with Azure Stream captured')
  })
  test('7 - Non-Sage comparison: E.E.V.A. (Archon) card screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const eevaCard = page.locator('[class*="card-outer"]').filter({ hasText: 'E.E.V.A.' }).first()
    const eevaVisible = await eevaCard.isVisible()
    console.log('  E.E.V.A. card visible: ' + eevaVisible)
    expect(eevaVisible).toBeTruthy()

    await eevaCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await eevaCard.screenshot({
      path: SCREENSHOTS_DIR + '/07a-eeva-archon-normal.png',
    })

    const classes = await eevaCard.getAttribute('class') || ''
    const hasArchonClass = classes.includes('rarity-legendary')
    const hasSageClass = classes.includes('rarity-rare')
    console.log('  E.E.V.A. has rarity-legendary: ' + hasArchonClass + ', rarity-rare: ' + hasSageClass)
    expect(hasArchonClass).toBeTruthy()
    expect(hasSageClass).toBeFalsy()

    await eevaCard.hover()
    await page.waitForTimeout(1500)

    await eevaCard.screenshot({
      path: SCREENSHOTS_DIR + '/07b-eeva-archon-hover.png',
    })

    console.log('  Test 7 PASSED: E.E.V.A. (Archon) comparison captured')
  })

  test('8 - Non-Sage comparison: Aegis (Warden) card screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const aegisCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Aegis' }).first()
    const aegisVisible = await aegisCard.isVisible()
    console.log('  Aegis card visible: ' + aegisVisible)
    expect(aegisVisible).toBeTruthy()

    await aegisCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    await aegisCard.screenshot({
      path: SCREENSHOTS_DIR + '/08a-aegis-warden-normal.png',
    })

    const classes = await aegisCard.getAttribute('class') || ''
    const hasWardenClass = classes.includes('rarity-epic')
    console.log('  Aegis has rarity-epic (Warden): ' + hasWardenClass)
    expect(hasWardenClass).toBeTruthy()

    await aegisCard.hover()
    await page.waitForTimeout(1500)

    await aegisCard.screenshot({
      path: SCREENSHOTS_DIR + '/08b-aegis-warden-hover.png',
    })

    console.log('  Test 8 PASSED: Aegis (Warden) comparison captured')
  })
  test('9 - Sage cards have Frost Pulse animation and spinning border', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    const cipherCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Cipher' }).first()
    await cipherCard.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    // Check for spinning border element
    const borderSpin = cipherCard.locator('[class*="border-spin"]')
    const borderSpinCount = await borderSpin.count()
    console.log('  Cipher card border-spin elements: ' + borderSpinCount)
    expect(borderSpinCount).toBeGreaterThan(0)

    // Check for cursor-glare element
    const cursorGlare = cipherCard.locator('[class*="cursor-glare"]')
    const cursorGlareCount = await cursorGlare.count()
    console.log('  Cipher card cursor-glare elements: ' + cursorGlareCount)
    expect(cursorGlareCount).toBeGreaterThan(0)

    // Sage cards should NOT have aurora orbs (Warden + Archon only)
    const auroraOrbs = cipherCard.locator('[class*="aurora-orb"]')
    const auroraOrbCount = await auroraOrbs.count()
    console.log('  Cipher card aurora-orb elements (should be 0): ' + auroraOrbCount)
    expect(auroraOrbCount).toBe(0)

    // Sage cards should NOT have holo-foil
    const holoFoil = cipherCard.locator('[class*="holo-foil"]')
    const holoFoilCount = await holoFoil.count()
    console.log('  Cipher card holo-foil elements (should be 0): ' + holoFoilCount)
    expect(holoFoilCount).toBe(0)

    // Validate Frost Pulse animation
    const animationInfo = await cipherCard.evaluate((el) => {
      const cs = window.getComputedStyle(el)
      return {
        animationName: cs.animationName,
        animationDuration: cs.animationDuration,
        boxShadow: cs.boxShadow,
      }
    })
    console.log('  Cipher Frost Pulse animation: ' + animationInfo.animationName)
    console.log('  Cipher animation duration: ' + animationInfo.animationDuration)
    console.log('  Cipher box-shadow: ' + animationInfo.boxShadow)

    // CSS modules mangle names, so just verify an animation is running at 3s
    expect(animationInfo.animationName).not.toBe('none')
    expect(animationInfo.animationDuration).toBe('3s')

    console.log('  Test 9 PASSED: Sage card CSS effects validated')
  })
  test('10 - Side-by-side visual comparison across all tiers', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1200 })
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/10-tier-comparison-overview.png',
      fullPage: false,
    })

    const tiers = [
      { name: 'Archon (E.E.V.A.)', text: 'E.E.V.A.', cssClass: 'rarity-legendary' },
      { name: 'Warden (Aegis)', text: 'Aegis', cssClass: 'rarity-epic' },
      { name: 'Sage (Cipher)', text: 'Cipher', cssClass: 'rarity-rare' },
    ]

    for (const tier of tiers) {
      const card = page.locator('[class*="card-outer"]').filter({ hasText: tier.text }).first()
      const isVisible = await card.isVisible()
      console.log('  ' + tier.name + ' visible: ' + isVisible)

      if (isVisible) {
        const classes = await card.getAttribute('class') || ''
        const hasExpectedClass = classes.includes(tier.cssClass)
        console.log('  ' + tier.name + ' has ' + tier.cssClass + ': ' + hasExpectedClass)
        expect(hasExpectedClass).toBeTruthy()
      }
    }

    console.log('  Test 10 PASSED: All tiers visually distinct')
  })
})
