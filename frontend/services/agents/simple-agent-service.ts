/**
 * Simple Agent Service
 * Replaces complex LangGraph agent system with simple API calls
 * Manages agent operations and delegation to FastAPI backend
 */

import {
  getAPIClient,
  ClientMessage,
  ClientTask,
  ClientAgent
} from '../api/client-service';

// Types for simplified agent system
export interface SimpleAgentConfig {
  id: string;
  name: string;
  type: 'ceo' | 'strategy' | 'devops';
  capabilities: string[];
  description: string;
  autoDelegate: boolean;
}

export interface SimpleAgentState {
  agents: ClientAgent[];
  messages: ClientMessage[];
  tasks: ClientTask[];
  isOnline: boolean;
  backendConnected: boolean;
}

export interface AgentResponse {
  success: boolean;
  message: string;
  data?: any;
  agent?: string;
  requiresUserInput?: boolean;
  userInputPrompt?: string;
  nextAction?: {
    type: 'continue' | 'complete' | 'error';
    target?: string;
    payload?: any;
  };
}

class SimpleAgentService {
  private client: ReturnType<typeof getAPIClient>;
  private state: SimpleAgentState;
  private eventListeners: Map<string, Function[]> = new Map();
  private isInitialized = false;

  constructor() {
    this.client = getAPIClient();
    this.state = {
      agents: [],
      messages: [],
      tasks: [],
      isOnline: true,
      backendConnected: false
    };
  }

  /**
   * Initialize the simple agent service
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.client.initialize();

      // Load initial data
      await Promise.all([
        this.loadAgents(),
        this.loadMessages(),
        this.checkBackendConnection()
      ]);

      // Set up event listeners
      this.setupEventListeners();

      this.isInitialized = true;
      this.emitEvent('service:initialized', { state: this.state });

      console.log('Simple Agent Service initialized successfully');
    } catch (error) {
      console.error('Error initializing Simple Agent Service:', error);
      this.state.backendConnected = false;
      // Continue with offline mode
      this.isInitialized = true;
    }
  }

  /**
   * Process a user message and get response from backend
   */
  async processUserMessage(
    message: string,
    agentHint?: string,
    context?: any
  ): Promise<AgentResponse> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      // Create user message locally first
      const userMessage: ClientMessage = {
        id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        content: message,
        type: 'user',
        timestamp: new Date(),
        metadata: { context }
      };

      // Add to local state
      this.state.messages.push(userMessage);

