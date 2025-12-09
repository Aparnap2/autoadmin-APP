/**
 * HTTP Polling Client for E2E Testing
 * Simulates frontend HTTP polling behavior for testing backend integration
 */

export interface PollingSession {
  session_id: string;
  user_id: string;
  interval: string;
  filters: Record<string, any>;
  created_at: string;
  last_activity: string;
}

export interface PollingEvent {
  event_id: string;
  event_type: string;
  data: Record<string, any>;
  timestamp: string;
  user_id: string;
  priority?: number;
  agent_id?: string;
  task_id?: string;
}

export interface PollingOptions {
  timeout?: number;
  max_events?: number;
  since?: string;
  filters?: Record<string, any>;
}

export class HTTPPollingClient {
  private baseURL: string;
  private sessions: Map<string, PollingSession> = new Map();
  private isConnected: boolean = false;

  constructor(baseURL: string) {
    this.baseURL = baseURL.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Create a new polling session
   */
  async createSession(config: {
    user_id: string;
    interval?: string;
    filters?: Record<string, any>;
    max_events?: number;
    timeout?: number;
  }): Promise<PollingSession> {
    const response = await fetch(`${this.baseURL}/api/http-polling/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Client': 'playwright-http-polling'
      },
      body: JSON.stringify({
        user_id: config.user_id,
        interval: config.interval || 'NORMAL',
        filters: config.filters || {},
        max_events: config.max_events || 50,
        timeout: config.timeout || 30000
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
    }

    const session: PollingSession = await response.json();
    this.sessions.set(session.session_id, session);
    return session;
  }

  /**
   * Get session information
   */
  async getSession(sessionId: string): Promise<PollingSession | null> {
    if (this.sessions.has(sessionId)) {
      return this.sessions.get(sessionId)!;
    }

    const response = await fetch(`${this.baseURL}/api/http-polling/sessions/${sessionId}`, {
      headers: {
        'X-Test-Client': 'playwright-http-polling'
      }
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.status} ${response.statusText}`);
    }

    const session: PollingSession = await response.json();
    this.sessions.set(sessionId, session);
    return session;
  }

