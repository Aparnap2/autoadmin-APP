/**
 * Comprehensive HTTP Polling Client for AutoAdmin Frontend
 * Provides seamless fallback from Server-Sent Events to HTTP polling
 * Includes event buffering, connection management, and performance monitoring
 */

import { EventEmitter } from 'events';

// Types
export interface PollingInterval {
  VERY_FAST: 5;    // 5 seconds - high priority tasks
  FAST: 15;        // 15 seconds - active tasks
  NORMAL: 30;      // 30 seconds - normal operation
  SLOW: 60;        // 60 seconds - background monitoring
  VERY_SLOW: 300; // 5 minutes - minimal monitoring
}

export interface ConnectionStatus {
  CONNECTING: 'connecting';
  CONNECTED: 'connected';
  DISCONNECTED: 'disconnected';
  ERROR: 'error';
  TIMEOUT: 'timeout';
  RECONNECTING: 'reconnecting';
}

export interface EventPriority {
  LOW: 1;
  MEDIUM: 2;
  HIGH: 3;
  CRITICAL: 4;
  URGENT: 5;
}

export interface ErrorType {
  NETWORK_ERROR: 'network_error';
  TIMEOUT_ERROR: 'timeout_error';
  AUTHENTICATION_ERROR: 'authentication_error';
  RATE_LIMIT_ERROR: 'rate_limit_error';
  SERVER_ERROR: 'server_error';
  CLIENT_ERROR: 'client_error';
  UNKNOWN_ERROR: 'unknown_error';
}

export interface PollingEvent {
  id: string;
  type: string;
  data: Record<string, any>;
  priority: number;
  timestamp: string;
  expires_at?: string;
  user_id?: string;
  session_id?: string;
  agent_id?: string;
  task_id?: string;
  retry_count: number;
  max_retries: number;
}

export interface PollingSession {
  id: string;
  user_id?: string;
  created_at: string;
  last_activity: string;
  interval: string;
  status: string;
  filters: Record<string, any>;
  is_active: boolean;
  delivered_events: string[];
  event_buffer: any[];
  metrics: PollingMetrics;
  backoff_factor: number;
  max_backoff: number;
  error_count: number;
  consecutive_errors: number;
}

export interface PollingMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  timeouts: number;
  avg_response_time: number;
  last_request_time?: string;
  last_success_time?: string;
  connection_drops: number;
  reconnections: number;
}

export interface EventBuffer {
  max_size: number;
  max_age: number;
  events: Record<string, PollingEvent>;
  priority_queues: Record<number, string[]>;
}

export interface ServiceMetrics {
  total_sessions: number;
  active_sessions: number;
  buffered_events: number;
  buffer_stats: EventBuffer;
  background_tasks: number;
  max_sessions: number;
  session_timeout: number;
}

export interface PerformanceMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  timeouts: number;
  overall_success_rate: number;
  overall_avg_response_time: number;
  connection_drops: number;
  reconnections: number;
}

export interface ErrorMetrics {
  sessions_by_status: Record<string, number>;
  total_consecutive_errors: number;
  error_rate: number;
}

export interface ConnectionHealth {
  status: string;
  connected_agents: number;
  error_sessions: number;
  timeout_sessions: number;
  reconnecting_sessions: number;
  avg_success_rate: number;
  buffer_stats: EventBuffer;
  timestamp: string;
}

export interface FallbackConfig {
  enable_sse: boolean;
  enable_polling: boolean;
  auto_fallback: boolean;
  fallback_threshold: number; // failed SSE attempts before fallback
  sse_timeout: number; // SSE connection timeout
  polling_intervals: PollingInterval;
  max_retries: number;
  retry_delays: number[];
}

export interface ClientConfig {
  base_url: string;
  user_id?: string;
  session_id?: string;
  fallback_config: FallbackConfig;
  event_types: string[];
  filters: Record<string, any>;
  max_buffer_size: number;
  enable_metrics: boolean;
  enable_logging: boolean;
  connection_timeout: number;
  heartbeat_interval: number;
  cleanup_interval: number;
}

export interface ConnectionState {
  mode: 'sse' | 'polling' | 'hybrid';
  status: ConnectionStatus[keyof ConnectionStatus];
  session_id?: string;
  last_activity: Date;
  metrics: {
    requests_count: number;
    success_count: number;
    error_count: number;
    avg_response_time: number;
    last_successful_request?: Date;
  };
  retry_count: number;
  consecutive_errors: number;
  backoff_factor: number;
}

