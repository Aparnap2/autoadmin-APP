/**
 * LLM Provider Factory and Configuration Management
 */

import { BaseLLMProvider, LLMProviderConfig, LLMProviderRegistry, validateLLMEnvironment } from './base-provider';
import OpenAIProvider from './openai-provider';
import AnthropicProvider from './anthropic-provider';
import GroqProvider from './groq-provider';
import CustomProvider from './custom-provider';

// Register all providers
LLMProviderRegistry.register('openai', OpenAIProvider);
LLMProviderRegistry.register('anthropic', AnthropicProvider);
LLMProviderRegistry.register('groq', GroqProvider);
LLMProviderRegistry.register('custom', CustomProvider);

export interface FallbackConfig {
  enabled: boolean;
  providers: string[];
  retryOnErrors: string[];
  maxRetries: number;
}

export interface LLMProviderSystemConfig {
  primary: LLMProviderConfig;
  fallback?: FallbackConfig;
  loadBalancing?: {
    enabled: boolean;
    strategy: 'round-robin' | 'random' | 'least-used';
    providers: LLMProviderConfig[];
  };
  caching?: {
    enabled: boolean;
    ttl: number; // Time to live in seconds
    maxSize: number; // Maximum cache size
  };
  monitoring?: {
    enabled: boolean;
    trackMetrics: boolean;
    trackCosts: boolean;
    alertOnFailures: boolean;
  };
}

export interface ProviderMetrics {
  requestCount: number;
  successCount: number;
  errorCount: number;
  averageResponseTime: number;
  totalCost: number;
  lastUsed: Date;
  lastError?: string;
  isHealthy: boolean;
}

/**
 * Main LLM Provider Factory
 */
export class LLMProviderFactory {
  private static config: LLMProviderSystemConfig | null = null;
  private static providers: Map<string, BaseLLMProvider> = new Map();
  private static metrics: Map<string, ProviderMetrics> = new Map();
  private static cache: Map<string, { response: any; timestamp: number }> = new Map();

  /**
   * Initialize the provider system with configuration
   */
  static async initialize(config?: Partial<LLMProviderSystemConfig>): Promise<void> {
    // Validate environment variables first
    const envValidation = validateLLMEnvironment();
    if (!envValidation.valid) {
      throw new Error(`LLM Provider System configuration error:\n${envValidation.errors.join('\n')}`);
    }

    // Show warnings
    if (envValidation.warnings.length > 0) {
      console.warn('LLM Provider System warnings:', envValidation.warnings);
    }

    // Create default configuration from environment variables
    const defaultConfig = this.createConfigFromEnvironment();

    // Merge with provided config
    this.config = {
      ...defaultConfig,
      ...config,
      primary: {
        ...defaultConfig.primary,
        ...config?.primary
      }
    };

    // Initialize primary provider
    await this.initializePrimaryProvider();

    // Initialize fallback providers if configured
    if (this.config.fallback?.enabled) {
      await this.initializeFallbackProviders();
    }

    // Initialize load balancing providers if configured
    if (this.config.loadBalancing?.enabled) {
      await this.initializeLoadBalancingProviders();
    }

    console.log(`LLM Provider System initialized with primary provider: ${this.config.primary.provider}`);
  }

  /**
   * Get the primary provider instance
   */
  static getPrimaryProvider(): BaseLLMProvider {
    if (!this.config) {
      throw new Error('LLM Provider System not initialized. Call initialize() first.');
    }

    const providerKey = this.getProviderKey(this.config.primary);

    if (!this.providers.has(providerKey)) {
      const provider = LLMProviderRegistry.getInstance(this.config.primary);
      this.providers.set(providerKey, provider);
      this.initializeMetrics(providerKey);
    }

    return this.providers.get(providerKey)!;
  }

