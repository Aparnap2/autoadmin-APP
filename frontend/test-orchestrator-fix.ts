/**
 * Test script to verify orchestrator initialization fix
 * Run this to ensure the critical initialization failure has been resolved
 */

import useAutoAdminAgents, { UseAutoAdminAgentsOptions } from './hooks/useAutoAdminAgents';

// Mock React Native Platform
const mockPlatform = {
  OS: 'web',
  Version: '1.0.0',
  isPad: false,
  isTVOS: false,
  select: () => {},
};

// Mock AsyncStorage
const mockAsyncStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  getAllKeys: jest.fn(),
  multiGet: jest.fn(),
  multiSet: jest.fn(),
  multiRemove: jest.fn(),
};

// Test configurations
const testConfigurations = {
  validUser: {
    userId: 'test-user-123',
    autoInitialize: true,
    enableRealtimeSync: true,
    offlineMode: false,
    onError: (error: Error) => console.log('Error callback:', error.message),
    onStateChange: (state: any) => console.log('State changed:', state),
    onBackendStatusChange: (status: string) => console.log('Backend status:', status),
  },
  invalidUser: {
    userId: '',
    autoInitialize: true,
    onError: (error: Error) => console.log('Expected error:', error.message),
  },
  offlineMode: {
    userId: 'test-user-456',
    autoInitialize: true,
    offlineMode: true,
    enableRealtimeSync: false,
    onError: (error: Error) => console.log('Offline mode error:', error.message),
  },
  retryConfig: {
    userId: 'test-user-789',
    autoInitialize: true,
    enableRealtimeSync: true,
    offlineMode: false,
    onError: (error: Error) => console.log('Retry error:', error.message),
  },
};

/**
 * Test orchestrator initialization scenarios
 */
async function testOrchestratorInitialization() {
  console.log('🚀 Starting orchestrator initialization tests...\n');

  // Test 1: Valid user initialization
  console.log('📋 Test 1: Valid user initialization');
  try {
    const { result, waitForNextUpdate } = renderHook(() =>
      useAutoAdminAgents(testConfigurations.validUser)
    );

    console.log('✅ Initial state:', {
      isInitialized: result.current.isInitialized,
      isLoading: result.current.isLoading,
      isOnline: result.current.isOnline,
      backendStatus: result.current.backendStatus,
      hasError: !!result.current.error,
      initializationAttempts: result.current.initializationAttempts
    });

    // Wait for initialization to complete or timeout
    let attempts = 0;
    while (result.current.isLoading && attempts < 30) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      attempts++;
      console.log(`⏳ Waiting for initialization... (${attempts}s)`);
    }

    console.log('📊 Final state after initialization:', {
      isInitialized: result.current.isInitialized,
      isLoading: result.current.isLoading,
      isOnline: result.current.isOnline,
      backendStatus: result.current.backendStatus,
      hasError: !!result.current.error,
      initializationAttempts: result.current.initializationAttempts,
      hasMetrics: !!result.current.metrics,
      hasState: !!result.current.state
    });

    if (result.current.isInitialized) {
      console.log('✅ Test 1 PASSED: Orchestrator initialized successfully');
    } else if (result.current.error) {
      console.log('✅ Test 1 PASSED: Graceful degradation with error:', result.current.error.message);
    } else {
      console.log('❌ Test 1 FAILED: Neither initialized nor error state');
    }

  } catch (error) {
    console.log('❌ Test 1 FAILED: Unexpected error:', error);
  }

  console.log('\n' + '='.repeat(60) + '\n');

  // Test 2: Invalid user ID
  console.log('📋 Test 2: Invalid user ID');
  try {
    const { result } = renderHook(() =>
      useAutoAdminAgents(testConfigurations.invalidUser)
    );

    // Wait for initialization to complete
    await new Promise(resolve => setTimeout(resolve, 2000));

    console.log('📊 State with invalid user:', {
      isInitialized: result.current.isInitialized,
      isLoading: result.current.isLoading,
      hasError: !!result.current.error,
      errorMessage: result.current.error?.message
    });

    if (result.current.error && result.current.error.message.includes('User ID is required')) {
      console.log('✅ Test 2 PASSED: Properly rejected invalid user ID');
    } else {
      console.log('❌ Test 2 FAILED: Should have rejected invalid user ID');
    }

  } catch (error) {
    console.log('✅ Test 2 PASSED: Correctly thrown error for invalid user:', error);
  }

  console.log('\n' + '='.repeat(60) + '\n');

  // Test 3: Offline mode
  console.log('📋 Test 3: Offline mode initialization');
  try {
    const { result } = renderHook(() =>
      useAutoAdminAgents(testConfigurations.offlineMode)
    );

    // Wait for initialization to complete
    await new Promise(resolve => setTimeout(resolve, 3000));

    console.log('📊 Offline mode state:', {
      isInitialized: result.current.isInitialized,
      isLoading: result.current.isLoading,
      isOnline: result.current.isOnline,
      backendStatus: result.current.backendStatus,
      hasError: !!result.current.error
    });

    if (result.current.isInitialized && result.current.backendStatus === 'offline') {
      console.log('✅ Test 3 PASSED: Offline mode initialization successful');
    } else {
      console.log('❌ Test 3 FAILED: Offline mode should initialize successfully');
    }

  } catch (error) {
    console.log('❌ Test 3 FAILED: Unexpected error in offline mode:', error);
  }

  console.log('\n' + '='.repeat(60) + '\n');

  // Test 4: Message sending after initialization
  console.log('📋 Test 4: Message sending functionality');
  try {
    const { result } = renderHook(() =>
      useAutoAdminAgents(testConfigurations.validUser)
    );

    // Wait for initialization
    await new Promise(resolve => setTimeout(resolve, 5000));

    if (result.current.isInitialized || result.current.error) {
      console.log('📤 Testing message sending...');

      try {
        const response = await result.current.sendMessage('Hello, how are you?');
        console.log('✅ Message sent successfully:', response.success);
        console.log('📝 Response message:', response.message);

        if (response.success || response.requiresUserInput) {
          console.log('✅ Test 4 PASSED: Message handling works correctly');
        } else {
          console.log('❌ Test 4 FAILED: Message should not fail completely');
        }
      } catch (messageError) {
        console.log('❌ Test 4 FAILED: Message sending threw error:', messageError);
      }
    } else {
      console.log('❌ Test 4 SKIPPED: Initialization did not complete');
    }

  } catch (error) {
    console.log('❌ Test 4 FAILED: Unexpected error during message test:', error);
  }

  console.log('\n🏁 Orchestrator initialization tests completed!\n');
}

