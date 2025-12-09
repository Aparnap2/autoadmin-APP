/**
 * HTTP-based Streaming Client for AutoAdmin Frontend
 * Replaces WebSocket communication with Server-Sent Events and HTTP polling
 * Provides real-time agent communication using standard HTTP protocols
 */

import { EventEmitter } from 'events';

export interface StreamingConnection {
  id: string;
  userId?: string;
  sessionId: string;
  eventTypes: string[];
  filters: Record<string, any>;
  isActive: boolean;
  createdAt: Date;
  lastActivity: Date;
}

export interface StreamingEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
  userId?: string;
  sessionId?: string;
  agentId?: string;
  taskId?: string;
}

export interface PollingSession {
  id: string;
  userId?: string;
  filters: Record<string, any>;
  createdAt: Date;
  lastActivity: Date;
  isActive: boolean;
  eventsSent: string[];
}

export interface AgentStatus {
  agentId: string;
  agentType: string;
  name: string;
  status: string;
  currentLoad: number;
  maxCapacity: number;
  currentTasks: string[];
  capabilities: string[];
  lastHeartbeat: string;
  metadata: Record<string, any>;
}

export interface TaskUpdate {
  taskId: string;
  taskType: string;
  status: string;
  progress: number;
  message?: string;
  result?: Record<string, any>;
  error?: string;
  assignedTo?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface ChatMessage {
  id: string;
  agentId: string;
  agentType: string;
  message: string;
  messageType: 'user_message' | 'agent_response' | 'system_message';
  timestamp: string;
  userId?: string;
  sessionId: string;
}

export enum ConnectionMode {
  SSE = 'sse',
  POLLING = 'polling',
  AUTO = 'auto' // Try SSE first, fallback to polling
}

export enum EventType {
  AGENT_STATUS_UPDATE = 'agent_status_update',
  TASK_PROGRESS = 'task_progress',
  TASK_COMPLETED = 'task_completed',
  TASK_FAILED = 'task_failed',
  SYSTEM_NOTIFICATION = 'system_notification',
  CHAT_MESSAGE = 'chat_message',
  HEALTH_CHECK = 'health_check',
  ERROR = 'error'
}

export interface StreamingClientOptions {
  baseUrl?: string;
  connectionMode?: ConnectionMode;
  eventTypes?: string[];
  filters?: Record<string, any>;
  userId?: string;
  sessionId?: string;
  pollingInterval?: number;
  pollingTimeout?: number;
  maxRetries?: number;
  retryDelay?: number;
  enableReconnect?: boolean;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  enableLogging?: boolean;
}

export interface CreateConnectionResponse {
  success: boolean;
  clientId: string;
  sessionId: string;
  endpoint: string;
  message: string;
  eventTypes?: string[];
  filters?: Record<string, any>;
  timestamp: string;
}

export interface PollingResponse {
  success: boolean;
  events: StreamingEvent[];
  sessionId: string;
  immediate?: boolean;
  timeout?: boolean;
  waitedSeconds?: number;
}

/**
 * HTTP-based Streaming Client
 * Provides WebSocket-like functionality through HTTP protocols
 */
export class HTTPStreamingClient extends EventEmitter {
  private baseUrl: string;
  private options: Required<StreamingClientOptions>;
  private connection: StreamingConnection | null = null;
  private pollingSession: PollingSession | null = null;
  private eventSource: EventSource | null = null;
  private pollingTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isConnected = false;
  private retryCount = 0;
  private lastEventId: string | null = null;
  private connectionMode: ConnectionMode;
  private shouldReconnect = true;
  private eventBuffer: StreamingEvent[] = [];
  private maxEventBufferSize = 1000;

