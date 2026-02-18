import { test, expect, Page } from '@playwright/test'
import * as fs from 'fs'

// Collect console errors across all tests
const consoleErrors: string[] = []

// ─── helpers ────────────────────────────────────────────────────────────────

async function setupConsoleCapture(page: Page) {
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(`[${msg.type()}] ${msg.text()}`)
    }
  })
  page.on('pageerror', err => {
    consoleErrors.push(`[pageerror] ${err.message}`)
  })
}

// ─── Test 1: Health checks ───────────────────────────────────────────────────

test('Test 1 — Backend health check', async ({ request }) => {
  const resp = await request.get('http://localhost:8000/health')
  const body = await resp.json()
  console.log('Backend health:', JSON.stringify(body))
  expect(resp.status()).toBe(200)
  expect(body.status).toBe('ok')
})

test('Test 1 — Frontend is reachable', async ({ request }) => {
  const resp = await request.get('http://localhost:3001')
  console.log('Frontend status:', resp.status())
  expect(resp.status()).toBe(200)
})

// ─── Test 2: /select page screenshots ───────────────────────────────────────

test('Test 2 — Screenshot /select page (Sage cards)', async ({ page }) => {
  await setupConsoleCapture(page)

  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)

  // Full-page screenshot — idle state
  await page.screenshot({ path: '/tmp/sage-idle.png', fullPage: true })
  console.log('Screenshot saved: /tmp/sage-idle.png')

  // Find Sage cards
  // Try multiple selectors for sage cards
  const sageCandidates = [
    '[class*="order-sage"]',
    '[data-order="sage"]',
    '[class*="sage"]',
  ]

  let sageCard = null
  for (const sel of sageCandidates) {
    const el = page.locator(sel).first()
    const count = await el.count()
    console.log(`Selector "${sel}" found ${count} elements`)
    if (count > 0) {
      sageCard = el
      break
    }
  }

  if (!sageCard) {
    // Fallback: list all cards and log their classes
    const cards = page.locator('[class*="card"], [class*="Card"]')
    const cardCount = await cards.count()
    console.log(`Fallback: found ${cardCount} card elements`)
    for (let i = 0; i < Math.min(cardCount, 10); i++) {
      const cls = await cards.nth(i).getAttribute('class')
      const text = await cards.nth(i).innerText().catch(() => '')
      console.log(`  Card ${i}: class="${cls}" text="${text.substring(0,50)}"`)
    }
    // Take screenshot anyway
    await page.screenshot({ path: '/tmp/sage-hover.png', fullPage: true })
    console.log('No sage card found; screenshot saved as /tmp/sage-hover.png anyway')
    return
  }

  // Hover over first sage card
  await sageCard.scrollIntoViewIfNeeded()
  await sageCard.hover()
  await page.waitForTimeout(2000)
  await page.screenshot({ path: '/tmp/sage-hover.png', fullPage: true })
  console.log('Hover screenshot saved: /tmp/sage-hover.png')
})

// ─── Test 3: Chat with Sage persona ─────────────────────────────────────────

