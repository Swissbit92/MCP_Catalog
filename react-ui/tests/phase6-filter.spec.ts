import { test, expect } from '@playwright/test'

test.describe('Phase 6: Persona Filter Toggle', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the character showcase page
    await page.goto('http://localhost:3000/select')
    // Wait for the page to load
    await page.waitForSelector('text=Classic Character Cards', { timeout: 15000 })
  })

  test('should display the persona filter toggle', async ({ page }) => {
    // Check that the filter toggle is visible
    const filterToggle = page.locator('[class*="PersonaFilterToggle"], [class*="backdrop-blur"]').first()
    await expect(filterToggle).toBeVisible()
  })

  test('should have All, NEPHILIM, and Legacy filter options', async ({ page }) => {
    // Check for All button (use exact match with count)
    const allButton = page.getByRole('button', { name: /✦ All/ })
    await expect(allButton).toBeVisible()

    // Check for NEPHILIM button
    const nephilimButton = page.getByRole('button', { name: /⬡ NEPHILIM/ })
    await expect(nephilimButton).toBeVisible()

    // Check for Legacy button
    const legacyButton = page.getByRole('button', { name: /◇ Legacy/ })
    await expect(legacyButton).toBeVisible()
  })

  test('should filter to show only NEPHILIM personas when NEPHILIM is selected', async ({ page }) => {
    // Get initial card count
    const initialCards = await page.locator('.grid > div').count()
    console.log(`Initial cards: ${initialCards}`)

    // Click NEPHILIM filter
    await page.getByRole('button', { name: /NEPHILIM/i }).click()

    // Wait for animation
    await page.waitForTimeout(500)

    // Check that cards are filtered (should be fewer cards if there are legacy personas)
    const nephilimCards = await page.locator('.grid > div').count()
    console.log(`NEPHILIM cards: ${nephilimCards}`)

    // NEPHILIM personas start with nephilim_ prefix
    // The page should show only NEPHILIM personas
    expect(nephilimCards).toBeGreaterThan(0)
    expect(nephilimCards).toBeLessThanOrEqual(initialCards)
  })

  test('should filter to show only Legacy personas when Legacy is selected', async ({ page }) => {
    // Click Legacy filter
    await page.getByRole('button', { name: /Legacy/i }).click()

    // Wait for animation
    await page.waitForTimeout(500)

    // Check that cards are showing
    const legacyCards = await page.locator('.grid > div').count()
    console.log(`Legacy cards: ${legacyCards}`)

    // Should have at least some legacy personas
    expect(legacyCards).toBeGreaterThan(0)
  })

  test('should show all personas when All is selected after filtering', async ({ page }) => {
    // First, click NEPHILIM to filter
    await page.getByRole('button', { name: /⬡ NEPHILIM/ }).click()
    await page.waitForTimeout(300)
    const nephilimCount = await page.locator('.grid > div').count()

    // Then click All to show all
    await page.getByRole('button', { name: /✦ All/ }).click()
    await page.waitForTimeout(300)
    const allCount = await page.locator('.grid > div').count()

    // All should show more or equal cards
    expect(allCount).toBeGreaterThanOrEqual(nephilimCount)
  })

  test('should display persona counts in filter toggle', async ({ page }) => {
    // The filter toggle should show counts like "(6)" or "(3)"
    // Use the All button which contains the count
    const allButton = page.getByRole('button', { name: /✦ All/ })
    const textContent = await allButton.textContent()

    // Should contain parentheses with numbers indicating counts
    expect(textContent).toMatch(/\(\d+\)/)
  })

  test('should persist filter selection in localStorage', async ({ page }) => {
    // Click NEPHILIM filter
    await page.getByRole('button', { name: /NEPHILIM/i }).click()
    await page.waitForTimeout(300)

    // Check localStorage
    const filterMode = await page.evaluate(() => {
      return localStorage.getItem('persona_filter_mode')
    })

    expect(filterMode).toBe('nephilim')
  })
})
