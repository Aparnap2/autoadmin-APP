/**
 * FastAPI Client Service
 * Type-safe HTTP client for FastAPI backend communication
 * Provides enhanced error handling, retry logic, validation, and WebSocket support
 */

import { Platform } from 'react-native';
import { EnhancedAPIClient, APIEndpoints } from './retry-client';
import { API_CONFIG } from './api-config';
import { RequestValidators, ResponseValidators } from './api-validator';

// Types based on FastAPI backend models
export interface FastAPIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface AgentTaskRequest {
  type: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  assigned_to?: string;
  metadata?: Record<string, any>;
  input_data?: Record<string, any>;
}

export interface AgentTaskResponse {
  id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'delegated';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at: string;
  assigned_to?: string;
  delegated_to?: string;
  result?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export interface AgentStatus {
  id: string;
  type: string;
  name: string;
  status: 'idle' | 'busy' | 'offline' | 'error';
  capabilities: string[];
  current_tasks: string[];
  last_activity: string;
}

export interface ServerSentEvent {
  type: 'task_update' | 'agent_status' | 'system_notification';
  data: any;
  timestamp: string;
  id: string;
}

// Configuration
interface FastAPIConfig {
  baseURL: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
  enableRealtime: boolean;
  apiKey?: string;
}

class FastAPIClient {
  private config: FastAPIConfig;
  private enhancedClient: EnhancedAPIClient;
  private endpoints: APIEndpoints;
  private eventSource: EventSource | null = null;
  private sseListeners: Map<string, ((data: any) => void)[]> = new Map();
  private pollingInterval: NodeJS.Timeout | null = null;

  constructor(config: Partial<FastAPIConfig> = {}) {
    // Use dynamic base URL from API_CONFIG
    const baseURL = config.baseURL || API_CONFIG.baseURL;

    this.config = {
      baseURL,
      timeout: API_CONFIG.request.timeout,
      retryAttempts: API_CONFIG.request.retryAttempts,
      retryDelay: API_CONFIG.request.retryDelay,
      enableRealtime: false, // Changed from true to false to disable polling by default
      ...config
    };

    // Initialize enhanced client with proper configuration
    this.enhancedClient = new EnhancedAPIClient({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      apiKey: this.config.apiKey,
      defaultHeaders: {
        'Content-Type': 'application/json',
      },
      retryOptions: {
        maxAttempts: this.config.retryAttempts,
        baseDelay: this.config.retryDelay,
        maxDelay: 10000,
        backoffMultiplier: 2,
        retryableErrors: ['timeout', 'network error', 'connection refused'],
        retryableStatusCodes: [408, 429, 500, 502, 503, 504]
      },
      circuitBreakerConfig: {
        failureThreshold: 5,
        recoveryTimeout: 30000,
        monitoringPeriod: 60000,
        expectedRecoveryTime: 10000
      },
      enableMetrics: true,
      enableLogging: true
    });

    this.endpoints = new APIEndpoints(this.enhancedClient);
  }

  /**
   * Generic HTTP request with enhanced retry logic and validation
   */
  private async makeRequest<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<FastAPIResponse<T>> {
    try {
      // Use the enhanced client for the request
      const response = await this.enhancedClient.request<T>(endpoint, options);

      // Validate response structure
      const validation = ResponseValidators.validateAPIResponse(response);
      if (!validation.isValid) {
        throw new Error(`Invalid response format: ${validation.errors.join(', ')}`);
      }

      return response as FastAPIResponse<T>;
    } catch (error) {
      // Enhanced error handling
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Request failed with unknown error');
    }
  }

