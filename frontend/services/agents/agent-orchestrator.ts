/**
 * Simple Agent Orchestrator - Main entry point for client-side agent system
 * Manages simple communication with FastAPI backend
 * React Native Compatible Implementation
 */

import {
  getSimpleAgentService,
  AgentResponse as SimpleAgentResponse
} from './simple-agent-service';
import {
  AgentResponse,
  AgentState,
  UserContext,
  ExecutionContext,
  TaskStatus,
  TaskType
} from './types';

export interface SimpleOrchestratorConfig {
  userId: string;
  backendURL?: string;
  enableRealtimeSync?: boolean;
  offlineMode?: boolean;
}

export interface SimpleAgentSwarmState {
  taskStatus: any;
  sessionId: string;
  userId: string;
  startTime: Date;
  lastActivity: Date;
  activeTasks: TaskStatus[];
  completedTasks: TaskStatus[];
  failedTasks: TaskStatus[];
  currentAgent?: string;
  userContext: UserContext;
  executionContext: ExecutionContext;
  isConnected: boolean;
  backendStatus: 'online' | 'offline' | 'error';
}

/**
 * Simple Agent Orchestrator - Client-side orchestrator
 * Handles communication with FastAPI backend and manages local state
 */
export class AgentOrchestrator {
  private config: SimpleOrchestratorConfig;
  private agentService: ReturnType<typeof getSimpleAgentService>;
  private state: SimpleAgentSwarmState;
  private isInitialized = false;
  private eventListeners: Map<string, Function[]> = new Map();

  constructor(config: SimpleOrchestratorConfig) {
    this.config = config;
    this.agentService = getSimpleAgentService();

    // Generate session ID first
    const sessionId = this.generateSessionId();

    // Initialize state
    this.state = {
      sessionId,
      userId: config.userId,
      startTime: new Date(),
      lastActivity: new Date(),
      activeTasks: [],
      completedTasks: [],
      failedTasks: [],
      userContext: this.createUserContext(),
      executionContext: this.createExecutionContext(sessionId),
      isConnected: false,
      backendStatus: 'offline'
    };
  }

  /**
   * Initialize the simple agent orchestrator with enhanced error handling
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('Agent orchestrator already initialized');
      return;
    }

    try {
      console.log('Initializing agent orchestrator...');
      console.log('Session ID:', this.state.sessionId);
      console.log('User ID:', this.state.userId);

      // Initialize the simple agent service with timeout
      const initPromise = this.agentService.initialize();
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Agent service initialization timeout (15s)')), 15000);
      });

      await Promise.race([initPromise, timeoutPromise]);
      console.log('Agent service initialized successfully');

      // Check backend connection with error handling
      try {
        this.state.isConnected = await this.agentService.checkBackendConnection();
        this.state.backendStatus = this.state.isConnected ? 'online' : 'offline';
        console.log('Backend connection status:', this.state.backendStatus);
      } catch (connectionError) {
        console.warn('Backend connection check failed, continuing in offline mode:', connectionError);
        this.state.isConnected = false;
        this.state.backendStatus = 'offline';
      }

      // Load conversation history with error handling
      try {
        const messages = await this.agentService.getConversationHistory();
        console.log('Loaded conversation history:', messages.length, 'messages');
        // Convert messages to tasks if needed
        await this.processMessageHistory(messages);
      } catch (historyError) {
        console.warn('Failed to load conversation history:', historyError);
        // Continue without history
      }

      // Set up event listeners for real-time updates
      try {
        this.setupEventListeners();
        console.log('Event listeners set up successfully');
      } catch (listenerError) {
        console.warn('Failed to set up some event listeners:', listenerError);
        // Continue without real-time updates
      }

      this.isInitialized = true;

      // Emit initialization event with comprehensive data
      this.emitEvent('orchestrator:initialized', {
        sessionId: this.state.sessionId,
        backendStatus: this.state.backendStatus,
        isConnected: this.state.isConnected,
        userId: this.state.userId,
        timestamp: new Date().toISOString(),
        offlineMode: this.config.offlineMode
      });

      console.log('Simple Agent Orchestrator initialized successfully');
      console.log('Initialization details:', {
        sessionId: this.state.sessionId,
        backendStatus: this.state.backendStatus,
        isConnected: this.state.isConnected,
        userId: this.state.userId
      });

    } catch (error) {
      console.error('Error initializing Simple Agent Orchestrator:', error);

      // Enhanced error handling with different error types
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorType = this.classifyError(error);

      console.error('Initialization error details:', {
        message: errorMessage,
        type: errorType,
        sessionId: this.state.sessionId,
        config: {
          userId: this.config.userId,
          backendURL: this.config.backendURL,
          enableRealtimeSync: this.config.enableRealtimeSync,
          offlineMode: this.config.offlineMode
        }
      });

      this.state.backendStatus = 'error';
      this.state.isConnected = false;

      // Continue in offline mode for certain error types
      if (errorType === 'network' || errorType === 'timeout') {
        console.log('Network/timeout error, continuing in offline mode');
        this.isInitialized = true;

        this.emitEvent('orchestrator:initialized', {
          sessionId: this.state.sessionId,
          backendStatus: 'offline',
          isConnected: false,
          userId: this.state.userId,
          timestamp: new Date().toISOString(),
          error: errorMessage,
          offlineMode: true
        });
      } else {
        // Emit error event for critical errors
        this.emitEvent('orchestrator:error', {
          sessionId: this.state.sessionId,
          error: errorMessage,
          errorType,
          backendStatus: this.state.backendStatus,
          timestamp: new Date().toISOString()
        });

        // Still mark as initialized to prevent infinite retry loops
        this.isInitialized = true;

        this.emitEvent('orchestrator:initialized', {
          sessionId: this.state.sessionId,
          backendStatus: 'error',
          isConnected: false,
          userId: this.state.userId,
          timestamp: new Date().toISOString(),
          error: errorMessage,
          errorType
        });
      }
    }
  }

  /**
   * Process a user message through the simple agent system
   */
  async processUserMessage(message: string, context?: any, agentHint?: string): Promise<AgentResponse> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    this.updateLastActivity();

