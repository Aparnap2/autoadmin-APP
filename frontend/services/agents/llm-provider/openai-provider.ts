/**
 * OpenAI Provider Implementation
 * Supports OpenAI API and compatible endpoints
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

export class OpenAIProvider extends BaseLLMProvider {
  private client: ChatOpenAI;

  constructor(config: LLMProviderConfig) {
    super(config);
    this.client = new ChatOpenAI({
      modelName: config.model,
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens,
      openAIApiKey: config.apiKey,
      configuration: config.baseUrl ? {
        baseURL: config.baseUrl,
      } : undefined,
      timeout: config.timeout ?? 60000, // 60 seconds default
      maxRetries: config.retryAttempts ?? 3,
      headers: config.customHeaders,
    });
  }

  /**
   * Get default configuration for OpenAI provider
   */
  protected getDefaultConfig(): Partial<LLMProviderConfig> {
    return {
      temperature: 0.7,
      maxTokens: 2048,
      timeout: 60000,
      retryAttempts: 3,
      model: 'gpt-3.5-turbo'
    };
  }

  /**
   * Validate OpenAI-specific configuration
   */
  protected validateConfig(config: LLMProviderConfig): void {
    if (!config.apiKey) {
      throw this.createError(
        'OpenAI API key is required',
        'MISSING_API_KEY',
        'authentication'
      );
    }

    if (!config.model) {
      throw this.createError(
        'Model name is required',
        'MISSING_MODEL',
        'invalid_request'
      );
    }

    // Validate OpenAI model names
    const validModels = [
      'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 'gpt-4o', 'gpt-4o-mini',
      'gpt-3.5-turbo', 'gpt-3.5-turbo-16k',
      'text-davinci-003', 'text-davinci-002'
    ];

    // For custom endpoints, allow any model name
    if (!config.baseUrl && !validModels.includes(config.model)) {
      throw this.createError(
        `Invalid model: ${config.model}. Valid models: ${validModels.join(', ')}`,
        'INVALID_MODEL',
        'invalid_request'
      );
    }

    // Validate temperature
    if (config.temperature !== undefined && (config.temperature < 0 || config.temperature > 2)) {
      throw this.createError(
        'Temperature must be between 0 and 2',
        'INVALID_TEMPERATURE',
        'invalid_request'
      );
    }

    // Validate maxTokens
    if (config.maxTokens !== undefined && config.maxTokens <= 0) {
      throw this.createError(
        'Max tokens must be greater than 0',
        'INVALID_MAX_TOKENS',
        'invalid_request'
      );
    }
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
            provider: 'openai'
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
      console.error('OpenAI health check failed:', error);
      return false;
    }
  }

  /**
   * Format messages for OpenAI API
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
   * Parse OpenAI response to standard format
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
        provider: 'openai',
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
    // OpenAI pricing (as of 2024, approximate - update with current pricing)
    const pricing: Record<string, { input: number; output: number }> = {
      'gpt-4': { input: 0.00003, output: 0.00006 },
      'gpt-4-turbo': { input: 0.00001, output: 0.00003 },
      'gpt-4-turbo-preview': { input: 0.00001, output: 0.00003 },
      'gpt-4o': { input: 0.000005, output: 0.000015 },
      'gpt-4o-mini': { input: 0.00000015, output: 0.0000006 },
      'gpt-3.5-turbo': { input: 0.0000005, output: 0.0000015 },
      'gpt-3.5-turbo-16k': { input: 0.000003, output: 0.000004 },
    };

    const modelPricing = pricing[this.config.model] || pricing['gpt-3.5-turbo'];

    // Estimate input tokens (rough approximation: 4 chars = 1 token)
    const inputText = messages.map(m => m.content).join(' ');
    const estimatedInputTokens = Math.ceil(inputText.length / 4);

    const outputTokens = maxTokens || this.config.maxTokens || 2048;

    const inputCost = (estimatedInputTokens / 1000) * modelPricing.input;
    const outputCost = (outputTokens / 1000) * modelPricing.output;

    return inputCost + outputCost;
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
    // Default rate limits for OpenAI (varies by tier)
    const limits = {
      requestsPerMinute: 3500,
      tokensPerMinute: 2000000,
      requestsRemaining: undefined,
      tokensRemaining: undefined,
      resetTime: undefined
    };

    // Try to get actual rate limits from headers (this would need to be implemented
    // based on the actual response headers from the last API call)
    // For now, return defaults

    return limits;
  }

  /**
   * Handle OpenAI-specific errors
   */
  private handleError(error: any): LLMProviderError {
    if (error.status === 401) {
      return this.createError(
        'Invalid OpenAI API key',
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

    if (error.status === 500) {
      return this.createError(
        'OpenAI server error',
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

    return this.createError(
      `OpenAI API error: ${error.message}`,
      'UNKNOWN_ERROR',
      'server_error',
      true
    );
  }

  /**
   * Get supported models for this provider
   */
  static getSupportedModels(): string[] {
    return [
      'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 'gpt-4o', 'gpt-4o-mini',
      'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'
    ];
  }

  /**
   * Get provider information
   */
  getProviderInfo(): { name: string; version: string; capabilities: string[] } {
    return {
      name: 'OpenAI',
      version: '1.0.0',
      capabilities: [
        'text-generation',
        'chat',
        'streaming',
        'function-calling',
        'json-mode'
      ]
    };
  }
}

export default OpenAIProvider;