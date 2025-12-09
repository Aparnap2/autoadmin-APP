/**
 * Groq Provider Implementation
 * Uses OpenAI SDK with Groq's base URL
 */

import { ChatOpenAI } from '@langchain/openai';
import { BaseMessage } from '@langchain/core/messages';
import {
  BaseLLMProvider,
  LLMProviderConfig,
  LLMResponse,
  StreamingLLMResponse,
  LLMProviderError
} from './base-provider';

export class GroqProvider extends BaseLLMProvider {
  private client: ChatOpenAI;

  constructor(config: LLMProviderConfig) {
    super(config);
    this.client = new ChatOpenAI({
      modelName: config.model,
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens,
      openAIApiKey: config.apiKey,
      configuration: {
        baseURL: config.baseUrl || 'https://api.groq.com/openai/v1',
      },
      timeout: config.timeout ?? 60000,
      maxRetries: config.retryAttempts ?? 3,
      headers: {
        ...config.customHeaders,
        'User-Agent': 'AutoAdmin/1.0'
      },
    });
  }

  /**
   * Get default configuration for Groq provider
   */
  protected getDefaultConfig(): Partial<LLMProviderConfig> {
    return {
      temperature: 0.7,
      maxTokens: 2048,
      timeout: 60000,
      retryAttempts: 3,
      model: 'llama3-8b-8192',
      baseUrl: 'https://api.groq.com/openai/v1'
    };
  }

  /**
   * Validate Groq-specific configuration
   */
  protected validateConfig(config: LLMProviderConfig): void {
    if (!config.apiKey) {
      throw this.createError(
        'Groq API key is required',
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

    const validModels = [
      'llama3-70b-8192',
      'llama3-8b-8192',
      'llama2-70b-4096',
      'mixtral-8x7b-32768',
      'gemma-7b-it'
    ];

    if (!validModels.includes(config.model)) {
      throw this.createError(
        `Invalid model: ${config.model}. Valid models: ${validModels.join(', ')}`,
        'INVALID_MODEL',
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
            provider: 'groq'
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
      console.error('Groq health check failed:', error);
      return false;
    }
  }

  /**
   * Format messages for Groq API (uses OpenAI format)
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
   * Parse Groq response to standard format
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
        provider: 'groq',
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
    // Groq pricing (as of 2024, approximate)
    const pricing: Record<string, { input: number; output: number }> = {
      'llama3-70b-8192': { input: 0.00000059, output: 0.00000079 },
      'llama3-8b-8192': { input: 0.00000005, output: 0.00000010 },
      'llama2-70b-4096': { input: 0.00000065, output: 0.00000087 },
      'mixtral-8x7b-32768': { input: 0.00000027, output: 0.00000027 },
      'gemma-7b-it': { input: 0.00000010, output: 0.00000010 }
    };

    const modelPricing = pricing[this.config.model] || pricing['llama3-8b-8192'];

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
    // Default rate limits for Groq
    const limits = {
      requestsPerMinute: 30,
      tokensPerMinute: 6000,
      requestsRemaining: undefined,
      tokensRemaining: undefined,
      resetTime: undefined
    };

    return limits;
  }

  /**
   * Handle Groq-specific errors
   */
  private handleError(error: any): LLMProviderError {
    if (error.status === 401) {
      return this.createError(
        'Invalid Groq API key',
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
        'Groq server error',
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
      `Groq API error: ${error.message}`,
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
      'llama3-70b-8192',
      'llama3-8b-8192',
      'llama2-70b-4096',
      'mixtral-8x7b-32768',
      'gemma-7b-it'
    ];
  }

  /**
   * Get provider information
   */
  getProviderInfo(): { name: string; version: string; capabilities: string[] } {
    return {
      name: 'Groq',
      version: '1.0.0',
      capabilities: [
        'text-generation',
        'chat',
        'streaming',
        'fast-inference'
      ]
    };
  }
}

export default GroqProvider;