    try {
      // Determine appropriate agent hint based on content if not provided
      if (!agentHint) {
        agentHint = this.determineAgentHint(message);
      }

      // Create initial task
      const task = this.createInitialTask(message);

      // Add to active tasks
      this.state.activeTasks.push(task);

      // Process with simple agent service (communicates with backend)
      const response = await this.agentService.processUserMessage(message, agentHint, context);

      // Update task status
      if (response.success) {
        task.status = 'completed';
        this.state.completedTasks.push(task);
      } else {
        task.status = 'failed';
        this.state.failedTasks.push(task);
      }

      // Remove from active tasks
      const index = this.state.activeTasks.findIndex(t => t.id === task.id);
      if (index > -1) {
        this.state.activeTasks.splice(index, 1);
      }

      // Update current agent if specified
      if (response.agent) {
        this.state.currentAgent = response.agent;
      }

      // Emit event
      this.emitEvent('message:processed', {
        message,
        response,
        sessionId: this.state.sessionId,
        agent: response.agent
      });

      return response;

    } catch (error) {
      console.error('Error processing user message:', error);

      const errorResponse: AgentResponse = {
        success: false,
        message: `Error processing message: ${error}`,
        requiresUserInput: true,
        userInputPrompt: 'There was an error processing your request. Would you like to try again or provide more details?'
      };

      this.emitEvent('message:error', {
        message,
        error,
        sessionId: this.state.sessionId
      });

      return errorResponse;
    }
  }

  /**
   * Get current orchestrator state
   */
  getState(): SimpleAgentSwarmState {
    return { ...this.state };
  }

  /**
   * Get agent metrics
   */
  async getAgentMetrics(): Promise<any> {
    const serviceState = this.agentService.getState();

    return {
      orchestrator: {
        sessionId: this.state.sessionId,
        totalTasks: this.state.activeTasks.length + this.state.completedTasks.length + this.state.failedTasks.length,
        activeTasks: this.state.activeTasks.length,
        completedTasks: this.state.completedTasks.length,
        failedTasks: this.state.failedTasks.length,
        uptime: Date.now() - this.state.startTime.getTime(),
        lastActivity: this.state.lastActivity
      },
      agents: serviceState.agents,
      backendStatus: this.state.backendStatus,
      isConnected: this.state.isConnected
    };
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(limit: number = 50): Promise<any[]> {
    return await this.agentService.getConversationHistory(limit);
  }

  /**
   * Clear conversation history
   */
  async clearConversationHistory(): Promise<void> {
    await this.agentService.clearConversationHistory();
    this.emitEvent('conversation:cleared', { sessionId: this.state.sessionId });
  }

  /**
   * Reset session
   */
  async resetSession(): Promise<void> {
    await this.agentService.reset();

    // Reset local state
    this.state.activeTasks = [];
    this.state.completedTasks = [];
    this.state.failedTasks = [];
    this.state.startTime = new Date();
    this.state.lastActivity = new Date();
    this.state.sessionId = this.generateSessionId();

    this.emitEvent('session:reset', { sessionId: this.state.sessionId });
  }

  /**
   * Add event listener
   */
  on(event: string, listener: Function): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);

    // Return unsubscribe function
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

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    try {
      await this.agentService.cleanup();

      // Clear event listeners
      this.eventListeners.clear();

      this.isInitialized = false;

      console.log('Simple Agent Orchestrator cleaned up successfully');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  /**
   * Private helper methods
   */
  private determineAgentHint(message: string): string {
    const messageLower = message.toLowerCase();

    if (messageLower.includes('research') || messageLower.includes('market') ||
        messageLower.includes('financial') || messageLower.includes('budget') ||
        messageLower.includes('strategy') || messageLower.includes('planning')) {
      return 'strategy';
    }

    if (messageLower.includes('code') || messageLower.includes('technical') ||
        messageLower.includes('ui') || messageLower.includes('ux') ||
        messageLower.includes('design') || messageLower.includes('performance') ||
        messageLower.includes('security')) {
      return 'devops';
    }

    // Default to CEO for general requests
    return 'ceo';
  }

  private createInitialTask(message: string): TaskStatus {
    return {
      id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: this.determineTaskType(message),
      status: 'processing',
      priority: 'medium',
      createdAt: new Date(),
      updatedAt: new Date(),
      assignedTo: 'ceo'
    };
  }

  private determineTaskType(message: string): TaskType {
    const messageLower = message.toLowerCase();

    if (messageLower.includes('research') || messageLower.includes('market')) {
      return 'market_research';
    }
    if (messageLower.includes('financial') || messageLower.includes('budget')) {
      return 'financial_analysis';
    }
    if (messageLower.includes('code') || messageLower.includes('technical')) {
      return 'code_analysis';
    }
    if (messageLower.includes('ui') || messageLower.includes('ux') || messageLower.includes('design')) {
      return 'ui_ux_review';
    }

    return 'strategic_planning';
  }

  private createUserContext(): UserContext {
    return {
      id: this.config.userId,
      preferences: {
        industry: 'Technology',
        businessSize: 'medium',
        timezone: 'UTC',
        language: 'en',
        notifications: {
          email: true,
          push: true,
          sms: false,
          frequency: 'daily',
          types: ['task_completed', 'error']
        }
      },
      businessProfile: {
        industry: 'Technology',
        segment: 'SaaS',
        employees: 50
      },
      subscription: {
        tier: 'pro',
        limits: {
          maxAgents: 3,
          maxTasksPerDay: 100,
          maxStorageSize: 1000000000, // 1GB
          maxAPICallsPerDay: 10000
        },
        features: ['multi_agent', 'realtime_sync', 'advanced_analytics']
      },
      sessionContext: {
        startTime: new Date(),
        lastActivity: new Date(),
        activeAgents: ['ceo', 'strategy', 'devops'],
        currentTasks: []
      }
    };
  }

  private createExecutionContext(sessionId: string): ExecutionContext {
    return {
      sessionId,
      requestId: '',
      timestamp: new Date(),
      environment: 'production',
      performance: {
        startTime: new Date()
      }
    };
  }

  private updateLastActivity(): void {
    this.state.lastActivity = new Date();
    this.state.userContext.sessionContext.lastActivity = new Date();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private setupEventListeners(): void {
    // Listen to simple agent service events
    this.agentService.on('service:initialized', (data: any) => {
      this.state.isConnected = data.state.isOnline;
      this.state.backendStatus = data.state.backendConnected ? 'online' : 'offline';
      this.emitEvent('backend:connected', { status: this.state.backendStatus });
    });

    this.agentService.on('message:received', (data: any) => {
      this.emitEvent('message:received', data);
    });

    this.agentService.on('task:updated', (data: any) => {
      // Update local task state if needed
      const task = this.state.activeTasks.find(t => t.id === data.task.id);
      if (task) {
        Object.assign(task, data.task);
      }
      this.emitEvent('task:updated', data);
    });

    this.agentService.on('agents:updated', (data: any) => {
      this.emitEvent('agents:updated', data);
    });
  }

  private async processMessageHistory(messages: any[]): Promise<void> {
    // Process existing messages to create task history if needed
    // This is a simplified version - in production you might want to restore more state
    for (const message of messages) {
      if (message.type === 'user') {
        // Could create completed tasks from user messages if needed
      }
    }
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
   * Classify error types for better handling
   */
  private classifyError(error: any): string {
    if (!error) return 'unknown';

    const message = error.message || String(error);

    if (message.includes('network') || message.includes('fetch') || message.includes('ECONNREFUSED')) {
      return 'network';
    }
    if (message.includes('timeout')) {
      return 'timeout';
    }
    if (message.includes('authentication') || message.includes('unauthorized')) {
      return 'authentication';
    }
    if (message.includes('permission') || message.includes('forbidden')) {
      return 'permission';
    }
    if (message.includes('validation') || message.includes('invalid')) {
      return 'validation';
    }
    if (message.includes('not found') || message.includes('404')) {
      return 'not_found';
    }
    if (message.includes('rate limit') || message.includes('429')) {
      return 'rate_limit';
    }
    if (message.includes('server error') || message.includes('500')) {
      return 'server_error';
    }

    return 'unknown';
  }
}

export default AgentOrchestrator;