/**
 * Debug script for testing frontend-backend connectivity
 * Run this in React Native app console or as a component
 */

const API_BASE_URL = 'http://10.0.2.2:8000';

// Test 1: Basic connectivity
async function testHealthEndpoint() {
  console.log('\n🔍 Testing Health Endpoint');
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    console.log('Response status:', response.status);
    console.log('Content-Type:', response.headers.get('content-type'));

    const text = await response.text();
    console.log('Raw response (first 200 chars):', text.substring(0, 200));

    if (response.headers.get('content-type')?.includes('application/json')) {
      const data = JSON.parse(text);
      console.log('✅ JSON parsed successfully');
      console.log('Backend status:', data?.data?.status);
      console.log('Available agents:', data?.data?.agents?.length || 0);
    } else {
      console.log('❌ Response is not JSON');
    }
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
  }
}

// Test 2: Test agents endpoint
async function testAgentsEndpoint() {
  console.log('\n🤖 Testing Agents Endpoint');
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/agents`);
    console.log('Response status:', response.status);

    const data = await response.json();
    if (data.success) {
      console.log('✅ Agents endpoint working');
      console.log('Available agents:');
      data.data.forEach(agent => {
        console.log(`  - ${agent.name} (${agent.type}): ${agent.status}`);
      });
    }
  } catch (error) {
    console.error('❌ Agents endpoint failed:', error.message);
  }
}

// Test 3: Test chat endpoint
async function testChatEndpoint() {
  console.log('\n💬 Testing Chat Endpoint');
  try {
    const chatData = {
      content: 'Hello from debug script!',
      agent_hint: 'ceo'
    };

    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(chatData)
    });

    console.log('Response status:', response.status);
    const data = await response.json();

    if (data.success) {
      console.log('✅ Chat endpoint working');
      console.log('Response message:', data?.data?.message?.substring(0, 100));
    } else {
      console.log('❌ Chat endpoint returned error:', data);
    }
  } catch (error) {
    console.error('❌ Chat endpoint failed:', error.message);
  }
}

// Test 4: Test network info
function testNetworkInfo() {
  console.log('\n📡 Network Information');
  console.log('Platform:', require('react-native').Platform.OS);
  console.log('API Base URL:', API_BASE_URL);

  // For React Native
  if (typeof __DEV__ !== 'undefined' && __DEV__) {
    console.log('Running in development mode');
    console.log('Debug server host:', __DEV__ ? 'localhost' : 'production');
  }
}

// Run all tests
export async function runConnectivityTests() {
  console.log('='.repeat(50));
  console.log('🚀 Starting AutoAdmin Connectivity Tests');
  console.log('='.repeat(50));

  testNetworkInfo();
  await testHealthEndpoint();
  await testAgentsEndpoint();
  await testChatEndpoint();

  console.log('\n' + '='.repeat(50));
  console.log('✅ Tests Complete');
  console.log('\nIf you see errors above:');
  console.log('1. Ensure backend is running: python simple_backend.py');
  console.log('2. Check Android emulator can access 10.0.2.2:8000');
  console.log('3. Verify EXPO_PUBLIC_FASTAPI_URL=http://10.0.2.2:8000');
}

// Export for use in components
export { testHealthEndpoint, testAgentsEndpoint, testChatEndpoint };

// Auto-run if in console
if (typeof window !== 'undefined') {
  // Browser console
  window.runAutoAdminTests = runConnectivityTests;
  console.log('Type runAutoAdminTests() to start connectivity tests');
}