export interface PollingClientOptions extends Partial<ClientConfig> {
  // Extensible for additional options
}

export interface PollingResponse {
  success: boolean;
  events: PollingEvent[];
  session_id: string;
  immediate?: boolean;
  timeout?: boolean;
  waited_seconds?: number;
  status?: string;
  metrics?: PollingMetrics;
  error?: string;
}

export interface ErrorResponse {
  success: false;
  error: string;
  details?: any;
  code?: string;
  timestamp: string;
}

// Constants
export const POLLING_INTERVALS: PollingInterval = {
  VERY_FAST: 5,
  FAST: 15,
  NORMAL: 30,
  SLOW: 60,
  VERY_SLOW: 300
};

export const CONNECTION_STATUS: ConnectionStatus = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  TIMEOUT: 'timeout',
  RECONNECTING: 'reconnecting'
};

export const EVENT_PRIORITY: EventPriority = {
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
  URGENT: 5
};

export const ERROR_TYPES: ErrorType = {
  NETWORK_ERROR: 'network_error',
  TIMEOUT_ERROR: 'timeout_error',
  AUTHENTICATION_ERROR: 'authentication_error',
  RATE_LIMIT_ERROR: 'rate_limit_error',
  SERVER_ERROR: 'server_error',
  CLIENT_ERROR: 'client_error',
  UNKNOWN_ERROR: 'unknown_error'
};

/**
 * Comprehensive HTTP Polling Client
 * Provides reliable real-time communication with automatic fallback
 */
export class HTTPPollingClient extends EventEmitter {
  private config: ClientConfig;
  private connection: ConnectionState;
  private eventBuffer: Map<string, PollingEvent> = new Map();
  private eventBufferArray: PollingEvent[] = [];
  private pollingTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private cleanupTimer: NodeJS.Timeout | null = null;
  private eventSource: EventSource | null = null;
  private isDestroyed = false;
  private retryDelays: number[] = [1000, 2000, 5000, 10000, 30000]; // Exponential backoff

  constructor(options: PollingClientOptions = {}) {
    super();

    // Default configuration
    this.config = {
      base_url: options.base_url || process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
      user_id: options.user_id,
      session_id: options.session_id || this.generateSessionId(),
      fallback_config: {
        enable_sse: options.fallback_config?.enable_sse ?? true,
        enable_polling: options.fallback_config?.enable_polling ?? true,
        auto_fallback: options.fallback_config?.auto_fallback ?? true,
        fallback_threshold: options.fallback_config?.fallback_threshold ?? 3,
        sse_timeout: options.fallback_config?.sse_timeout ?? 30000,
        polling_intervals: options.fallback_config?.polling_intervals || POLLING_INTERVALS,
        max_retries: options.fallback_config?.max_retries ?? 5,
        retry_delays: options.fallback_config?.retry_delays || this.retryDelays
      },
      event_types: options.event_types || [
        'agent_status_update',
        'task_progress',
        'task_completed',
        'task_failed',
        'system_notification',
        'chat_message',
        'health_check',
        'error'
      ],
      filters: options.filters || {},
      max_buffer_size: options.max_buffer_size || 10000,
      enable_metrics: options.enable_metrics ?? true,
      enable_logging: options.enable_logging ?? false,
      connection_timeout: options.connection_timeout || 30000,
      heartbeat_interval: options.heartbeat_interval || 30000,
      cleanup_interval: options.cleanup_interval || 300000 // 5 minutes
    };

    // Initialize connection state
    this.connection = {
      mode: 'hybrid',
      status: 'DISCONNECTED',
      last_activity: new Date(),
      metrics: {
        requests_count: 0,
        success_count: 0,
        error_count: 0,
        avg_response_time: 0
      },
      retry_count: 0,
      consecutive_errors: 0,
      backoff_factor: 1.0
    };

    // Bind methods to maintain context
    this.handleSSEMessage = this.handleSSEMessage.bind(this);
    this.handleSSEError = this.handleSSEError.bind(this);
    this.handleSSEOpen = this.handleSSEOpen.bind(this);
    this.handleSSEClose = this.handleSSEClose.bind(this);

    this.log('HTTP Polling Client initialized', this.config);
  }

