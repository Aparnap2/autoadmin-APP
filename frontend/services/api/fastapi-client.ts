/**
 * FastAPI Client Service
 * Type-safe HTTP client for FastAPI backend communication
 * Provides error handling, retry logic, and WebSocket support
 */

import { Platform } from 'react-native';

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

export interface WebSocketMessage {
  type: 'task_update' | 'agent_status' | 'system_notification';
  data: any;
  timestamp: string;
}

// Configuration
interface FastAPIConfig {
  baseURL: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
  enableWebSocket: boolean;
  apiKey?: string;
}

class FastAPIClient {
  private config: FastAPIConfig;
  private websocket: WebSocket | null = null;
  private wsListeners: Map<string, ((data: any) => void)[]> = new Map();

  constructor(config: Partial<FastAPIConfig> = {}) {
    const baseURL = config.baseURL ||
      (Platform.OS === 'web'
        ? 'http://localhost:8000'
        : 'http://192.168.1.100:8000'); // Update with your server IP

    this.config = {
      baseURL,
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      enableWebSocket: true,
      ...config
    };
  }

  /**
   * Generic HTTP request with retry logic
   */
  private async makeRequest<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<FastAPIResponse<T>> {
    const url = `${this.config.baseURL}/api/v1${endpoint}`;

    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` }),
    };

    // Create timeout abort controller with React Native compatibility
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= this.config.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: { ...defaultHeaders, ...options.headers },
          signal: controller.signal,
        });

        clearTimeout(timeoutId); // Clear timeout if request succeeds

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        return data;
      } catch (error) {
        lastError = error as Error;

        if (attempt < this.config.retryAttempts) {
          console.warn(`Request failed (attempt ${attempt}/${this.config.retryAttempts}):`, error);
          await new Promise(resolve => setTimeout(resolve, this.config.retryDelay * attempt));
        }
      }
    }

    // Clear timeout if all attempts failed
    clearTimeout(timeoutId);
    throw lastError || new Error('Request failed after all retry attempts');
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<FastAPIResponse<{ status: string }>> {
    return this.makeRequest('/health');
  }

  /**
   * Agent operations
   */
  // Get all agents
  async getAgents(): Promise<FastAPIResponse<AgentStatus[]>> {
    return this.makeRequest('/agents');
  }

  // Get specific agent
  async getAgent(agentId: string): Promise<FastAPIResponse<AgentStatus>> {
    return this.makeRequest(`/agents/${agentId}`);
  }

  // Trigger agent task
  async triggerAgentTask(request: AgentTaskRequest): Promise<FastAPIResponse<AgentTaskResponse>> {
    return this.makeRequest('/agents/trigger', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Get agent status
  async getAgentStatus(agentId: string): Promise<FastAPIResponse<AgentStatus>> {
    return this.makeRequest(`/agents/${agentId}/status`);
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
   * WebSocket operations
   */
  connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.config.enableWebSocket) {
        reject(new Error('WebSocket is disabled'));
        return;
      }

      try {
        const wsProtocol = this.config.baseURL.startsWith('https') ? 'wss' : 'ws';
        const wsURL = this.config.baseURL.replace(/^https?/, wsProtocol) + '/ws';

        this.websocket = new WebSocket(wsURL);

        this.websocket.onopen = () => {
          console.log('WebSocket connected');
          resolve();
        };

        this.websocket.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.websocket.onclose = () => {
          console.log('WebSocket disconnected');
          this.websocket = null;
        };

        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnectWebSocket(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  // WebSocket event listeners
  addWebSocketListener(eventType: string, callback: (data: any) => void): void {
    if (!this.wsListeners.has(eventType)) {
      this.wsListeners.set(eventType, []);
    }
    this.wsListeners.get(eventType)!.push(callback);
  }

  removeWebSocketListener(eventType: string, callback: (data: any) => void): void {
    const listeners = this.wsListeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    const listeners = this.wsListeners.get(message.type);
    if (listeners) {
      listeners.forEach(callback => callback(message.data));
    }
  }

  /**
   * Utility methods
   */
  isConnected(): boolean {
    return this.websocket?.readyState === WebSocket.OPEN;
  }

  getBaseURL(): string {
    return this.config.baseURL;
  }

  updateConfig(newConfig: Partial<FastAPIConfig>): void {
    this.config = { ...this.config, ...newConfig };
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