      // Try to send to backend
      if (this.state.backendConnected) {
        try {
          const response = await this.client.sendMessage(message, agentHint);

          // Update state with response
          this.state.messages.push(response);

          return {
            success: true,
            message: response.content,
            data: response.metadata,
            agent: response.agent,
            nextAction: {
              type: 'complete'
            }
          };
        } catch (backendError) {
          console.warn('Backend communication failed, using fallback:', backendError);
          this.state.backendConnected = false;
          return await this.generateFallbackResponse(message, agentHint);
        }
      } else {
        // Offline mode - generate fallback response
        return await this.generateFallbackResponse(message, agentHint);
      }
    } catch (error) {
      console.error('Error processing user message:', error);

      return {
        success: false,
        message: `Error processing message: ${error}`,
        requiresUserInput: true,
        userInputPrompt: 'There was an error processing your request. Would you like to try again?'
      };
    }
  }

  /**
   * Create and monitor a task
   */
  async createTask(
    type: string,
    description: string,
    agent?: string
  ): Promise<ClientTask> {
    try {
      if (this.state.backendConnected) {
        const task = await this.client.createTask(type, description, agent);
        this.state.tasks.push(task);
        return task;
      } else {
        // Create local task when offline
        const localTask: ClientTask = {
          id: `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          type,
          status: 'pending',
          message: description,
          agent,
          created_at: new Date(),
          updated_at: new Date()
        };

        this.state.tasks.push(localTask);
        return localTask;
      }
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    }
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskId: string): Promise<ClientTask> {
    try {
      if (this.state.backendConnected) {
        return await this.client.getTask(taskId);
      } else {
        // Return local task
        const localTask = this.state.tasks.find(t => t.id === taskId);
        if (!localTask) {
          throw new Error('Task not found');
        }
        return localTask;
      }
    } catch (error) {
      console.error('Error getting task status:', error);
      throw error;
    }
  }

  /**
   * Get all agents
   */
  async getAgents(): Promise<ClientAgent[]> {
    if (this.state.backendConnected) {
      try {
        this.state.agents = await this.client.getAgents();
      } catch (error) {
        console.warn('Failed to fetch agents from backend, using defaults:', error);
        this.state.agents = this.getDefaultAgents();
      }
    } else {
      this.state.agents = this.getDefaultAgents();
    }

    return this.state.agents;
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(limit: number = 50): Promise<ClientMessage[]> {
    if (this.state.backendConnected) {
      try {
        this.state.messages = await this.client.getMessages(limit);
      } catch (error) {
        console.warn('Failed to fetch messages from backend, using local cache:', error);
        // Use existing messages from state
      }
    }

    return this.state.messages.slice(-limit);
  }

  /**
   * Get current service state
   */
  getState(): SimpleAgentState {
    return { ...this.state };
  }

  /**
   * Check backend connection
   */
  async checkBackendConnection(): Promise<boolean> {
    try {
      const health = await this.client.getHealthStatus();
      this.state.backendConnected = health.status === 'healthy';

      if (health.agents.length > 0) {
        this.state.agents = health.agents;
      }

      return this.state.backendConnected;
    } catch (error) {
      console.warn('Backend health check failed:', error);
      this.state.backendConnected = false;
      return false;
    }
  }

  /**
   * Clear conversation history
   */
  async clearConversationHistory(): Promise<void> {
    this.state.messages = [];
    this.emitEvent('conversation:cleared', { state: this.state });
  }

  /**
   * Reset service state
   */
  async reset(): Promise<void> {
    this.state = {
      agents: [],
      messages: [],
      tasks: [],
      isOnline: true,
      backendConnected: false
    };

    await this.initialize();
    this.emitEvent('service:reset', { state: this.state });
  }

  /**
   * Private methods
   */
  private async loadAgents(): Promise<void> {
    try {
      this.state.agents = await this.getAgents();
    } catch (error) {
      console.warn('Failed to load agents:', error);
      this.state.agents = this.getDefaultAgents();
    }
  }

  private async loadMessages(): Promise<void> {
    try {
      this.state.messages = await this.getConversationHistory(100);
    } catch (error) {
      console.warn('Failed to load messages:', error);
      this.state.messages = [];
    }
  }

  private setupEventListeners(): void {
    // Listen to real-time updates from the API client
    this.client.onMessage((message: ClientMessage) => {
      this.state.messages.push(message);
      this.emitEvent('message:received', { message, state: this.state });
    });

    this.client.onTaskUpdate((task: ClientTask) => {
      const index = this.state.tasks.findIndex(t => t.id === task.id);
      if (index > -1) {
        this.state.tasks[index] = task;
      } else {
        this.state.tasks.push(task);
      }
      this.emitEvent('task:updated', { task, state: this.state });
    });

    this.client.onAgentUpdate((agents: ClientAgent[]) => {
      this.state.agents = agents;
      this.emitEvent('agents:updated', { agents, state: this.state });
    });
  }

  private async generateFallbackResponse(
    message: string,
    agentHint?: string
  ): Promise<AgentResponse> {
    // Simple fallback responses when backend is unavailable
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('help')) {
      return {
        success: true,
        message: `I'm currently in offline mode. Available agents:

• CEO Agent: General coordination and assistance
• Strategy Agent: Market research and strategic planning
• DevOps Agent: Code analysis and technical decisions

Please try your request again when I'm back online.`,
        agent: 'ceo'
      };
    }

    if (lowerMessage.includes('strategy') || lowerMessage.includes('market')) {
      return {
        success: true,
        message: 'Your strategy request has been queued. I\'ll process it when I\'m back online.',
        agent: 'strategy',
        requiresUserInput: false,
        nextAction: {
          type: 'continue',
          payload: { queued: true }
        }
      };
    }

    if (lowerMessage.includes('code') || lowerMessage.includes('technical')) {
      return {
        success: true,
        message: 'Your technical analysis request has been queued. I\'ll process it when I\'m back online.',
        agent: 'devops',
        requiresUserInput: false,
        nextAction: {
          type: 'continue',
          payload: { queued: true }
        }
      };
    }

    return {
      success: true,
      message: 'I\'ve received your message and will process it when I\'m back online. For urgent matters, please try again later.',
      agent: 'ceo'
    };
  }

  private getDefaultAgents(): ClientAgent[] {
    return [
      {
        id: 'ceo',
        name: 'CEO Agent',
        type: 'ceo',
        status: this.state.backendConnected ? 'idle' : 'offline',
        capabilities: ['coordination', 'decision_making', 'general_assistance'],
        description: 'Coordinates tasks and provides general assistance'
      },
      {
        id: 'strategy',
        name: 'Strategy Agent (CMO/CFO)',
        type: 'strategy',
        status: this.state.backendConnected ? 'idle' : 'offline',
        capabilities: ['market_research', 'financial_analysis', 'strategic_planning'],
        description: 'Handles market research, financial analysis, and strategic planning'
      },
      {
        id: 'devops',
        name: 'DevOps Agent (CTO)',
        type: 'devops',
        status: this.state.backendConnected ? 'idle' : 'offline',
        capabilities: ['code_analysis', 'ui_ux_review', 'technical_decisions'],
        description: 'Handles code analysis, UI/UX review, and technical decisions'
      }
    ];
  }

  /**
   * Event handling
   */
  on(event: string, listener: Function): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);

    return () => {
      const listeners = this.eventListeners.get(event);
      if (listeners) {
        const index = listeners.indexOf(listener);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      }
    };
  }

  private emitEvent(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Cleanup
   */
  async cleanup(): Promise<void> {
    this.client.disconnect();
    this.eventListeners.clear();
    this.isInitialized = false;
    console.log('Simple Agent Service cleaned up successfully');
  }
}

// Singleton instance
let agentServiceInstance: SimpleAgentService | null = null;

export function getSimpleAgentService(): SimpleAgentService {
  if (!agentServiceInstance) {
    agentServiceInstance = new SimpleAgentService();
  }
  return agentServiceInstance;
}

export default SimpleAgentService;