  constructor(options: StreamingClientOptions = {}) {
    super();

    // Default options
    this.options = {
      baseUrl: options.baseUrl || process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
      connectionMode: options.connectionMode || ConnectionMode.AUTO,
      eventTypes: options.eventTypes || Object.values(EventType),
      filters: options.filters || {},
      userId: options.userId,
      sessionId: options.sessionId || this.generateSessionId(),
      pollingInterval: options.pollingInterval || 5000,
      pollingTimeout: options.pollingTimeout || 30000,
      maxRetries: options.maxRetries || 5,
      retryDelay: options.retryDelay || 1000,
      enableReconnect: options.enableReconnect !== false,
      reconnectDelay: options.reconnectDelay || 5000,
      heartbeatInterval: options.heartbeatInterval || 30000,
      enableLogging: options.enableLogging !== false
    };

    this.baseUrl = this.options.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.connectionMode = this.options.connectionMode;

    // Bind methods to maintain context
    this.handleSSEMessage = this.handleSSEMessage.bind(this);
    this.handleSSEError = this.handleSSEError.bind(this);
    this.handleSSEOpen = this.handleSSEOpen.bind(this);
    this.handleSSEClose = this.handleSSEClose.bind(this);
  }

  /**
   * Connect to the streaming service
   */
  async connect(): Promise<boolean> {
    try {
      if (this.isConnecting || this.isConnected) {
        this.log('Already connected or connecting');
        return true;
      }

      this.isConnecting = true;
      this.emit('connecting');

      // Determine connection mode
      let modeToUse = this.connectionMode;
      if (modeToUse === ConnectionMode.AUTO) {
        modeToUse = ConnectionMode.SSE; // Try SSE first
      }

      let connected = false;

      if (modeToUse === ConnectionMode.SSE) {
        connected = await this.connectSSE();
        if (!connected && this.connectionMode === ConnectionMode.AUTO) {
          this.log('SSE failed, falling back to polling');
          connected = await this.connectPolling();
        }
      } else {
        connected = await this.connectPolling();
      }

      this.isConnecting = false;

      if (connected) {
        this.isConnected = true;
        this.retryCount = 0;
        this.emit('connected', this.connection);
        this.startHeartbeat();
        return true;
      } else {
        this.emit('error', new Error('Failed to establish connection'));
        return false;
      }

    } catch (error) {
      this.isConnecting = false;
      this.log('Connection error:', error);
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Disconnect from the streaming service
   */
  async disconnect(): Promise<void> {
    this.shouldReconnect = false;

    // Clear timers
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
      this.pollingTimer = null;
    }

    // Close SSE connection
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    // Cleanup polling session
    if (this.pollingSession) {
      try {
        await this.removePollingSession(this.pollingSession.id);
      } catch (error) {
        this.log('Error removing polling session:', error);
      }
      this.pollingSession = null;
    }

    // Close connection
    if (this.connection) {
      try {
        await this.removeConnection(this.connection.id);
      } catch (error) {
        this.log('Error removing connection:', error);
      }
      this.connection = null;
    }

    this.isConnected = false;
    this.emit('disconnected');
  }

  /**
   * Send a chat message to an agent
   */
  async sendChatMessage(
    agentType: string,
    message: string,
    messageType: string = 'user_message'
  ): Promise<string | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/chat/stream/${agentType}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          user_id: this.options.userId,
          session_id: this.options.sessionId,
          message_type: messageType
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.session_id;
    } catch (error) {
      this.log('Error sending chat message:', error);
      this.emit('error', error);
      return null;
    }
  }

