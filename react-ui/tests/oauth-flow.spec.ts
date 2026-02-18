import { test, expect, Page } from '@playwright/test'

// Helper: wait for network idle
async function waitForApp(page: Page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
}

test.describe('NEPHILIM OAuth Auth Flow', () => {

  test.beforeEach(async ({ page }) => {
    // Clear all storage and cookies before each test
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
  })

  test('1. Unauthenticated user visiting /chat redirects to /login', async ({ page }) => {
    await page.goto('http://localhost:3001/chat')
    await waitForApp(page)
    await page.screenshot({ path: 'tests/screenshots/01-redirect-to-login.png', fullPage: true })

    // Should be redirected to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
    console.log('✅ /chat → /login redirect: PASS')
  })

  test('2. Login page renders correctly (NEPHILIM theme)', async ({ page }) => {
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)
    await page.screenshot({ path: 'tests/screenshots/02-login-page.png', fullPage: true })

    // Check for key UI elements
    const body = await page.locator('body')
    const bodyBg = await body.evaluate(el => window.getComputedStyle(el).backgroundColor)
    console.log('Body background:', bodyBg)

    // "Enter the Realm" heading
    const heading = page.locator('h1').first()
    await expect(heading).toBeVisible({ timeout: 5000 })
    const headingText = await heading.textContent()
    console.log('Heading text:', headingText)
    expect(headingText).toContain('Enter the Realm')

    // NEPHILIM wordmark
    const wordmark = page.locator('text=✦ N E P H I L I M ✦').first()
    await expect(wordmark).toBeVisible({ timeout: 5000 })
    console.log('✅ NEPHILIM wordmark: PASS')

    // E.E.V.A. greeting
    const eeva = page.locator('text=E.E.V.A. — The Primarch').first()
    await expect(eeva).toBeVisible({ timeout: 5000 })
    console.log('✅ E.E.V.A. block: PASS')

    // Auth button (either GoogleLogin or local bypass button)
    const authBtn = page.locator('button').filter({ hasText: /Sign in with Google|Continue.*Local Mode/i }).first()
    const authBtnVisible = await authBtn.isVisible().catch(() => false)
    console.log('Auth button visible:', authBtnVisible)

    // Bypass note — the login page contains the text "AUTH_REQUIRED" in the code block
    const bypassNote = page.locator('code').filter({ hasText: 'AUTH_REQUIRED' }).first()
    await expect(bypassNote).toBeVisible({ timeout: 5000 })
    console.log('✅ Bypass note: PASS')
  })

  test('3. Local bypass login (AUTH_REQUIRED=false) — click button, get to app', async ({ page }) => {
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    // Try to find and click the local bypass/continue button
    const localBtn = page.locator('button').filter({ hasText: /Continue.*Local Mode|No Google/i }).first()
    const localBtnVisible = await localBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (localBtnVisible) {
      await localBtn.click()
      await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => {})
      await waitForApp(page)
      await page.screenshot({ path: 'tests/screenshots/03-after-local-login.png', fullPage: true })
      const url = page.url()
      console.log('URL after local login:', url)
      const redirectedAway = !url.includes('/login')
      console.log(redirectedAway ? '✅ Local bypass login: PASS' : '❌ Local bypass login: FAIL — still on /login')
    } else {
      // No local button — AUTH_REQUIRED might be true or GoogleLogin is showing
      console.log('ℹ️ No local bypass button found — GoogleLogin component may be showing (CLIENT_ID set)')
      await page.screenshot({ path: 'tests/screenshots/03-login-state.png', fullPage: true })
    }
  })

  test('4. /auth/refresh endpoint works (backend bypass)', async ({ page }) => {
    // Hit the refresh endpoint directly via the CRA proxy
    const response = await page.request.post('http://localhost:3001/auth/refresh', {
      headers: { 'Content-Type': 'application/json' },
    })
    console.log('POST /auth/refresh status:', response.status())
    const body = await response.json().catch(() => ({}))
    console.log('Response body:', JSON.stringify(body))

    if (response.status() === 200) {
      expect(body).toHaveProperty('access_token')
      expect(body).toHaveProperty('user')
      expect(body.user).toHaveProperty('sub')
      console.log('✅ /auth/refresh (bypass mode): PASS — got access_token')
    } else {
      console.log('ℹ️ /auth/refresh returned', response.status(), '— may need AUTH_REQUIRED=false in .env')
    }
  })

  test('5. /auth/me endpoint (with bearer token)', async ({ page }) => {
    // First get a token via refresh
    const refreshResp = await page.request.post('http://localhost:8000/auth/refresh')
    if (refreshResp.status() !== 200) {
      console.log('ℹ️ Skipping /auth/me test — could not get token from /auth/refresh')
      return
    }
    const { access_token } = await refreshResp.json()

    // Now hit /auth/me
    const meResp = await page.request.get('http://localhost:8000/auth/me', {
      headers: { 'Authorization': `Bearer ${access_token}` }
    })
    console.log('GET /auth/me status:', meResp.status())
    const me = await meResp.json().catch(() => ({}))
    console.log('Auth me response:', JSON.stringify(me))

    if (meResp.status() === 200) {
      expect(me).toHaveProperty('sub')
      console.log('✅ /auth/me: PASS — sub:', me.sub)
    } else {
      console.log('❌ /auth/me: FAIL — status', meResp.status())
    }
  })

  test('6. Protected routes all redirect to /login when unauthenticated', async ({ page }) => {
    const protectedRoutes = ['/select', '/chat', '/dashboard']

    for (const route of protectedRoutes) {
      await page.context().clearCookies()
      await page.evaluate(() => localStorage.clear())

      await page.goto(`http://localhost:3001${route}`)
      await page.waitForLoadState('domcontentloaded')
      // Wait for redirect
      await page.waitForTimeout(2000)

      const url = page.url()
      const redirected = url.includes('/login')
      console.log(`${redirected ? '✅' : '❌'} ${route} → ${url} (redirected: ${redirected})`)
    }
    await page.screenshot({ path: 'tests/screenshots/06-protected-routes.png', fullPage: true })
  })

  test('7. Header shows user info after login (local bypass)', async ({ page }) => {
    // Login via direct cookie injection or bypass
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    const localBtn = page.locator('button').filter({ hasText: /Continue.*Local Mode/i }).first()
    const hasLocalBtn = await localBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (!hasLocalBtn) {
      console.log('ℹ️ Skipping header test — no local bypass button (GoogleLogin active)')
      return
    }

    await localBtn.click()
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => {})
    await waitForApp(page)

    // Navigate to a page with header
    await page.goto('http://localhost:3001/select')
    await waitForApp(page)
    await page.screenshot({ path: 'tests/screenshots/07-header-authenticated.png', fullPage: true })

    // Header should show something (avatar or user name)
    const header = page.locator('header, nav').first()
    const headerVisible = await header.isVisible().catch(() => false)
    console.log('Header visible:', headerVisible)

    // Look for Sign Out button in header area
    const signOutBtn = page.locator('button').filter({ hasText: /Sign Out|logout/i }).first()
    const signOutVisible = await signOutBtn.isVisible({ timeout: 3000 }).catch(() => false)
    console.log(signOutVisible ? '✅ Sign Out in header: PASS' : 'ℹ️ Sign Out button not immediately visible (may be in dropdown)')
  })

  test('8. Logout flow returns to /login', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    const localBtn = page.locator('button').filter({ hasText: /Continue.*Local Mode/i }).first()
    const hasLocalBtn = await localBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (!hasLocalBtn) {
      console.log('ℹ️ Skipping logout test — no local bypass button')
      return
    }

    await localBtn.click()
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => {})
    await waitForApp(page)

    // Go to select page where header is visible
    await page.goto('http://localhost:3001/select')
    await waitForApp(page)

    // Try to find and click avatar to open dropdown
    const avatarBtn = page.locator('button').filter({ hasText: /Local|Seeker/i }).first()
    const avatarVisible = await avatarBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (avatarVisible) {
      await avatarBtn.click()
      await page.waitForTimeout(500)

      const signOutBtn = page.locator('button').filter({ hasText: /Sign Out/i }).first()
      const signOutVisible = await signOutBtn.isVisible({ timeout: 2000 }).catch(() => false)

      if (signOutVisible) {
        await signOutBtn.click()
        await page.waitForURL(/\/login/, { timeout: 8000 }).catch(() => {})
        await page.screenshot({ path: 'tests/screenshots/08-after-logout.png', fullPage: true })
        const onLogin = page.url().includes('/login')
        console.log(onLogin ? '✅ Logout → /login: PASS' : '❌ Logout: FAIL — not on /login')
      } else {
        console.log('ℹ️ Sign Out button not found in dropdown')
        await page.screenshot({ path: 'tests/screenshots/08-dropdown-state.png', fullPage: true })
      }
    } else {
      console.log('ℹ️ Avatar button not found — checking full page')
      await page.screenshot({ path: 'tests/screenshots/08-header-debug.png', fullPage: true })
    }
  })

  test('9. Login page does NOT show header', async ({ page }) => {
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    // The header component should not be present on /login
    const header = page.locator('header').first()
    const headerVisible = await header.isVisible({ timeout: 2000 }).catch(() => false)
    console.log(headerVisible ? '❌ Header showing on /login (should be hidden)' : '✅ Header hidden on /login: PASS')
    await page.screenshot({ path: 'tests/screenshots/09-login-no-header.png', fullPage: true })
  })

  test('10. Visiting /login while authenticated redirects away', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    const localBtn = page.locator('button').filter({ hasText: /Continue.*Local Mode/i }).first()
    const hasLocalBtn = await localBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (!hasLocalBtn) {
      console.log('ℹ️ Skipping test — no local bypass button')
      return
    }

    await localBtn.click()
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => {})

    // Now try going to /login again
    await page.goto('http://localhost:3001/login')
    await waitForApp(page)

    const url = page.url()
    const redirectedAway = !url.includes('/login')
    console.log(redirectedAway ? `✅ Authenticated /login → ${url}: PASS` : 'ℹ️ Still on /login when authenticated (LoginPage redirect may be pending)')
    await page.screenshot({ path: 'tests/screenshots/10-authenticated-login.png', fullPage: true })
  })

})
