import { defineConfig, devices } from '@playwright/test';

// Runs against a served build (the hardened container in CI): E2E_BASE_URL, default http://127.0.0.1:8080.
export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8080',
    trace: 'off',
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1366, height: 900 } } },
    { name: 'movil', use: { ...devices['Pixel 7'] } },
  ],
});
