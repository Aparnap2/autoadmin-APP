/**
 * Connection Manager Service
 * Manages API connection health, monitoring, and automatic recovery
 */

import FastAPIClient from './fastapi-client';
import { API_CONFIG } from './api-config';

export interface ConnectionHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency: number;
  lastCheck: Date;
  consecutiveFailures: number;
  uptime: number;
  issues: string[];
  circuitBreakerStatus: {
    state: string;
    failures: number;
  };
  realtimeConnection: boolean;
  metrics: {
    totalRequests: number;
    successRate: number;
    averageResponseTime: number;
  };
}

export interface ConnectionAlert {
  type: 'error' | 'warning' | 'info';
  message: string;
  timestamp: Date;
  details?: any;
}

export class ConnectionManager {
  private client: FastAPIClient;
  private healthCheckInterval: number;
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private status: ConnectionHealthStatus;
  private alerts: ConnectionAlert[] = [];
  private listeners: Map<string, (status: ConnectionHealthStatus) => void> = new Map();
  private startTime: Date;

  constructor(client: FastAPIClient, healthCheckInterval = 30000) {
    this.client = client;
    this.healthCheckInterval = healthCheckInterval;
    this.startTime = new Date();
    this.status = this.initializeStatus();
  }

  /**
   * Start health monitoring
   */
  start(): void {
    console.log('Starting connection health monitoring...');

    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
    }

    this.healthCheckTimer = setInterval(() => {
      this.performHealthCheck();
    }, this.healthCheckInterval);