  /**
   * Get a provider by name (for fallback or load balancing)
   */
  static async getProvider(providerName: string): Promise<BaseLLMProvider> {
    if (!this.config) {
      throw new Error('LLM Provider System not initialized. Call initialize() first.');
    }

    let providerConfig: LLMProviderConfig | undefined;

    // Check fallback providers
    if (this.config.fallback?.providers.includes(providerName)) {
      providerConfig = this.createProviderConfig(providerName);
    }

    // Check load balancing providers
    if (this.config.loadBalancing?.enabled) {
      const lbProvider = this.config.loadBalancing.providers.find(p => p.provider === providerName);
      if (lbProvider) {
        providerConfig = lbProvider;
      }
    }

    if (!providerConfig) {
      throw new Error(`Provider '${providerName}' not found in configuration`);
    }

    const providerKey = this.getProviderKey(providerConfig);

    if (!this.providers.has(providerKey)) {
      const provider = LLMProviderRegistry.getInstance(providerConfig);

      // Health check before returning
      const isHealthy = await provider.healthCheck();
      if (!isHealthy) {
        throw new Error(`Provider '${providerName}' failed health check`);
      }

      this.providers.set(providerKey, provider);
      this.initializeMetrics(providerKey);
    }

    return this.providers.get(providerKey)!;
  }

  /**
   * Execute a request with automatic fallback
   */
  static async executeWithFallback(
    messages: any[],
    options?: {
      enableCache?: boolean;
      cacheKey?: string;
      customFallbacks?: string[];
    }
  ): Promise<any> {
    if (!this.config) {
      throw new Error('LLM Provider System not initialized. Call initialize() first.');
    }

    // Check cache first
    if (options?.enableCache && this.config.caching?.enabled) {
      const cacheKey = options.cacheKey || this.generateCacheKey(messages);
      const cached = this.getCachedResponse(cacheKey);
      if (cached) {
        return cached;
      }
    }

    let lastError: Error | null = null;
    const primaryProvider = this.getPrimaryProvider();

    // Try primary provider first
    try {
      const response = await this.executeWithMetrics(primaryProvider, messages);

      // Cache response if enabled
      if (options?.enableCache && this.config.caching?.enabled) {
        this.cacheResponse(options.cacheKey || this.generateCacheKey(messages), response);
      }

      return response;
    } catch (error) {
      lastError = error as Error;
      console.warn('Primary provider failed, trying fallbacks:', error);
    }

    // Try fallback providers if configured
    if (this.config.fallback?.enabled) {
      const fallbackProviders = [
        ...(this.config.fallback.providers || []),
        ...(options?.customFallbacks || [])
      ];

      for (const providerName of fallbackProviders) {
        try {
          const provider = await this.getProvider(providerName);
          const response = await this.executeWithMetrics(provider, messages);

          console.log(`Fallback provider '${providerName}' succeeded`);

          // Cache response if enabled
          if (options?.enableCache && this.config.caching?.enabled) {
            this.cacheResponse(options.cacheKey || this.generateCacheKey(messages), response);
          }

          return response;
        } catch (error) {
          lastError = error as Error;
          console.warn(`Fallback provider '${providerName}' failed:`, error);
        }
      }
    }

    // All providers failed
    throw lastError || new Error('All LLM providers failed');
  }

  /**
   * Execute with load balancing
   */
  static async executeWithLoadBalancing(messages: any[]): Promise<any> {
    if (!this.config?.loadBalancing?.enabled) {
      return this.executeWithFallback(messages);
    }

    const providers = this.config.loadBalancing.providers;
    const strategy = this.config.loadBalancing.strategy;
    const selectedProvider = this.selectLoadBalancedProvider(providers, strategy);

    try {
      const provider = await this.getProvider(selectedProvider.provider);
      return await this.executeWithMetrics(provider, messages);
    } catch (error) {
      console.warn(`Load balanced provider '${selectedProvider.provider}' failed:`, error);
      // Fallback to regular execution
      return this.executeWithFallback(messages);
    }
  }

  /**
   * Get provider metrics
   */
  static getMetrics(): Record<string, ProviderMetrics> {
    return Object.fromEntries(this.metrics);
  }

  /**
   * Reset provider metrics
   */
  static resetMetrics(providerName?: string): void {
    if (providerName) {
      this.metrics.delete(providerName);
    } else {
      this.metrics.clear();
    }
  }

  /**
   * Switch primary provider at runtime
   */
  static async switchProvider(newProviderConfig: LLMProviderConfig): Promise<void> {
    if (!this.config) {
      throw new Error('LLM Provider System not initialized. Call initialize() first.');
    }

    // Validate new configuration
    const providerKey = this.getProviderKey(newProviderConfig);
    const provider = LLMProviderRegistry.getInstance(newProviderConfig);

    // Health check the new provider
    const isHealthy = await provider.healthCheck();
    if (!isHealthy) {
      throw new Error(`New provider '${newProviderConfig.provider}' failed health check`);
    }

    // Update configuration
    this.config.primary = newProviderConfig;

    // Cache the new provider
    this.providers.set(providerKey, provider);
    this.initializeMetrics(providerKey);

    console.log(`Switched primary provider to: ${newProviderConfig.provider}`);
  }

