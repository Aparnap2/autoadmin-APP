/**
 * Anthropic Claude Provider Implementation
 */

import { BaseMessage, HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';
import {
  BaseLLMProvider,
  LLMProviderConfig,
  LLMResponse,
  StreamingLLMResponse,
  LLMProviderError
} from './base-provider';

interface AnthropicMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AnthropicResponse {
  content: Array<{ type: string; text: string }>;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
  model: string;
  stop_reason: string;
  stop_sequence?: string;
  id: string;
  type: 'message';
  role: 'assistant';
}

export class AnthropicProvider extends BaseLLMProvider {
  private baseUrl: string;

  constructor(config: LLMProviderConfig) {
    super(config);
    this.baseUrl = config.baseUrl || 'https://api.anthropic.com';
  }

  /**
   * Get default configuration for Anthropic provider
   */
  protected getDefaultConfig(): Partial<LLMProviderConfig> {
    return {
      temperature: 0.7,
      maxTokens: 2048,
      timeout: 60000,
      retryAttempts: 3,
      model: 'claude-3-sonnet-20240229'
    };
  }

  /**
   * Validate Anthropic-specific configuration
   */
  protected validateConfig(config: LLMProviderConfig): void {
    if (!config.apiKey) {
      throw this.createError(
        'Anthropic API key is required',
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
      'claude-3-opus-20240229',
      'claude-3-sonnet-20240229',
      'claude-3-haiku-20240307',
      'claude-2.1',
      'claude-2.0',
      'claude-instant-1.2'
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
      const { system, anthropicMessages } = this.formatMessages(messages);

      const response = await this.makeRequest('/v1/messages', {
        model: this.config.model,
        max_tokens: this.config.maxTokens || 2048,
        temperature: this.config.temperature,
        messages: anthropicMessages,
        ...(system && { system })
      });

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
      const { system, anthropicMessages } = this.formatMessages(messages);

      const response = await this.makeStreamRequest('/v1/messages', {
        model: this.config.model,
        max_tokens: this.config.maxTokens || 2048,
        temperature: this.config.temperature,
        messages: anthropicMessages,
        ...(system && { system })
      });

      let fullContent = '';
      let finalResponse: LLMResponse | null = null;

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Stream not available');
      }

      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
                fullContent += parsed.delta.text;

                onChunk({
                  content: fullContent,
                  done: false,
                  metadata: {
                    model: this.config.model,
                    provider: 'anthropic'
                  }
                });
              }

              if (parsed.type === 'message_stop') {
                // Create final response
                finalResponse = {
                  content: fullContent,
                  model: this.config.model,
                  usage: {
                    promptTokens: 0, // Would need to track from usage events
                    completionTokens: 0,
                    totalTokens: 0
                  },
                  metadata: {
                    provider: 'anthropic',
                    stopReason: parsed.stop_reason
                  }
                };

                onChunk({
                  content: finalResponse.content,
                  done: true,
                  usage: finalResponse.usage,
                  metadata: finalResponse.metadata
                });
              }
            } catch (e) {
              // Ignore parsing errors for malformed chunks
            }
          }
        }
      }

      return finalResponse || {
        content: fullContent,
        model: this.config.model,
        usage: {
          promptTokens: 0,
          completionTokens: 0,
          totalTokens: 0
        }
      };
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Check if the provider is available and properly configured
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.makeRequest('/v1/messages', {
        model: this.config.model,
        max_tokens: 10,
        messages: [{ role: 'user', content: 'Hello' }]
      });
      return !!response.content;
    } catch (error) {
      console.error('Anthropic health check failed:', error);
      return false;
    }
  }

  /**
   * Format messages for Anthropic API
   */
  protected formatMessages(messages: BaseMessage[]): { system?: string; anthropicMessages: AnthropicMessage[] } {
    const anthropicMessages: AnthropicMessage[] = [];
    let system: string | undefined;

    for (const message of messages) {
      if (message.getType() === 'system') {
        system = message.content as string;
      } else if (message.getType() === 'human') {
        anthropicMessages.push({
          role: 'user',
          content: message.content as string
        });
      } else if (message.getType() === 'ai') {
        anthropicMessages.push({
          role: 'assistant',
          content: message.content as string
        });
      }
    }

    return { system, anthropicMessages };
  }

  /**
   * Parse Anthropic response to standard format
   */
  protected parseResponse(response: AnthropicResponse): LLMResponse {
    const content = response.content
      .filter(item => item.type === 'text')
      .map(item => item.text)
      .join('');

    return {
      content,
      usage: {
        promptTokens: response.usage.input_tokens,
        completionTokens: response.usage.output_tokens,
        totalTokens: response.usage.input_tokens + response.usage.output_tokens
      },
      model: response.model,
      finishReason: response.stop_reason,
      metadata: {
        provider: 'anthropic',
        responseId: response.id,
        type: response.type,
        stopSequence: response.stop_sequence
      }
    };
  }

  /**
   * Make HTTP request to Anthropic API
   */
  private async makeRequest(endpoint: string, data: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01',
        ...this.config.customHeaders
      },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(this.config.timeout || 60000)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`HTTP ${response.status}: ${errorData.error?.message || response.statusText}`);
    }

    return response.json();
  }

  /**
   * Make streaming request to Anthropic API
   */
  private async makeStreamRequest(endpoint: string, data: any): Promise<Response> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01',
        ...this.config.customHeaders
      },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(this.config.timeout || 60000)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`HTTP ${response.status}: ${errorData.error?.message || response.statusText}`);
    }

    return response;
  }

  /**
   * Calculate estimated cost for the request
   */
  estimateCost(messages: BaseMessage[], maxTokens?: number): number {
    // Anthropic pricing (as of 2024, approximate)
    const pricing: Record<string, { input: number; output: number }> = {
      'claude-3-opus-20240229': { input: 0.000015, output: 0.000075 },
      'claude-3-sonnet-20240229': { input: 0.000003, output: 0.000015 },
      'claude-3-haiku-20240307': { input: 0.00000025, output: 0.00000125 },
      'claude-2.1': { input: 0.000008, output: 0.000024 },
      'claude-2.0': { input: 0.000008, output: 0.000024 },
      'claude-instant-1.2': { input: 0.0000008, output: 0.0000024 }
    };

    const modelPricing = pricing[this.config.model] || pricing['claude-3-sonnet-20240229'];

    // Estimate input tokens
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
    // Default rate limits for Anthropic
    return {
      requestsPerMinute: 1000,
      tokensPerMinute: 40000
    };
  }

  /**
   * Handle Anthropic-specific errors
   */
  private handleError(error: any): LLMProviderError {
    if (error.message.includes('401') || error.message.includes('authentication')) {
      return this.createError(
        'Invalid Anthropic API key',
        'INVALID_API_KEY',
        'authentication',
        false
      );
    }

    if (error.message.includes('429') || error.message.includes('rate limit')) {
      return this.createError(
        'Rate limit exceeded',
        'RATE_LIMIT_EXCEEDED',
        'rate_limit',
        true
      );
    }

    if (error.message.includes('400')) {
      return this.createError(
        `Bad request: ${error.message}`,
        'BAD_REQUEST',
        'invalid_request',
        false
      );
    }

    if (error.message.includes('500')) {
      return this.createError(
        'Anthropic server error',
        'SERVER_ERROR',
        'server_error',
        true
      );
    }

    if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
      return this.createError(
        'Request timeout',
        'TIMEOUT',
        'timeout',
        true
      );
    }

    return this.createError(
      `Anthropic API error: ${error.message}`,
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
      'claude-3-opus-20240229',
      'claude-3-sonnet-20240229',
      'claude-3-haiku-20240307',
      'claude-2.1',
      'claude-2.0',
      'claude-instant-1.2'
    ];
  }
}

export default AnthropicProvider;