import { test, expect, Page } from '@playwright/test'

const consoleErrors: string[] = []
const consoleWarnings: string[] = []
const consoleLogs: string[] = []

async function setupConsoleCapture(page: Page) {
  page.on('console', msg => {
    const text = `[${msg.type()}] ${msg.text()}`
    if (msg.type() === 'error') consoleErrors.push(text)
    else if (msg.type() === 'warning') consoleWarnings.push(text)
    else consoleLogs.push(text)
  })
  page.on('pageerror', err => {
    consoleErrors.push(`[pageerror] ${err.message}`)
  })
}

test('Chat page — inspect input selectors', async ({ page }) => {
  await setupConsoleCapture(page)

  // Navigate to select, click Cipher, land on chat
  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)

  const cipherCard = page.locator('[class*="card"], [class*="Card"], button').filter({ hasText: 'Cipher' }).first()
  await cipherCard.click()
  await page.waitForTimeout(2000)

  console.log('URL:', page.url())

  // Dump all interactive elements
  const interactives = await page.evaluate(() => {
    const els = document.querySelectorAll('textarea, input[type="text"], [contenteditable="true"], [role="textbox"]')
    return Array.from(els).map(el => ({
      tag: el.tagName,
      type: (el as HTMLInputElement).type || '',
      placeholder: (el as HTMLInputElement).placeholder || '',
      className: el.className,
      id: el.id,
      ariaLabel: el.getAttribute('aria-label') || '',
      visible: (el as HTMLElement).offsetParent !== null,
    }))
  })
  console.log('=== All input/textarea elements ===')
  console.log(JSON.stringify(interactives, null, 2))

  // Dump all buttons
  const buttons = await page.evaluate(() => {
    const els = document.querySelectorAll('button')
    return Array.from(els).map(el => ({
      text: el.textContent?.trim().substring(0, 60) || '',
      className: el.className.substring(0, 80),
      ariaLabel: el.getAttribute('aria-label') || '',
      type: el.type,
      disabled: el.disabled,
    }))
  })
  console.log('=== All buttons ===')
  console.log(JSON.stringify(buttons, null, 2))

  // Check page structure
  const mainContent = await page.evaluate(() => {
    const main = document.querySelector('main') || document.body
    return main.innerHTML.substring(0, 3000)
  })
  console.log('=== Main HTML (first 3000 chars) ===')
  console.log(mainContent)
})