  /**
   * Create configuration from environment variables
   */
  private static createConfigFromEnvironment(): LLMProviderSystemConfig {
    const provider = (process.env.LLM_PROVIDER || 'openai').toLowerCase();
    const apiKey = process.env.LLM_API_KEY || '';
    const baseUrl = process.env.LLM_BASE_URL;
    const model = process.env.LLM_MODEL || 'gpt-3.5-turbo';
    const temperature = parseFloat(process.env.LLM_TEMPERATURE || '0.7');
    const maxTokens = parseInt(process.env.LLM_MAX_TOKENS || '2048');

    // Support legacy environment variables
    const legacyApiKey = process.env.EXPO_PUBLIC_OPENAI_API_KEY;
    const finalApiKey = apiKey || legacyApiKey || '';

    const primaryConfig: LLMProviderConfig = {
      provider: provider as any,
      apiKey: finalApiKey,
      model,
      temperature,
      maxTokens,
      ...(baseUrl && { baseUrl })
    };

    // Fallback configuration
    const fallbackConfig: FallbackConfig = {
      enabled: process.env.LLM_ENABLE_FALLBACK === 'true',
      providers: (process.env.LLM_FALLBACK_PROVIDERS || '').split(',').filter(Boolean),
      retryOnErrors: (process.env.LLM_RETRY_ERRORS || 'rate_limit,server_error,timeout').split(','),
      maxRetries: parseInt(process.env.LLM_MAX_RETRIES || '3')
    };

    return {
      primary: primaryConfig,
      fallback: fallbackConfig.enabled ? fallbackConfig : undefined,
      caching: {
        enabled: process.env.LLM_ENABLE_CACHE === 'true',
        ttl: parseInt(process.env.LLM_CACHE_TTL || '300'),
        maxSize: parseInt(process.env.LLM_CACHE_MAX_SIZE || '1000')
      },
      monitoring: {
        enabled: process.env.LLM_ENABLE_MONITORING !== 'false',
        trackMetrics: process.env.LLM_TRACK_METRICS !== 'false',
        trackCosts: process.env.LLM_TRACK_COSTS === 'true',
        alertOnFailures: process.env.LLM_ALERT_FAILURES === 'true'
      }
    };
  }

  /**
   * Create provider config from provider name
   */
  private static createProviderConfig(providerName: string): LLMProviderConfig {
    // This would need to be enhanced to support different provider configurations
    // For now, use environment variables
    return this.createConfigFromEnvironment().primary;
  }

  /**
   * Initialize primary provider
   */
  private static async initializePrimaryProvider(): Promise<void> {
    const primaryProvider = this.getPrimaryProvider();
    const isHealthy = await primaryProvider.healthCheck();

    if (!isHealthy) {
      throw new Error(`Primary provider '${this.config!.primary.provider}' failed health check`);
    }
  }

  /**
   * Initialize fallback providers
   */
  private static async initializeFallbackProviders(): Promise<void> {
    if (!this.config?.fallback?.enabled) return;

    for (const providerName of this.config.fallback.providers) {
      try {
        await this.getProvider(providerName);
        console.log(`Fallback provider '${providerName}' initialized successfully`);
      } catch (error) {
        console.warn(`Failed to initialize fallback provider '${providerName}':`, error);
      }
    }
  }

  /**
   * Initialize load balancing providers
   */
  private static async initializeLoadBalancingProviders(): Promise<void> {
    if (!this.config?.loadBalancing?.enabled) return;

    for (const providerConfig of this.config.loadBalancing.providers) {
      try {
        const providerKey = this.getProviderKey(providerConfig);
        const provider = LLMProviderRegistry.getInstance(providerConfig);

        const isHealthy = await provider.healthCheck();
        if (!isHealthy) {
          console.warn(`Load balancing provider '${providerConfig.provider}' failed health check`);
          continue;
        }

        this.providers.set(providerKey, provider);
        this.initializeMetrics(providerKey);
      } catch (error) {
        console.warn(`Failed to initialize load balancing provider '${providerConfig.provider}':`, error);
      }
    }
  }

