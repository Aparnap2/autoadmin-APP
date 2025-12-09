/**
 * API Configuration Management
 * Centralized configuration for all API endpoints and settings
 */

export const API_CONFIG = {
  // Base URLs - automatically detected based on environment
  get baseURL(): string {
    // Check for environment variable first
    if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_FASTAPI_URL) {
      return process.env.EXPO_PUBLIC_FASTAPI_URL;
    }

    if (typeof window !== 'undefined') {
      // Browser environment
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;

      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return `${protocol}//${hostname}:8000`;
      } else {
        // Production environment
        return `${protocol}//${hostname}/api`;
      }
    } else {
      // React Native environment
      // For Android emulator: 10.0.2.2
      // For iOS simulator: localhost
      return 'http://10.0.2.2:8000';
    }
  },

  // API endpoints based on actual backend structure
  endpoints: {
    // Health and status
    health: '/health',

    // Agent endpoints
    agents: '/agents',
    agentStatus: (agentId: string) => `/agents/${agentId}/status`,
    agentTasks: (agentId: string) => `/agents/${agentId}/tasks`,
    agentAction: (agentId: string) => `/agents/${agentId}/actions`,

    // Swarm endpoints
    swarmStatus: '/agents/swarm/status',
    swarmProcess: '/agents/swarm/process',
    swarmChat: (agentType: string) => `/agents/swarm/chat/${agentType}`,
    swarmAgents: '/agents/swarm/agents',

    // Task endpoints (if available)
    tasks: '/tasks',
    task: (taskId: string) => `/tasks/${taskId}`,

    // AI endpoints (if available)
    aiChat: '/ai/chat',
    aiGenerate: '/ai/generate',
    aiEmbeddings: '/ai/embeddings',

    // Vector search (if available)
    vectorSearch: '/vector/search',

    // File operations (if available)
    fileUpload: '/files/upload',
    file: (fileId: string) => `/files/${fileId}`,
  },

  // Server-Sent Events configuration (replaces WebSocket)
  serverSentEvents: {
    get url(): string {
      return `${API_CONFIG.baseURL}/events`;
    },
    reconnectAttempts: 5,
    reconnectDelay: 1000,
    heartbeatInterval: 30000,
  },

  // Request configuration
  request: {
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000,
    retryBackoffMultiplier: 2,
    retryMaxDelay: 10000,
  },

  // Validation rules
  validation: {
    maxRequestSize: 10 * 1024 * 1024, // 10MB
    allowedTaskTypes: [
      'research',
      'analysis',
      'content_creation',
      'data_processing',
      'web_scraping',
      'email_outreach',
      'social_media',
      'report_generation',
      'market_research',
      'financial_analysis',
      'code_analysis',
      'ui_ux_review',
      'strategic_planning',
      'technical_decision'
    ],
    allowedAgentTypes: [
      'marketing',
      'finance',
      'devops',
      'strategy'
    ],
    allowedPriorities: ['low', 'medium', 'high'],
    maxTitleLength: 200,
    maxDescriptionLength: 2000,
  },

  // Rate limiting
  rateLimit: {
    requestsPerSecond: 10,
    burstLimit: 20,
    windowSize: 60000, // 1 minute
  },

  // Cache configuration
  cache: {
    defaultTTL: 300000, // 5 minutes
    maxSize: 100, // max cached items
    enableBackgroundSync: true,
    syncInterval: 60000, // 1 minute
  },
};

// Environment-specific overrides
export const ENV_CONFIG = {
  development: {
    ...API_CONFIG,
    request: {
      ...API_CONFIG.request,
      timeout: 60000, // Longer timeout for development
      retryAttempts: 5,
    }
  },

  production: {
    ...API_CONFIG,
    request: {
      ...API_CONFIG.request,
      timeout: 20000, // Faster timeout for production
      retryAttempts: 2,
    }
  },

  test: {
    ...API_CONFIG,
    baseURL: 'http://localhost:8001', // Different port for testing
    request: {
      ...API_CONFIG.request,
      timeout: 10000,
      retryAttempts: 1,
    }
  }
};

// Get current environment config
export function getCurrentConfig() {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return ENV_CONFIG.development;
    }
  }

  // Default to production for other environments
  return ENV_CONFIG.production;
}

// Export current config as default
export default getCurrentConfig();