    // Perform initial health check
    this.performHealthCheck();
  }

  /**
   * Stop health monitoring
   */
  stop(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
    console.log('Connection health monitoring stopped');
  }

  /**
   * Perform comprehensive health check
   */
  private async performHealthCheck(): Promise<void> {
    const startTime = Date.now();

    try {
      // Run client diagnostics
      const diagnostics = await this.client.runDiagnostics();
      const latency = Date.now() - startTime;

      // Get additional metrics
      const metrics = this.client.getMetrics();
      const uptime = Date.now() - this.startTime.getTime();

      // Determine health status
      const status = this.determineHealthStatus(diagnostics, metrics, latency, uptime);

      // Update status
      this.status = {
        ...status,
        latency,
        lastCheck: new Date(),
        uptime
      };

      // Check for issues and create alerts
      this.checkForIssues();

      // Notify listeners
      this.notifyListeners();

    } catch (error) {
      console.error('Health check failed:', error);
      this.handleError(error as Error);
    }
  }

  /**
   * Determine overall health status
   */
  private determineHealthStatus(
    diagnostics: any,
    metrics: any,
    latency: number,
    uptime: number
  ): Omit<ConnectionHealthStatus, 'latency' | 'lastCheck' | 'uptime'> {
    const issues: string[] = [];

    // Check connectivity
    if (!diagnostics.connectivity) {
      issues.push('API connectivity failed');
    }

    // Check latency
    if (latency > 5000) {
      issues.push('High latency detected');
    }

    // Check circuit breaker
    if (diagnostics.circuitBreaker.state !== 'CLOSED') {
      issues.push(`Circuit breaker is ${diagnostics.circuitBreaker.state}`);
    }

    // Check success rate
    const successRate = metrics.totalRequests > 0
      ? (metrics.successfulRequests / metrics.totalRequests) * 100
      : 100;

    if (successRate < 95) {
      issues.push(`Low success rate: ${successRate.toFixed(2)}%`);
    }

    // Check real-time connection
    if (!diagnostics.realtimeConnection) {
      issues.push('Real-time connection not available');
    }

    // Determine overall status
    let status: 'healthy' | 'degraded' | 'unhealthy';
    if (issues.length === 0) {
      status = 'healthy';
    } else if (issues.length <= 2 && diagnostics.connectivity) {
      status = 'degraded';
    } else {
      status = 'unhealthy';
    }

    return {
      status,
      consecutiveFailures: metrics.consecutiveFailures,
      issues,
      circuitBreakerStatus: diagnostics.circuitBreaker,
      realtimeConnection: diagnostics.realtimeConnection,
      metrics: {
        totalRequests: metrics.totalRequests,
        successRate,
        averageResponseTime: metrics.averageResponseTime
      }
    };
  }

  /**
   * Check for specific issues and create alerts
   */
  private checkForIssues(): void {
    // Reset alerts if connection is healthy
    if (this.status.status === 'healthy') {
      if (this.status.consecutiveFailures > 0) {
        this.addAlert({
          type: 'info',
          message: 'Connection recovered after previous issues',
          timestamp: new Date(),
          details: { previousFailures: this.status.consecutiveFailures }
        });
      }
      return;
    }

    // Circuit breaker issues
    if (this.status.circuitBreakerStatus.state !== 'CLOSED') {
      this.addAlert({
        type: 'warning',
        message: `Circuit breaker is ${this.status.circuitBreakerStatus.state}`,
        timestamp: new Date(),
        details: this.status.circuitBreakerStatus
      });
    }

    // High latency
    if (this.status.latency > 5000) {
      this.addAlert({
        type: 'warning',
        message: `High latency detected: ${this.status.latency}ms`,
        timestamp: new Date(),
        details: { latency: this.status.latency }
      });
    }

    // Low success rate
    if (this.status.metrics.successRate < 95) {
      this.addAlert({
        type: 'warning',
        message: `Low success rate: ${this.status.metrics.successRate.toFixed(2)}%`,
        timestamp: new Date(),
        details: { successRate: this.status.metrics.successRate }
      });
    }

    // Real-time connection lost
    if (!this.status.realtimeConnection) {
      this.addAlert({
        type: 'warning',
        message: 'Real-time connection not available',
        timestamp: new Date()
      });
    }

    // Unhealthy status
    if (this.status.status === 'unhealthy') {
      this.addAlert({
        type: 'error',
        message: 'Connection is unhealthy',
        timestamp: new Date(),
        details: {
          issues: this.status.issues,
          consecutiveFailures: this.status.consecutiveFailures
        }
      });
    }
  }

  /**
   * Handle errors during health checks
   */
  private handleError(error: Error): void {
    this.status.consecutiveFailures++;
    this.status.status = 'unhealthy';
    this.status.issues.push(error.message);

    this.addAlert({
      type: 'error',
      message: 'Health check failed',
      timestamp: new Date(),
      details: { error: error.message }
    });

    this.notifyListeners();
  }

  /**
   * Add alert to history
   */
  private addAlert(alert: ConnectionAlert): void {
    this.alerts.unshift(alert);

    // Keep only last 100 alerts
    if (this.alerts.length > 100) {
      this.alerts = this.alerts.slice(0, 100);
    }

    console.log(`[Connection Alert] ${alert.type.toUpperCase()}: ${alert.message}`);
  }

  /**
   * Notify all listeners
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.status);
      } catch (error) {
        console.error('Error in connection status listener:', error);
      }
    });
  }

  /**
   * Initialize status object
   */
  private initializeStatus(): ConnectionHealthStatus {
    return {
      status: 'healthy',
      latency: 0,
      lastCheck: new Date(),
      consecutiveFailures: 0,
      uptime: 0,
      issues: [],
      circuitBreakerStatus: {
        state: 'CLOSED',
        failures: 0
      },
      realtimeConnection: false,
      metrics: {
        totalRequests: 0,
        successRate: 100,
        averageResponseTime: 0
      }
    };
  }

  /**
   * Public API methods
   */

  // Get current status
  getStatus(): ConnectionHealthStatus {
    return { ...this.status };
  }

  // Get recent alerts
  getAlerts(limit = 50): ConnectionAlert[] {
    return this.alerts.slice(0, limit);
  }

  // Add status change listener
  addStatusListener(id: string, listener: (status: ConnectionHealthStatus) => void): void {
    this.listeners.set(id, listener);
  }

  // Remove status change listener
  removeStatusListener(id: string): void {
    this.listeners.delete(id);
  }

  // Force health check
  async forceHealthCheck(): Promise<ConnectionHealthStatus> {
    await this.performHealthCheck();
    return this.getStatus();
  }

  // Get connection recommendations
  getRecommendations(): string[] {
    const recommendations: string[] = [];

    if (this.status.status === 'unhealthy') {
      recommendations.push('Check network connectivity');
      recommendations.push('Verify backend service is running');
    }

    if (this.status.latency > 5000) {
      recommendations.push('Consider increasing timeout settings');
      recommendations.push('Check network performance');
    }

    if (this.status.metrics.successRate < 95) {
      recommendations.push('Review API request patterns');
      recommendations.push('Check for malformed requests');
    }

    if (!this.status.realtimeConnection) {
      recommendations.push('Check real-time connection');
      recommendations.push('Verify SSE endpoint is available');
    }

    if (this.status.circuitBreakerStatus.state !== 'CLOSED') {
      recommendations.push('Wait for circuit breaker recovery');
      recommendations.push('Review recent request patterns');
    }

    return recommendations;
  }

  // Attempt recovery actions
  async attemptRecovery(): Promise<{ success: boolean; actions: string[] }> {
    const actions: string[] = [];

    try {
      // Reset circuit breaker if it's open
      if (this.status.circuitBreakerStatus.state !== 'CLOSED') {
        this.client.resetCircuitBreaker();
        actions.push('Reset circuit breaker');
      }

      // Reconnect real-time updates if disconnected
      if (!this.status.realtimeConnection) {
        this.client.disconnectRealtimeUpdates();
        await this.client.connectRealtimeUpdates();
        actions.push('Reconnected real-time updates');
      }

      // Test connection after recovery attempts
      await this.forceHealthCheck();
      actions.push('Performed health check');

      return {
        success: this.status.status === 'healthy',
        actions
      };

    } catch (error) {
      actions.push(`Recovery failed: ${error}`);
      return { success: false, actions };
    }
  }

  // Get connection statistics
  getStatistics(): {
    uptime: string;
    totalAlerts: number;
    alertsByType: Record<string, number>;
    averageResponseTime: number;
    successRate: number;
  } {
    const alertsByType = this.alerts.reduce((acc, alert) => {
      acc[alert.type] = (acc[alert.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      uptime: this.formatDuration(this.status.uptime),
      totalAlerts: this.alerts.length,
      alertsByType,
      averageResponseTime: this.status.metrics.averageResponseTime,
      successRate: this.status.metrics.successRate
    };
  }

  // Format duration in human readable format
  private formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days}d ${hours % 24}h ${minutes % 60}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }
}

// Singleton instance
let connectionManager: ConnectionManager | null = null;

export function getConnectionManager(client?: FastAPIClient): ConnectionManager {
  if (!connectionManager) {
    if (!client) {
      throw new Error('Client must be provided when creating connection manager for the first time');
    }
    connectionManager = new ConnectionManager(client);
  }
  return connectionManager;
}

export default ConnectionManager;