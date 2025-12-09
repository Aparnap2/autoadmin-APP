# Flexible LLM Provider System

A comprehensive, flexible provider system for Large Language Models that supports multiple providers with automatic fallback, load balancing, caching, and monitoring capabilities.

## Overview

This system replaces hardcoded LLM integrations with a flexible, multi-provider architecture that allows you to:

- **Switch between providers** without changing code
- **Use automatic fallbacks** when a provider fails
- **Implement load balancing** across multiple providers
- **Cache responses** to reduce API costs
- **Monitor performance** and track costs
- **Maintain LangChain compatibility** with existing code

## Supported Providers

### Primary Providers
- **OpenAI** - GPT-4, GPT-3.5-turbo, and compatible endpoints
- **Anthropic** - Claude 3 Opus, Sonnet, Haiku
- **Groq** - Llama 3, Mixtral, Gemma (fast inference)
- **Custom** - Any OpenAI-compatible endpoint

### Provider Capabilities
| Provider | Streaming | Function Calling | JSON Mode | Cost |
|----------|-----------|------------------|-----------|------|
| OpenAI   | ✅        | ✅               | ✅        | 💰💰 |
| Anthropic| ✅        | ❌               | ❌        | 💰💰💰 |
| Groq     | ✅        | ❌               | ❌        | 💰 |
| Custom   | ✅        | ✅*              | ✅*       | 💰💰 |

*Depends on endpoint capabilities

## Quick Start

### 1. Environment Configuration

```bash
# Primary LLM Provider
LLM_PROVIDER=openai                    # Options: openai, anthropic, groq, custom
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# Optional: Custom endpoint
LLM_BASE_URL=https://api.example.com/v1

# Fallback Configuration
LLM_ENABLE_FALLBACK=true
LLM_FALLBACK_PROVIDERS=anthropic,groq

# Caching
LLM_ENABLE_CACHE=true
LLM_CACHE_TTL=300
```

### 2. Basic Usage

```typescript
import { LLMProviderFactory } from './llm-provider/provider-factory';

// Initialize the system
await LLMProviderFactory.initialize();

// Get the primary provider
const provider = LLMProviderFactory.getPrimaryProvider();

// Generate a response
const messages = [new HumanMessage('Hello, how are you?')];
const response = await provider.generate(messages);

console.log(response.content);
```

### 3. With Automatic Fallback

```typescript
// Execute with automatic fallback on errors
const response = await LLMProviderFactory.executeWithFallback(messages, {
  enableCache: true,
  cacheKey: 'user-query-123'
});
```

### 4. LangChain Integration

```typescript
import { createChatOpenAIWithProviderSystem } from './llm-provider/langchain-adapter';
import { createReactAgent } from '@langchain/langgraph/prebuilt';

// Create LangChain-compatible LLM
const llm = createChatOpenAIWithProviderSystem({
  model: 'gpt-4',
  temperature: 0.7,
  useFallback: true,
  enableCaching: true
});

// Use with existing LangChain agents
const agent = createReactAgent({
  llm,
  tools: [...],
  stateModifier: 'You are a helpful assistant.'
});
```

## Advanced Configuration

### Provider Switching

```typescript
// Switch providers at runtime
await LLMProviderFactory.switchProvider({
  provider: 'anthropic',
  apiKey: 'sk-ant-key',
  model: 'claude-3-sonnet-20240229',
  temperature: 0.5
});
```

### Load Balancing

```typescript
await LLMProviderFactory.initialize({
  loadBalancing: {
    enabled: true,
    strategy: 'round-robin', // or 'random', 'least-used'
    providers: [
      { provider: 'openai', apiKey: 'key1', model: 'gpt-4' },
      { provider: 'anthropic', apiKey: 'key2', model: 'claude-3-sonnet' }
    ]
  }
});
```

### Custom Provider Implementation

```typescript
import { BaseLLMProvider, LLMProviderConfig } from './base-provider';

class MyCustomProvider extends BaseLLMProvider {
  protected getDefaultConfig() {
    return { temperature: 0.7, maxTokens: 2048 };
  }

  protected validateConfig(config: LLMProviderConfig) {
    // Your validation logic
  }

  async generate(messages: BaseMessage[]): Promise<LLMResponse> {
    // Your implementation
  }

  async generateStream(messages: BaseMessage[], onChunk: Function): Promise<LLMResponse> {
    // Your streaming implementation
  }

  async healthCheck(): Promise<boolean> {
    // Your health check
  }

  // ... other required methods
}

// Register the provider
LLMProviderRegistry.register('myprovider', MyCustomProvider);
```

## Agent System Integration

The BaseAgent class has been updated to use the new provider system automatically:

```typescript
// CEO Agent with provider switching
const ceoAgent = new CEOAgent(config, userId);

// Switch provider for this agent
await ceoAgent.switchLLMProvider({
  provider: 'anthropic',
  model: 'claude-3-opus-20240229'
});

// Get provider info
const providerInfo = ceoAgent.getLLMProviderInfo();

// Get metrics
const metrics = ceoAgent.getLLMMetrics();

// Estimate costs
const cost = ceoAgent.estimateLLMCost(messages);
```

