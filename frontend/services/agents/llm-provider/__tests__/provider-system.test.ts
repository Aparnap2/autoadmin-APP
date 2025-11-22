/**
 * Test Suite for LLM Provider System
 * Tests all providers, factory, and functionality
 */

import {
  BaseLLMProvider,
  LLMProviderRegistry,
  LLMProviderFactory,
  OpenAIProvider,
  AnthropicProvider,
  GroqProvider,
  CustomProvider,
  validateLLMEnvironment,
  type LLMProviderConfig,
  type LLMProviderSystemConfig
} from '../index';
import { HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';

// Mock environment variables
const mockEnvVars = {
  LLM_PROVIDER: 'openai',
  LLM_API_KEY: 'test-key-12345',
  LLM_MODEL: 'gpt-3.5-turbo',
  LLM_TEMPERATURE: '0.7',
  LLM_MAX_TOKENS: '2048',
  LLM_ENABLE_FALLBACK: 'false',
  LLM_ENABLE_CACHE: 'true',
  LLM_CACHE_TTL: '300',
  LLM_CACHE_MAX_SIZE: '1000',
  LLM_ENABLE_MONITORING: 'true',
  LLM_TRACK_METRICS: 'true'
};

// Setup and teardown
beforeAll(() => {
  // Set environment variables for testing
  Object.entries(mockEnvVars).forEach(([key, value]) => {
    process.env[key] = value;
  });
});

afterAll(() => {
  // Clean up environment variables
  Object.keys(mockEnvVars).forEach(key => {
    delete process.env[key];
  });
});

describe('LLM Provider Registry', () => {
  test('should register all providers correctly', () => {
    const registeredProviders = LLMProviderRegistry.listProviders();
    expect(registeredProviders).toContain('openai');
    expect(registeredProviders).toContain('anthropic');
    expect(registeredProviders).toContain('groq');
    expect(registeredProviders).toContain('custom');
  });

  test('should get provider class by name', () => {
    const OpenAIClass = LLMProviderRegistry.getProvider('openai');
    expect(OpenAIClass).toBe(OpenAIProvider);

    const AnthropicClass = LLMProviderRegistry.getProvider('anthropic');
    expect(AnthropicClass).toBe(AnthropicProvider);

    const GroqClass = LLMProviderRegistry.getProvider('groq');
    expect(GroqClass).toBe(GroqProvider);

    const CustomClass = LLMProviderRegistry.getProvider('custom');
    expect(CustomClass).toBe(CustomProvider);
  });

  test('should return undefined for unregistered provider', () => {
    const UnknownClass = LLMProviderRegistry.getProvider('unknown');
    expect(UnknownClass).toBeUndefined();
  });
});

describe('Provider Configuration', () => {
  test('should validate OpenAI provider configuration', () => {
    const validConfig: LLMProviderConfig = {
      provider: 'openai',
      apiKey: 'sk-test-key',
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      maxTokens: 2048
    };

    expect(() => new OpenAIProvider(validConfig)).not.toThrow();
  });

  test('should reject invalid OpenAI configuration', () => {
    const invalidConfig: LLMProviderConfig = {
      provider: 'openai',
      apiKey: '', // Empty API key
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      maxTokens: 2048
    };

    expect(() => new OpenAIProvider(invalidConfig)).toThrow('OpenAI API key is required');
  });

  test('should validate Anthropic provider configuration', () => {
    const validConfig: LLMProviderConfig = {
      provider: 'anthropic',
      apiKey: 'sk-ant-test-key',
      model: 'claude-3-sonnet-20240229',
      temperature: 0.7,
      maxTokens: 2048
    };

    expect(() => new AnthropicProvider(validConfig)).not.toThrow();
  });

  test('should validate Groq provider configuration', () => {
    const validConfig: LLMProviderConfig = {
      provider: 'groq',
      apiKey: 'gsk_test_key',
      model: 'llama3-8b-8192',
      temperature: 0.7,
      maxTokens: 2048
    };

    expect(() => new GroqProvider(validConfig)).not.toThrow();
  });

  test('should validate Custom provider configuration', () => {
    const validConfig: LLMProviderConfig = {
      provider: 'custom',
      apiKey: 'custom-key',
      model: 'custom-model',
      temperature: 0.7,
      maxTokens: 2048,
      baseUrl: 'https://api.example.com/v1'
    };

    expect(() => new CustomProvider(validConfig)).not.toThrow();
  });

  test('should reject custom provider without base URL', () => {
    const invalidConfig: LLMProviderConfig = {
      provider: 'custom',
      apiKey: 'custom-key',
      model: 'custom-model',
      temperature: 0.7,
      maxTokens: 2048
      // Missing baseUrl
    };

    expect(() => new CustomProvider(invalidConfig)).toThrow('Base URL is required');
  });
});

describe('Environment Validation', () => {
  test('should validate environment variables correctly', () => {
    const validation = validateLLMEnvironment();
    expect(validation.valid).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  test('should detect missing required environment variables', () => {
    delete process.env.LLM_PROVIDER;

    const validation = validateLLMEnvironment();
    expect(validation.valid).toBe(false);
    expect(validation.errors).toContain('Missing required environment variable: LLM_PROVIDER');

    // Restore
    process.env.LLM_PROVIDER = 'openai';
  });

  test('should detect unsupported provider', () => {
    process.env.LLM_PROVIDER = 'unsupported';

    const validation = validateLLMEnvironment();
    expect(validation.valid).toBe(false);
    expect(validation.errors).toContain('Unsupported LLM provider: unsupported');

    // Restore
    process.env.LLM_PROVIDER = 'openai';
  });

  test('should show warnings for deprecated variables', () => {
    process.env.EXPO_PUBLIC_OPENAI_API_KEY = 'deprecated-key';

    const validation = validateLLMEnvironment();
    expect(validation.warnings).toContain('EXPO_PUBLIC_OPENAI_API_KEY is deprecated. Use LLM_API_KEY instead.');

    // Restore
    delete process.env.EXPO_PUBLIC_OPENAI_API_KEY;
  });
});

describe('LLM Provider Factory', () => {
  beforeAll(async () => {
    // Mock the health check to avoid actual API calls
    jest.spyOn(OpenAIProvider.prototype, 'healthCheck').mockResolvedValue(true);
    jest.spyOn(AnthropicProvider.prototype, 'healthCheck').mockResolvedValue(true);
    jest.spyOn(GroqProvider.prototype, 'healthCheck').mockResolvedValue(true);
    jest.spyOn(CustomProvider.prototype, 'healthCheck').mockResolvedValue(true);

    // Mock the generate method
    jest.spyOn(OpenAIProvider.prototype, 'generate').mockResolvedValue({
      content: 'Test response',
      model: 'gpt-3.5-turbo',
      usage: {
        promptTokens: 10,
        completionTokens: 5,
        totalTokens: 15
      }
    });
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  test('should initialize with environment configuration', async () => {
    await expect(LLMProviderFactory.initialize()).resolves.not.toThrow();
  });

  test('should get primary provider after initialization', async () => {
    await LLMProviderFactory.initialize();
    const provider = LLMProviderFactory.getPrimaryProvider();
    expect(provider).toBeInstanceOf(BaseLLMProvider);
    expect(provider.getProviderInfo().name).toBe('OpenAI');
  });

  test('should create config from environment variables', async () => {
    await LLMProviderFactory.initialize();
    const provider = LLMProviderFactory.getPrimaryProvider();
    const config = provider.getConfig();

    expect(config.provider).toBe('openai');
    expect(config.apiKey).toBe('test-key-12345');
    expect(config.model).toBe('gpt-3.5-turbo');
  });

  test('should execute requests with fallback disabled', async () => {
    await LLMProviderFactory.initialize();

    const messages = [new HumanMessage('Hello')];
    const response = await LLMProviderFactory.executeWithFallback(messages, {
      enableCache: false // Disable caching for this test
    });

    expect(response.content).toBe('Test response');
    expect(response.model).toBe('gpt-3.5-turbo');
  });

  test('should track provider metrics', async () => {
    await LLMProviderFactory.initialize();

    const messages = [new HumanMessage('Hello')];
    await LLMProviderFactory.executeWithFallback(messages, {
      enableCache: false
    });

    const metrics = LLMProviderFactory.getMetrics();
    expect(Object.keys(metrics)).toContain('openai_gpt-3.5-turbo_default');
    expect(metrics['openai_gpt-3.5-turbo_default'].requestCount).toBeGreaterThan(0);
  });

  test('should switch providers at runtime', async () => {
    await LLMProviderFactory.initialize();

    const newConfig: LLMProviderConfig = {
      provider: 'anthropic',
      apiKey: 'sk-ant-new-key',
      model: 'claude-3-sonnet-20240229',
      temperature: 0.5,
      maxTokens: 1024
    };

    await expect(LLMProviderFactory.switchProvider(newConfig)).resolves.not.toThrow();

    const provider = LLMProviderFactory.getPrimaryProvider();
    expect(provider.getProviderInfo().name).toBe('Anthropic');
  });

  test('should get system status', async () => {
    await LLMProviderFactory.initialize();

    const status = await LLMProviderFactory.getSystemStatus();
    expect(status).toHaveProperty('primaryProvider');
    expect(status).toHaveProperty('isHealthy');
    expect(status).toHaveProperty('fallbackProviders');
    expect(status).toHaveProperty('metrics');
    expect(status).toHaveProperty('cacheSize');
  });
});

describe('Provider Cost Estimation', () => {
  test('should estimate OpenAI costs correctly', () => {
    const provider = new OpenAIProvider({
      provider: 'openai',
      apiKey: 'test-key',
      model: 'gpt-3.5-turbo'
    });

    const messages = [
      new HumanMessage('This is a test message for cost estimation.')
    ];

    const cost = provider.estimateCost(messages, 100);
    expect(typeof cost).toBe('number');
    expect(cost).toBeGreaterThanOrEqual(0);
  });

  test('should estimate Anthropic costs correctly', () => {
    const provider = new AnthropicProvider({
      provider: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-3-sonnet-20240229'
    });

    const messages = [
      new HumanMessage('This is a test message for cost estimation.')
    ];

    const cost = provider.estimateCost(messages, 100);
    expect(typeof cost).toBe('number');
    expect(cost).toBeGreaterThanOrEqual(0);
  });

  test('should estimate Groq costs correctly', () => {
    const provider = new GroqProvider({
      provider: 'groq',
      apiKey: 'test-key',
      model: 'llama3-8b-8192'
    });

    const messages = [
      new HumanMessage('This is a test message for cost estimation.')
    ];

    const cost = provider.estimateCost(messages, 100);
    expect(typeof cost).toBe('number');
    expect(cost).toBeGreaterThanOrEqual(0);
  });

  test('should return zero cost for custom provider', () => {
    const provider = new CustomProvider({
      provider: 'custom',
      apiKey: 'test-key',
      model: 'custom-model',
      baseUrl: 'https://api.example.com/v1'
    });

    const messages = [
      new HumanMessage('This is a test message.')
    ];

    const cost = provider.estimateCost(messages, 100);
    expect(cost).toBe(0);
  });
});

describe('Provider Capabilities', () => {
  test('should return correct capabilities for OpenAI provider', () => {
    const provider = new OpenAIProvider({
      provider: 'openai',
      apiKey: 'test-key',
      model: 'gpt-3.5-turbo'
    });

    const info = provider.getProviderInfo();
    expect(info.capabilities).toContain('text-generation');
    expect(info.capabilities).toContain('chat');
    expect(info.capabilities).toContain('streaming');
    expect(info.capabilities).toContain('function-calling');
    expect(info.capabilities).toContain('json-mode');
  });

  test('should return correct capabilities for Anthropic provider', () => {
    const provider = new AnthropicProvider({
      provider: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-3-sonnet-20240229'
    });

    const info = provider.getProviderInfo();
    expect(info.capabilities).toContain('text-generation');
    expect(info.capabilities).toContain('chat');
    expect(info.capabilities).toContain('streaming');
  });

  test('should return correct capabilities for Groq provider', () => {
    const provider = new GroqProvider({
      provider: 'groq',
      apiKey: 'test-key',
      model: 'llama3-8b-8192'
    });

    const info = provider.getProviderInfo();
    expect(info.capabilities).toContain('text-generation');
    expect(info.capabilities).toContain('chat');
    expect(info.capabilities).toContain('streaming');
    expect(info.capabilities).toContain('fast-inference');
  });

  test('should return correct capabilities for Custom provider', () => {
    const provider = new CustomProvider({
      provider: 'custom',
      apiKey: 'test-key',
      model: 'custom-model',
      baseUrl: 'https://api.example.com/v1'
    });

    const info = provider.getProviderInfo();
    expect(info.capabilities).toContain('text-generation');
    expect(info.capabilities).toContain('chat');
    expect(info.capabilities).toContain('streaming');
  });
});

describe('Rate Limit Information', () => {
  test('should return rate limit info for OpenAI provider', async () => {
    const provider = new OpenAIProvider({
      provider: 'openai',
      apiKey: 'test-key',
      model: 'gpt-3.5-turbo'
    });

    const rateLimit = await provider.getRateLimitInfo();
    expect(rateLimit).toHaveProperty('requestsPerMinute');
    expect(rateLimit).toHaveProperty('tokensPerMinute');
    expect(typeof rateLimit.requestsPerMinute).toBe('number');
    expect(typeof rateLimit.tokensPerMinute).toBe('number');
  });

  test('should return rate limit info for Anthropic provider', async () => {
    const provider = new AnthropicProvider({
      provider: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-3-sonnet-20240229'
    });

    const rateLimit = await provider.getRateLimitInfo();
    expect(rateLimit).toHaveProperty('requestsPerMinute');
    expect(rateLimit).toHaveProperty('tokensPerMinute');
    expect(typeof rateLimit.requestsPerMinute).toBe('number');
    expect(typeof rateLimit.tokensPerMinute).toBe('number');
  });

  test('should return rate limit info for Groq provider', async () => {
    const provider = new GroqProvider({
      provider: 'groq',
      apiKey: 'test-key',
      model: 'llama3-8b-8192'
    });

    const rateLimit = await provider.getRateLimitInfo();
    expect(rateLimit).toHaveProperty('requestsPerMinute');
    expect(rateLimit).toHaveProperty('tokensPerMinute');
    expect(typeof rateLimit.requestsPerMinute).toBe('number');
    expect(typeof rateLimit.tokensPerMinute).toBe('number');
  });

  test('should return rate limit info for Custom provider', async () => {
    const provider = new CustomProvider({
      provider: 'custom',
      apiKey: 'test-key',
      model: 'custom-model',
      baseUrl: 'https://api.example.com/v1'
    });

    const rateLimit = await provider.getRateLimitInfo();
    expect(rateLimit).toHaveProperty('requestsPerMinute');
    expect(rateLimit).toHaveProperty('tokensPerMinute');
    expect(typeof rateLimit.requestsPerMinute).toBe('number');
    expect(typeof rateLimit.tokensPerMinute).toBe('number');
  });
});

describe('Supported Models', () => {
  test('should return correct supported models for OpenAI', () => {
    const models = OpenAIProvider.getSupportedModels();
    expect(models).toContain('gpt-4');
    expect(models).toContain('gpt-3.5-turbo');
    expect(models).toContain('gpt-4o');
    expect(models).toContain('gpt-4o-mini');
  });

  test('should return correct supported models for Anthropic', () => {
    const models = AnthropicProvider.getSupportedModels();
    expect(models).toContain('claude-3-opus-20240229');
    expect(models).toContain('claude-3-sonnet-20240229');
    expect(models).toContain('claude-3-haiku-20240307');
  });

  test('should return correct supported models for Groq', () => {
    const models = GroqProvider.getSupportedModels();
    expect(models).toContain('llama3-70b-8192');
    expect(models).toContain('llama3-8b-8192');
    expect(models).toContain('mixtral-8x7b-32768');
  });
});