test('Chat page — send message and wait for response', async ({ page }) => {
  await setupConsoleCapture(page)

  // Navigate to chat with Cipher
  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)

  const cipherCard = page.locator('[class*="card"], [class*="Card"], button').filter({ hasText: 'Cipher' }).first()
  await cipherCard.click()
  await page.waitForTimeout(2000)
  console.log('URL after click:', page.url())

  // Wait for chat to be fully loaded - look for the loading states to clear
  // The page shows "Loading Cipher — The Maven..." and "channeling..." text
  // Wait for those to disappear or timeout
  try {
    await page.waitForSelector('text=Loading Cipher', { state: 'hidden', timeout: 15000 })
    console.log('Loading state cleared')
  } catch {
    console.log('Loading state did not clear (may be a static label)')
  }

  await page.waitForTimeout(1000)

  // Get ALL input elements including those inside shadow DOM or iframes
  const allInputsCount = await page.locator('textarea, input, [contenteditable]').count()
  console.log(`Total inputs/textareas on page: ${allInputsCount}`)

  for (let i = 0; i < allInputsCount; i++) {
    const el = page.locator('textarea, input, [contenteditable]').nth(i)
    const tag = await el.evaluate(e => e.tagName)
    const placeholder = await el.getAttribute('placeholder') || ''
    const cls = await el.getAttribute('class') || ''
    const visible = await el.isVisible().catch(() => false)
    console.log(`  Input ${i}: <${tag}> placeholder="${placeholder}" class="${cls.substring(0,60)}" visible=${visible}`)
  }

  // Try each textarea specifically
  const textareas = page.locator('textarea')
  const taCount = await textareas.count()
  console.log(`Textareas found: ${taCount}`)

  if (taCount > 0) {
    for (let i = 0; i < taCount; i++) {
      const ta = textareas.nth(i)
      const placeholder = await ta.getAttribute('placeholder') || ''
      const disabled = await ta.isDisabled().catch(() => false)
      const visible = await ta.isVisible().catch(() => false)
      const enabled = await ta.isEnabled().catch(() => false)
      console.log(`  Textarea ${i}: placeholder="${placeholder}" disabled=${disabled} visible=${visible} enabled=${enabled}`)
    }

    // Use first enabled textarea
    let activeTA = null
    for (let i = 0; i < taCount; i++) {
      const ta = textareas.nth(i)
      const enabled = await ta.isEnabled().catch(() => false)
      const visible = await ta.isVisible().catch(() => false)
      if (enabled && visible) {
        activeTA = ta
        console.log(`Using textarea ${i}`)
        break
      }
    }

    if (activeTA) {
      await activeTA.click()
      await activeTA.fill('Hello, what is your name and what can you help me with?')
      console.log('Message typed successfully')

      // Screenshot before sending
      await page.screenshot({ path: '/tmp/sage-chat-before-send.png', fullPage: true })
      console.log('Before-send screenshot saved to /tmp/sage-chat-before-send.png')

      // Send the message
      await activeTA.press('Enter')
      console.log('Enter pressed to send')

      // Wait for response — up to 20s
      console.log('Waiting for response...')
      let responseText = ''
      const deadline = Date.now() + 20000

      while (Date.now() < deadline) {
        // Look for messages that are from the assistant
        const msgSelectors = [
          '[class*="assistant"]',
          '[class*="ai"]',
          '[class*="bot"]',
          '[data-role="assistant"]',
          '[class*="response"]',
        ]
        for (const sel of msgSelectors) {
          const msgs = page.locator(sel)
          const cnt = await msgs.count()
          if (cnt > 0) {
            const lastText = await msgs.last().innerText().catch(() => '')
            if (lastText.trim().length > 10) {
              responseText = lastText
              console.log(`Response detected (${sel}): "${lastText.substring(0, 150)}"`)
              break
            }
          }
        }
        if (responseText) break
        await page.waitForTimeout(1000)
      }

      // Also check full page text for any new content
      const fullBody = await page.innerText('body').catch(() => '')
      console.log('Page body after wait (first 2000 chars):')
      console.log(fullBody.substring(0, 2000))

      await page.screenshot({ path: '/tmp/sage-chat.png', fullPage: true })
      console.log('Chat screenshot saved to /tmp/sage-chat.png')

      if (!responseText) {
        console.log('WARNING: No response detected within 20s — response may still be loading')
      }
    }
  } else {
    // Take diagnostic screenshot
    await page.screenshot({ path: '/tmp/sage-chat-no-input.png', fullPage: true })
    console.log('ERROR: No textarea found on chat page')
    console.log('Screenshot saved to /tmp/sage-chat-no-input.png')
  }

  // Report console errors
  console.log(`\n=== Console Errors: ${consoleErrors.length} ===`)
  consoleErrors.forEach(e => console.log(e))
  console.log(`=== Console Warnings: ${consoleWarnings.length} ===`)
  consoleWarnings.slice(0, 10).forEach(w => console.log(w))
})

test('Select page — detailed card audit', async ({ page }) => {
  await setupConsoleCapture(page)

  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)

  // Audit all cards on the page
  const cardData = await page.evaluate(() => {
    // Try various card selectors
    const selectors = [
      '[class*="card"]',
      '[class*="Card"]',
      '[class*="persona"]',
      '[class*="character"]',
    ]
    const seen = new Set()
    const results: any[] = []
    for (const sel of selectors) {
      const els = document.querySelectorAll(sel)
      els.forEach(el => {
        if (!seen.has(el)) {
          seen.add(el)
          const rect = el.getBoundingClientRect()
          results.push({
            selector: sel,
            className: el.className.substring(0, 100),
            id: el.id,
            text: (el as HTMLElement).innerText?.substring(0, 100) || '',
            visible: rect.width > 0 && rect.height > 0,
            hasOrderSage: el.className.includes('order-sage') || el.className.includes('sage'),
            hasOrderWarden: el.className.includes('order-warden') || el.className.includes('warden'),
            hasOrderArchon: el.className.includes('order-archon') || el.className.includes('archon'),
            hasOrderWanderer: el.className.includes('order-wanderer') || el.className.includes('wanderer'),
          })
        }
      })
    }
    return results
  })

  console.log(`Total card elements found: ${cardData.length}`)
  console.log(JSON.stringify(cardData, null, 2))

  // Count by order
  const sageCnt = cardData.filter(c => c.hasOrderSage).length
  const wardenCnt = cardData.filter(c => c.hasOrderWarden).length
  const archonCnt = cardData.filter(c => c.hasOrderArchon).length
  const wandererCnt = cardData.filter(c => c.hasOrderWanderer).length
  console.log(`\nOrder counts: sage=${sageCnt} warden=${wardenCnt} archon=${archonCnt} wanderer=${wandererCnt}`)

  // Report errors
  console.log(`\nConsole errors: ${consoleErrors.length}`)
  consoleErrors.forEach(e => console.log(e))
})
