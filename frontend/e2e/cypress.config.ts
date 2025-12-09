import { defineConfig } from 'cypress';

/**
 * Cypress E2E Testing Configuration for AutoAdmin HTTP-only communication
 * Focused on user interaction testing and visual regression
 */
export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',

    // Default viewport for desktop testing
    viewportWidth: 1280,
    viewportHeight: 720,

    // Test timeout configuration
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    taskTimeout: 60000,

    // Video and screenshots
    video: true,
    videoUploadOnPasses: false,
    screenshotOnRunFailure: true,
    trashAssetsBeforeRuns: true,

    // Reporter configuration
    reporter: 'cypress-mochawesome-reporter',
    reporterOptions: {
      reportDir: 'cypress/results',
      charts: true,
      reportPageTitle: 'AutoAdmin E2E Test Report',
      embeddedScreenshots: true,
      inlineAssets: true,
      saveAllAttempts: false
    },

    // Experimental features
    experimentalStudio: true,
    experimentalWebKitSupport: true,

    // Environment variables
    env: {
      // Backend configuration
      BACKEND_URL: 'http://localhost:8000',

      // Test user credentials
      TEST_EMAIL: 'test@autoadmin.local',
      TEST_PASSWORD: 'test123456',

      // Feature flags
      ENABLE_POLLING: true,
      ENABLE_SSE: true,
      ENABLE_REAL_TIME: true,

      // Test configuration
      POLLING_INTERVAL: 5000,
      RETRY_ATTEMPTS: 3,
      TIMEOUT_DURATION: 10000
    },

    // Setup and teardown
    setupNodeEvents(on, config) {
      // Plugins configuration
      require('cypress-mochawesome-reporter/plugin')(on);

      // Custom tasks
      on('task', {
        // Backend API interaction tasks
        'create-test-user': ({ email, password }) => {
          // Create test user via API
          return require('./cypress/tasks/api-tasks').createTestUser(email, password);
        },

        'cleanup-test-user': ({ email }) => {
          // Cleanup test user after tests
          return require('./cypress/tasks/api-tasks').cleanupTestUser(email);
        },

        'setup-test-data': (testType) => {
          // Setup test data for specific test scenarios
          return require('./cypress/tasks/data-tasks').setupTestData(testType);
        },

        'cleanup-test-data': (testType) => {
          // Cleanup test data after tests
          return require('./cypress/tasks/data-tasks').cleanupTestData(testType);
        },

        'poll-events': ({ sessionId, timeout }) => {
          // Poll for HTTP events
          return require('./cypress/tasks/polling-tasks').pollEvents(sessionId, timeout);
        },

        'create-sse-connection': ({ userId }) => {
          // Create SSE connection for testing
          return require('./cypress/tasks/sse-tasks').createSSEConnection(userId);
        },

        'validate-agent-workflow': ({ workflowConfig }) => {
          // Validate complete agent workflow
          return require('./cypress/tasks/workflow-tasks').validateAgentWorkflow(workflowConfig);
        },

        // Performance testing tasks
        'measure-page-load': (url) => {
          return require('./cypress/tasks/performance-tasks').measurePageLoad(url);
        },

        'measure-api-response': (endpoint) => {
          return require('./cypress/tasks/performance-tasks').measureApiResponse(endpoint);
        },

        // Database interaction tasks
        'query-database': (query) => {
          return require('./cypress/tasks/database-tasks').queryDatabase(query);
        },

        'seed-database': (data) => {
          return require('./cypress/tasks/database-tasks').seedDatabase(data);
        },

        // Firebase interaction tasks
        'firebase-auth': ({ email, password }) => {
          return require('./cypress/tasks/firebase-tasks').authenticate(email, password);
        },

        'firebase-cleanup': (userId) => {
          return require('./cypress/tasks/firebase-tasks').cleanup(userId);
        },

        // File system tasks
        'read-file': (filePath) => {
          return require('fs').promises.readFile(filePath, 'utf8');
        },

        'write-file': ({ filePath, content }) => {
          return require('fs').promises.writeFile(filePath, content, 'utf8');
        },

        // Log tasks
        'log-message': ({ level, message }) => {
          console.log(`[${level.toUpperCase()}] ${message}`);
          return null;
        }
      });
    }
  },

  // Component testing configuration (optional)
  component: {
    devServer: {
      framework: 'create-react-app',
      bundler: 'webpack'
    }
  },

  // Parallel testing
  numTestsKeptInMemory: 50,

  // Request retries
  retries: {
    runMode: 2,
    openMode: 0
  },

  // Screen recording
  screenshotOnHeadlessFailure: true,

  // Chrome/Firefox configuration
  chromeWebSecurity: false,
  firefoxGcInterval: {
    runMode: 1,
    openMode: null
  },

  // Watch for file changes in development
  watchForFileChanges: false
});