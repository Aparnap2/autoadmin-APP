import '@testing-library/jest-dom';

// Mock environment variables
process.env.EXPO_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-service-role-key';
process.env.GITHUB_TOKEN = 'test-github-token';
process.env.GITHUB_REPO_OWNER = 'test-owner';
process.env.GITHUB_REPO_NAME = 'test-repo';
process.env.WEBHOOK_SECRET = 'test-webhook-secret';
process.env.EXPO_PUBLIC_NETLIFY_FUNCTIONS_URL = 'https://test.netlify.app';

// Mock Next.js API request/response
global.NextApiRequest = class MockNextApiRequest {
  constructor(options = {}) {
    this.method = options.method || 'GET';
    this.query = options.query || {};
    this.body = options.body || {};
    this.headers = options.headers || {};
  }
};

global.NextApiResponse = class MockNextApiResponse {
  constructor() {
    this.statusCode = 200;
    this.headersSent = false;
    this.locals = {};
  }

  status(code) {
    this.statusCode = code;
    return this;
  }

  json(data) {
    this.data = data;
    return this;
  }

  send(data) {
    this.data = data;
    return this;
  }

  setHeader(name, value) {
    this.headers = this.headers || {};
    this.headers[name] = value;
    return this;
  }
};

// Mock Supabase client
jest.mock('@supabase/supabase-js', () => ({
  createClient: jest.fn(() => ({
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      insert: jest.fn().mockReturnThis(),
      update: jest.fn().mockReturnThis(),
      delete: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      in: jest.fn().mockReturnThis(),
      or: jest.fn().mockReturnThis(),
      order: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      range: jest.fn().mockReturnThis(),
      single: jest.fn().mockReturnThis(),
      rpc: jest.fn().mockReturnThis()
    })),
    auth: {
      setSession: jest.fn(),
      getUser: jest.fn().mockResolvedValue({ data: { user: null }, error: null })
    },
    storage: {
      from: jest.fn(() => ({
        upload: jest.fn(),
        download: jest.fn(),
        remove: jest.fn(),
        list: jest.fn()
      }))
    }
  }))
}));

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock crypto for webhook signatures
global.crypto = {
  createHmac: jest.fn(() => ({
    update: jest.fn().mockReturnThis(),
    digest: jest.fn((format) => {
      if (format === 'hex') {
        return 'mock-signature-hex';
      }
      return Buffer.from('mock-signature');
    })
  })),
  timingSafeEqual: jest.fn((a, b) => {
    return Buffer.compare(a, b) === 0;
  })
};

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
};

// Mock timers for async tests
jest.useFakeTimers();

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  global.fetch.mockClear();
});

// Clean up after each test
afterEach(() => {
  jest.clearAllTimers();
});

// Mock worklets
jest.mock('react-native-worklets-core', () => ({
  worklet: (fn) => fn,
  runOnUI: (fn) => fn,
  runOnJS: (fn) => fn
}));

// Test utilities
export const createMockRequest = (overrides = {}) => {
  return {
    method: 'GET',
    query: {},
    body: {},
    headers: {},
    ...overrides
  };
};

export const createMockResponse = () => {
  const res = {
    statusCode: 200,
    headersSent: false,
    headers: {},
    locals: {},
    data: null,

    status: function(code) {
      this.statusCode = code;
      return this;
    },

    json: function(data) {
      this.data = data;
      return this;
    },

    send: function(data) {
      this.data = data;
      return this;
    },

    setHeader: function(name, value) {
      this.headers[name] = value;
      return this;
    }
  };

  return res;
};

export const createMockSupabaseClient = (overrides = {}) => {
  const defaultClient = {
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      insert: jest.fn().mockReturnThis(),
      update: jest.fn().mockReturnThis(),
      delete: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      in: jest.fn().mockReturnThis(),
      or: jest.fn().mockReturnThis(),
      order: jest.fn().mockReturnThis(),
      limit: jest.fn().mockReturnThis(),
      range: jest.fn().mockReturnThis(),
      single: jest.fn().mockReturnThis(),
      rpc: jest.fn().mockReturnThis()
    })),
    auth: {
      setSession: jest.fn(),
      getUser: jest.fn().mockResolvedValue({ data: { user: null }, error: null })
    },
    ...overrides
  };

  return defaultClient;
};