  /**
   * Enhanced request method with validation
   */
  private async makeValidatedRequest<T = any>(
    endpoint: string,
    requestData?: any,
    options: RequestInit = {}
  ): Promise<FastAPIResponse<T>> {
    // Validate request data if provided
    if (requestData) {
      const validation = RequestValidators.validateAgentTaskRequest(requestData);
      if (!validation.isValid) {
        throw new Error(`Invalid request data: ${validation.errors.join(', ')}`);
      }

      // Use sanitized data
      options = {
        ...options,
        body: JSON.stringify(validation.sanitized)
      };
    }

    return this.makeRequest<T>(endpoint, options);
  }

  
  /**
   * Agent operations
   */
  // Get all agents
  async getAgents(params?: {
    agent_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<FastAPIResponse<AgentStatus[]>> {
    const query = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.makeRequest(`/agents${query}`);
  }

  // Get specific agent
  async getAgent(agentId: string): Promise<FastAPIResponse<AgentStatus>> {
    return this.makeRequest(`/agents/${agentId}`);
  }

  // Create agent task
  async createAgentTask(agentId: string, request: AgentTaskRequest): Promise<FastAPIResponse<AgentTaskResponse>> {
    return this.makeValidatedRequest(`/agents/${agentId}/tasks`, request, {
      method: 'POST',
    });
  }

  // Get agent tasks
  async getAgentTasks(agentId: string, params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<FastAPIResponse<{ items: AgentTaskResponse[]; total: number; page: number; page_size: number }>> {
    const query = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.makeRequest(`/agents/${agentId}/tasks${query}`);
  }

  // Execute agent action
  async executeAgentAction(agentId: string, action: { action: string; parameters?: Record<string, any> }): Promise<FastAPIResponse<any>> {
    const validation = RequestValidators.validateAgentActionRequest(action);
    if (!validation.isValid) {
      throw new Error(`Invalid action data: ${validation.errors.join(', ')}`);
    }

    return this.makeRequest(`/agents/${agentId}/actions`, {
      method: 'POST',
      body: JSON.stringify(validation.sanitized)
    });
  }

  // Legacy method for backward compatibility
  async triggerAgentTask(request: AgentTaskRequest): Promise<FastAPIResponse<AgentTaskResponse>> {
    // Use swarm process instead
    return this.processWithSwarm({
      message: request.description,
      context: { ...request.metadata, task_type: request.type }
    });
  }

  // Get agent status
  async getAgentStatus(agentId: string): Promise<FastAPIResponse<AgentStatus>> {
    const response = await this.makeRequest(`/agents/${agentId}/status`);

    // Validate agent status response
    const validation = ResponseValidators.validateAgentStatusResponse(response.data);
    if (!validation.isValid) {
      throw new Error(`Invalid agent status response: ${validation.errors.join(', ')}`);
    }

    return response;
  }

  /**
   * Task operations
   */
  // Get all tasks
  async getTasks(params?: {
    status?: string;
    agent_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<FastAPIResponse<{ tasks: AgentTaskResponse[]; total: number }>> {
    const queryParams = new URLSearchParams(params as any).toString();
    const endpoint = queryParams ? `/tasks?${queryParams}` : '/tasks';
    return this.makeRequest(endpoint);
  }

  // Get specific task
  async getTask(taskId: string): Promise<FastAPIResponse<AgentTaskResponse>> {
    return this.makeRequest(`/tasks/${taskId}`);
  }

  // Create new task
  async createTask(request: AgentTaskRequest): Promise<FastAPIResponse<AgentTaskResponse>> {
    return this.makeRequest('/tasks', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Update task
  async updateTask(taskId: string, updates: Partial<AgentTaskRequest>): Promise<FastAPIResponse<AgentTaskResponse>> {
    return this.makeRequest(`/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  // Cancel task
  async cancelTask(taskId: string): Promise<FastAPIResponse<{ message: string }>> {
    return this.makeRequest(`/tasks/${taskId}/cancel`, {
      method: 'POST',
    });
  }

  /**
   * AI operations
   */
  // AI Chat completion
  async aiChat(messages: Array<{ role: string; content: string }>): Promise<FastAPIResponse<{ response: string }>> {
    return this.makeRequest('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ messages }),
    });
  }

  // AI Generate content
  async aiGenerate(prompt: string, options?: {
    max_tokens?: number;
    temperature?: number;
    model?: string;
  }): Promise<FastAPIResponse<{ content: string }>> {
    return this.makeRequest('/ai/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt, ...options }),
    });
  }

  // AI Generate embeddings
  async aiEmbeddings(text: string, options?: {
    model?: string;
  }): Promise<FastAPIResponse<{
    embedding: number[];
    dimensions: number;
    model: string;
    usage?: any;
  }>> {
    return this.makeRequest('/ai/embeddings', {
      method: 'POST',
      body: JSON.stringify({ text, ...options }),
    });
  }

  // Vector search
  async vectorSearch(queryEmbedding: number[], options?: {
    matchThreshold?: number;
    limit?: number;
    collection?: string;
  }): Promise<FastAPIResponse<{
    results: Array<{
      id: string;
      content: string;
      type: string;
      similarity: number;
      metadata?: Record<string, any>;
    }>;
    count: number;
  }>> {
    return this.makeRequest('/vector/search', {
      method: 'POST',
      body: JSON.stringify({
        queryEmbedding,
        ...options
      }),
    });
  }

  /**
   * Swarm operations
   */
  // Get swarm status
  async getSwarmStatus(): Promise<FastAPIResponse<any>> {
    return this.makeRequest('/agents/swarm/status');
  }

  // Process task with swarm
  async processWithSwarm(taskData: any): Promise<FastAPIResponse<any>> {
    const validation = RequestValidators.validateSwarmProcessRequest(taskData);
    if (!validation.isValid) {
      throw new Error(`Invalid swarm process request: ${validation.errors.join(', ')}`);
    }

    return this.makeRequest('/agents/swarm/process', {
      method: 'POST',
      body: JSON.stringify(validation.sanitized)
    });
  }

  // Chat with swarm agent
  async chatWithSwarmAgent(agentType: string, messageData: any): Promise<FastAPIResponse<any>> {
    // Validate agent type
    const validAgentTypes = ['ceo', 'strategy', 'devops'];
    if (!validAgentTypes.includes(agentType)) {
      throw new Error(`Invalid agent type: ${agentType}. Valid types: ${validAgentTypes.join(', ')}`);
    }

    // Validate message data
    if (!messageData.message || typeof messageData.message !== 'string') {
      throw new Error('Message is required and must be a string');
    }

    return this.makeRequest(`/agents/swarm/chat/${agentType}`, {
      method: 'POST',
      body: JSON.stringify({
        message: messageData.message,
        ...messageData
      })
    });
  }

  // Get swarm agents
  async getSwarmAgents(): Promise<FastAPIResponse<any>> {
    return this.makeRequest('/agents/swarm/agents');
  }

  /**
   * File operations
   */
  // Upload file
  async uploadFile(file: File, metadata?: Record<string, any>): Promise<FastAPIResponse<{ file_id: string; url: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    return this.makeRequest('/files/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
  }

  // Get file info
  async getFileInfo(fileId: string): Promise<FastAPIResponse<any>> {
    return this.makeRequest(`/files/${fileId}`);
  }

  /**
   * Server-Sent Events operations (replaces WebSocket)
   */
  async connectRealtimeUpdates(): Promise<void> {
    if (!this.config.enableRealtime) {
      console.warn('Real-time updates are disabled');
      return;
    }

    try {
      // Close existing connection if any
      this.disconnectRealtimeUpdates();

      // Try Server-Sent Events first
      if (typeof EventSource !== 'undefined') {
        await this.connectEventSource();
      } else {
        // Fallback to HTTP polling
        this.startHttpPolling();
      }
    } catch (error) {
      console.error('Failed to connect realtime updates, falling back to polling:', error);
      this.startHttpPolling();
    }
  }

  disconnectRealtimeUpdates(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  private async connectEventSource(): Promise<void> {
    return new Promise((resolve, reject) => {
      const eventURL = API_CONFIG.serverSentEvents.url;

      this.eventSource = new EventSource(eventURL);
      let reconnectAttempts = 0;
      const maxReconnectAttempts = API_CONFIG.serverSentEvents.reconnectAttempts;

      this.eventSource.onopen = () => {
        console.log('Server-Sent Events connected');
        reconnectAttempts = 0;
        resolve();
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerSentEvent(data);
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        if (reconnectAttempts === 0) {
          reject(error);
        }

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          const delay = API_CONFIG.serverSentEvents.reconnectDelay * Math.pow(2, reconnectAttempts - 1);
          setTimeout(() => {
            this.connectRealtimeUpdates().catch(console.error);
          }, delay);
        } else {
          // Fallback to polling after max reconnection attempts
          this.startHttpPolling();
        }
      };
    });
  }

  private startHttpPolling(): void {
    if (this.pollingInterval) {
      return; // Already polling
    }

    console.log('Starting HTTP polling for real-time updates');

    const pollInterval = API_CONFIG.serverSentEvents.heartbeatInterval;
    let lastTaskCount = 0;

    this.pollingInterval = setInterval(async () => {
      try {
        // Poll for task updates
        const tasksResponse = await this.getTasks({ limit: 50 });
        const currentTaskCount = tasksResponse.data?.tasks?.length || 0;

        if (currentTaskCount !== lastTaskCount) {
          lastTaskCount = currentTaskCount;
          // Trigger task update event
          this.notifyListeners('task_update', { tasks: tasksResponse.data?.tasks });
        }

        // Poll for agent status
        const agentsResponse = await this.getAgents();
        this.notifyListeners('agent_status', { agents: agentsResponse.data });

      } catch (error) {
        console.error('HTTP polling error:', error);
      }
    }, pollInterval);
  }

  // Server-Sent Events event listeners
  addRealtimeListener(eventType: string, callback: (data: any) => void): void {
    if (!this.sseListeners.has(eventType)) {
      this.sseListeners.set(eventType, []);
    }
    this.sseListeners.get(eventType)!.push(callback);
  }

  removeRealtimeListener(eventType: string, callback: (data: any) => void): void {
    const listeners = this.sseListeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private handleServerSentEvent(event: ServerSentEvent): void {
    const listeners = this.sseListeners.get(event.type);
    if (listeners) {
      listeners.forEach(callback => callback(event.data));
    }
  }

  private notifyListeners(eventType: string, data: any): void {
    const listeners = this.sseListeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  // Legacy WebSocket methods for backward compatibility
  connectWebSocket(): Promise<void> {
    console.warn('connectWebSocket() is deprecated, use connectRealtimeUpdates() instead');
    return this.connectRealtimeUpdates();
  }

  disconnectWebSocket(): void {
    console.warn('disconnectWebSocket() is deprecated, use disconnectRealtimeUpdates() instead');
    this.disconnectRealtimeUpdates();
  }

  addWebSocketListener(eventType: string, callback: (data: any) => void): void {
    console.warn('addWebSocketListener() is deprecated, use addRealtimeListener() instead');
    this.addRealtimeListener(eventType, callback);
  }

  removeWebSocketListener(eventType: string, callback: (data: any) => void): void {
    console.warn('removeWebSocketListener() is deprecated, use removeRealtimeListener() instead');
    this.removeRealtimeListener(eventType, callback);
  }

  /**
   * Utility methods
   */
  isConnected(): boolean {
    // Check if either EventSource is connected or polling is active
    return (this.eventSource?.readyState === EventSource.OPEN) ||
           (this.pollingInterval !== null);
  }

  getBaseURL(): string {
    return this.config.baseURL;
  }

  updateConfig(newConfig: Partial<FastAPIConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Enhanced utility methods using enhanced client
   */
  getMetrics() {
    return this.enhancedClient.getMetrics();
  }

  getCircuitBreakerStatus() {
    return this.enhancedClient.getCircuitBreakerStatus();
  }

  async healthCheck() {
    return this.enhancedClient.healthCheck();
  }

  resetCircuitBreaker() {
    this.enhancedClient.resetCircuitBreaker();
  }

  /**
   * Batch operations for improved performance
   */
  async batchRequests<T>(requests: Array<{ endpoint: string; options?: RequestInit }>): Promise<T[]> {
    const promises = requests.map(req =>
      this.enhancedClient.request<T>(req.endpoint, req.options)
    );
    return Promise.all(promises);
  }

  /**
   * Stream processing for large responses
   */
  async *streamResponses<T>(endpoint: string, options: RequestInit = {}): AsyncGenerator<T> {
    const response = await fetch(`${this.config.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` }),
        ...options.headers
      }
    });

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line);
              yield data;
            } catch (error) {
              console.error('Error parsing streamed data:', error);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
    * HubSpot operations
    */
  // Get HubSpot contacts
  async getHubSpotContacts(limit: number = 100): Promise<FastAPIResponse<any[]>> {
    return this.makeRequest(`/hubspot/contacts?limit=${limit}`);
  }

  // Get HubSpot deals
  async getHubSpotDeals(limit: number = 100): Promise<FastAPIResponse<any[]>> {
    return this.makeRequest(`/hubspot/deals?limit=${limit}`);
  }

  // Get HubSpot companies
  async getHubSpotCompanies(limit: number = 100): Promise<FastAPIResponse<any[]>> {
    return this.makeRequest(`/hubspot/companies?limit=${limit}`);
  }

  // Get HubSpot integration status
  async getHubSpotStatus(): Promise<FastAPIResponse<any>> {
    return this.makeRequest('/hubspot/status');
  }

  // Sync HubSpot data manually
  async syncHubSpotData(): Promise<FastAPIResponse<any>> {
    return this.makeRequest('/hubspot/sync', {
      method: 'POST'
    });
  }

  /**
    * Connection monitoring and diagnostics
    */
  async runDiagnostics(): Promise<{
    connectivity: boolean;
    latency: number;
    circuitBreaker: any;
    metrics: any;
    realtimeConnection: boolean;
    errors: string[];
  }> {
    const errors: string[] = [];

    // Test basic connectivity
    const connectivityTest = await this.enhancedClient.healthCheck();
    const connectivity = connectivityTest.healthy;

    if (!connectivity) {
      errors.push(`Connectivity failed: ${connectivityTest.error || 'Unknown error'}`);
    }

    // Get metrics
    const metrics = this.getMetrics();
    const circuitBreaker = this.getCircuitBreakerStatus();

    // Test real-time connection (SSE or polling)
    const realtimeConnection = this.isConnected();

    return {
      connectivity,
      latency: connectivityTest.latency,
      circuitBreaker,
      metrics,
      realtimeConnection,
      errors
    };
  }
}

// Singleton instance
let fastapiClient: FastAPIClient | null = null;

export function getFastAPIClient(config?: Partial<FastAPIConfig>): FastAPIClient {
  if (!fastapiClient) {
    fastapiClient = new FastAPIClient(config);
  }
  return fastapiClient;
}

export default FastAPIClient;