  /**
   * Get provider key for caching
   */
  private static getProviderKey(config: LLMProviderConfig): string {
    return `${config.provider}_${config.model}_${config.baseUrl || 'default'}`;
  }

  /**
   * Initialize metrics for a provider
   */
  private static initializeMetrics(providerKey: string): void {
    if (!this.metrics.has(providerKey)) {
      this.metrics.set(providerKey, {
        requestCount: 0,
        successCount: 0,
        errorCount: 0,
        averageResponseTime: 0,
        totalCost: 0,
        lastUsed: new Date(),
        isHealthy: true
      });
    }
  }

  /**
   * Execute request and track metrics
   */
  private static async executeWithMetrics(provider: BaseLLMProvider, messages: any[]): Promise<any> {
    const startTime = Date.now();
    const providerKey = this.getProviderKey(provider.getConfig());
    const metrics = this.metrics.get(providerKey)!;

    try {
      metrics.requestCount++;
      metrics.lastUsed = new Date();

      const response = await provider.generate(messages);
      const responseTime = Date.now() - startTime;

      // Update metrics
      metrics.successCount++;
      metrics.averageResponseTime = (metrics.averageResponseTime * (metrics.successCount - 1) + responseTime) / metrics.successCount;

      if (this.config?.monitoring?.trackCosts) {
        metrics.totalCost += provider.estimateCost(messages);
      }

      metrics.isHealthy = true;

      return response;
    } catch (error) {
      const responseTime = Date.now() - startTime;

      // Update error metrics
      metrics.errorCount++;
      metrics.lastError = error instanceof Error ? error.message : 'Unknown error';
      metrics.isHealthy = false;

      throw error;
    }
  }

  /**
   * Select provider using load balancing strategy
   */
  private static selectLoadBalancedProvider(
    providers: LLMProviderConfig[],
    strategy: string
  ): LLMProviderConfig {
    switch (strategy) {
      case 'round-robin':
        // Simple round-robin implementation
        const index = Date.now() % providers.length;
        return providers[index];

      case 'random':
        return providers[Math.floor(Math.random() * providers.length)];

      case 'least-used':
        // Find provider with least usage
        let leastUsedProvider = providers[0];
        let minRequests = Infinity;

        for (const provider of providers) {
          const providerKey = this.getProviderKey(provider);
          const metrics = this.metrics.get(providerKey);
          const requests = metrics?.requestCount || 0;

          if (requests < minRequests) {
            minRequests = requests;
            leastUsedProvider = provider;
          }
        }

        return leastUsedProvider;

      default:
        return providers[0];
    }
  }

  /**
   * Generate cache key from messages
   */
  private static generateCacheKey(messages: any[]): string {
    const messageString = JSON.stringify(messages);
    return `llm_cache_${Buffer.from(messageString).toString('base64')}`;
  }

  /**
   * Get cached response
   */
  private static getCachedResponse(cacheKey: string): any | null {
    if (!this.config?.caching?.enabled) return null;

    const cached = this.cache.get(cacheKey);
    if (!cached) return null;

    const now = Date.now();
    const ttl = this.config.caching.ttl * 1000; // Convert to milliseconds

    if (now - cached.timestamp > ttl) {
      this.cache.delete(cacheKey);
      return null;
    }

    return cached.response;
  }

  /**
   * Cache a response
   */
  private static cacheResponse(cacheKey: string, response: any): void {
    if (!this.config?.caching?.enabled) return;

    this.cache.set(cacheKey, {
      response,
      timestamp: Date.now()
    });

    // Clean up old cache entries if cache is too large
    if (this.cache.size > this.config.caching.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }
  }

  /**
   * Get system status
   */
  static async getSystemStatus(): Promise<{
    primaryProvider: string;
    isHealthy: boolean;
    fallbackProviders: string[];
    metrics: Record<string, ProviderMetrics>;
    cacheSize: number;
  }> {
    const primaryProvider = this.getPrimaryProvider();
    const isHealthy = await primaryProvider.healthCheck();

    return {
      primaryProvider: this.config!.primary.provider,
      isHealthy,
      fallbackProviders: this.config?.fallback?.providers || [],
      metrics: this.getMetrics(),
      cacheSize: this.cache.size
    };
  }
}

export default LLMProviderFactory;