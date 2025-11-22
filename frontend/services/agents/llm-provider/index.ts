/**
 * LLM Provider System - Main Export
 *
 * This module provides a flexible, multi-provider LLM system that supports:
 * - OpenAI (including compatible endpoints)
 * - Anthropic Claude
 * - Groq
 * - Custom OpenAI-compatible endpoints
 * - Provider switching and fallbacks
 * - Load balancing
 * - Caching
 * - Metrics and monitoring
 */

// Base interfaces and classes
export {
  BaseLLMProvider,
  LLMProviderConfig,
  LLMResponse,
  LLMProviderError,
  StreamingLLMResponse,
  LLMProviderRegistry,
  validateLLMEnvironment
} from './base-provider';

// Individual provider implementations
export { default as OpenAIProvider } from './openai-provider';
export { default as AnthropicProvider } from './anthropic-provider';
export { default as GroqProvider } from './groq-provider';
export { default as CustomProvider } from './custom-provider';

// Factory and management system
export {
  LLMProviderFactory,
  type LLMProviderSystemConfig,
  type FallbackConfig,
  type ProviderMetrics
} from './provider-factory';

// Convenience exports
export { default } from './provider-factory';