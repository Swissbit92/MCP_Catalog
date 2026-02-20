import { test, expect, Page } from '@playwright/test'

const consoleErrors: string[] = []
const consoleWarnings: string[] = []

async function setupConsoleCapture(page: Page) {
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(`[error] ${msg.text()}`)
    if (msg.type() === 'warning') consoleWarnings.push(`[warn] ${msg.text()}`)
  })
  page.on('pageerror', err => consoleErrors.push(`[pageerror] ${err.message}`))
}

test('Test 3 — Chat with Cipher (Sage) using correct input selector', async ({ page }) => {
  test.setTimeout(60000)
  await setupConsoleCapture(page)

  // Navigate to select page and pick Cipher
  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)

  // Click Cipher card
  const cipherCard = page.locator('[class*="card-outer"]').filter({ hasText: 'Cipher' }).first()
  await cipherCard.click()
  await page.waitForTimeout(2000)
  console.log('URL after click:', page.url())

  // Wait for persona greeting to load
  try {
    await page.waitForSelector('text=Loading Cipher', { state: 'hidden', timeout: 10000 })
    console.log('Greeting loaded')
  } catch {
    console.log('Greeting load timeout (possibly already loaded)')
  }
  await page.waitForTimeout(1000)

  // The chat input is <input type="text" placeholder="Type a message...">
  const chatInput = page.locator('input[placeholder="Type a message..."]')
  await expect(chatInput).toBeVisible({ timeout: 10000 })
  console.log('Chat input found and visible')

  // Check if input is enabled (may be disabled during greeting)
  const isDisabled = await chatInput.isDisabled()
  console.log(`Input disabled: ${isDisabled}`)
  if (isDisabled) {
    console.log('Waiting for input to become enabled...')
    await page.waitForFunction(() => {
      const inp = document.querySelector('input[placeholder="Type a message..."]') as HTMLInputElement
      return inp && !inp.disabled
    }, { timeout: 15000 })
    console.log('Input is now enabled')
  }

  // Type the message
  await chatInput.click()
  await chatInput.fill('Hello, what is your name and what can you help me with?')
  console.log('Message typed')

  // Screenshot before sending
  await page.screenshot({ path: '/tmp/sage-chat-before-send.png', fullPage: true })
  console.log('Before-send screenshot: /tmp/sage-chat-before-send.png')

  // Find the Send button (it's currently disabled because input was empty, but now has content)
  // The button: "Send➤" with class containing bg-cyan-500
  const sendBtn = page.locator('button:has-text("Send")').last()
  const sendBtnCount = await sendBtn.count()
  console.log(`Send buttons found: ${sendBtnCount}`)

  if (sendBtnCount > 0) {
    const disabled = await sendBtn.isDisabled()
    console.log(`Send button disabled: ${disabled}`)
    await sendBtn.click({ force: !disabled })
    console.log('Send button clicked')
  } else {
    await chatInput.press('Enter')
    console.log('Pressed Enter to send')
  }

  console.log('Waiting up to 25s for AI response...')

  // Wait for a response message to appear
  // The chat renders messages - look for any message bubble from the assistant
  // Based on Chat.tsx structure, messages appear in the message list
  let responseText = ''
  const deadline = Date.now() + 25000

  while (Date.now() < deadline) {
    await page.waitForTimeout(1000)

    // Check page text for response indicators
    const bodyText = await page.innerText('body').catch(() => '')

    // Look for the input to be re-enabled (usually means response is done)
    const inputEnabled = await chatInput.isEnabled().catch(() => false)

    // Look for message content that isn't the user message
    // Messages usually appear in divs with message-like classes
    const msgElements = await page.evaluate(() => {
      // Find elements that might be message bubbles
      const selectors = [
        '[class*="message"]',
        '[class*="bubble"]',
        '[class*="assistant"]',
        '[class*="msg"]',
      ]
      const results: string[] = []
      for (const sel of selectors) {
        const els = document.querySelectorAll(sel)
        els.forEach(el => {
          const text = (el as HTMLElement).innerText?.trim()
          if (text && text.length > 10 && !text.includes('Type a message')) {
            results.push(`[${sel}] "${text.substring(0, 80)}"`)
          }
        })
      }
      return results
    })

    if (msgElements.length > 0) {
      console.log('Message elements found:')
      msgElements.forEach(m => console.log(' ', m))
    }

    // Check if input was re-enabled after typing+sending — indicates response cycle complete
    if (inputEnabled) {
      // Check if the page has more content than just the user message
      const pageText = await page.innerText('body').catch(() => '')
      if (pageText.includes('Hello, what is your name')) {
        // User message is there; check if there's also a response
        if (pageText.length > 1000) { // arbitrary threshold — response added content
          responseText = 'Response detected via page content length'
          console.log('Response likely present (page has substantial content)')
          break
        }
      }
    }
  }

  // Final screenshot of the chat
  await page.screenshot({ path: '/tmp/sage-chat.png', fullPage: true })
  console.log('Final chat screenshot: /tmp/sage-chat.png')

  // Print the full page text for analysis
  const finalBodyText = await page.innerText('body').catch(() => '')
  console.log('\n=== Final page content (first 2000 chars) ===')
  console.log(finalBodyText.substring(0, 2000))

  console.log(`\n=== Console Errors (${consoleErrors.length}) ===`)
  consoleErrors.forEach(e => console.log(e))
  console.log(`=== Console Warnings (${consoleWarnings.length}) ===`)
  consoleWarnings.slice(0, 5).forEach(w => console.log(w))
})

test('Test 4 — Check for console errors on /select and /chat', async ({ page }) => {
  const errors: string[] = []
  const warnings: string[] = []

  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(`[error] ${msg.text()}`)
    if (msg.type() === 'warning') warnings.push(`[warn] ${msg.text()}`)
  })
  page.on('pageerror', err => errors.push(`[pageerror] ${err.message}`))

  // Test /select page
  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)

  // Test /chat page
  await page.goto('http://localhost:3001/chat', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)

  // Test / (home)
  await page.goto('http://localhost:3001/', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)

  console.log(`\n=== Browser Console Errors: ${errors.length} ===`)
  errors.forEach(e => console.log(e))
  console.log(`=== Browser Console Warnings: ${warnings.length} ===`)
  warnings.slice(0, 10).forEach(w => console.log(w))

  if (errors.length > 0) {
    console.log('ISSUES FOUND: Console errors detected')
  } else {
    console.log('CLEAN: No console errors detected across /, /select, /chat')
  }
})
