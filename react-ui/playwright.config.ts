import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 1,
  expect: {
    timeout: 10000
  },
  use: {
    baseURL: 'http://localhost:3001',
    screenshot: 'on',
    video: 'off',
    viewport: { width: 1280, height: 800 },
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
})
