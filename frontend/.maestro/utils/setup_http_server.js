// Setup HTTP Server Mock for Maestro Tests
// This script configures HTTP server behavior for testing

// Mock server configuration
const mockServer = {
  baseUrl: process.env.API_BASE_URL || "http://localhost:8000/api/v1",
  httpOnlyMode: process.env.HTTP_ONLY_MODE === "true",
  enableStreaming: process.env.ENABLE_STREAMING === "true",
  enableSSEFallback: process.env.ENABLE_SSE_FALLBACK === "true"
};

// Mock response delays (simulating network conditions)
const mockDelays = {
  fast: 500,      // Fast response
  medium: 1500,   // Medium response
  slow: 3000      // Slow response
};

// Mock data generators
const generateMockAgentStatus = () => ({
  ceo: { status: 'online', lastSeen: new Date().toISOString(), responseTime: '120ms' },
  strategy: { status: 'online', lastSeen: new Date().toISOString(), responseTime: '150ms' },
  devops: { status: 'online', lastSeen: new Date().toISOString(), responseTime: '180ms' }
});

const generateMockSystemMetrics = () => ({
  responseTime: Math.floor(Math.random() * 500) + 100,
  successRate: 95 + Math.random() * 4,
  activeConnections: Math.floor(Math.random() * 50) + 10,
  memoryUsage: Math.floor(Math.random() * 60) + 20,
  cpuUsage: Math.floor(Math.random() * 30) + 10
});

const generateMockHubSpotData = () => ({
  contacts: Math.floor(Math.random() * 1000) + 100,
  deals: Math.floor(Math.random() * 500) + 50,
  recentActivity: Math.floor(Math.random() * 100) + 10,
  companies: Math.floor(Math.random() * 200) + 20
});

// HTTP response simulators
const simulateHTTPResponse = (endpoint, delay = mockDelays.medium) => {
  console.log(`🌐 Simulating HTTP response for ${endpoint} with ${delay}ms delay`);

  return new Promise((resolve) => {
    setTimeout(() => {
      const responses = {
        '/status': { status: 'ok', httpOnly: true, timestamp: new Date().toISOString() },
        '/agents': generateMockAgentStatus(),
        '/metrics': generateMockSystemMetrics(),
        '/hubspot': generateMockHubSpotData(),
        '/health': { status: 'healthy', uptime: '24h 35m' }
      };

      resolve(responses[endpoint] || { status: 'ok' });
    }, delay);
  });
};

const simulateStreamingResponse = async (message) => {
  console.log(`📡 Simulating HTTP streaming response for: "${message}"`);

  const chunks = [
    "Processing your request...",
    "Analyzing data patterns...",
    "Generating insights...",
    "Finalizing response..."
  ];

  for (let i = 0; i < chunks.length; i++) {
    console.log(`📦 Streaming chunk ${i + 1}: ${chunks[i]}`);
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  return {
    message: "Response completed successfully",
    agent: "Mock Agent",
    timestamp: new Date().toISOString()
  };
};

// Test scenario simulators
const simulateNetworkInterruption = async () => {
  console.log("🔌 Simulating network interruption...");
  await new Promise(resolve => setTimeout(resolve, 2000));
  console.log("🔄 Network restored");
};

const simulateServerError = async () => {
  console.log("🚫 Simulating server error...");
  await new Promise(resolve => setTimeout(resolve, 1000));
  console.log("✅ Server recovered");
};

const simulateTimeout = async () => {
  console.log("⏱️ Simulating timeout scenario...");
  await new Promise(resolve => setTimeout(resolve, 20000));
  console.log("⏰ Timeout occurred");
};

// Initialize test environment
console.log("🚀 Initializing HTTP-only test environment...");
console.log(`📋 Configuration:`, mockServer);

// Export functions for test flows
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    mockServer,
    simulateHTTPResponse,
    simulateStreamingResponse,
    simulateNetworkInterruption,
    simulateServerError,
    simulateTimeout,
    generateMockAgentStatus,
    generateMockSystemMetrics,
    generateMockHubSpotData
  };
}

// Global setup for Maestro tests
global.mockHTTPServer = {
  simulateHTTPResponse,
  simulateStreamingResponse,
  simulateNetworkInterruption,
  simulateServerError,
  simulateTimeout
};

console.log("✅ HTTP server mock setup completed");