  /**
   * Connect to the polling service with automatic fallback
   */
  async connect(): Promise<boolean> {
    try {
      if (this.connection.status !== 'DISCONNECTED') {
        this.log('Already connected or connecting');
        return true;
      }

      this.connection.status = 'CONNECTING';
      this.emit('connecting', this.getConnectionState());

      // Try SSE first if enabled
      if (this.config.fallback_config.enable_sse) {
        const sseConnected = await this.connectSSE();
        if (sseConnected) {
          this.connection.mode = 'sse';
          this.connection.status = 'CONNECTED';
          this.startHeartbeat();
          this.startCleanup();
          this.emit('connected', this.getConnectionState());
          this.log('Connected via SSE');
          return true;
        } else if (this.config.fallback_config.auto_fallback && this.config.fallback_config.enable_polling) {
          this.log('SSE failed, falling back to HTTP polling');
          const pollingConnected = await this.connectPolling();
          if (pollingConnected) {
            this.connection.mode = 'polling';
            this.connection.status = 'CONNECTED';
            this.startHeartbeat();
            this.startCleanup();
            this.emit('connected', this.getConnectionState());
            this.log('Connected via HTTP polling fallback');
            return true;
          }
        }
      } else if (this.config.fallback_config.enable_polling) {
        // Direct to polling if SSE is disabled
        const pollingConnected = await this.connectPolling();
        if (pollingConnected) {
          this.connection.mode = 'polling';
          this.connection.status = 'CONNECTED';
          this.startHeartbeat();
          this.startCleanup();
          this.emit('connected', this.getConnectionState());
          this.log('Connected via HTTP polling');
          return true;
        }
      }

      this.connection.status = 'ERROR';
      this.emit('error', new Error('Failed to establish connection'));
      return false;

    } catch (error) {
      this.connection.status = 'ERROR';
      this.log('Connection error:', error);
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Disconnect from the polling service
   */
  async disconnect(): Promise<void> {
    this.log('Disconnecting...');

    // Clear timers
    this.stopTimers();

    // Close SSE connection
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    // Cleanup polling session
    if (this.connection.session_id) {
      try {
        await this.removePollingSession(this.connection.session_id);
      } catch (error) {
        this.log('Error removing polling session:', error);
      }
    }

    this.connection.status = 'DISCONNECTED';
    this.connection.session_id = undefined;
    this.emit('disconnected', this.getConnectionState());
    this.log('Disconnected');
  }

  /**
   * Create a polling session
   */
  async createPollingSession(interval: keyof PollingInterval = 'NORMAL'): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.config.user_id,
          interval: interval,
          event_types: this.config.event_types,
          filters: this.config.filters,
          max_buffer_size: this.config.max_buffer_size
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.connection.session_id = data.session_id;
          this.log('Polling session created:', data.session_id);
          return true;
        }
      }
      return false;

    } catch (error) {
      this.log('Error creating polling session:', error);
      return false;
    }
  }

  /**
   * Poll for events
   */
  async pollForEvents(timeout?: number, max_events = 50): Promise<PollingResponse> {
    if (!this.connection.session_id || this.connection.status !== 'CONNECTED') {
      return {
        success: false,
        error: 'Not connected',
        events: []
      };
    }

    try {
      const startTime = Date.now();

      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/poll`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.connection.session_id,
          timeout: timeout || this.config.fallback_config.polling_intervals.NORMAL,
          max_events: max_events,
          include_metrics: this.config.enable_metrics
        })
      });

      const responseTime = Date.now() - startTime;
      this.updateConnectionMetrics(response.ok, responseTime);

      if (response.ok) {
        const data: PollingResponse = await response.json();

        if (data.success && data.events) {
          // Process events
          data.events.forEach(event => this.processEvent(event));

          // Update connection state
          this.connection.last_activity = new Date();
          this.connection.consecutive_errors = 0;
          this.connection.backoff_factor = Math.max(1.0, this.connection.backoff_factor * 0.8);

          // Include connection state in response
          data.events.forEach(event => {
            event.data.connection_state = this.getConnectionState();
          });

          return data;
        }
      }

      throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    } catch (error) {
      this.updateConnectionMetrics(false, 0);
      this.connection.consecutive_errors++;
      this.connection.backoff_factor = Math.min(
        this.connection.backoff_factor * 1.5,
        60.0 // Max backoff of 60 seconds
      );

      this.log('Polling error:', error);
      this.emit('polling_error', error);

      // Consider reconnection if too many errors
      if (this.connection.consecutive_errors >= this.config.fallback_config.fallback_threshold) {
        this.handleReconnection();
      }

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown polling error',
        events: []
      };
    }
  }

  /**
   * Send a chat message to an agent
   */
  async sendChatMessage(
    agent_type: string,
    message: string,
    message_type: string = 'user_message'
  ): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/streaming/chat/stream/${agent_type}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          user_id: this.config.user_id,
          session_id: this.connection.session_id,
          message_type
        })
      });

      return response.ok;

    } catch (error) {
      this.log('Error sending chat message:', error);
      this.emit('error', error);
      return false;
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
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/events/system-notification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          level,
          user_id: this.config.user_id,
          data,
          priority: 'LOW'
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
    agent_id: string,
    status: string,
    additional_data?: Record<string, any>
  ): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/events/agent-status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_id,
          status,
          user_id: this.config.user_id,
          additional_data,
          priority: 'MEDIUM'
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
    task_id: string,
    progress: number,
    agent_id?: string,
    message?: string
  ): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/events/task-progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id,
          progress,
          agent_id,
          user_id: this.config.user_id,
          message,
          priority: 'MEDIUM'
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
   * Get buffered events
   */
  getBufferedEvents(max_events: number = 100): PollingEvent[] {
    return this.eventBufferArray.slice(-max_events);
  }

  /**
   * Get connection state
   */
  getConnectionState(): ConnectionState {
    return {
      ...this.connection,
      session_id: this.connection.session_id,
      last_successful_request: this.connection.metrics.last_successful_request
        ? new Date(this.connection.metrics.last_successful_request)
        : undefined
    };
  }

  /**
   * Get service metrics
   */
  async getServiceMetrics(): Promise<{
    service: ServiceMetrics;
    performance: PerformanceMetrics;
    errors: ErrorMetrics;
  } | null> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/metrics`);

      if (response.ok) {
        return await response.json();
      }
      return null;

    } catch (error) {
      this.log('Error getting service metrics:', error);
      return null;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<ConnectionHealth | null> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/health`);

      if (response.ok) {
        const health: ConnectionHealth = await response.json();
        health.timestamp = new Date().toISOString();
        return health;
      }
      return null;

    } catch (error) {
      this.log('Health check failed:', error);
      return null;
    }
  }

  /**
   * Destroy the client and cleanup resources
   */
  async destroy(): Promise<void> {
    this.isDestroyed = true;
    await this.disconnect();
    this.eventBuffer.clear();
    this.eventBufferArray = [];
    this.removeAllListeners();
    this.log('HTTP Polling Client destroyed');
  }

  // Private methods

  private async connectSSE(): Promise<boolean> {
    try {
      const eventUrl = `${this.config.base_url}/api/v1/streaming/connect?with_history=true&history_count=50`;

      const response = await this.fetchWithTimeout(`${this.config.base_url}/api/v1/streaming/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: this.config.user_id,
          session_id: this.config.session_id,
          event_types: this.config.event_types,
          filters: this.config.filters
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success) {
        this.connection.session_id = data.session_id;

        // Create EventSource
        this.eventSource = new EventSource(`${eventUrl}&session_id=${data.session_id}`);

        // Setup event handlers
        this.eventSource.addEventListener('message', this.handleSSEMessage);
        this.eventSource.addEventListener('error', this.handleSSEError);
        this.eventSource.addEventListener('open', this.handleSSEOpen);
        this.eventSource.addEventListener('close', this.handleSSEClose);

        return true;
      }
      return false;

    } catch (error) {
      this.log('SSE connection failed:', error);
      return false;
    }
  }

  private async connectPolling(): Promise<boolean> {
    try {
      // Create polling session first
      const sessionCreated = await this.createPollingSession('NORMAL');
      if (!sessionCreated) {
        return false;
      }

      // Start polling
      this.startPolling();
      return true;

    } catch (error) {
      this.log('Polling connection failed:', error);
      return false;
    }
  }

  private startPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
    }

    const effectiveInterval = this.config.fallback_config.polling_intervals.NORMAL * this.connection.backoff_factor;

    this.pollingTimer = setInterval(async () => {
      if (this.connection.status === 'CONNECTED' && this.connection.mode === 'polling') {
        await this.pollForEvents();
      }
    }, effectiveInterval * 1000);

    // Immediate first poll
    this.pollForEvents();
  }

  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    this.heartbeatTimer = setInterval(async () => {
      if (this.connection.status === 'CONNECTED' && this.connection.session_id) {
        try {
          await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/agent/${this.connection.session_id}/heartbeat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              timestamp: new Date().toISOString(),
              connection_state: this.getConnectionState()
            })
          });
        } catch (error) {
          this.log('Heartbeat failed:', error);
        }
      }
    }, this.config.heartbeat_interval);
  }

  private startCleanup(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
    }

    this.cleanupTimer = setInterval(() => {
      this.cleanupExpiredEvents();
    }, this.config.cleanup_interval);
  }

  private stopTimers(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
  }

  private handleReconnection(): void {
    if (this.connection.retry_count >= this.config.fallback_config.max_retries) {
      this.log('Max reconnection attempts reached');
      this.emit('error', new Error('Max reconnection attempts reached'));
      return;
    }

    this.connection.status = 'RECONNECTING';
    this.emit('reconnecting', this.getConnectionState());

    const retryDelay = this.config.fallback_config.retry_delays[
      Math.min(this.connection.retry_count, this.config.fallback_config.retry_delays.length - 1)
    ];

    this.log(`Reconnection attempt ${this.connection.retry_count + 1}/${this.config.fallback_config.max_retries} in ${retryDelay}ms`);

    setTimeout(async () => {
      this.connection.retry_count++;
      try {
        await this.disconnect();
        await this.connect();
      } catch (error) {
        this.log('Reconnection failed:', error);
        this.handleReconnection(); // Try again
      }
    }, retryDelay);
  }

  private processEvent(event: PollingEvent): void {
    // Add to buffer
    this.eventBuffer.set(event.id, event);
    this.eventBufferArray.push(event);

    // Limit buffer size
    if (this.eventBufferArray.length > this.config.max_buffer_size) {
      const removedEvent = this.eventBufferArray.shift();
      if (removedEvent) {
        this.eventBuffer.delete(removedEvent.id);
      }
    }

    // Emit specific events based on type
    switch (event.type) {
      case 'agent_status_update':
        this.emit('agent_status', event.data);
        break;
      case 'task_progress':
        this.emit('task_progress', event.data);
        break;
      case 'task_completed':
        this.emit('task_completed', event.data);
        break;
      case 'task_failed':
        this.emit('task_failed', event.data);
        break;
      case 'system_notification':
        this.emit('notification', event.data);
        break;
      case 'chat_message':
        this.emit('chat_message', event.data);
        break;
      case 'health_check':
        this.emit('heartbeat', event.data);
        break;
      case 'error':
        this.emit('error', event.data);
        break;
      default:
        this.emit('event', event);
        break;
    }

    // Emit generic event
    this.emit('polling_event', event);
  }

  private updateConnectionMetrics(success: boolean, responseTime: number): void {
    this.connection.metrics.requests_count++;
    this.connection.metrics.avg_response_time =
      (this.connection.metrics.avg_response_time * (this.connection.metrics.requests_count - 1) + responseTime) /
      this.connection.metrics.requests_count;

    if (success) {
      this.connection.metrics.success_count++;
      this.connection.metrics.last_successful_request = new Date();
    } else {
      this.connection.metrics.error_count++;
    }
  }

  private cleanupExpiredEvents(): void {
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - 24 * 60 * 60 * 1000); // 24 hours

    const expiredEvents: string[] = [];
    for (const [id, event] of this.eventBuffer) {
      const eventTime = new Date(event.timestamp);
      if (eventTime < cutoffTime) {
        expiredEvents.push(id);
      }
    }

    expiredEvents.forEach(id => {
      this.eventBuffer.delete(id);
      const index = this.eventBufferArray.findIndex(e => e.id === id);
      if (index !== -1) {
        this.eventBufferArray.splice(index, 1);
      }
    });

    if (expiredEvents.length > 0) {
      this.log(`Cleaned up ${expiredEvents.length} expired events`);
    }
  }

  private async removePollingSession(sessionId: string): Promise<void> {
    try {
      await this.fetchWithTimeout(`${this.config.base_url}/api/v1/polling/session/${sessionId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      this.log('Error removing polling session:', error);
    }
  }

  private async fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.connection_timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private handleSSEMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      if (data.id) {
        this.processEvent(data);
      }
    } catch (error) {
      this.log('Error parsing SSE message:', error);
    }
  }

  private handleSSEError(event: Event): void {
    this.log('SSE error:', event);
    if (this.config.fallback_config.auto_fallback) {
      this.handleReconnection();
    }
  }

  private handleSSEOpen(event: Event): void {
    this.log('SSE connection opened');
  }

  private handleSSEClose(event: Event): void {
    this.log('SSE connection closed');
    if (this.config.fallback_config.auto_fallback && this.connection.status === 'CONNECTED') {
      this.handleReconnection();
    }
  }

  private log(...args: any[]): void {
    if (this.config.enable_logging) {
      console.log('[HTTPPollingClient]', ...args);
    }
  }
}

export default HTTPPollingClient;