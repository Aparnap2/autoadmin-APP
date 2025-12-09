/**
 * Simple API Client Service
 * Replaces complex LangGraph agent system with simple HTTP API calls
 * Handles all communication with FastAPI backend
 */

import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Types for API communication
export interface ClientMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: Date;
  agent?: string;
  metadata?: Record<string, any>;
}

export interface ClientTask {
  id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  result?: any;
  error?: string;
  agent?: string;
  created_at: Date;
  updated_at: Date;
}

export interface ClientAgent {
  id: string;
  name: string;
  type: 'ceo' | 'strategy' | 'devops';
  status: 'idle' | 'busy' | 'offline';
  capabilities: string[];
  description: string;
}

export interface ClientConfig {
  baseURL: string;
  timeout: number;
  retryAttempts: number;
  enableRealtime: boolean;
  apiKey?: string;
}

class SimpleAPIClient {
  private config: ClientConfig;
  private eventSource: EventSource | null = null;
  private messageListeners: ((message: ClientMessage) => void)[] = [];
  private taskListeners: ((task: ClientTask) => void)[] = [];
  private agentListeners: ((agents: ClientAgent[]) => void)[] = [];

  constructor(config: Partial<ClientConfig> = {}) {
    const baseURL = config.baseURL ||
      (Platform.OS === 'web'
        ? 'http://localhost:8000'
        : 'http://10.0.2.2:8000'); // Use Android emulator address by default

    this.config = {
      baseURL,
      timeout: 30000,
      retryAttempts: 3,
      enableRealtime: false, // Changed from true to false to disable polling by default
      ...config
    };
  }

  /**
   * Initialize the client
   */
  async initialize(): Promise<void> {
    try {
      // Load stored configuration
      const storedConfig = await AsyncStorage.getItem('api_client_config');
      if (storedConfig) {
        this.config = { ...this.config, ...JSON.parse(storedConfig) };
      }

      console.log('Simple API Client initialized successfully');
    } catch (error) {
      console.error('Error initializing API client:', error);
      throw error;
    }
  }

