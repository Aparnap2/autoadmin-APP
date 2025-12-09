import { defineConfig, devices } from '@playwright/test';

/**
 * Comprehensive E2E Testing Configuration for AutoAdmin HTTP-only communication
 * Tests complete system spanning frontend and backend with HTTP-only workflows
 */
export default defineConfig({
  testDir: './e2e/tests',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'e2e/results/playwright-report' }],
    ['json', { outputFile: 'e2e/results/test-results.json' }],
    ['junit', { outputFile: 'e2e/results/test-results.xml' }]
  ],

  // Global setup and teardown
  globalSetup: './e2e/setup/global-setup.ts',
  globalTeardown: './e2e/setup/global-teardown.ts',

  // Global test configuration
  use: {
    // Base URL for tests - can be configured for different environments
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:3000',

    // API base URL for backend
    httpCredentials: {
      username: process.env.TEST_API_USER || '',
      password: process.env.TEST_API_PASSWORD || ''
    },

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Record video on failure
    video: 'retain-on-failure',

    // Take screenshot on failure
    screenshot: 'only-on-failure',

    // Extra HTTP headers for all requests
    extraHTTPHeaders: {
      'X-Test-Environment': 'playwright',
      'X-Test-Run': process.env.TEST_RUN_ID || 'local'
    },

    // Action and navigation timeouts
    actionTimeout: 30000,
    navigationTimeout: 60000,

    // User agent
    userAgent: 'AutoAdmin-E2E-Test/1.0.0 (Playwright)'
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: '**/mobile.spec.ts',
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: '**/mobile.spec.ts',
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: '**/mobile.spec.ts',
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testMatch: '**/mobile.spec.ts',
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      testMatch: '**/mobile.spec.ts',
    },
    // API-only testing project
    {
      name: 'api',
      testMatch: '**/api.spec.ts',
      use: {
        // No browser context needed for API tests
      }
    }
  ],

  // Run your local dev server before starting the tests
  webServer: [
    {
      command: 'cd ../backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe'
    },
    {
      command: 'npx expo start --web --port 3000',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 180 * 1000,
      stdout: 'pipe',
      stderr: 'pipe'
    }
  ],

  // Test environment variables
  env: {
    // Backend API configuration
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
    API_TIMEOUT: process.env.API_TIMEOUT || '30000',

    // Test data configuration
    TEST_USER_EMAIL: process.env.TEST_USER_EMAIL || 'test@autoadmin.local',
    TEST_USER_PASSWORD: process.env.TEST_USER_PASSWORD || 'test123456',

    // Feature flags
    ENABLE_POLLING_TESTS: process.env.ENABLE_POLLING_TESTS || 'true',
    ENABLE_SSE_TESTS: process.env.ENABLE_SSE_TESTS || 'true',
    ENABLE_INTEGRATION_TESTS: process.env.ENABLE_INTEGRATION_TESTS || 'true',

    // Performance testing
    PERFORMANCE_SAMPLE_SIZE: process.env.PERFORMANCE_SAMPLE_SIZE || '5',

    // Real-time testing
    POLLING_TIMEOUT: process.env.POLLING_TIMEOUT || '10000',
    SSE_TIMEOUT: process.env.SSE_TIMEOUT || '15000'
  },

  // Output directory for test results
  outputDir: 'e2e/results/test-artifacts',

  // Test timeout
  timeout: 120 * 1000, // 2 minutes per test

  // Expect timeout
  expect: {
    timeout: 10000
  }
});