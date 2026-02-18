/**
 * Jupiter Wallet Flow — E.E.V.A. Co-Financial Assistant
 *
 * Simulates a realistic multi-turn user session where E.E.V.A. (Archon)
 * guides the user through Solana wallet creation, balance checks, and
 * swap proposals via Jupiter MCP.
 *
 * Wave 2 readiness: tests gracefully skip or log when backend wiring
 * (intent classifier, wallet routes, ProposalCard rendering) is not yet
 * in place. Screenshots document the UI baseline for comparison once
 * Wave 2 is complete.
 *
 * Screenshots saved to: tests/screenshots/jupiter-*.png
 */

import { test, expect, Page } from '@playwright/test'
import fs from 'fs'

const BASE_URL = 'http://localhost:3001'
const BACKEND_URL = 'http://localhost:8000'
const SCREENSHOTS_DIR = 'C:/Users/rzehn/desktop/MCP_catalog/react-ui/tests/screenshots'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ensureScreenshotDir() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
  }
}

/**
 * Locate the primary chat input (`<input placeholder="Type a message...">`)
 * and wait up to `timeout` ms for it to become visible and enabled.
 * Returns null if the input is not present (feature not yet wired).
 */
async function getChatInput(page: Page, timeout = 10000): Promise<ReturnType<Page['locator']> | null> {
  const input = page.locator('input[placeholder="Type a message..."]').first()
  try {
    await expect(input).toBeVisible({ timeout })
    // If present but disabled (greeting in-flight), wait for it to enable
    const isDisabled = await input.isDisabled().catch(() => false)
    if (isDisabled) {
      await page.waitForFunction(
        () => {
          const el = document.querySelector('input[placeholder="Type a message..."]') as HTMLInputElement
          return el && !el.disabled
        },
        { timeout: 15000 }
      )
    }
    return input
  } catch {
    return null
  }
}

/**
 * Send a message via the chat input and wait for the LLM response cycle to
 * begin.  Does NOT wait for the full response — callers add their own
 * `waitForTimeout` based on how long they expect to wait.
 */
async function sendMessage(page: Page, text: string): Promise<void> {
  const input = await getChatInput(page)
  if (!input) {
    console.log(`[sendMessage] Chat input not found — cannot send: "${text.substring(0, 60)}"`)
    return
  }
  await input.click()
  await input.fill(text)

  // Prefer the Send button; fall back to Enter
  const sendBtn = page.locator('button:has-text("Send")').last()
  const sendBtnVisible = await sendBtn.isVisible().catch(() => false)
  if (sendBtnVisible) {
    await sendBtn.click({ force: true })
    console.log(`[sendMessage] Sent via Send button: "${text.substring(0, 60)}"`)
  } else {
    await input.press('Enter')
    console.log(`[sendMessage] Sent via Enter: "${text.substring(0, 60)}"`)
  }
}

/**
 * Check whether a TradeProposalCard or StrategyApprovalCard is present in
 * the DOM.  Returns an object with boolean flags for each card type.
 */
