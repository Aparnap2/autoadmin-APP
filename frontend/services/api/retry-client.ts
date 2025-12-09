/**
 * Enhanced API Client with Retry Logic and Connection Management
 * Provides robust HTTP client with exponential backoff, circuit breaking, and health monitoring
 */

import { API_CONFIG } from './api-config';

// Types
export interface RetryOptions {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  retryableErrors: string[];
  retryableStatusCodes: number[];
}

export interface CircuitBreakerConfig {
  failureThreshold: number;
  recoveryTimeout: number;
  monitoringPeriod: number;
  expectedRecoveryTime: number;
}

export interface RequestConfig extends RequestInit {
  timeout?: number;
  retries?: Partial<RetryOptions>;
  circuitBreaker?: boolean;
  validateResponse?: boolean;
  enableCache?: boolean;
}

export interface ClientConfig {
  baseURL: string;
  timeout: number;
  apiKey?: string;
  defaultHeaders?: Record<string, string>;
  retryOptions?: Partial<RetryOptions>;
  circuitBreakerConfig?: CircuitBreakerConfig;
  enableMetrics: boolean;
  enableLogging: boolean;
}

// Circuit breaker states
enum CircuitBreakerState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN'
}

// Request metrics
export interface RequestMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  lastRequestTime: number;
  consecutiveFailures: number;
}

// Circuit breaker implementation
class CircuitBreaker {
  private state: CircuitBreakerState = CircuitBreakerState.CLOSED;
  private failureCount = 0;
  private lastFailureTime = 0;
  private nextAttempt = 0;

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(request: () => Promise<T>): Promise<T> {
    if (this.state === CircuitBreakerState.OPEN) {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is OPEN');
      } else {
        this.state = CircuitBreakerState.HALF_OPEN;
      }
    }

    try {
      const result = await request();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = CircuitBreakerState.CLOSED;
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitBreakerState.OPEN;
      this.nextAttempt = Date.now() + this.config.recoveryTimeout;
    }
  }

  getState(): CircuitBreakerState {
    return this.state;
  }

  getFailureCount(): number {
    return this.failureCount;
  }
}

// Enhanced API client
export class EnhancedAPIClient {
  private config: ClientConfig;
  private circuitBreaker: CircuitBreaker;
  private metrics: RequestMetrics = {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    averageResponseTime: 0,
    lastRequestTime: 0,
    consecutiveFailures: 0
  };

  constructor(config: Partial<ClientConfig> = {}) {
    this.config = {
      baseURL: API_CONFIG.baseURL,
      timeout: API_CONFIG.request.timeout,
      defaultHeaders: {
        'Content-Type': 'application/json',
      },
      enableMetrics: true,
      enableLogging: true,
      ...config
    };

    const circuitBreakerConfig = {
      failureThreshold: 5,
      recoveryTimeout: 30000,
      monitoringPeriod: 60000,
      expectedRecoveryTime: 10000,
      ...config.circuitBreakerConfig
    };

    this.circuitBreaker = new CircuitBreaker(circuitBreakerConfig);
  }

  /**
   * Make HTTP request with retry logic and circuit breaker
   */
  async request<T = any>(endpoint: string, options: RequestConfig = {}): Promise<T> {
    const startTime = Date.now();
    this.metrics.totalRequests++;

    const retryOptions = this.mergeRetryOptions(options.retries);
    const useCircuitBreaker = options.circuitBreaker ?? true;

    try {
      const response = useCircuitBreaker
        ? await this.circuitBreaker.execute(() => this.makeRequestWithRetry<T>(endpoint, options, retryOptions))
        : await this.makeRequestWithRetry<T>(endpoint, options, retryOptions);

      const responseTime = Date.now() - startTime;
      this.updateMetrics(true, responseTime);

      if (this.config.enableLogging) {
        console.log(`API Request Success: ${endpoint} (${responseTime}ms)`);
      }

      return response;
    } catch (error) {
      const responseTime = Date.now() - startTime;
      this.updateMetrics(false, responseTime);

      if (this.config.enableLogging) {
        console.error(`API Request Failed: ${endpoint} (${responseTime}ms)`, error);
      }

      throw error;
    }
  }

