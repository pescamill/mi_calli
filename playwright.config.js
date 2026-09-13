const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    // Fixed port belongs to compose.e2e.yml, never the normal app on port 80.
    baseURL: 'http://127.0.0.1:18080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', testMatch: '**/e2e/*.spec.js', use: devices['Desktop Chrome'] },
    {
      name: 'benchmark', testMatch: '**/benchmarks/*.spec.js',
      retries: 0, timeout: 120_000,
    },
  ],
});