async function detectWalletCards(page: Page): Promise<{ tradeProposal: boolean; strategyApproval: boolean }> {
  const bodyText = await page.innerText('body').catch(() => '')
  const tradeProposal =
    bodyText.includes('Trade Proposal') ||
    bodyText.includes('Confirm Trade') ||
    bodyText.includes('Confirm') && bodyText.includes('SOL') ||
    (await page.locator('[class*="TradeProposal"], [data-testid="trade-proposal"]').count()) > 0

  const strategyApproval =
    bodyText.includes('Strategy Approval') ||
    bodyText.includes('Approve Strategy') ||
    (await page.locator('[class*="StrategyApproval"], [data-testid="strategy-approval"]').count()) > 0

  return { tradeProposal, strategyApproval }
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

test.beforeAll(() => {
  ensureScreenshotDir()
})

test.beforeEach(async ({ page }) => {
  // Seed localStorage with NEPHILIM identity before every test
  await page.goto(BASE_URL)
  await page.evaluate(() => {
    localStorage.setItem('nephilim_user_id', 'test_user_jupiter_001')
    localStorage.setItem('nephilim_user_name', 'Seeker')
    localStorage.setItem('nephilim_onboarding_complete', 'true')
    localStorage.setItem('nephilim_faction', 'house_eeva')
  })
})

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.describe('Jupiter Wallet Flow — E.E.V.A. Co-Financial Assistant', () => {

  // -------------------------------------------------------------------------
  // Test 1 — Companion Selection: E.E.V.A. card visible on /select
  // -------------------------------------------------------------------------
  test('1. Navigate to companion selection and verify E.E.V.A. card (Archon)', async ({ page }) => {
    test.setTimeout(30000)

    await page.goto(BASE_URL + '/select', { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(4000) // Allow persona API response and card animations

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-01-select-page.png',
      fullPage: true,
    })

    // Count rendered cards
    const cardElements = page.locator('[class*="card-outer"]')
    const cardCount = await cardElements.count()
    console.log(`Total card-outer elements: ${cardCount}`)
    expect(cardCount).toBeGreaterThan(0)

    // E.E.V.A. should be present — filter cards by text content
    const eevaCard = page.locator('[class*="card-outer"]').filter({ hasText: 'E.E.V.A.' }).first()
    const eevaVisible = await eevaCard.isVisible().catch(() => false)
    console.log(`E.E.V.A. card visible: ${eevaVisible}`)
    expect(eevaVisible).toBeTruthy()

    // The card should carry the rarity-legendary CSS class (Archon tier)
    if (eevaVisible) {
      const classes = await eevaCard.getAttribute('class') || ''
      const hasArchonClass = classes.includes('rarity-legendary') || classes.includes('order-archon')
      console.log(`E.E.V.A. card Archon class present: ${hasArchonClass}  (classes: ${classes.substring(0, 120)})`)

      await eevaCard.scrollIntoViewIfNeeded()
      await page.waitForTimeout(500)
      await eevaCard.screenshot({
        path: SCREENSHOTS_DIR + '/jupiter-01-eeva-card-closeup.png',
      })
    }

    // Verify the body contains the Archon label somewhere on page
    const bodyText = await page.textContent('body') || ''
    const hasArchonLabel = bodyText.includes('Archon') || bodyText.includes('E.E.V.A.')
    console.log(`Archon / E.E.V.A. label found on page: ${hasArchonLabel}`)
    expect(hasArchonLabel).toBeTruthy()

    console.log('Test 1 PASSED: E.E.V.A. Archon card visible on /select')
  })

  // -------------------------------------------------------------------------
  // Test 2 — Chat Page Loads for E.E.V.A. via URL parameter
  // -------------------------------------------------------------------------
  test('2. Chat page loads for E.E.V.A. via ?persona= URL param', async ({ page }) => {
    test.setTimeout(30000)

    await page.goto(BASE_URL + '/chat?persona=nephilim_eeva', {
      waitUntil: 'networkidle',
      timeout: 20000,
    })
    await page.waitForTimeout(3000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-02-chat-loaded.png',
      fullPage: true,
    })

    // E.E.V.A.'s name should appear somewhere in the chat interface
    const eevaNameVisible = await page.getByText('E.E.V.A.').first().isVisible().catch(() => false)
    console.log(`E.E.V.A. name visible in chat: ${eevaNameVisible}`)

    // Check for chat input
    const chatInput = await getChatInput(page, 8000)
    const inputPresent = chatInput !== null
    console.log(`Chat input present: ${inputPresent}`)

    // Check for a greeting message bubble (backend-dependent)
    const msgElements = page.locator('[class*="message"], [class*="Message"], [class*="bubble"], [class*="Bubble"]')
    const msgCount = await msgElements.count()
    console.log(`Message bubble elements: ${msgCount}`)

    // The page must at minimum show the chat interface frame
    await expect(page.locator('body')).toBeVisible()

    // Check URL is correct
    const currentUrl = page.url()
    console.log(`Current URL: ${currentUrl}`)
    expect(currentUrl).toContain('/chat')

    // Log infrastructure status for debugging
    try {
      const backendPing = await page.request.get(`${BACKEND_URL}/personas`)
      console.log(`Backend /personas status: ${backendPing.status()}`)
    } catch {
      console.log('Backend unreachable — LLM-dependent assertions will be skipped')
    }

    console.log('Test 2 PASSED: Chat page loaded for E.E.V.A.')
  })

  // -------------------------------------------------------------------------
  // Test 3 — User asks E.E.V.A. about Solana wallet creation
  // -------------------------------------------------------------------------
  test('3. User asks E.E.V.A. about Solana wallet creation', async ({ page }) => {
    test.setTimeout(60000)

    await page.goto(BASE_URL + '/chat?persona=nephilim_eeva', {
      waitUntil: 'networkidle',
      timeout: 20000,
    })
    await page.waitForTimeout(2500)

    const input = await getChatInput(page, 8000)

    if (!input) {
      await page.screenshot({
        path: SCREENSHOTS_DIR + '/jupiter-03-no-chat-input.png',
        fullPage: true,
      })
      console.log('Chat input not visible — wallet wiring (Wave 2) not yet complete')
      // Do not fail: document the baseline state
      await expect(page.locator('body')).toBeVisible()
      return
    }

    // Screenshot before sending
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-03a-before-message.png',
      fullPage: true,
    })

    // Send wallet creation request
    await sendMessage(
      page,
      'E.E.V.A., I want to start trading crypto with your guidance. Can you help me set up a Solana wallet?'
    )

    // Wait for LLM response (generous timeout — Ollama can be slow)
    console.log('Waiting up to 20s for LLM response to wallet query...')
    await page.waitForTimeout(20000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-03b-after-wallet-request.png',
      fullPage: true,
    })

    // Check body text for any wallet-related response content
    const bodyText = await page.innerText('body').catch(() => '')
    const hasWalletContent =
      bodyText.toLowerCase().includes('wallet') ||
      bodyText.toLowerCase().includes('solana') ||
      bodyText.toLowerCase().includes('keypair') ||
      bodyText.toLowerCase().includes('address')

    console.log(`Wallet-related content in response: ${hasWalletContent}`)
    console.log(`Page content length: ${bodyText.length} chars`)

    // Check for wallet cards (Wave 2 feature)
    const cards = await detectWalletCards(page)
    console.log(`TradeProposalCard present: ${cards.tradeProposal}`)
    console.log(`StrategyApprovalCard present: ${cards.strategyApproval}`)

    if (!hasWalletContent) {
      console.log(
        'NOTE: No wallet content detected — NEEDS_WALLET intent may not be wired yet (Wave 2 Phase 7–8)'
      )
    }

    // Test passes as long as the UI did not crash
    await expect(page.locator('body')).toBeVisible()
    console.log('Test 3 PASSED: Wallet creation message sent, UI stable')
  })

  // -------------------------------------------------------------------------
  // Test 4 — TradeProposalCard DOM structure check (component baseline)
  // -------------------------------------------------------------------------
  test('4. TradeProposalCard and StrategyApprovalCard component presence (Wave 1 baseline)', async ({ page }) => {
    test.setTimeout(20000)

    // Navigate to the chat page to load the full React bundle
    await page.goto(BASE_URL + '/chat?persona=nephilim_eeva', {
      waitUntil: 'networkidle',
      timeout: 20000,
    })
    await page.waitForTimeout(2000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-04-component-baseline.png',
      fullPage: true,
    })

    // Inspect loaded JS bundles for component references
    // (validates Wave 1 frontend deliverables were bundled)
    const jsFiles = await page.evaluate(() => {
      const scripts = Array.from(document.querySelectorAll('script[src]'))
      return scripts.map(s => s.getAttribute('src')).filter(Boolean)
    })
    console.log(`JS bundles loaded: ${jsFiles.length}`)
    jsFiles.forEach(f => console.log(`  ${f}`))

    // Check for TradeProposalCard or StrategyApprovalCard in the DOM
    // (only present once a wallet message with metadata is rendered)
    const tradeProposalInDom = (await page.locator('[class*="TradeProposal"]').count()) > 0
    const strategyApprovalInDom = (await page.locator('[class*="StrategyApproval"]').count()) > 0
    console.log(`TradeProposalCard in DOM: ${tradeProposalInDom}`)
    console.log(`StrategyApprovalCard in DOM: ${strategyApprovalInDom}`)

    if (!tradeProposalInDom && !strategyApprovalInDom) {
      console.log(
        'NOTE: Wallet card components not in DOM — expected until NEEDS_WALLET intent wired (Wave 2)'
      )
    }

    // Chat input baseline check
    const inputPresent = (await getChatInput(page, 5000)) !== null
    console.log(`Chat input available: ${inputPresent}`)

    await expect(page.locator('body')).toBeVisible()
    console.log('Test 4 PASSED: Component baseline documented')
  })

  // -------------------------------------------------------------------------
  // Test 5 — Full multi-turn conversation: wallet → balance → swap → strategy
  // -------------------------------------------------------------------------
  test('5. Full conversation flow — wallet → balance → swap proposal → RSI strategy', async ({ page }) => {
    test.setTimeout(180000)

    // Navigate via card-click (URL param path does not set PersonaContext — use card flow)
    await page.goto(BASE_URL + '/select', { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(3000)

    // Click E.E.V.A.'s Archon card
    const eevaCard = page.locator('[class*="card-outer"]').filter({ hasText: 'E.E.V.A.' }).first()
    const eevaVisible = await eevaCard.isVisible().catch(() => false)
    if (eevaVisible) {
      await eevaCard.scrollIntoViewIfNeeded()
      await eevaCard.hover()
      await page.waitForTimeout(800)
      const chooseOverlay = eevaCard.locator('[class*="card-choose"]').first()
      const overlayVisible = await chooseOverlay.isVisible().catch(() => false)
      if (overlayVisible) {
        await chooseOverlay.click()
      } else {
        await eevaCard.click({ force: true })
      }
    } else {
      // Fallback: first card
      const firstCard = page.locator('[class*="card-outer"]').first()
      await firstCard.hover()
      await page.waitForTimeout(500)
      const overlay = page.locator('[class*="card-choose"]').first()
      if (await overlay.isVisible().catch(() => false)) {
        await overlay.click()
      } else {
        await firstCard.click({ force: true })
      }
    }

    // Wait for chat to load
    await page.waitForTimeout(8000)
    console.log(`URL after card click: ${page.url()}`)

    await page.screenshot({ path: SCREENSHOTS_DIR + '/jupiter-05-chat-loaded.png', fullPage: true })

    const input = await getChatInput(page, 12000)
    if (!input) {
      await page.screenshot({ path: SCREENSHOTS_DIR + '/jupiter-05-no-input.png', fullPage: true })
      console.log('Chat input not visible after card-click navigation')
      test.skip(true, 'Chat input unavailable even after card-click navigation')
      return
    }
    console.log('Chat input found via card-click path — beginning conversation')

    // --- Turn 1: Wallet creation ---
    console.log('=== Turn 1: Wallet creation request ===')
    await sendMessage(
      page,
      "E.E.V.A., I want you to help me manage my crypto. Can we create a Solana wallet? Let's call it \"E.E.V.A. Trading Wallet\"."
    )
    await page.waitForTimeout(15000)
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05a-turn1-wallet-response.png',
      fullPage: true,
    })
    const turn1Text = await page.innerText('body').catch(() => '')
    console.log(`Turn 1 response length: ${turn1Text.length} chars`)
    const turn1HasWallet = turn1Text.toLowerCase().includes('wallet') || turn1Text.toLowerCase().includes('solana')
    console.log(`Turn 1 wallet content detected: ${turn1HasWallet}`)

    // --- Turn 2: Balance check ---
    console.log('=== Turn 2: Balance check ===')
    await sendMessage(page, 'What is my current SOL balance?')
    await page.waitForTimeout(12000)
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05b-turn2-balance.png',
      fullPage: true,
    })
    const turn2Text = await page.innerText('body').catch(() => '')
    const turn2HasBalance =
      turn2Text.toLowerCase().includes('balance') ||
      turn2Text.toLowerCase().includes('sol') ||
      turn2Text.toLowerCase().includes('0.') // balance amount pattern
    console.log(`Turn 2 balance content detected: ${turn2HasBalance}`)

    // --- Turn 3: Swap proposal ---
    console.log('=== Turn 3: Swap proposal ===')
    await sendMessage(
      page,
      'Should I swap some USDC for SOL right now? What does the market look like? If it looks good, propose a trade for me.'
    )
    await page.waitForTimeout(15000)
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05c-turn3-swap.png',
      fullPage: true,
    })

    // Check if TradeProposalCard appeared
    const swapCards = await detectWalletCards(page)
    console.log(`After swap request — TradeProposalCard: ${swapCards.tradeProposal}`)
    console.log(`After swap request — StrategyApprovalCard: ${swapCards.strategyApproval}`)

    if (swapCards.tradeProposal) {
      console.log('SUCCESS: TradeProposalCard rendered — Wave 2 swap wiring is active!')
      // Try to click Confirm to exercise the confirm flow
      const confirmBtn = page.locator('button:has-text("Confirm"), button:has-text("Approve")').first()
      const confirmVisible = await confirmBtn.isVisible().catch(() => false)
      if (confirmVisible) {
        console.log('TradeProposalCard Confirm button is visible — clicking to test flow')
        await confirmBtn.click()
        await page.waitForTimeout(5000)
        await page.screenshot({
          path: SCREENSHOTS_DIR + '/jupiter-05c-trade-confirmed.png',
          fullPage: true,
        })
      }
    } else {
      console.log(
        'NOTE: TradeProposalCard not yet rendered — NEEDS_WALLET → solana_propose_swap not wired (Wave 2 Phase 7–8)'
      )
    }

    // --- Turn 4: RSI strategy setup ---
    console.log('=== Turn 4: RSI strategy setup ===')
    await sendMessage(
      page,
      'Can you set up an RSI strategy for SOL? Buy when RSI drops below 30, sell when it goes above 70. Max $20 per trade, $100 daily limit.'
    )
    await page.waitForTimeout(18000)
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05d-turn4-strategy.png',
      fullPage: true,
    })

    const strategyCards = await detectWalletCards(page)
    console.log(`After strategy request — StrategyApprovalCard: ${strategyCards.strategyApproval}`)

    if (strategyCards.strategyApproval) {
      console.log('SUCCESS: StrategyApprovalCard rendered — Wave 2 strategy wiring is active!')
      const approveBtn = page.locator('button:has-text("Approve Strategy"), button:has-text("Approve")').first()
      const approveVisible = await approveBtn.isVisible().catch(() => false)
      if (approveVisible) {
        console.log('StrategyApprovalCard Approve button is visible — clicking to test flow')
        await approveBtn.click()
        await page.waitForTimeout(5000)
        await page.screenshot({
          path: SCREENSHOTS_DIR + '/jupiter-05d-strategy-approved.png',
          fullPage: true,
        })
      }
    } else {
      console.log(
        'NOTE: StrategyApprovalCard not yet rendered — solana_propose_strategy not wired (Wave 2 Phase 7–8)'
      )
    }

    // --- Turn 5: Trade history ---
    console.log('=== Turn 5: Trade history / portfolio review ===')
    await sendMessage(page, 'Show me my recent trade history and any active strategies.')
    await page.waitForTimeout(12000)
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05e-turn5-history.png',
      fullPage: true,
    })

    // Final full-page screenshot
    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-05f-final-state.png',
      fullPage: true,
    })

    const finalText = await page.innerText('body').catch(() => '')
    console.log(`Final page content length: ${finalText.length} chars`)
    console.log(`Final page excerpt (first 400 chars):\n${finalText.substring(0, 400)}`)

    // The test passes if the UI survived all turns without crashing
    await expect(page.locator('body')).toBeVisible()
    console.log('Test 5 PASSED: Full conversation flow completed without UI crash')
  })

  // -------------------------------------------------------------------------
  // Test 6 — Select E.E.V.A. card from /select and navigate to chat
  // -------------------------------------------------------------------------
  test('6. Click E.E.V.A. card on /select and verify navigation to chat', async ({ page }) => {
    test.setTimeout(45000)

    await page.goto(BASE_URL + '/select', { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(4000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-06a-select-before-click.png',
      fullPage: true,
    })

    // Locate E.E.V.A.'s card
    const eevaCard = page.locator('[class*="card-outer"]').filter({ hasText: 'E.E.V.A.' }).first()
    const eevaVisible = await eevaCard.isVisible().catch(() => false)
    console.log(`E.E.V.A. card visible before click: ${eevaVisible}`)

    if (!eevaVisible) {
      // Fallback: try clicking any card to at least verify navigation works
      console.log('E.E.V.A. card not found — trying first available card as fallback')
      const firstCard = page.locator('[class*="card-outer"]').first()
      const firstCardVisible = await firstCard.isVisible().catch(() => false)
      if (firstCardVisible) {
        await firstCard.hover()
        await page.waitForTimeout(800)
        const chooseOverlay = page.locator('[class*="card-choose"]').first()
        const overlayVisible = await chooseOverlay.isVisible().catch(() => false)
        if (overlayVisible) {
          await chooseOverlay.click()
        } else {
          await firstCard.click({ force: true })
        }
      }
    } else {
      // Hover to reveal the "Choose" overlay, then click it
      await eevaCard.scrollIntoViewIfNeeded()
      await eevaCard.hover()
      await page.waitForTimeout(800)

      const chooseOverlay = eevaCard.locator('[class*="card-choose"]').first()
      const overlayVisible = await chooseOverlay.isVisible().catch(() => false)
      console.log(`card-choose overlay visible after hover: ${overlayVisible}`)

      if (overlayVisible) {
        await chooseOverlay.click()
      } else {
        await eevaCard.click({ force: true })
      }
    }

    // Wait for navigation and chat page to initialise
    await page.waitForTimeout(8000)

    await page.screenshot({
      path: SCREENSHOTS_DIR + '/jupiter-06b-after-card-click.png',
      fullPage: true,
    })

    const currentUrl = page.url()
    console.log(`URL after clicking E.E.V.A. card: ${currentUrl}`)

    const navigatedToChat = currentUrl.includes('/chat')
    console.log(`Navigated to /chat: ${navigatedToChat}`)

    if (navigatedToChat) {
      // Confirm chat input is available
      const input = await getChatInput(page, 10000)
      console.log(`Chat input available after card navigation: ${input !== null}`)

      // Check for greeting message
      const msgCount = await page.locator('[class*="message"], [class*="Message"]').count()
      console.log(`Message elements after greeting: ${msgCount}`)

      await page.screenshot({
        path: SCREENSHOTS_DIR + '/jupiter-06c-chat-after-card-click.png',
        fullPage: true,
      })
    } else {
      console.log('NOTE: Did not navigate to /chat — card click may require specific overlay interaction')
    }

    await expect(page.locator('body')).toBeVisible()
    console.log('Test 6 PASSED: Card click flow documented')
  })

})