  /**
   * Make HTTP request with retry logic
   */
  private async makeRequestWithRetry<T>(
    endpoint: string,
    options: RequestConfig,
    retryOptions: Required<RetryOptions>
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= retryOptions.maxAttempts; attempt++) {
      try {
        return await this.makeRequest<T>(endpoint, options);
      } catch (error) {
        lastError = error as Error;

        // Check if we should retry
        if (!this.shouldRetry(error, attempt, retryOptions)) {
          throw error;
        }

        if (attempt < retryOptions.maxAttempts) {
          const delay = this.calculateRetryDelay(attempt, retryOptions);
          if (this.config.enableLogging) {
            console.warn(`Request failed (attempt ${attempt}/${retryOptions.maxAttempts}), retrying in ${delay}ms:`, error);
          }
          await this.delay(delay);
        }
      }
    }

    throw lastError || new Error('Request failed after all retry attempts');
  }

  /**
   * Make actual HTTP request
   */
  private async makeRequest<T>(endpoint: string, options: RequestConfig): Promise<T> {
    const url = `${this.config.baseURL}${endpoint}`;
    const timeout = options.timeout ?? this.config.timeout;

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const headers = {
        ...this.config.defaultHeaders,
        ...(this.config.apiKey && { Authorization: `Bearer ${this.config.apiKey}` }),
        ...options.headers
      };

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Validate response if required
      if (options.validateResponse !== false) {
        this.validateResponse(data);
      }

      return data;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Check if request should be retried
   */
  private shouldRetry(error: Error, attempt: number, retryOptions: Required<RetryOptions>): boolean {
    // Don't retry if we've reached max attempts
    if (attempt >= retryOptions.maxAttempts) {
      return false;
    }

    // Check for timeout errors
    if (error.name === 'AbortError') {
      return true;
    }

    // Check for network errors
    if (error.message.includes('fetch') || error.message.includes('network')) {
      return true;
    }

    // Check for specific error messages
    for (const retryableError of retryOptions.retryableErrors) {
      if (error.message.includes(retryableError)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(attempt: number, retryOptions: Required<RetryOptions>): number {
    const delay = retryOptions.baseDelay * Math.pow(retryOptions.backoffMultiplier, attempt - 1);
    const jitter = delay * 0.1 * Math.random(); // Add 10% jitter
    return Math.min(delay + jitter, retryOptions.maxDelay);
  }

  /**
   * Validate API response structure
   */
  private validateResponse(response: any): void {
    if (!response || typeof response !== 'object') {
      throw new Error('Invalid response: Response must be an object');
    }

    if ('success' in response && typeof response.success !== 'boolean') {
      throw new Error('Invalid response: success field must be boolean');
    }

    if (response.success === false && !response.error) {
      throw new Error('Invalid response: failed response must include error message');
    }
  }

  /**
   * Merge retry options with defaults
   */
  private mergeRetryOptions(options?: Partial<RetryOptions>): Required<RetryOptions> {
    const defaults = {
      maxAttempts: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      backoffMultiplier: 2,
      retryableErrors: ['timeout', 'network error', 'connection refused'],
      retryableStatusCodes: [408, 429, 500, 502, 503, 504]
    };

    const merged = { ...defaults, ...API_CONFIG.request, ...options };
    return merged as Required<RetryOptions>;
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Update request metrics
   */
  private updateMetrics(success: boolean, responseTime: number): void {
    if (!this.config.enableMetrics) {
      return;
    }

    this.metrics.lastRequestTime = Date.now();

    if (success) {
      this.metrics.successfulRequests++;
      this.metrics.consecutiveFailures = 0;
    } else {
      this.metrics.failedRequests++;
      this.metrics.consecutiveFailures++;
    }

    // Update average response time
    const totalRequests = this.metrics.totalRequests;
    const currentAvg = this.metrics.averageResponseTime;
    this.metrics.averageResponseTime = ((currentAvg * (totalRequests - 1)) + responseTime) / totalRequests;
  }

  /**
   * Get request metrics
   */
  getMetrics(): RequestMetrics {
    return { ...this.metrics };
  }

  /**
   * Get circuit breaker status
   */
  getCircuitBreakerStatus(): { state: CircuitBreakerState; failures: number } {
    return {
      state: this.circuitBreaker.getState(),
      failures: this.circuitBreaker.getFailureCount()
    };
  }

  /**
   * Perform health check
   */
  async healthCheck(): Promise<{ healthy: boolean; latency: number; error?: string }> {
    const startTime = Date.now();
    try {
      await this.request(API_CONFIG.endpoints.health, {
        timeout: 5000,
        retries: { maxAttempts: 1 },
        circuitBreaker: false,
        validateResponse: false
      });

      const latency = Date.now() - startTime;
      return { healthy: true, latency };
    } catch (error) {
      const latency = Date.now() - startTime;
      return {
        healthy: false,
        latency,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Reset circuit breaker
   */
  resetCircuitBreaker(): void {
    this.circuitBreaker = new CircuitBreaker(this.config.circuitBreakerConfig || {
      failureThreshold: 5,
      recoveryTimeout: 30000,
      monitoringPeriod: 60000,
      expectedRecoveryTime: 10000
    });
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<ClientConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
}

// Convenience method wrappers
export class APIEndpoints {
  constructor(private client: EnhancedAPIClient) {}

  // Agent endpoints
  async getAgents(params?: Record<string, any>) {
    const query = params ? `?${new URLSearchParams(params).toString()}` : '';
    return this.client.request(`/agents${query}`);
  }

  async getAgent(agentId: string) {
    return this.client.request(`/agents/${agentId}`);
  }

  async getAgentStatus(agentId: string) {
    return this.client.request(`/agents/${agentId}/status`);
  }

  async createAgentTask(agentId: string, taskData: any) {
    return this.client.request(`/agents/${agentId}/tasks`, {
      method: 'POST',
      body: JSON.stringify(taskData)
    });
  }

  async getAgentTasks(agentId: string, params?: Record<string, any>) {
    const query = params ? `?${new URLSearchParams(params).toString()}` : '';
    return this.client.request(`/agents/${agentId}/tasks${query}`);
  }

  async executeAgentAction(agentId: string, actionData: any) {
    return this.client.request(`/agents/${agentId}/actions`, {
      method: 'POST',
      body: JSON.stringify(actionData)
    });
  }

  // Swarm endpoints
  async getSwarmStatus() {
    return this.client.request('/agents/swarm/status');
  }

  async processWithSwarm(taskData: any) {
    return this.client.request('/agents/swarm/process', {
      method: 'POST',
      body: JSON.stringify(taskData)
    });
  }

  async chatWithSwarmAgent(agentType: string, messageData: any) {
    return this.client.request(`/agents/swarm/chat/${agentType}`, {
      method: 'POST',
      body: JSON.stringify(messageData)
    });
  }

  async getSwarmAgents() {
    return this.client.request('/agents/swarm/agents');
  }

  // Health endpoint
  async health() {
    return this.client.request('/health');
  }
}

// Factory function
export function createAPIClient(config?: Partial<ClientConfig>): {
  client: EnhancedAPIClient;
  endpoints: APIEndpoints;
} {
  const client = new EnhancedAPIClient(config);
  const endpoints = new APIEndpoints(client);

  return { client, endpoints };
}

// Default client instance
export const { client: defaultAPIClient, endpoints: apiEndpoints } = createAPIClient();

export default EnhancedAPIClient;