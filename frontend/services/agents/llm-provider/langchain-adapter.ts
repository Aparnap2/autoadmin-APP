/**
 * LangChain Adapter for LLM Provider System
 * Bridges our provider system with LangChain ChatOpenAI interface
 */

import { ChatOpenAI } from '@langchain/openai';
import { BaseMessage } from '@langchain/core/messages';
import { LLMProviderFactory, LLMProviderSystemConfig } from './provider-factory';
import { BaseLLMProvider, LLMProviderConfig, LLMResponse } from './base-provider';

/**
 * LangChain-compatible adapter that uses our flexible LLM provider system
 */
export class LangChainLLMAdapter extends ChatOpenAI {
  private providerSystem: typeof LLMProviderFactory;
  private useFallback: boolean;
  private enableCaching: boolean;

  constructor(
    config: {
      providerSystemConfig?: Partial<LLMProviderSystemConfig>;
      useFallback?: boolean;
      enableCaching?: boolean;
    } = {}
  ) {
    // Create a dummy ChatOpenAI instance to satisfy LangChain requirements
    // The actual LLM logic will be handled by our provider system
    super({
      modelName: 'gpt-3.5-turbo',
      openAIApiKey: 'dummy-key', // We'll override this in our implementation
      temperature: 0.7,
      maxTokens: 2048,
    });

    this.providerSystem = LLMProviderFactory;
    this.useFallback = config.useFallback ?? true;
    this.enableCaching = config.enableCaching ?? true;
  }

  /**
   * Initialize the provider system
   */
  async initialize(): Promise<void> {
    await this.providerSystem.initialize();
  }

  /**
   * Override the invoke method to use our provider system
   */
  async _call(messages: BaseMessage[]): Promise<string> {
    if (this.useFallback) {
      const response = await this.providerSystem.executeWithFallback(
        messages,
        {
          enableCache: this.enableCaching
        }
      );
      return response.content;
    } else {
      const provider = this.providerSystem.getPrimaryProvider();
      const response = await provider.generate(messages);
      return response.content;
    }
  }

  /**
   * Override streaming support
   */
  async *_stream(
    messages: BaseMessage[]
  ): AsyncGenerator<string> {
    if (this.useFallback) {
      let fullContent = '';

      const response = await this.providerSystem.executeWithFallback(
        messages,
        {
          enableCache: this.enableCaching
        }
      );

      // Simulate streaming by yielding chunks
      const chunkSize = 10; // characters per chunk
      for (let i = 0; i < response.content.length; i += chunkSize) {
        const chunk = response.content.slice(i, i + chunkSize);
        yield chunk;
        // Small delay to simulate streaming
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    } else {
      const provider = this.providerSystem.getPrimaryProvider();
      let fullContent = '';

      // Use real streaming if supported by the provider
      const response = await provider.generateStream(
        messages,
        (chunk) => {
          if (chunk.content.length > fullContent.length) {
            const newContent = chunk.content.slice(fullContent.length);
            fullContent = chunk.content;
            // Yield new content
            // Note: This is a simplified approach for streaming
            // In a real implementation, you'd want to handle this more gracefully
          }
        }
      );

      // For simplicity, we'll simulate streaming from the final response
      const chunkSize = 10;
      for (let i = 0; i < response.content.length; i += chunkSize) {
        const chunk = response.content.slice(i, i + chunkSize);
        yield chunk;
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    }
  }

  /**
   * Get provider system metrics
   */
  getMetrics() {
    return this.providerSystem.getMetrics();
  }

  /**
   * Get system status
   */
  async getSystemStatus() {
    return this.providerSystem.getSystemStatus();
  }

  /**
   * Switch to a different provider at runtime
   */
  async switchProvider(providerConfig: LLMProviderConfig) {
    await this.providerSystem.switchProvider(providerConfig);
  }

  /**
   * Get current provider info
   */
  getProviderInfo() {
    const provider = this.providerSystem.getPrimaryProvider();
    return provider.getProviderInfo();
  }

  /**
   * Estimate cost for a request
   */
  estimateCost(messages: BaseMessage[]) {
    const provider = this.providerSystem.getPrimaryProvider();
    return provider.estimateCost(messages);
  }
}

/**
 * Factory function to create LangChain-compatible LLM instances
 */
export function createLangChainLLM(
  config: {
    providerSystemConfig?: Partial<LLMProviderSystemConfig>;
    useFallback?: boolean;
    enableCaching?: boolean;
  } = {}
): LangChainLLMAdapter {
  return new LangChainLLMAdapter(config);
}

/**
 * Initialize the LLM provider system for use with LangChain
 */
export async function initializeLLMSystem(
  config?: Partial<LLMProviderSystemConfig>
): Promise<LangChainLLMAdapter> {
  const adapter = createLangChainLLM({ providerSystemConfig: config });
  await adapter.initialize();
  return adapter;
}

/**
 * Legacy compatibility function - creates an adapter that looks like ChatOpenAI
 * but uses our flexible provider system underneath
 */
export function createChatOpenAIWithProviderSystem(
  options: {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    providerSystemConfig?: Partial<LLMProviderSystemConfig>;
  } = {}
): LangChainLLMAdapter {
  const config = {
    providerSystemConfig: {
      ...options.providerSystemConfig,
      primary: {
        ...(options.providerSystemConfig?.primary || {}),
        model: options.model,
        temperature: options.temperature,
        maxTokens: options.maxTokens
      }
    },
    useFallback: true,
    enableCaching: true
  };

  return new LangChainLLMAdapter(config);
}

export default LangChainLLMAdapter;