import { chromium, FullConfig } from '@playwright/test';
import { testConfig } from '../config/test-config';
import { cleanupTestData, setupTestData } from '../helpers/test-data-manager';
import { startBackend, startFrontend } from '../helpers/test-server';

/**
 * Global setup for E2E tests
 * Initializes test environment, starts services, and prepares test data
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global E2E test setup...');

  try {
    // 1. Initialize test configuration
    console.log('📋 Initializing test configuration...');
    await testConfig.initialize();

    // 2. Start backend service
    console.log('🔧 Starting backend service...');
    const backendInfo = await startBackend();
    console.log(`✅ Backend started at ${backendInfo.url}`);

    // 3. Wait for backend health check
    console.log('🏥 Checking backend health...');
    await waitForBackendHealth(backendInfo.url);
    console.log('✅ Backend is healthy');

    // 4. Start frontend service
    console.log('🌐 Starting frontend service...');
    const frontendInfo = await startFrontend();
    console.log(`✅ Frontend started at ${frontendInfo.url}`);

    // 5. Wait for frontend to be ready
    console.log('⏳ Waiting for frontend to be ready...');
    await waitForFrontendReady(frontendInfo.url);
    console.log('✅ Frontend is ready');

    // 6. Setup test data
    console.log('📊 Setting up test data...');
    await setupTestData();
    console.log('✅ Test data setup complete');

    // 7. Initialize HTTP polling service tests
    if (process.env.ENABLE_POLLING_TESTS === 'true') {
      console.log('🔄 Initializing HTTP polling tests...');
      await initializePollingTests(backendInfo.url);
      console.log('✅ HTTP polling tests ready');
    }

    // 8. Initialize SSE service tests
    if (process.env.ENABLE_SSE_TESTS === 'true') {
      console.log('📡 Initializing SSE tests...');
      await initializeSSETests(backendInfo.url);
      console.log('✅ SSE tests ready');
    }

    // 9. Store service information for tests
    process.env.TEST_BACKEND_URL = backendInfo.url;
    process.env.TEST_FRONTEND_URL = frontendInfo.url;

    console.log('✨ Global setup completed successfully!');

  } catch (error) {
    console.error('❌ Global setup failed:', error);
    await globalCleanup();
    throw error;
  }
}

/**
 * Wait for backend health endpoint to respond
 */
async function waitForBackendHealth(backendUrl: string, maxAttempts = 30): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  try {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await context.request.get(`${backendUrl}/health`, {
          timeout: 5000
        });

        if (response.status() === 200) {
          const health = await response.json();
          if (health.status === 'healthy') {
            return;
          }
        }
      } catch (error) {
        // Service not ready yet, continue waiting
      }

      console.log(`Backend health check attempt ${attempt}/${maxAttempts}`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    throw new Error(`Backend health check failed after ${maxAttempts} attempts`);
  } finally {
    await browser.close();
  }
}

/**
 * Wait for frontend to be ready
 */
async function waitForFrontendReady(frontendUrl: string, maxAttempts = 30): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  try {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await context.request.get(frontendUrl, {
          timeout: 5000
        });

        if (response.status() === 200) {
          // Check if page contains expected content
          const content = await response.text();
          if (content.includes('AutoAdmin') || content.includes('React')) {
            return;
          }
        }
      } catch (error) {
        // Frontend not ready yet, continue waiting
      }

      console.log(`Frontend ready check attempt ${attempt}/${maxAttempts}`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    throw new Error(`Frontend ready check failed after ${maxAttempts} attempts`);
  } finally {
    await browser.close();
  }
}

/**
 * Initialize HTTP polling service tests
 */
async function initializePollingTests(backendUrl: string): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  try {
    // Create test polling session
    const response = await context.request.post(`${backendUrl}/api/http-polling/sessions`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        user_id: 'e2e_test_user',
        interval: 'FAST',
        filters: { event_types: ['test', 'e2e'] }
      }
    });

    if (response.status() === 201) {
      const session = await response.json();
      process.env.TEST_POLLING_SESSION_ID = session.session_id;
      console.log(`Created test polling session: ${session.session_id}`);
    }
  } catch (error) {
    console.warn('Failed to create test polling session:', error);
  } finally {
    await browser.close();
  }
}

/**
 * Initialize SSE service tests
 */
async function initializeSSETests(backendUrl: string): Promise<void> {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  try {
    // Test SSE endpoint availability
    const response = await context.request.get(`${backendUrl}/api/streaming/health`, {
      timeout: 5000
    });

    if (response.status() === 200) {
      process.env.TEST_SSE_AVAILABLE = 'true';
      console.log('SSE service is available for testing');
    }
  } catch (error) {
    console.warn('SSE service not available:', error);
    process.env.TEST_SSE_AVAILABLE = 'false';
  } finally {
    await browser.close();
  }
}

/**
 * Global cleanup function
 */
async function globalCleanup(): Promise<void> {
  console.log('🧹 Running global cleanup...');

  try {
    // Cleanup test data
    await cleanupTestData();

    // Close any remaining service connections
    // (Services will be terminated by Playwright automatically)

    console.log('✅ Global cleanup completed');
  } catch (error) {
    console.error('❌ Global cleanup error:', error);
  }
}

// Export for potential reuse
export { globalSetup, globalCleanup };