  /**
   * Send a user message to the backend
   */
  async sendMessage(content: string, agentHint?: string): Promise<ClientMessage> {
    try {
      const messageData = {
        content,
        agent_hint: agentHint,
        timestamp: new Date().toISOString()
      };

      const response = await this.makeRequest('/api/v1/chat', {
        method: 'POST',
        body: JSON.stringify(messageData)
      });

      if (!response.success) {
        throw new Error(response.error || 'Failed to send message');
      }

      const message: ClientMessage = {
        id: response.data.id,
        content: response.data.content,
        type: response.data.type,
        timestamp: new Date(response.data.timestamp),
        agent: response.data.agent,
        metadata: response.data.metadata
      };

      // Store message locally
      await this.storeMessage(message);

      // Notify listeners
      this.notifyMessageListeners(message);

      return message;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * Get conversation history
   */
  async getMessages(limit: number = 50): Promise<ClientMessage[]> {
    try {
      const response = await this.makeRequest(`/api/v1/chat/history?limit=${limit}`);

      if (!response.success) {
        throw new Error(response.error || 'Failed to get messages');
      }

      return response.data.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        type: msg.type,
        timestamp: new Date(msg.timestamp),
        agent: msg.agent,
        metadata: msg.metadata
      }));
    } catch (error) {
      console.error('Error getting messages:', error);
      // Fallback to local storage
      return this.getLocalMessages(limit);
    }
  }

  /**
   * Create a new task
   */
  async createTask(type: string, description: string, agent?: string): Promise<ClientTask> {
    try {
      const taskData = {
        type,
        description,
        agent,
        priority: 'medium' as const
      };

      const response = await this.makeRequest('/api/v1/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData)
      });

      if (!response.success) {
        throw new Error(response.error || 'Failed to create task');
      }

      const task: ClientTask = {
        id: response.data.id,
        type: response.data.type,
        status: response.data.status,
        message: response.data.description,
        agent: response.data.agent,
        created_at: new Date(response.data.created_at),
        updated_at: new Date(response.data.updated_at)
      };

      // Notify listeners
      this.notifyTaskListeners(task);

      return task;
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    }
  }

  /**
   * Get task status
   */
  async getTask(taskId: string): Promise<ClientTask> {
    try {
      const response = await this.makeRequest(`/api/v1/tasks/${taskId}`);

      if (!response.success) {
        throw new Error(response.error || 'Failed to get task');
      }

      return {
        id: response.data.id,
        type: response.data.type,
        status: response.data.status,
        message: response.data.description,
        result: response.data.result,
        error: response.data.error,
        agent: response.data.agent,
        created_at: new Date(response.data.created_at),
        updated_at: new Date(response.data.updated_at)
      };
    } catch (error) {
      console.error('Error getting task:', error);
      throw error;
    }
  }

  /**
   * Get all available agents
   */
  async getAgents(): Promise<ClientAgent[]> {
    try {
      const response = await this.makeRequest('/api/v1/agents');

      if (!response.success) {
        throw new Error(response.error || 'Failed to get agents');
      }

      const agents = response.data.map((agent: any) => ({
        id: agent.id,
        name: agent.name,
        type: agent.type,
        status: agent.status,
        capabilities: agent.capabilities,
        description: agent.description
      }));

      // Notify listeners
      this.notifyAgentListeners(agents);

      return agents;
    } catch (error) {
      console.error('Error getting agents:', error);
      // Return default agents as fallback
      return this.getDefaultAgents();
    }
  }

  /**
   * Get health status
   */
  async getHealthStatus(): Promise<{ status: string; agents: ClientAgent[] }> {
    try {
      const response = await this.makeRequest('/health');  // Changed from /api/v1/health to /health to match backend

      if (!response.success) {
        throw new Error(response.error || 'Health check failed');
      }

      return {
        status: response.status || response.data?.status || 'healthy',
        agents: response.agents || response.data?.agents || []
      };
    } catch (error) {
      console.error('Health check failed:', error);
      return {
        status: 'unhealthy',
        agents: this.getDefaultAgents()
      };
    }
  }

  /**
   * HTTP polling for real-time updates
   */
  private async setupHttpPolling(): Promise<void> {
    try {
      console.log('Setting up HTTP polling for real-time updates');

      // Poll every 30 seconds for task and agent updates
      const pollInterval = 30000;

      setInterval(async () => {
        try {
          // Poll for task updates
          const response = await this.makeRequest('/api/v1/tasks?limit=50');
          if (response.success && response.data) {
            this.handleTaskUpdates(response.data);
          }

          // Poll for agent status updates
          const agentsResponse = await this.makeRequest('/api/v1/agents');
          if (agentsResponse.success && agentsResponse.data) {
            this.handleAgentUpdates(agentsResponse.data);
          }

          // Poll for new messages
          const messagesResponse = await this.makeRequest('/api/v1/chat/history?limit=10');
          if (messagesResponse.success && messagesResponse.data) {
            this.handleMessageUpdates(messagesResponse.data);
          }

        } catch (error) {
          console.error('Error during HTTP polling:', error);
        }
      }, pollInterval);

    } catch (error) {
      console.error('Error setting up HTTP polling:', error);
      // Continue without real-time updates
    }
  }

  private handleTaskUpdates(tasks: any[]): void {
    tasks.forEach(task => {
      this.notifyTaskListeners({
        id: task.id,
        type: task.type,
        status: task.status,
        message: task.description,
        result: task.result,
        error: task.error,
        agent: task.agent,
        created_at: new Date(task.created_at),
        updated_at: new Date(task.updated_at)
      });
    });
  }

  private handleAgentUpdates(agents: any[]): void {
    const mappedAgents = agents.map((agent: any) => ({
      id: agent.id,
      name: agent.name,
      type: agent.type,
      status: agent.status,
      capabilities: agent.capabilities,
      description: agent.description
    }));
    this.notifyAgentListeners(mappedAgents);
  }

  private handleMessageUpdates(messages: any[]): void {
    messages.forEach((msg: any) => {
      this.notifyMessageListeners({
        id: msg.id,
        content: msg.content,
        type: msg.type,
        timestamp: new Date(msg.timestamp),
        agent: msg.agent,
        metadata: msg.metadata
      });
    });
  }

  
  /**
   * HTTP request helper
   */
  private async makeRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.config.baseURL}${endpoint}`;

    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` }),
    };

    let lastError: Error | null = null;

    // Create timeout abort controller with React Native compatibility
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    for (let attempt = 1; attempt <= this.config.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: { ...defaultHeaders, ...options.headers },
          signal: controller.signal,
        });

        clearTimeout(timeoutId); // Clear timeout if request succeeds

        let data;
        try {
          data = await response.json();
        } catch (parseError) {
          // If JSON parsing fails, get response as text for debugging
          const text = await response.text();
          console.error(`Failed to parse JSON response from ${url}:`, text.substring(0, 200));
          throw new Error(`Invalid JSON response from server: ${parseError instanceof Error ? parseError.message : 'Unknown error'}. Response starts with: ${text.substring(0, 50)}`);
        }

        if (!response.ok) {
          throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        return data;
      } catch (error) {
        lastError = error as Error;

        if (attempt < this.config.retryAttempts) {
          console.warn(`Request failed (attempt ${attempt}/${this.config.retryAttempts}):`, error);
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
      }
    }

    // Clear timeout if all attempts failed
    clearTimeout(timeoutId);
    throw lastError || new Error('Request failed after all retry attempts');
  }

  /**
   * Local storage helpers
   */
  private async storeMessage(message: ClientMessage): Promise<void> {
    try {
      const existingMessages = await this.getLocalMessages(1000);
      existingMessages.push(message);

      // Keep only last 1000 messages
      const trimmedMessages = existingMessages.slice(-1000);

      await AsyncStorage.setItem('chat_messages', JSON.stringify(trimmedMessages));
    } catch (error) {
      console.error('Error storing message:', error);
    }
  }

  private async getLocalMessages(limit: number): Promise<ClientMessage[]> {
    try {
      const stored = await AsyncStorage.getItem('chat_messages');
      if (!stored) return [];

      const messages = JSON.parse(stored);
      return messages
        .map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
        .slice(-limit);
    } catch (error) {
      console.error('Error getting local messages:', error);
      return [];
    }
  }

  private getDefaultAgents(): ClientAgent[] {
    return [
      {
        id: 'ceo',
        name: 'CEO Agent',
        type: 'ceo',
        status: 'idle',
        capabilities: ['coordination', 'decision_making', 'general_assistance'],
        description: 'Coordinates tasks and provides general assistance'
      },
      {
        id: 'strategy',
        name: 'Strategy Agent',
        type: 'strategy',
        status: 'idle',
        capabilities: ['market_research', 'financial_analysis', 'strategic_planning'],
        description: 'Handles market research and strategic planning'
      },
      {
        id: 'devops',
        name: 'DevOps Agent',
        type: 'devops',
        status: 'idle',
        capabilities: ['code_analysis', 'ui_ux_review', 'technical_decisions'],
        description: 'Handles technical analysis and decisions'
      }
    ];
  }

  /**
   * Event listeners
   */
  onMessage(listener: (message: ClientMessage) => void): () => void {
    this.messageListeners.push(listener);
    return () => {
      const index = this.messageListeners.indexOf(listener);
      if (index > -1) {
        this.messageListeners.splice(index, 1);
      }
    };
  }

  onTaskUpdate(listener: (task: ClientTask) => void): () => void {
    this.taskListeners.push(listener);
    return () => {
      const index = this.taskListeners.indexOf(listener);
      if (index > -1) {
        this.taskListeners.splice(index, 1);
      }
    };
  }

  onAgentUpdate(listener: (agents: ClientAgent[]) => void): () => void {
    this.agentListeners.push(listener);
    return () => {
      const index = this.agentListeners.indexOf(listener);
      if (index > -1) {
        this.agentListeners.splice(index, 1);
      }
    };
  }

  private notifyMessageListeners(message: ClientMessage): void {
    this.messageListeners.forEach(listener => {
      try {
        listener(message);
      } catch (error) {
        console.error('Error in message listener:', error);
      }
    });
  }

  private notifyTaskListeners(task: ClientTask): void {
    this.taskListeners.forEach(listener => {
      try {
        listener(task);
      } catch (error) {
        console.error('Error in task listener:', error);
      }
    });
  }

  private notifyAgentListeners(agents: ClientAgent[]): void {
    this.agentListeners.forEach(listener => {
      try {
        listener(agents);
      } catch (error) {
        console.error('Error in agent listener:', error);
      }
    });
  }

  /**
   * Cleanup
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.messageListeners = [];
    this.taskListeners = [];
    this.agentListeners = [];
  }

  /**
   * Configuration
   */
  async updateConfig(newConfig: Partial<ClientConfig>): Promise<void> {
    this.config = { ...this.config, ...newConfig };
    await AsyncStorage.setItem('api_client_config', JSON.stringify(this.config));
  }

  getConfig(): ClientConfig {
    return { ...this.config };
  }
}

// Singleton instance
let clientInstance: SimpleAPIClient | null = null;

export function getAPIClient(config?: Partial<ClientConfig>): SimpleAPIClient {
  if (!clientInstance) {
    clientInstance = new SimpleAPIClient(config);
  }
  return clientInstance;
}

export default SimpleAPIClient;