## API Endpoints

### Provider Management API

```bash
# Get system status
GET /api/llm/provider?action=status

# Get metrics
GET /api/llm/provider?action=metrics

# Switch provider
POST /api/llm/provider
{
  "action": "switch",
  "provider": "anthropic",
  "apiKey": "sk-ant-key",
  "model": "claude-3-sonnet-20240229"
}

# Health check
POST /api/llm/provider
{
  "action": "health_check"
}
```

## Monitoring and Metrics

### Provider Metrics

```typescript
const metrics = LLMProviderFactory.getMetrics();
console.log(metrics);
/*
{
  "openai_gpt-3.5-turbo_default": {
    requestCount: 150,
    successCount: 148,
    errorCount: 2,
    averageResponseTime: 1250,
    totalCost: 0.75,
    lastUsed: "2024-01-15T10:30:00Z",
    isHealthy: true
  }
}
*/
```

### System Status

```typescript
const status = await LLMProviderFactory.getSystemStatus();
console.log(status);
/*
{
  primaryProvider: "openai",
  isHealthy: true,
  fallbackProviders: ["anthropic", "groq"],
  metrics: {...},
  cacheSize: 45
}
*/
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | Primary provider |
| `LLM_API_KEY` | Yes | - | API key for primary provider |
| `LLM_MODEL` | Yes | `gpt-3.5-turbo` | Model name |
| `LLM_TEMPERATURE` | No | `0.7` | Temperature (0-2) |
| `LLM_MAX_TOKENS` | No | `2048` | Max tokens per response |
| `LLM_BASE_URL` | No | - | Custom endpoint URL |
| `LLM_TIMEOUT` | No | `60000` | Request timeout (ms) |
| `LLM_ENABLE_FALLBACK` | No | `false` | Enable fallback providers |
| `LLM_FALLBACK_PROVIDERS` | No | - | Comma-separated fallback list |
| `LLM_ENABLE_CACHE` | No | `true` | Enable response caching |
| `LLM_CACHE_TTL` | No | `300` | Cache TTL (seconds) |
| `LLM_ENABLE_MONITORING` | No | `true` | Enable monitoring |

### Provider-Specific API Keys

| Provider | Environment Variable |
|----------|----------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Custom | `CUSTOM_API_KEY` |

## Migration Guide

### From Legacy OpenAI Integration

**Before:**
```typescript
const llm = new ChatOpenAI({
  model: 'gpt-3.5-turbo',
  openAIApiKey: process.env.EXPO_PUBLIC_OPENAI_API_KEY
});
```

**After:**
```typescript
const llm = createChatOpenAIWithProviderSystem({
  model: 'gpt-3.5-turbo',
  useFallback: true
});
```

### Environment Variables Migration

**Deprecated:**
```bash
EXPO_PUBLIC_OPENAI_API_KEY=your_key
```

**New:**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=your_key
```

## Error Handling

The system provides comprehensive error handling:

```typescript
try {
  const response = await LLMProviderFactory.executeWithFallback(messages);
} catch (error) {
  if (error.retryable) {
    // Automatically retried with fallbacks
    console.log('All providers failed, but some were retryable');
  } else {
    // Non-retryable error (e.g., invalid API key)
    console.log('Configuration error:', error.message);
  }
}
```

## Testing

Run the comprehensive test suite:

```bash
npm test -- llm-provider
```

Test coverage includes:
- ✅ Provider configuration validation
- ✅ Environment variable validation
- ✅ Provider initialization and health checks
- ✅ Fallback and error handling
- ✅ Cost estimation
- ✅ LangChain integration
- ✅ API endpoints
- ✅ Metrics and monitoring

## Best Practices

### 1. Configuration Management
- Use environment variables for all configuration
- Set appropriate timeouts and retry limits
- Configure fallback providers for reliability

### 2. Cost Optimization
- Enable caching for repeated queries
- Use cheaper models for simple tasks
- Monitor costs with built-in metrics

### 3. Performance
- Choose appropriate providers for your use case
- Use streaming for long responses
- Implement proper error handling

### 4. Security
- Never commit API keys to version control
- Use different keys for different environments
- Implement proper access controls for API endpoints

## Troubleshooting

### Common Issues

**Provider initialization failed:**
- Check API key is correct
- Verify provider name is supported
- Check network connectivity

**Fallback not working:**
- Ensure `LLM_ENABLE_FALLBACK=true`
- Verify fallback providers are configured
- Check fallback API keys

**Caching issues:**
- Check `LLM_ENABLE_CACHE=true`
- Verify cache TTL settings
- Monitor cache size limits

### Debug Mode

Enable debug logging:

```typescript
process.env.LLM_DEBUG = 'true';
```

This will provide detailed logs for:
- Provider initialization
- Request/response details
- Fallback attempts
- Cache operations

## Contributing

To add a new provider:

1. Extend `BaseLLMProvider`
2. Implement all required methods
3. Add comprehensive tests
4. Register with `LLMProviderRegistry`
5. Update documentation

## License

This LLM Provider System is part of the AutoAdmin project and follows the same licensing terms.