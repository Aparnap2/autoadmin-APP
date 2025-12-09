/**
 * Custom Provider Implementation
 * For any OpenAI-compatible endpoint
 */

import { ChatOpenAI } from '@langchain/openai';
import { BaseMessage, HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';
import {
  BaseLLMProvider,
  LLMProviderConfig,
  LLMResponse,
  StreamingLLMResponse,
  LLMProviderError
} from './base-provider';

export class CustomProvider extends BaseLLMProvider {
  private client: ChatOpenAI;

  constructor(config: LLMProviderConfig) {
    super(config);
    this.client = new ChatOpenAI({
      modelName: config.model,
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens,
      openAIApiKey: config.apiKey,
      configuration: {
        baseURL: config.baseUrl,
      },
      timeout: config.timeout ?? 60000,
      maxRetries: config.retryAttempts ?? 3,
      headers: {
        'User-Agent': 'AutoAdmin/1.0',
        ...config.customHeaders
      },
    });
  }

  /**
   * Get default configuration for Custom provider
   */
  protected getDefaultConfig(): Partial<LLMProviderConfig> {
    return {
      temperature: 0.7,
      maxTokens: 2048,
      timeout: 60000,
      retryAttempts: 3
    };
  }

  /**
   * Validate Custom provider configuration
   */
  protected validateConfig(config: LLMProviderConfig): void {
    if (!config.apiKey && !this.isApiKeyOptional(config.baseUrl)) {
      throw this.createError(
        'API key is required for this endpoint',
        'MISSING_API_KEY',
        'authentication'
      );
    }

    if (!config.baseUrl) {
      throw this.createError(
        'Base URL is required for custom provider',
        'MISSING_BASE_URL',
        'invalid_request'
      );
    }

    if (!config.model) {
      throw this.createError(
        'Model name is required',
        'MISSING_MODEL',
        'invalid_request'
      );
    }

    // Validate URL format
    try {
      new URL(config.baseUrl);
    } catch {
      throw this.createError(
        'Invalid base URL format',
        'INVALID_BASE_URL',
        'invalid_request'
      );
    }
  }

  /**
   * Check if API key is optional for certain endpoints
   */
  private isApiKeyOptional(baseUrl?: string): boolean {
    if (!baseUrl) return false;

    // Local endpoints might not require API keys
    const optionalKeyPatterns = [
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      '192.168.',
      '10.',
      '.local'
    ];

    return optionalKeyPatterns.some(pattern => baseUrl.includes(pattern));
  }

  /**
   * Generate a completion for the given messages
   */
  async generate(messages: BaseMessage[]): Promise<LLMResponse> {
    try {
      const formattedMessages = this.formatMessages(messages);
      const response = await this.client.invoke(formattedMessages);

      return this.parseResponse(response);
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Generate a streaming completion
   */
  async generateStream(
    messages: BaseMessage[],
    onChunk: (chunk: StreamingLLMResponse) => void
  ): Promise<LLMResponse> {
    try {
      const formattedMessages = this.formatMessages(messages);
      let fullContent = '';
      let finalResponse: LLMResponse | null = null;

      const stream = await this.client.stream(formattedMessages);

      for await (const chunk of stream) {
        const content = chunk.content as string;
        fullContent += content;

        onChunk({
          content: fullContent,
          done: false,
          metadata: {
            model: this.config.model,
            provider: 'custom',
            endpoint: this.config.baseUrl
          }
        });
      }

      // Get final response for usage information
      try {
        const finalChunk = await this.client.invoke(formattedMessages);
        finalResponse = this.parseResponse(finalChunk);
      } catch (error) {
        // If we can't get final response, create a basic one
        finalResponse = {
          content: fullContent,
          model: this.config.model,
          usage: {
            promptTokens: 0,
            completionTokens: 0,
            totalTokens: 0
          },
          metadata: {
            provider: 'custom',
            endpoint: this.config.baseUrl
          }
        };
      }

      // Send final chunk
      onChunk({
        content: finalResponse.content,
        done: true,
        usage: finalResponse.usage,
        metadata: finalResponse.metadata
      });

      return finalResponse;
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Check if the provider is available and properly configured
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.invoke([new HumanMessage('Hello')]);
      return true;
    } catch (error) {
      console.error('Custom provider health check failed:', error);
      return false;
    }
  }

  /**
   * Format messages for OpenAI-compatible API
   */
  protected formatMessages(messages: BaseMessage[]): BaseMessage[] {
    return messages.map(msg => {
      if (msg.getType() === 'human') {
        return new HumanMessage(msg.content);
      } else if (msg.getType() === 'ai') {
        return new AIMessage(msg.content);
      } else if (msg.getType() === 'system') {
        return new SystemMessage(msg.content);
      }
      return msg;
    });
  }

  /**
   * Parse response to standard format
   */
  protected parseResponse(response: any): LLMResponse {
    return {
      content: response.content as string,
      usage: response.usage ? {
        promptTokens: response.usage.prompt_tokens || 0,
        completionTokens: response.usage.completion_tokens || 0,
        totalTokens: response.usage.total_tokens || 0
      } : {
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0
      },
      model: response.model || this.config.model,
      finishReason: response.finish_reason,
      metadata: {
        provider: 'custom',
        endpoint: this.config.baseUrl,
        responseId: response.id,
        created: response.created,
        object: response.object
      }
    };
  }

  /**
   * Calculate estimated cost for the request
   */
  estimateCost(messages: BaseMessage[], maxTokens?: number): number {
    // For custom endpoints, we can't estimate cost accurately
    // Return 0 or implement a configurable pricing model
    return 0;
  }

  /**
   * Get rate limit information
   */
  async getRateLimitInfo(): Promise<{
    requestsPerMinute: number;
    tokensPerMinute: number;
    requestsRemaining?: number;
    tokensRemaining?: number;
    resetTime?: Date;
  }> {
    // For custom endpoints, return conservative defaults
    return {
      requestsPerMinute: 60,
      tokensPerMinute: 100000
    };
  }

  /**
   * Handle custom provider errors
   */
  private handleError(error: any): LLMProviderError {
    if (error.status === 401) {
      return this.createError(
        'Authentication failed. Check your API key.',
        'INVALID_API_KEY',
        'authentication',
        false
      );
    }

    if (error.status === 429) {
      return this.createError(
        'Rate limit exceeded',
        'RATE_LIMIT_EXCEEDED',
        'rate_limit',
        true
      );
    }

    if (error.status === 400) {
      return this.createError(
        `Bad request: ${error.message}`,
        'BAD_REQUEST',
        'invalid_request',
        false
      );
    }

    if (error.status === 404) {
      return this.createError(
        'Endpoint not found. Check your base URL.',
        'ENDPOINT_NOT_FOUND',
        'invalid_request',
        false
      );
    }

    if (error.status === 500) {
      return this.createError(
        'Provider server error',
        'SERVER_ERROR',
        'server_error',
        true
      );
    }

    if (error.name === 'TimeoutError') {
      return this.createError(
        'Request timeout',
        'TIMEOUT',
        'timeout',
        true
      );
    }

    if (error.code === 'ECONNREFUSED') {
      return this.createError(
        'Connection refused. Check if the endpoint is running.',
        'CONNECTION_REFUSED',
        'server_error',
        true
      );
    }

    return this.createError(
      `Custom provider error: ${error.message}`,
      'UNKNOWN_ERROR',
      'server_error',
      true
    );
  }

  /**
   * Get provider information
   */
  getProviderInfo(): { name: string; version: string; capabilities: string[] } {
    return {
      name: 'Custom',
      version: '1.0.0',
      capabilities: [
        'text-generation',
        'chat',
        'streaming'
      ]
    };
  }
}

export default CustomProvider;