/**
 * Integration Tests for LangChain Adapter
 * Tests the integration between our provider system and LangChain
 */

import { LangChainLLMAdapter, createChatOpenAIWithProviderSystem } from '../langchain-adapter';
import { LLMProviderFactory } from '../provider-factory';
import { HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';

// Mock environment variables
const mockEnvVars = {
  LLM_PROVIDER: 'openai',
  LLM_API_KEY: 'test-key-12345',
  LLM_MODEL: 'gpt-3.5-turbo',
  LLM_TEMPERATURE: '0.7',
  LLM_MAX_TOKENS: '2048'
};

beforeAll(() => {
  Object.entries(mockEnvVars).forEach(([key, value]) => {
    process.env[key] = value;
  });

  // Mock the health check and generate methods
  jest.spyOn(LLMProviderFactory, 'initialize').mockResolvedValue();
  jest.spyOn(LLMProviderFactory, 'getPrimaryProvider').mockImplementation(() => {
    const mockProvider = {
      generate: jest.fn().mockResolvedValue({
        content: 'Mock response',
        model: 'gpt-3.5-turbo',
        usage: {
          promptTokens: 10,
          completionTokens: 5,
          totalTokens: 15
        }
      }),
      generateStream: jest.fn().mockImplementation(async (messages, onChunk) => {
        const response = 'Mock streamed response';
        for (let i = 0; i < response.length; i++) {
          onChunk({
            content: response.slice(0, i + 1),
            done: false
          });
          await new Promise(resolve => setTimeout(resolve, 1));
        }
        onChunk({
          content: response,
          done: true
        });
        return {
          content: response,
          model: 'gpt-3.5-turbo',
          usage: {
            promptTokens: 10,
            completionTokens: response.length / 4,
            totalTokens: 10 + response.length / 4
          }
        };
      }),
      healthCheck: jest.fn().mockResolvedValue(true),
      getProviderInfo: jest.fn().mockReturnValue({
        name: 'OpenAI',
        version: '1.0.0',
        capabilities: ['text-generation', 'chat', 'streaming']
      }),
      getConfig: jest.fn().mockReturnValue({
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        temperature: 0.7,
        maxTokens: 2048
      }),
      estimateCost: jest.fn().mockReturnValue(0.001)
    } as any;

    return mockProvider;
  });
});

afterAll(() => {
  jest.restoreAllMocks();
  Object.keys(mockEnvVars).forEach(key => {
    delete process.env[key];
  });
});

describe('LangChainLLMAdapter', () => {
  let adapter: LangChainLLMAdapter;

  beforeEach(() => {
    adapter = new LangChainLLMAdapter({
      useFallback: true,
      enableCaching: true
    });
  });

  test('should initialize successfully', async () => {
    await expect(adapter.initialize()).resolves.not.toThrow();
  });

  test('should create LangChain-compatible instance', () => {
    const langChainAdapter = createChatOpenAIWithProviderSystem({
      model: 'gpt-4',
      temperature: 0.5,
      maxTokens: 1024
    });

    expect(langChainAdapter).toBeInstanceOf(LangChainLLMAdapter);
  });

  test('should handle legacy-style creation', () => {
    const langChainAdapter = createChatOpenAIWithProviderSystem({
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      maxTokens: 2048,
      providerSystemConfig: {
        primary: {
          provider: 'openai' as const,
          apiKey: 'test-key',
          model: 'gpt-3.5-turbo'
        }
      }
    });

    expect(langChainAdapter).toBeInstanceOf(LangChainLLMAdapter);
  });

  test('should invoke with messages', async () => {
    const messages = [new HumanMessage('Hello, how are you?')];

    // Mock the internal _call method
    const _callSpy = jest.spyOn(adapter as any, '_call');
    _callSpy.mockResolvedValue('Hello! I am doing well, thank you.');

    const response = await adapter.invoke(messages);

    expect(response).toBe('Hello! I am doing well, thank you.');
    expect(_callSpy).toHaveBeenCalledWith(messages);
  });

  test('should handle streaming responses', async () => {
    const messages = [new HumanMessage('Tell me a story')];

    const chunks: string[] = [];
    for await (const chunk of adapter._stream(messages)) {
      chunks.push(chunk);
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.join('')).toBe('Mock streamed response');
  });

  test('should get provider metrics', () => {
    const metrics = adapter.getMetrics();
    expect(typeof metrics).toBe('object');
  });

  test('should get system status', async () => {
    const status = await adapter.getSystemStatus();
    expect(status).toHaveProperty('primaryProvider');
    expect(status).toHaveProperty('isHealthy');
    expect(status).toHaveProperty('fallbackProviders');
    expect(status).toHaveProperty('metrics');
  });

  test('should switch providers at runtime', async () => {
    const newConfig = {
      provider: 'anthropic' as const,
      apiKey: 'sk-ant-new-key',
      model: 'claude-3-sonnet-20240229',
      temperature: 0.5,
      maxTokens: 1024
    };

    await expect(adapter.switchProvider(newConfig)).resolves.not.toThrow();
  });

  test('should get current provider info', () => {
    const info = adapter.getProviderInfo();
    expect(info).toHaveProperty('name');
    expect(info).toHaveProperty('version');
    expect(info).toHaveProperty('capabilities');
    expect(info.name).toBe('OpenAI');
  });

  test('should estimate request cost', () => {
    const messages = [
      new SystemMessage('You are a helpful assistant.'),
      new HumanMessage('What is the capital of France?')
    ];

    const cost = adapter.estimateCost(messages);
    expect(typeof cost).toBe('number');
    expect(cost).toBeGreaterThanOrEqual(0);
  });

  test('should handle fallback disabled', async () => {
    const noFallbackAdapter = new LangChainLLMAdapter({
      useFallback: false,
      enableCaching: false
    });

    await noFallbackAdapter.initialize();

    const messages = [new HumanMessage('Test message')];
    const _callSpy = jest.spyOn(noFallbackAdapter as any, '_call');
    _callSpy.mockResolvedValue('Test response');

    const response = await noFallbackAdapter.invoke(messages);
    expect(response).toBe('Test response');
  });

  test('should handle caching disabled', async () => {
    const noCacheAdapter = new LangChainLLMAdapter({
      useFallback: true,
      enableCaching: false
    });

    await noCacheAdapter.initialize();

    const messages = [new HumanMessage('Test message')];
    const _callSpy = jest.spyOn(noCacheAdapter as any, '_call');
    _callSpy.mockResolvedValue('Test response');

    const response = await noCacheAdapter.invoke(messages);
    expect(response).toBe('Test response');
  });
});

describe('LangChain Integration', () => {
  test('should work with LangChain createReactAgent', async () => {
    const { createReactAgent } = require('@langchain/langgraph/prebuilt');
    const { tool } = require('@langchain/core/tools');
    const { z } = require('zod');

    const adapter = createChatOpenAIWithProviderSystem();
    await adapter.initialize();

    // Create a simple tool for testing
    const testTool = tool(
      async (input: { query: string }) => {
        return `Result for: ${input.query}`;
      },
      {
        name: 'test_tool',
        description: 'A test tool',
        schema: z.object({
          query: z.string().describe('The query to process')
        })
      }
    );

    // Create agent with our adapter
    const agent = createReactAgent({
      llm: adapter,
      tools: [testTool],
      stateModifier: 'You are a helpful assistant.'
    });

    // Test agent invocation
    const result = await agent.invoke({
      messages: [new HumanMessage('Use the test tool with query "hello"')]
    });

    expect(result).toHaveProperty('messages');
    expect(result.messages.length).toBeGreaterThan(0);
  });

  test('should maintain compatibility with existing LangChain patterns', async () => {
    const adapter = createChatOpenAIWithProviderSystem({
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      maxTokens: 2048
    });

    await adapter.initialize();

    // Test that adapter behaves like a standard LangChain ChatOpenAI
    expect(typeof adapter.invoke).toBe('function');
    expect(typeof adapter.stream).toBe('function');
    expect(typeof adapter._call).toBe('function');
    expect(typeof adapter._stream).toBe('function');

    // Test basic message handling
    const messages = [
      new SystemMessage('You are a helpful assistant.'),
      new HumanMessage('Say hello')
    ];

    const _callSpy = jest.spyOn(adapter as any, '_call');
    _callSpy.mockResolvedValue('Hello! How can I help you today?');

    const response = await adapter.invoke(messages);
    expect(response).toBe('Hello! How can I help you today?');
    expect(_callSpy).toHaveBeenCalledWith(messages);
  });
});

describe('Error Handling', () => {
  test('should handle initialization errors gracefully', async () => {
    const mockInit = jest.spyOn(LLMProviderFactory, 'initialize');
    mockInit.mockRejectedValue(new Error('Initialization failed'));

    const adapter = new LangChainLLMAdapter();

    await expect(adapter.initialize()).rejects.toThrow('Initialization failed');

    mockInit.mockRestore();
  });

  test('should handle provider switching errors', async () => {
    const adapter = new LangChainLLMAdapter();
    await adapter.initialize();

    // Mock a provider switching error
    const mockSwitch = jest.spyOn(LLMProviderFactory, 'switchProvider');
    mockSwitch.mockRejectedValue(new Error('Provider not available'));

    const invalidConfig = {
      provider: 'invalid' as any,
      apiKey: 'test-key',
      model: 'invalid-model'
    };

    await expect(adapter.switchProvider(invalidConfig)).rejects.toThrow('Provider not available');

    mockSwitch.mockRestore();
  });

  test('should handle runtime errors in _call method', async () => {
    const adapter = new LangChainLLMAdapter();

    // Mock executeWithFallback to throw an error
    const mockExecute = jest.spyOn(LLMProviderFactory, 'executeWithFallback');
    mockExecute.mockRejectedValue(new Error('API call failed'));

    const messages = [new HumanMessage('Test message')];

    await expect((adapter as any)._call(messages)).rejects.toThrow('API call failed');

    mockExecute.mockRestore();
  });
});