/**
 * Abstract LLM Provider Interface
 * Defines the contract for all LLM providers in the system
 */

import { BaseMessage, HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';

export interface LLMProviderConfig {
  provider: 'openai' | 'anthropic' | 'groq' | 'custom' | 'azure';
  apiKey: string;
  baseUrl?: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
  timeout?: number;
  retryAttempts?: number;
  customHeaders?: Record<string, string>;
}

export interface LLMResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  model: string;
  finishReason?: string;
  metadata?: Record<string, any>;
}

export interface LLMProviderError extends Error {
  code?: string;
  type?: 'rate_limit' | 'authentication' | 'invalid_request' | 'server_error' | 'timeout';
  retryable?: boolean;
  provider?: string;
}

export interface StreamingLLMResponse {
  content: string;
  done: boolean;
  usage?: LLMResponse['usage'];
  metadata?: Record<string, any>;
}

/**
 * Abstract base class for all LLM providers
 */
export abstract class BaseLLMProvider {
  protected config: LLMProviderConfig;

  constructor(config: LLMProviderConfig) {
    this.validateConfig(config);
    this.config = { ...this.getDefaultConfig(), ...config };
  }

  /**
   * Get default configuration for the provider
   */
  protected abstract getDefaultConfig(): Partial<LLMProviderConfig>;

  /**
   * Validate provider-specific configuration
   */
  protected abstract validateConfig(config: LLMProviderConfig): void;

  /**
   * Generate a completion for the given messages
   */
  abstract generate(messages: BaseMessage[]): Promise<LLMResponse>;

  /**
   * Generate a streaming completion
   */
  abstract generateStream(
    messages: BaseMessage[],
    onChunk: (chunk: StreamingLLMResponse) => void
  ): Promise<LLMResponse>;

  /**
   * Check if the provider is available and properly configured
   */
  abstract healthCheck(): Promise<boolean>;

  /**
   * Get provider information
   */
  getProviderInfo(): { name: string; version: string; capabilities: string[] } {
    return {
      name: this.config.provider,
      version: '1.0.0',
      capabilities: ['text-generation', 'chat']
    };
  }

  /**
   * Get current configuration
   */
  getConfig(): LLMProviderConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<LLMProviderConfig>): void {
    this.validateConfig({ ...this.config, ...updates });
    this.config = { ...this.config, ...updates };
  }

  /**
   * Create a standardized error
   */
  protected createError(
    message: string,
    code?: string,
    type?: LLMProviderError['type'],
    retryable: boolean = false
  ): LLMProviderError {
    const error = new Error(message) as LLMProviderError;
    error.code = code;
    error.type = type;
    error.retryable = retryable;
    error.provider = this.config.provider;
    return error;
  }

  /**
   * Convert messages to the format expected by the provider
   */
  protected abstract formatMessages(messages: BaseMessage[]): any[];

  /**
   * Parse provider response to standard format
   */
  protected abstract parseResponse(response: any): LLMResponse;

  /**
   * Calculate estimated cost for the request
   */
  abstract estimateCost(messages: BaseMessage[], maxTokens?: number): number;

  /**
   * Get rate limit information
   */
  abstract getRateLimitInfo(): Promise<{
    requestsPerMinute: number;
    tokensPerMinute: number;
    requestsRemaining?: number;
    tokensRemaining?: number;
    resetTime?: Date;
  }>;
}

/**
 * Provider Registry for managing available providers
 */
export class LLMProviderRegistry {
  private static providers = new Map<string, typeof BaseLLMProvider>();
  private static instances = new Map<string, BaseLLMProvider>();

  /**
   * Register a new provider type
   */
  static register(name: string, providerClass: typeof BaseLLMProvider): void {
    this.providers.set(name.toLowerCase(), providerClass);
  }

  /**
   * Get a registered provider class
   */
  static getProvider(name: string): typeof BaseLLMProvider | undefined {
    return this.providers.get(name.toLowerCase());
  }

  /**
   * List all registered providers
   */
  static listProviders(): string[] {
    return Array.from(this.providers.keys());
  }

  /**
   * Create or get a cached provider instance
   */
  static getInstance(config: LLMProviderConfig): BaseLLMProvider {
    const cacheKey = `${config.provider}_${config.model}_${config.apiKey.slice(-8)}`;

    if (!this.instances.has(cacheKey)) {
      const ProviderClass = this.getProvider(config.provider);
      if (!ProviderClass) {
        throw new Error(`Provider '${config.provider}' not registered. Available providers: ${this.listProviders().join(', ')}`);
      }

      const instance = new ProviderClass(config);
      this.instances.set(cacheKey, instance);
    }

    return this.instances.get(cacheKey)!;
  }

  /**
   * Clear cached instances
   */
  static clearCache(): void {
    this.instances.clear();
  }

  /**
   * Remove a specific instance from cache
   */
  static removeInstance(config: LLMProviderConfig): void {
    const cacheKey = `${config.provider}_${config.model}_${config.apiKey.slice(-8)}`;
    this.instances.delete(cacheKey);
  }
}

/**
 * Utility function to validate environment variables for LLM configuration
 */
export function validateLLMEnvironment(): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  const requiredEnvVars = [
    'LLM_PROVIDER',
    'LLM_API_KEY',
    'LLM_MODEL'
  ];

  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      errors.push(`Missing required environment variable: ${envVar}`);
    }
  }

  const provider = process.env.LLM_PROVIDER?.toLowerCase();
  const supportedProviders = ['openai', 'anthropic', 'groq', 'custom', 'azure'];

  if (provider && !supportedProviders.includes(provider)) {
    errors.push(`Unsupported LLM provider: ${provider}. Supported providers: ${supportedProviders.join(', ')}`);
  }

  // Check for deprecated environment variables
  if (process.env.EXPO_PUBLIC_OPENAI_API_KEY && !process.env.LLM_API_KEY) {
    warnings.push('EXPO_PUBLIC_OPENAI_API_KEY is deprecated. Use LLM_API_KEY instead.');
  }

  if (process.env.GROQ_API_KEY && provider !== 'groq') {
    warnings.push('GROQ_API_KEY is set but LLM_PROVIDER is not "groq"');
  }

  if (process.env.ANTHROPIC_API_KEY && provider !== 'anthropic') {
    warnings.push('ANTHROPIC_API_KEY is set but LLM_PROVIDER is not "anthropic"');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

export default BaseLLMProvider;