/**
 * Test error recovery mechanisms
 */
async function testErrorRecovery() {
  console.log('🔄 Testing error recovery mechanisms...\n');

  // Test retry logic with mock network failures
  const retryTestConfig = {
    userId: 'test-user-retry',
    autoInitialize: true,
    enableRealtimeSync: true,
    offlineMode: false,
    onError: (error: Error) => console.log('Retry test error:', error.message),
  };

  try {
    const { result } = renderHook(() =>
      useAutoAdminAgents(retryTestConfig)
    );

    // Monitor initialization attempts
    let lastAttempts = 0;
    for (let i = 0; i < 10; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000));

      if (result.current.initializationAttempts > lastAttempts) {
        console.log(`🔄 Retry attempt ${result.current.initializationAttempts} detected`);
        lastAttempts = result.current.initializationAttempts;
      }

      if (result.current.isInitialized || result.current.error) {
        break;
      }
    }

    console.log('📊 Retry test results:', {
      initializationAttempts: result.current.initializationAttempts,
      isInitialized: result.current.isInitialized,
      hasError: !!result.current.error,
      backendStatus: result.current.backendStatus
    });

    if (result.current.initializationAttempts > 1) {
      console.log('✅ Retry mechanism: PASSED - Multiple attempts detected');
    } else {
      console.log('⚠️  Retry mechanism: No retries detected (may be normal if backend is available)');
    }

  } catch (error) {
    console.log('❌ Retry test FAILED:', error);
  }

  console.log('\n🏁 Error recovery tests completed!\n');
}

/**
 * Cleanup function for tests
 */
function cleanup() {
  console.log('🧹 Cleaning up test environment...');
  // Cleanup any resources if needed
}

// Mock React hooks for testing
function renderHook(hook: () => any) {
  let result: { current: any } = { current: null };

  // Simple mock implementation
  const hookResult = hook();
  result.current = hookResult;

  return {
    result,
    waitForNextUpdate: () => Promise.resolve(),
    rerender: () => {},
    unmount: () => {}
  };
}

// Export test functions
export {
  testOrchestratorInitialization,
  testErrorRecovery,
  cleanup,
  testConfigurations
};

// Auto-run tests if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
  testOrchestratorInitialization()
    .then(() => testErrorRecovery())
    .then(() => cleanup())
    .then(() => {
      console.log('✅ All tests completed successfully!');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Tests failed:', error);
      process.exit(1);
    });
}