  /**
   * Update session configuration
   */
  async updateSession(sessionId: string, updates: {
    interval?: string;
    filters?: Record<string, any>;
    max_events?: number;
  }): Promise<boolean> {
    const response = await fetch(`${this.baseURL}/api/http-polling/sessions/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Client': 'playwright-http-polling'
      },
      body: JSON.stringify(updates)
    });

    if (!response.ok) {
      throw new Error(`Failed to update session: ${response.status} ${response.statusText}`);
    }

    // Update local session cache
    if (this.sessions.has(sessionId)) {
      const session = this.sessions.get(sessionId)!;
      Object.assign(session, updates);
    }

    return true;
  }

  /**
   * Poll for events from a session
   */
  async pollEvents(sessionId: string, options: PollingOptions = {}): Promise<PollingEvent[]> {
    const params = new URLSearchParams();

    if (options.timeout) {
      params.append('timeout', options.timeout.toString());
    }
    if (options.max_events) {
      params.append('max_events', options.max_events.toString());
    }
    if (options.since) {
      params.append('since', options.since);
    }

    const response = await fetch(
      `${this.baseURL}/api/http-polling/sessions/${sessionId}/poll?${params}`,
      {
        headers: {
          'X-Test-Client': 'playwright-http-polling'
        }
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to poll events: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();

    if (result.success) {
      return result.events || [];
    }

    return [];
  }

  /**
   * Add a test event
   */
  async addEvent(eventData: {
    event_type: string;
    data: Record<string, any>;
    user_id: string;
    priority?: number;
    agent_id?: string;
    task_id?: string;
    expires_in?: number;
  }): Promise<string> {
    const response = await fetch(`${this.baseURL}/api/http-polling/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Client': 'playwright-http-polling'
      },
      body: JSON.stringify(eventData)
    });

    if (!response.ok) {
      throw new Error(`Failed to add event: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    return result.event_id;
  }

  /**
   * Add agent status event
   */
  async addAgentStatusEvent(data: {
    agent_id: string;
    status: string;
    user_id: string;
    additional_data?: Record<string, any>;
  }): Promise<string> {
    return this.addEvent({
      event_type: 'agent_status_update',
      data: {
        status: data.status,
        ...data.additional_data
      },
      user_id: data.user_id,
      agent_id: data.agent_id,
      priority: 3
    });
  }

  /**
   * Add task progress event
   */
  async addTaskProgressEvent(data: {
    task_id: string;
    progress: number;
    message?: string;
    agent_id?: string;
    user_id: string;
  }): Promise<string> {
    return this.addEvent({
      event_type: 'task_progress',
      data: {
        progress: data.progress,
        message: data.message
      },
      user_id: data.user_id,
      task_id: data.task_id,
      agent_id: data.agent_id,
      priority: 4
    });
  }

  /**
   * Add system notification event
   */
  async addSystemNotificationEvent(data: {
    message: string;
    level: 'info' | 'warning' | 'error' | 'success';
    user_id: string;
  }): Promise<string> {
    return this.addEvent({
      event_type: 'system_notification',
      data: {
        message: data.message,
        level: data.level
      },
      user_id: data.user_id,
      priority: data.level === 'error' ? 5 : 2
    });
  }

  /**
   * Add error event
   */
  async addErrorEvent(data: {
    error: string;
    error_type?: string;
    user_id: string;
    context?: Record<string, any>;
    priority?: number;
  }): Promise<string> {
    return this.addEvent({
      event_type: 'system_error',
      data: {
        error: data.error,
        error_type: data.error_type || 'general_error',
        ...data.context
      },
      user_id: data.user_id,
      priority: data.priority || 5
    });
  }

  /**
   * Remove a polling session
   */
  async removeSession(sessionId: string): Promise<boolean> {
    const response = await fetch(`${this.baseURL}/api/http-polling/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'X-Test-Client': 'playwright-http-polling'
      }
    });

    if (response.status === 404) {
      return false;
    }

    if (!response.ok) {
      throw new Error(`Failed to remove session: ${response.status} ${response.statusText}`);
    }

    this.sessions.delete(sessionId);
    return true;
  }

  /**
   * Get service health status
   */
  async getHealth(): Promise<any> {
    const response = await fetch(`${this.baseURL}/api/http-polling/health`, {
      headers: {
        'X-Test-Client': 'playwright-http-polling'
      }
    });

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get service metrics
   */
  async getMetrics(): Promise<any> {
    const response = await fetch(`${this.baseURL}/api/http-polling/metrics`, {
      headers: {
        'X-Test-Client': 'playwright-http-polling'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get session metrics
   */
  async getSessionMetrics(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseURL}/api/http-polling/sessions/${sessionId}/metrics`, {
      headers: {
        'X-Test-Client': 'playwright-http-polling'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get session metrics: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Continuous polling with callback
   */
  async startContinuousPolling(
    sessionId: string,
    onEvent: (event: PollingEvent) => void,
    options: {
      interval?: number;
      maxEvents?: number;
      timeout?: number;
      onError?: (error: Error) => void;
    } = {}
  ): Promise<() => void> {
    const interval = options.interval || 1000;
    const maxEvents = options.maxEvents || 10;
    const timeout = options.timeout || 30000;

    let isActive = true;
    let eventCount = 0;

    const poll = async () => {
      while (isActive && eventCount < maxEvents) {
        try {
          const events = await this.pollEvents(sessionId, {
            timeout: Math.min(timeout, 5000),
            max_events: 1
          });

          for (const event of events) {
            if (isActive) {
              onEvent(event);
              eventCount++;
            }
          }

          // Wait before next poll
          if (isActive && eventCount < maxEvents) {
            await new Promise(resolve => setTimeout(resolve, interval));
          }
        } catch (error) {
          if (isActive && options.onError) {
            options.onError(error as Error);
          }
          break;
        }
      }
    };

    // Start polling
    poll();

    // Return stop function
    return () => {
      isActive = false;
    };
  }

  /**
   * Poll until specific condition is met
   */
  async pollUntil(
    sessionId: string,
    condition: (events: PollingEvent[]) => boolean,
    options: {
      timeout?: number;
      interval?: number;
      maxPolls?: number;
    } = {}
  ): Promise<PollingEvent[]> {
    const timeout = options.timeout || 30000;
    const interval = options.interval || 1000;
    const maxPolls = options.maxPolls || 30;

    const startTime = Date.now();
    let pollCount = 0;

    while (pollCount < maxPolls && Date.now() - startTime < timeout) {
      try {
        const events = await this.pollEvents(sessionId, {
          timeout: Math.min(interval * 0.8, 5000),
          max_events: 20
        });

        if (condition(events)) {
          return events;
        }

        pollCount++;
        await new Promise(resolve => setTimeout(resolve, interval));
      } catch (error) {
        // Log error but continue polling
        console.warn('Poll error:', error);
        pollCount++;
        await new Promise(resolve => setTimeout(resolve, interval));
      }
    }

    throw new Error(`Polling condition not met within ${timeout}ms or ${maxPolls} polls`);
  }

  /**
   * Get all active sessions
   */
  getActiveSessions(): PollingSession[] {
    return Array.from(this.sessions.values());
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    const sessionIds = Array.from(this.sessions.keys());

    // Remove all sessions
    await Promise.all(
      sessionIds.map(sessionId => this.removeSession(sessionId).catch(() => {}))
    );

    this.sessions.clear();
    this.isConnected = false;
  }

  /**
   * Test connection to polling service
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.getHealth();
      this.isConnected = true;
      return true;
    } catch (error) {
      this.isConnected = false;
      return false;
    }
  }
}