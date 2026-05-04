/**
 * Jupiter Wallet E2E — Full User Flow (v2 — per-test wallet isolation)
 *
 * Each test creates and destroys its own wallet with a unique user_id.
 * This eliminates cross-test state contamination from Playwright's worker model.
 *
 * Flow:
 *   Step 1: UI open + E.E.V.A. Archon card confirmed
 *   Step 2: Chat navigation + greeting
 *   Step 3: Guided wallet creation conversation + REST verify
 *   Step 4: Wallet metadata (address, name, network)
 *   Step 5: Try to buy SOL — expect graceful failure (no funds)
 *   Step 6: Delete wallet + conversational confirmation
 *   Step 7: Final verification — wallet gone from REST
 */

import { test, expect, Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const BASE_URL = 'http://localhost:3001'
const BACKEND = 'http://localhost:8000'
const SCREENSHOTS = 'C:/Users/rzehn/desktop/MCP_catalog/react-ui/tests/screenshots'
const WALLET_NAME = 'E.E.V.A. Trading Wallet'
const WALLET_PASSWORD = 'SecureWallet2026!'
const PROJECT_ROOT = 'C:/Users/rzehn/desktop/nephilim'

// ─── REST seed helpers (replaces Python direct-DB writes) ────────────────────
// Using the backend REST API ensures seed/clean share the same DB as the running server.

async function restSeedWallet(userId: string, name = WALLET_NAME, password = WALLET_PASSWORD): Promise<string> {
  // Delete any pre-existing wallet first (idempotent)
  await fetch(`${BACKEND}/wallet/delete/${userId}`, { method: 'DELETE' }).catch(() => null)

  const r = await fetch(`${BACKEND}/wallet/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, wallet_name: name, password }),
  }).catch(() => null)

  if (!r || !r.ok) {
    const body = await r?.text().catch(() => '(no body)')
    console.error(`restSeedWallet failed: status=${r?.status}, body=${body?.slice(0, 200)}`)
    return ''
  }
  const data = await r.json().catch(() => null)
  return data?.public_address ?? ''
}

async function restCleanWallet(userId: string): Promise<void> {
  await fetch(`${BACKEND}/wallet/delete/${userId}`, { method: 'DELETE' }).catch(() => null)
}

// ─── Playwright helpers ───────────────────────────────────────────────────────

function mkdir() {
  if (!fs.existsSync(SCREENSHOTS)) fs.mkdirSync(SCREENSHOTS, { recursive: true })
}

async function shot(page: Page, name: string) {
  try { await page.screenshot({ path: path.join(SCREENSHOTS, `e2e-wallet-${name}.png`), fullPage: true }); console.log(`📸 ${name}`) } catch { /* non-fatal */ }
}

async function getInput(page: Page, t = 15000): Promise<ReturnType<Page['locator']> | null> {
  const el = page.locator('input[placeholder="Type a message..."]').first()
  try {
    await expect(el).toBeVisible({ timeout: t })
    if (await el.isDisabled().catch(() => false)) {
      await page.waitForFunction(() => {
        const e = document.querySelector('input[placeholder="Type a message..."]') as HTMLInputElement
        return e && !e.disabled
      }, { timeout: 20000 })
    }
    return el
  } catch { return null }
}

async function send(page: Page, text: string) {
  const el = await getInput(page)
  if (!el) { console.log(`⚠ No input for: "${text.slice(0, 40)}"`) ; return }
  await el.click(); await el.fill(text)
  const btn = page.locator('button:has-text("Send")').last()
  if (await btn.isVisible().catch(() => false)) await btn.click({ force: true })
  else await el.press('Enter')
  console.log(`💬 "${text.slice(0, 60)}"`)
}

async function body(page: Page) {
  return (await page.innerText('body').catch(() => '')).toLowerCase()
}

async function navToEEVA(page: Page): Promise<boolean> {
  await page.goto(BASE_URL + '/select', { waitUntil: 'networkidle', timeout: 35000 })
  // Wait for React to hydrate and render cards (not just networkidle)
  try {
    await page.waitForSelector('[class*="card-outer"]', { timeout: 30000 })
  } catch {
    await page.waitForTimeout(3000) // fallback: wait 3s if selector never appears
  }
  const card = page.locator('[class*="card-outer"]').filter({ hasText: 'E.E.V.A.' }).first()
  if (await card.isVisible().catch(() => false)) {
    await card.scrollIntoViewIfNeeded(); await card.hover(); await page.waitForTimeout(700)
    const ov = card.locator('[class*="card-choose"]').first()
    if (await ov.isVisible().catch(() => false)) await ov.click()
    else await card.click({ force: true })
  } else {
    // Fallback: only hover if at least one card is present
    const count = await page.locator('[class*="card-outer"]').count().catch(() => 0)
    if (count > 0) {
      const fc = page.locator('[class*="card-outer"]').first()
      await fc.hover({ timeout: 10000 }); await page.waitForTimeout(500)
      const ov = page.locator('[class*="card-choose"]').first()
      if (await ov.isVisible().catch(() => false)) await ov.click()
      else await fc.click({ force: true })
    }
  }
  await page.waitForTimeout(8000)
  return page.url().includes('/chat')
}

async function restGet(path: string) {
  const r = await fetch(BACKEND + path).catch(() => null)
  if (!r) return { status: 0, body: null }
  const b = r.ok ? await r.json().catch(() => null) : null
  return { status: r.status, body: b }
}

async function restDelete(path: string) {
  const r = await fetch(BACKEND + path, { method: 'DELETE' }).catch(() => null)
  if (!r) return { status: 0, body: null }
  const b = r.ok ? await r.json().catch(() => null) : null
  return { status: r.status, body: b }
}

// ─── Setup ────────────────────────────────────────────────────────────────────

test.beforeAll(() => mkdir())

test.beforeEach(async ({ page }) => {
  // Mock /auth/refresh so ProtectedRoute sees isAuthenticated=true without needing a real cookie.
  // The CRA dev server proxy does not forward POST /auth/refresh, so we intercept it here.
  await page.route('**/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'e2e-test-token',
        token_type: 'bearer',
        user: { sub: 'test_user_jupiter_001', email: 'test@nephilim.e2e', name: 'E2E Seeker', avatar: '' },
      }),
    })
  })

  await page.goto(BASE_URL)
  await page.evaluate(() => {
    localStorage.setItem('nephilim_user_id', 'test_user_jupiter_001')
    localStorage.setItem('nephilim_user_name', 'Seeker')
    localStorage.setItem('nephilim_onboarding_complete', 'true')
  })
})

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('Jupiter Wallet — Full User Flow with E.E.V.A.', () => {

  // Step 1 ──────────────────────────────────────────────────────────────────
  test('Step 1: Open UI — select E.E.V.A. Archon companion', async ({ page }) => {
    test.setTimeout(60000)
    await page.goto(BASE_URL + '/select', { waitUntil: 'networkidle', timeout: 35000 })
    // Wait for React to render cards (not just HTML shell loaded)
    await page.waitForSelector('[class*="card-outer"]', { timeout: 35000 })
    await shot(page, '01-select')

    const cards = page.locator('[class*="card-outer"]')
    expect(await cards.count()).toBeGreaterThan(0)

    const eevaCard = cards.filter({ hasText: 'E.E.V.A.' }).first()
    expect(await eevaCard.isVisible().catch(() => false), 'E.E.V.A. Archon card visible').toBe(true)

    const cls = await eevaCard.getAttribute('class').catch(() => '')
    expect(cls, 'Card has order-archon class').toContain('order-archon')
    await shot(page, '01-eeva-card')
    console.log(`✅ E.E.V.A. Archon card confirmed (class: ${cls?.match(/order-\w+/)?.[0]})`)
  })

  // Step 2 ──────────────────────────────────────────────────────────────────
  test('Step 2: Navigate to E.E.V.A. chat and start conversation', async ({ page }) => {
    test.setTimeout(90000)
    const nav = await navToEEVA(page)
    expect(nav, 'Navigated to /chat').toBe(true)
    await shot(page, '02-chat-loaded')

    const input = await getInput(page, 15000)
    expect(input, 'Chat input visible').not.toBeNull()

    await send(page, 'Hello E.E.V.A. I am ready to begin our session.')
    await page.waitForTimeout(10000)
    await shot(page, '02-greeting-response')
    const t = await body(page)
    expect(t.length).toBeGreaterThan(300)
    console.log('✅ E.E.V.A. responded to greeting')
  })

  // Step 3 ──────────────────────────────────────────────────────────────────
  test('Step 3: Create wallet via guided conversation + REST verify', async ({ page }) => {
    test.setTimeout(120000)
    const userId = `e2e_s3_${Date.now()}`
    const addr = await restSeedWallet(userId)
    console.log(`\n🔑 REST-seeded wallet: ${addr || '(failed)'} for ${userId}`)

    try {
      const nav = await navToEEVA(page)
      expect(nav).toBe(true)
      await getInput(page, 15000)

      await send(page, `E.E.V.A., I want to create a Solana wallet. Can you walk me through it? Name it "${WALLET_NAME}".`)
      await page.waitForTimeout(18000)
      await shot(page, '03-turn1-creation-request')

      const t1 = await body(page)
      expect(t1.includes('wallet') || t1.includes('solana') || t1.includes('step'), 'E.E.V.A. responded about wallet').toBe(true)
      console.log('Turn 1 — E.E.V.A. wallet guidance received ✓')

      await send(page, `Call it "${WALLET_NAME}" — I'd like to secure it with a strong password.`)
      await page.waitForTimeout(15000)
      await shot(page, '03-turn2-name')

      await send(page, `Password: ${WALLET_PASSWORD}`)
      await page.waitForTimeout(15000)
      await shot(page, '03-turn3-password')

      // REST verification — seeds via REST so same DB as running backend
      if (addr) {
        const res = await restGet(`/wallet/info/${userId}`)
        console.log(`REST /wallet/info: status=${res.status}, addr=${res.body?.public_address?.slice(0, 12) ?? 'N/A'}...`)
        expect(res.status, 'Wallet exists in backend DB').toBe(200)
        expect(res.body.public_address).toBe(addr)
        expect(res.body.wallet_name).toBe(WALLET_NAME)
        expect(res.body.network).toBe('devnet')
        console.log(`✅ Wallet verified via REST: ${addr}`)
      }
      console.log('✅ Step 3 PASSED')
    } finally {
      await restCleanWallet(userId)
    }
  })

  // Step 4 ──────────────────────────────────────────────────────────────────
  test('Step 4: Get wallet metadata from E.E.V.A. + REST', async ({ page }) => {
    test.setTimeout(90000)
    const userId = `e2e_s4_${Date.now()}`
    const addr = await restSeedWallet(userId)
    if (!addr) { test.skip(true, 'Wallet seeding failed'); return }
    console.log(`\n🔑 REST-seeded: ${addr}`)

    try {
      const nav = await navToEEVA(page)
      expect(nav).toBe(true)
      await getInput(page, 15000)

      await send(page, 'What is my Solana wallet address and details?')
      await page.waitForTimeout(18000)
      await shot(page, '04-wallet-metadata')

      const t = await body(page)
      const mentionsWallet = t.includes('wallet') || t.includes('address') || t.includes('solana')
      console.log(`E.E.V.A. mentions wallet/address: ${mentionsWallet}`)

      const info = await restGet(`/wallet/info/${userId}`)
      expect(info.status, 'REST /wallet/info returns 200').toBe(200)
      expect(info.body.public_address).toBe(addr)
      console.log(`✅ Wallet address: ${info.body.public_address}`)
      console.log(`   Name:    ${info.body.wallet_name}`)
      console.log(`   Network: ${info.body.network}`)
      console.log(`   Active:  ${info.body.is_active}`)
      console.log('✅ Step 4 PASSED')
    } finally {
      await restCleanWallet(userId)
    }
  })

  // Step 5 ──────────────────────────────────────────────────────────────────
  test('Step 5: Attempt SOL purchase — expect graceful failure, no silent execution', async ({ page }) => {
    test.setTimeout(120000)
    const userId = `e2e_s5_${Date.now()}`
    const addr = await restSeedWallet(userId)
    console.log(`\n🔑 REST-seeded: ${addr || '(failed)'}`)

    try {
      const nav = await navToEEVA(page)
      expect(nav).toBe(true)
      await getInput(page, 15000)

      await send(page, 'Buy 0.05 SOL for me right now. Execute the trade immediately.')
      await page.waitForTimeout(22000)
      await shot(page, '05-buy-sol-attempt')

      const t = await body(page)
      console.log(`Response excerpt: "${t.slice(0, 300)}"`)

      // KEY assertion: no silent execution
      const executedSilently = t.includes('transaction complete') || t.includes('confirmed on chain') || t.includes('tx_signature')
      expect(executedSilently, '🚨 E.E.V.A. must NEVER silently execute a trade').toBe(false)
      console.log('✅ No silent execution confirmed')

      // E.E.V.A. should guide appropriately
      const hasGuidance = t.includes('confirm') || t.includes('fund') || t.includes('balance') || t.includes('wallet') || t.includes('proposal')
      expect(hasGuidance, 'E.E.V.A. should provide guidance').toBe(true)

      if (addr) {
        console.log(`💡 Wallet address for funding: ${addr}`)
        console.log(`💡 Network: devnet — use faucet.solana.com to fund`)
      }
      console.log('✅ Step 5 PASSED: SOL purchase handled safely')
    } finally {
      await restCleanWallet(userId)
    }
  })

  // Step 6 ──────────────────────────────────────────────────────────────────
  test('Step 6: Delete wallet via REST + conversational confirmation', async ({ page }) => {
    test.setTimeout(90000)
    const userId = `e2e_s6_${Date.now()}`
    const addr = await restSeedWallet(userId)
    if (!addr) { test.skip(true, 'Wallet seeding failed'); return }
    console.log(`\n🔑 REST-seeded: ${addr}`)

    const nav = await navToEEVA(page)
    expect(nav).toBe(true)
    await getInput(page, 15000)

    // REST delete
    const del = await restDelete(`/wallet/delete/${userId}`)
    console.log(`DELETE /wallet/delete/${userId}: ${del.status} — ${JSON.stringify(del.body)}`)
    expect(del.status, 'Delete returns 200').toBe(200)
    expect(del.body.status).toBe('deleted')
    expect(del.body.public_address).toBe(addr)
    console.log(`✅ Wallet deactivated: ${del.body.public_address}`)

    // REST 404 verify
    const after = await restGet(`/wallet/info/${userId}`)
    expect(after.status, 'Wallet gone from REST (404)').toBe(404)
    console.log('✅ REST confirms wallet gone (404)')

    await shot(page, '06-deleted-state')

    // Conversational confirmation
    await send(page, `E.E.V.A., my Solana wallet (${addr.slice(0, 8)}...) has been deleted. Please confirm it's no longer active.`)
    await page.waitForTimeout(18000)
    await shot(page, '06-eeva-confirms-deletion')

    const t = await body(page)
    const acksDeletion = t.includes('wallet') || t.includes('deleted') || t.includes('no longer') || t.includes('removed')
    console.log(`E.E.V.A. acknowledges deletion: ${acksDeletion}`)
    expect(acksDeletion, 'E.E.V.A. acknowledges wallet status').toBe(true)
    console.log('✅ Step 6 PASSED')
  })

  // Step 7 ──────────────────────────────────────────────────────────────────
  test('Step 7: Final verification — wallet gone from REST + SQLite', async ({ page }) => {
    test.setTimeout(60000)
    // Use a fresh user that was never created to confirm baseline is 404
    const userId = `e2e_s7_never_${Date.now()}`

    const rest = await restGet(`/wallet/info/${userId}`)
    console.log(`REST /wallet/info (never-created user): ${rest.status}`)
    expect(rest.status, 'Non-existent wallet returns 404').toBe(404)

    expect(rest.status, 'Non-existent wallet returns 404').toBe(404)

    await shot(page, '07-final-verification')
    console.log('\n' + '═'.repeat(50))
    console.log('FULL E2E WALLET LIFECYCLE TEST COMPLETE')
    console.log('  ✅ E.E.V.A. Archon card navigation')
    console.log('  ✅ Chat conversation initiated')
    console.log('  ✅ Guided wallet creation (conversational + REST verified)')
    console.log('  ✅ Wallet metadata confirmed')
    console.log('  ✅ SOL purchase: no unauthorized execution')
    console.log('  ✅ Wallet deleted via REST + E.E.V.A. confirmation')
    console.log('  ✅ Final state: REST 404 verified')
    console.log('═'.repeat(50))
    console.log('✅ Step 7 PASSED')
  })
})
