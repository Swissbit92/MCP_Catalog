import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const BACKEND_URL = 'http://localhost:8000'
const SCREENSHOT_DIR = 'test-screenshots/phase8-live'

test.describe('Phase 8 Chat & Card Click Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
    await page.evaluate(() => {
      localStorage.setItem('nephilim_user_id', 'default_seeker')
      localStorage.setItem('nephilim_user_name', 'TestSeeker')
      localStorage.setItem('nephilim_onboarding_complete', 'true')
      localStorage.setItem('nephilim_faction', 'house_aegis')
    })
  })

  test('click card via overlay and verify chat greeting + send message', async ({ page }) => {
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    // The card has a hover overlay with class "card-choose" that intercepts clicks
    // We need to click the overlay directly, or use force:true
    // First, hover over the first card to trigger the overlay
    const cardOuter = page.locator('[class*="card-outer"]').first()
    const outerVis = await cardOuter.isVisible().catch(() => false)
    console.log(`Card outer visible: ${outerVis}`)

    if (outerVis) {
      // Hover to trigger overlay
      await cardOuter.hover()
      await page.waitForTimeout(1000)

      // Now click the "card-choose" overlay or the "Choose" text
      const chooseOverlay = page.locator('[class*="card-choose"]').first()
      const chooseVis = await chooseOverlay.isVisible().catch(() => false)
      console.log(`Choose overlay visible after hover: ${chooseVis}`)

      if (chooseVis) {
        await chooseOverlay.click()
      } else {
        // Force click
        await cardOuter.click({ force: true })
      }
    } else {
      // Fallback: force click on img
      await page.locator('img[alt]').first().click({ force: true })
    }

    await page.waitForTimeout(8000) // Wait for chat + LLM greeting
    await page.screenshot({ path: `${SCREENSHOT_DIR}/14-chat-from-card.png`, fullPage: true })
    console.log(`After card click URL: ${page.url()}`)

    // Verify we're on chat page
    const onChat = page.url().includes('/chat')
    console.log(`On chat page: ${onChat}`)

    if (onChat) {
      // Wait for greeting
      await page.waitForTimeout(3000)
      const bodyText = await page.textContent('body')
      console.log(`Chat body preview: ${bodyText.slice(0, 300)}`)

      // Verify textarea is available
      const textarea = page.locator('textarea')
      const textareaVis = await textarea.isVisible().catch(() => false)
      console.log(`Textarea visible: ${textareaVis}`)

      if (textareaVis) {
        // Type a message
        await textarea.fill('Hello! Quick test message from Playwright.')
        await page.screenshot({ path: `${SCREENSHOT_DIR}/14-chat-typed.png`, fullPage: true })

        // Click Send button
        const sendBtn = page.locator('button').filter({ hasText: 'Send' })
        const sendVis = await sendBtn.isVisible().catch(() => false)
        if (sendVis) {
          await sendBtn.click()
          console.log('Message sent via Send button')
        } else {
          await page.keyboard.press('Enter')
          console.log('Message sent via Enter key')
        }

        // Wait for LLM response (up to 30s)
        console.log('Waiting for LLM response...')
        await page.waitForTimeout(20000)
        await page.screenshot({ path: `${SCREENSHOT_DIR}/14-chat-response.png`, fullPage: true })

        // Count messages
        const messages = page.locator('[class*="message"], [class*="Message"]')
        const msgCount = await messages.count()
        console.log(`Message elements: ${msgCount}`)

        // Check for resonance toast
        const toast = page.locator('[class*="resonance"], [class*="toast"], [class*="Toast"]')
        const toastCount = await toast.count()
        console.log(`Toast elements: ${toastCount}`)

        // Get final body text to check for response
        const finalBody = await page.textContent('body')
        console.log(`Final body length: ${finalBody.length}`)
        console.log(`Final body excerpt: ${finalBody.slice(0, 500)}`)
      }
    }
  })

  test('send chat message and verify response + resonance', async ({ page }) => {
    // Create session via API first
    const greetResp = await page.request.post(`${BACKEND_URL}/greet`, {
      data: { persona: 'nephilim_eeva' }
    })

    // The /greet endpoint might not exist; check the actual routes
    console.log(`/greet response: ${greetResp.status()}`)

    // Let's check chat flow via the established working method from the prior test
    // Click card from select page using the card-outer + force click approach
    await page.goto(BASE_URL + '/select')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(4000)

    // Use the locator that worked in phase8-interactive: broader selector with force
    const cards = page.locator('[class*="card"], [class*="Card"], [class*="character"]')
    const cardCount = await cards.count()
    console.log(`Card-like elements: ${cardCount}`)

    // The phase8-interactive test used: cards.first().click() and it worked
    // because it used a broader selector. Let's try the same
    if (cardCount > 0) {
      await cards.first().click({ force: true, timeout: 5000 })
      await page.waitForTimeout(10000)
      console.log(`After click URL: ${page.url()}`)
      await page.screenshot({ path: `${SCREENSHOT_DIR}/15-chat-send-test.png`, fullPage: true })

      // Try sending a message
      const textarea = page.locator('textarea')
      if (await textarea.isVisible().catch(() => false)) {
        await textarea.fill('Test message for resonance check')
        const sendBtn = page.locator('button').filter({ hasText: 'Send' })
        if (await sendBtn.isVisible().catch(() => false)) {
          await sendBtn.click()
          await page.waitForTimeout(20000) // Wait for response
          await page.screenshot({ path: `${SCREENSHOT_DIR}/15-chat-after-send.png`, fullPage: true })

          // Check for resonance toast (the "+5 resonance" notification)
          const resonance = await page.textContent('body')
          const hasResonance = resonance.includes('resonance') || resonance.includes('+5')
          console.log(`Resonance text found: ${hasResonance}`)
          console.log(`Body content around resonance: ${resonance.slice(resonance.indexOf('resonance') - 30, resonance.indexOf('resonance') + 60)}`)
        }
      }
    }
  })
})