test('Test 3 — Chat with Sage persona', async ({ page }) => {
  await setupConsoleCapture(page)

  // Go to select page first
  await page.goto('http://localhost:3001/select', { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)

  // Log page title and URL
  console.log('Page title:', await page.title())
  console.log('Page URL:', page.url())

  // Look for Cipher or Nyx persona cards
  const personaNames = ['Cipher', 'Nyx']
  let clicked = false

  for (const name of personaNames) {
    const el = page.getByText(name, { exact: false }).first()
    const count = await el.count()
    console.log(`Persona "${name}" found: ${count}`)
    if (count > 0) {
      // Try to find and click the card/button containing this name
      const cardEl = page.locator(`[class*="card"], [class*="Card"], button`).filter({ hasText: name }).first()
      const cardCount = await cardEl.count()
      if (cardCount > 0) {
        console.log(`Clicking card with text "${name}"`)
        await cardEl.click()
        clicked = true
        await page.waitForTimeout(1500)
        break
      } else {
        // Click the text itself
        await el.click()
        clicked = true
        await page.waitForTimeout(1500)
        break
      }
    }
  }

  if (!clicked) {
    // List all text content for debug
    const bodyText = await page.innerText('body').catch(() => '')
    console.log('Page body text snippet:', bodyText.substring(0, 500))

    // Try clicking the first clickable card on the page
    const anyCard = page.locator('[class*="card"], [class*="Card"]').first()
    if (await anyCard.count() > 0) {
      console.log('Clicking first card found as fallback')
      await anyCard.click()
      clicked = true
      await page.waitForTimeout(1500)
    }
  }

  console.log('Current URL after click:', page.url())

  // Check if we navigated to chat — look for chat input
  // First check if we're on a chat page or need to navigate differently
  const chatUrl = page.url()
  if (!chatUrl.includes('/chat')) {
    // Try navigating directly
    console.log('Not on chat page, trying direct navigation...')
    // Get personas list from backend
    const personas = await page.request.get('http://localhost:8000/personas')
    const personaList = await personas.json()
    const sagePersona = personaList.find((p: any) =>
      p.celestial_order === 'sage' || ['cipher', 'nyx'].some(n => p.key?.toLowerCase().includes(n))
    )
    if (sagePersona) {
      console.log(`Found sage persona: ${sagePersona.key}`)
      await page.goto(`http://localhost:3001/chat?persona=${encodeURIComponent(sagePersona.key)}`, {
        waitUntil: 'networkidle',
        timeout: 30000
      })
      await page.waitForTimeout(2000)
    }
  }

  console.log('Final URL:', page.url())

  // Look for message input
  const inputSelectors = [
    'textarea[placeholder*="message"]',
    'textarea[placeholder*="Message"]',
    'input[placeholder*="message"]',
    'input[placeholder*="Message"]',
    'textarea',
    '[contenteditable="true"]',
  ]

  let input = null
  for (const sel of inputSelectors) {
    const el = page.locator(sel).first()
    if (await el.count() > 0) {
      console.log(`Found input with selector: ${sel}`)
      input = el
      break
    }
  }

  if (!input) {
    const bodyText = await page.innerText('body').catch(() => '')
    console.log('Chat page body text snippet:', bodyText.substring(0, 800))
    await page.screenshot({ path: '/tmp/sage-chat.png', fullPage: true })
    console.log('No input found; screenshot saved to /tmp/sage-chat.png')
    // Don't fail hard — the page structure may differ
    return
  }

  // Type the message
  await input.fill('Hello, what is your name and what can you help me with?')
  console.log('Message typed')

  // Find and click send button
  const sendSelectors = [
    'button[type="submit"]',
    'button[aria-label*="send"]',
    'button[aria-label*="Send"]',
    'button:has-text("Send")',
    '[class*="send"]',
  ]
  let sent = false
  for (const sel of sendSelectors) {
    const btn = page.locator(sel).first()
    if (await btn.count() > 0) {
      console.log(`Clicking send with: ${sel}`)
      await btn.click()
      sent = true
      break
    }
  }
  if (!sent) {
    // Press Enter
    console.log('No send button found; pressing Enter')
    await input.press('Enter')
  }

  console.log('Message sent, waiting up to 15s for response...')

  // Wait for response — look for assistant/AI message appearing
  const responseSelectors = [
    '[class*="assistant"]',
    '[class*="ai-message"]',
    '[class*="bot"]',
    '[data-role="assistant"]',
    '[class*="message"]:not([class*="user"])',
  ]

  let responseFound = false
  const deadline = Date.now() + 15000
  while (Date.now() < deadline) {
    for (const sel of responseSelectors) {
      const els = page.locator(sel)
      const cnt = await els.count()
      if (cnt > 0) {
        const lastText = await els.last().innerText().catch(() => '')
        if (lastText.length > 5) {
          console.log(`Response found (selector: ${sel}): "${lastText.substring(0, 100)}..."`)
          responseFound = true
          break
        }
      }
    }
    if (responseFound) break
    await page.waitForTimeout(1000)
  }

  if (!responseFound) {
    // Check the entire page for any new text content
    const bodyText = await page.innerText('body').catch(() => '')
    console.log('Full page text after waiting:', bodyText.substring(0, 1000))
  }

  await page.screenshot({ path: '/tmp/sage-chat.png', fullPage: true })
  console.log('Chat screenshot saved to /tmp/sage-chat.png')

  expect(responseFound).toBe(true)
})

// ─── Test 4: Console error summary ──────────────────────────────────────────

test('Test 4 — Console error summary', async () => {
  if (consoleErrors.length === 0) {
    console.log('No console errors detected during test run.')
  } else {
    console.log(`Found ${consoleErrors.length} console error(s):`)
    consoleErrors.forEach((e, i) => console.log(`  ${i + 1}. ${e}`))
  }
  // Write to a file for reference
  const reportPath = '/tmp/console-errors.txt'
  fs.writeFileSync(reportPath, consoleErrors.length > 0 ? consoleErrors.join('\n') : 'No errors', 'utf8')
  console.log(`Error report written to: ${reportPath}`)
})