  /**
   * Send a system notification
   */
  async sendNotification(
    message: string,
    level: string = 'info',
    data?: Record<string, any>
  ): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/events/notify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          level,
          user_id: this.options.userId,
          data
        })
      });

      return response.ok;
    } catch (error) {
      this.log('Error sending notification:', error);
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Update agent status
   */
  async updateAgentStatus(
    agentId: string,
    status: string,
    additionalData?: Record<string, any>
  ): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/events/agent-status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_id: agentId,
          status,
          user_id: this.options.userId,
          additional_data: additionalData
        })
      });

      return response.ok;
    } catch (error) {
      this.log('Error updating agent status:', error);
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Update task progress
   */
  async updateTaskProgress(
    taskId: string,
    progress: number,
    agentId?: string,
    message?: string
  ): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/events/task-progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: taskId,
          progress,
          agent_id: agentId,
          user_id: this.options.userId,
          message
        })
      });

      return response.ok;
    } catch (error) {
      this.log('Error updating task progress:', error);
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Get connection status
   */
  getStatus(): {
    isConnected: boolean;
    isConnecting: boolean;
    connectionMode: ConnectionMode;
    connection?: StreamingConnection;
    pollingSession?: PollingSession;
    retryCount: number;
  } {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      connectionMode: this.connectionMode,
      connection: this.connection || undefined,
      pollingSession: this.pollingSession || undefined,
      retryCount: this.retryCount
    };
  }

  /**
   * Get buffered events
   */
  getBufferedEvents(maxEvents: number = 50): StreamingEvent[] {
    return this.eventBuffer.slice(-maxEvents);
  }

  /**
   * Clear event buffer
   */
  clearEventBuffer(): void {
    this.eventBuffer = [];
  }

  // Private methods

  private async connectSSE(): Promise<boolean> {
    try {
      // Create connection
      const connectionData = await this.createConnection();

      if (!connectionData.success) {
        throw new Error('Failed to create streaming connection');
      }

      // Create connection object
      this.connection = {
        id: connectionData.clientId,
        userId: this.options.userId,
        sessionId: connectionData.sessionId,
        eventTypes: this.options.eventTypes,
        filters: this.options.filters,
        isActive: true,
        createdAt: new Date(),
        lastActivity: new Date()
      };

      // Create EventSource
      const eventUrl = `${this.baseUrl}${connectionData.endpoint}?with_history=true&history_count=50`;
      this.eventSource = new EventSource(eventUrl);

      // Set up event handlers
      this.eventSource.addEventListener('message', this.handleSSEMessage);
      this.eventSource.addEventListener('error', this.handleSSEError);
      this.eventSource.addEventListener('open', this.handleSSEOpen);
      this.eventSource.addEventListener('close', this.handleSSEClose);

      // Set up specific event type handlers
      this.options.eventTypes.forEach(eventType => {
        this.eventSource!.addEventListener(eventType, (event: any) => {
          try {
            const data = JSON.parse(event.data);
            this.processStreamingEvent(data);
          } catch (error) {
            this.log('Error parsing SSE event:', error);
          }
        });
      });

      this.log('SSE connection established');
      return true;

    } catch (error) {
      this.log('SSE connection failed:', error);
      return false;
    }
  }

  private async connectPolling(): Promise<boolean> {
    try {
      // Create polling session
      const sessionData = await this.createPollingSession();

      if (!sessionData.success) {
        throw new Error('Failed to create polling session');
      }

      // Create session object
      this.pollingSession = {
        id: sessionData.session_id,
        userId: this.options.userId,
        filters: this.options.filters,
        createdAt: new Date(),
        lastActivity: new Date(),
        isActive: true,
        eventsSent: []
      };

      // Start polling
      this.startPolling();

      this.log('Polling connection established');
      return true;

    } catch (error) {
      this.log('Polling connection failed:', error);
      return false;
    }
  }

  private async createConnection(): Promise<CreateConnectionResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/streaming/connect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: this.options.userId,
        session_id: this.options.sessionId,
        event_types: this.options.eventTypes,
        filters: this.options.filters
      })
    });

    return response.json();
  }

  private async createPollingSession(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/streaming/polling/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: this.options.userId,
        event_types: this.options.eventTypes,
        filters: this.options.filters
      })
    });

    return response.json();
  }

  private async pollForEvents(): Promise<void> {
    if (!this.pollingSession || !this.pollingSession.isActive) {
      return;
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/polling/poll`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.pollingSession.id,
          timeout: this.options.pollingTimeout / 1000,
          max_events: 50
        })
      });

      if (response.ok) {
        const data: PollingResponse = await response.json();

        if (data.success && data.events) {
          data.events.forEach(event => {
            this.processStreamingEvent(event);
            this.pollingSession!.eventsSent.push(event.id);
          });

          this.pollingSession.lastActivity = new Date();
        }
      }

    } catch (error) {
      this.log('Polling error:', error);
      this.emit('error', error);
    }

    // Schedule next poll
    if (this.pollingSession && this.pollingSession.isActive) {
      this.pollingTimer = setTimeout(() => {
        this.pollForEvents();
      }, this.options.pollingInterval);
    }
  }

  private startPolling(): void {
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
    }

    this.pollForEvents();
  }

  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        // Update last activity
        if (this.connection) {
          this.connection.lastActivity = new Date();
        }
        if (this.pollingSession) {
          this.pollingSession.lastActivity = new Date();
        }
      }
    }, this.options.heartbeatInterval);
  }

  private handleSSEOpen(event: Event): void {
    this.log('SSE connection opened');
    this.connectionMode = ConnectionMode.SSE;
  }

  private handleSSEMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      this.processStreamingEvent(data);
    } catch (error) {
      this.log('Error parsing SSE message:', error);
    }
  }

  private handleSSEError(event: Event): void {
    this.log('SSE error:', event);

    if (this.shouldReconnect && this.isConnected) {
      this.handleReconnect();
    }
  }

  private handleSSEClose(event: Event): void {
    this.log('SSE connection closed');

    if (this.shouldReconnect && this.isConnected) {
      this.handleReconnect();
    }
  }

  private handleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.retryCount++;
    this.isConnected = false;
    this.emit('disconnected');

    if (this.retryCount <= this.options.maxRetries) {
      this.log(`Reconnecting attempt ${this.retryCount}/${this.options.maxRetries}`);

      this.reconnectTimer = setTimeout(async () => {
        try {
          await this.connect();
        } catch (error) {
          this.log('Reconnection failed:', error);
        }
      }, this.options.reconnectDelay * this.retryCount);
    } else {
      this.log('Max reconnection attempts reached');
      this.emit('error', new Error('Max reconnection attempts reached'));
    }
  }

  private processStreamingEvent(event: StreamingEvent): void {
    // Update last event ID
    this.lastEventId = event.id;

    // Add to buffer
    this.eventBuffer.push(event);
    if (this.eventBuffer.length > this.maxEventBufferSize) {
      this.eventBuffer.shift();
    }

    // Emit specific events based on type
    switch (event.type) {
      case EventType.AGENT_STATUS_UPDATE:
        this.emit('agentStatus', event.data);
        break;
      case EventType.TASK_PROGRESS:
        this.emit('taskProgress', event.data);
        break;
      case EventType.TASK_COMPLETED:
        this.emit('taskCompleted', event.data);
        break;
      case EventType.TASK_FAILED:
        this.emit('taskFailed', event.data);
        break;
      case EventType.SYSTEM_NOTIFICATION:
        this.emit('notification', event.data);
        break;
      case EventType.CHAT_MESSAGE:
        this.emit('chatMessage', event.data);
        break;
      case EventType.HEALTH_CHECK:
        this.emit('heartbeat', event.data);
        break;
      case EventType.ERROR:
        this.emit('streamingError', event.data);
        break;
      default:
        this.emit('event', event);
        break;
    }

    // Emit generic event
    this.emit('streamingEvent', event);
  }

  private async removeConnection(clientId: string): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/api/v1/streaming/connect/${clientId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      this.log('Error removing connection:', error);
    }
  }

  private async removePollingSession(sessionId: string): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/api/v1/streaming/polling/session/${sessionId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      this.log('Error removing polling session:', error);
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private log(...args: any[]): void {
    if (this.options.enableLogging) {
      console.log('[HTTPStreamingClient]', ...args);
    }
  }

  /**
   * Get streaming service statistics
   */
  async getStats(): Promise<Record<string, any> | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/status`);

      if (response.ok) {
        return response.json();
      }
    } catch (error) {
      this.log('Error getting stats:', error);
    }

    return null;
  }

  /**
   * Health check for the streaming service
   */
  async healthCheck(): Promise<Record<string, any> | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/streaming/health`);

      if (response.ok) {
        return response.json();
      }
    } catch (error) {
      this.log('Health check failed:', error);
    }

    return null;
  }
}

export default HTTPStreamingClient;