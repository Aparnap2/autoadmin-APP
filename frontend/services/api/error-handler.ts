/**
 * Enhanced Error Handler Service
 * Centralized error handling, classification, and recovery strategies
 */

import FastAPIClient from './fastapi-client';
import { getConnectionManager } from './connection-manager';

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ErrorCategory {
  NETWORK = 'network',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  RATE_LIMIT = 'rate_limit',
  SERVER_ERROR = 'server_error',
  CLIENT_ERROR = 'client_error',
  TIMEOUT = 'timeout',
  CIRCUIT_BREAKER = 'circuit_breaker',
  UNKNOWN = 'unknown'
}

export interface ErrorDetails {
  code: string;
  message: string;
  severity: ErrorSeverity;
  category: ErrorCategory;
  retryable: boolean;
  suggestedActions: string[];
  originalError?: Error;
  context?: Record<string, any>;
  timestamp: Date;
  correlationId?: string;
}

export interface RecoveryAction {
  type: 'retry' | 'reconnect' | 'reset' | 'fallback' | 'escalate';
  description: string;
  action: () => Promise<any>;
}

export class EnhancedErrorHandler {
  private errorHistory: ErrorDetails[] = [];
  private recoveryStrategies: Map<string, RecoveryAction[]> = new Map();
  private correlationCounter = 0;

  constructor(private client: FastAPIClient) {
    this.initializeRecoveryStrategies();
  }

  /**
   * Handle and classify errors with suggested recovery actions
   */
  async handleError(error: Error | string, context?: Record<string, any>): Promise<ErrorDetails> {
    const errorDetails = this.classifyError(error, context);

    // Add to history
    this.errorHistory.unshift(errorDetails);
    if (this.errorHistory.length > 100) {
      this.errorHistory = this.errorHistory.slice(0, 100);
    }

    // Log error
    this.logError(errorDetails);

    // Attempt automatic recovery if possible
    if (errorDetails.retryable) {
      await this.attemptRecovery(errorDetails);
    }

    return errorDetails;
  }

  /**
   * Classify error and provide structured details
   */
  private classifyError(error: Error | string, context?: Record<string, any>): ErrorDetails {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const errorName = typeof error === 'string' ? 'Error' : error.name;
    const correlationId = this.generateCorrelationId();

    // Network errors
    if (this.isNetworkError(errorMessage)) {
      return {
        code: 'NETWORK_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.HIGH,
        category: ErrorCategory.NETWORK,
        retryable: true,
        suggestedActions: [
          'Check network connectivity',
          'Verify backend service is running',
          'Attempt automatic reconnection'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Timeout errors
    if (this.isTimeoutError(errorMessage, errorName)) {
      return {
        code: 'TIMEOUT_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.MEDIUM,
        category: ErrorCategory.TIMEOUT,
        retryable: true,
        suggestedActions: [
          'Increase timeout settings',
          'Check network latency',
          'Reduce request payload size'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Validation errors
    if (this.isValidationError(errorMessage)) {
      return {
        code: 'VALIDATION_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.MEDIUM,
        category: ErrorCategory.VALIDATION,
        retryable: false,
        suggestedActions: [
          'Check request data format',
          'Validate input parameters',
          'Review API documentation'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Authentication errors
    if (this.isAuthenticationError(errorMessage)) {
      return {
        code: 'AUTHENTICATION_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.HIGH,
        category: ErrorCategory.AUTHENTICATION,
        retryable: false,
        suggestedActions: [
          'Check API key configuration',
          'Verify authentication credentials',
          'Refresh authentication tokens'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Rate limit errors
    if (this.isRateLimitError(errorMessage)) {
      return {
        code: 'RATE_LIMIT_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.MEDIUM,
        category: ErrorCategory.RATE_LIMIT,
        retryable: true,
        suggestedActions: [
          'Wait before retrying',
          'Reduce request frequency',
          'Implement exponential backoff'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Circuit breaker errors
    if (this.isCircuitBreakerError(errorMessage)) {
      return {
        code: 'CIRCUIT_BREAKER_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.HIGH,
        category: ErrorCategory.CIRCUIT_BREAKER,
        retryable: false,
        suggestedActions: [
          'Wait for circuit breaker to reset',
          'Check backend service health',
          'Monitor system recovery'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Server errors
    if (this.isServerError(errorMessage)) {
      return {
        code: 'SERVER_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.HIGH,
        category: ErrorCategory.SERVER_ERROR,
        retryable: true,
        suggestedActions: [
          'Retry request after delay',
          'Check backend service status',
          'Monitor system health'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Client errors (4xx)
    if (this.isClientError(errorMessage)) {
      return {
        code: 'CLIENT_ERROR',
        message: errorMessage,
        severity: ErrorSeverity.MEDIUM,
        category: ErrorCategory.CLIENT_ERROR,
        retryable: false,
        suggestedActions: [
          'Check request parameters',
          'Verify endpoint URL',
          'Review API documentation'
        ],
        originalError: typeof error === 'object' ? error : new Error(errorMessage),
        context,
        timestamp: new Date(),
        correlationId
      };
    }

    // Unknown errors
    return {
      code: 'UNKNOWN_ERROR',
      message: errorMessage,
      severity: ErrorSeverity.MEDIUM,
      category: ErrorCategory.UNKNOWN,
      retryable: true,
      suggestedActions: [
        'Check system logs',
        'Contact support team',
        'Retry with different parameters'
      ],
      originalError: typeof error === 'object' ? error : new Error(errorMessage),
      context,
      timestamp: new Date(),
      correlationId
    };
  }

  /**
   * Error type detection methods
   */
  private isNetworkError(message: string): boolean {
    const networkKeywords = [
      'network error',
      'connection refused',
      'connection timeout',
      'dns lookup failed',
      'socket timeout',
      'fetch failed',
      'connection lost',
      'no network'
    ];
    return networkKeywords.some(keyword => message.toLowerCase().includes(keyword));
  }

  private isTimeoutError(message: string, name: string): boolean {
    return name === 'AbortError' || message.toLowerCase().includes('timeout');
  }

  private isValidationError(message: string): boolean {
    return message.toLowerCase().includes('validation') ||
           message.toLowerCase().includes('invalid') ||
           message.toLowerCase().includes('malformed') ||
           message.toLowerCase().includes('bad request');
  }

  private isAuthenticationError(message: string): boolean {
    const authKeywords = [
      'unauthorized',
      'authentication failed',
      'invalid credentials',
      'api key',
      'token expired',
      '401'
    ];
    return authKeywords.some(keyword => message.toLowerCase().includes(keyword));
  }

  private isRateLimitError(message: string): boolean {
    const rateLimitKeywords = [
      'rate limit',
      'too many requests',
      '429',
      'quota exceeded',
      'throttled'
    ];
    return rateLimitKeywords.some(keyword => message.toLowerCase().includes(keyword));
  }

  private isCircuitBreakerError(message: string): boolean {
    return message.toLowerCase().includes('circuit breaker') ||
           message.toLowerCase().includes('service unavailable');
  }

  private isServerError(message: string): boolean {
    const serverErrorCodes = ['500', '502', '503', '504'];
    return serverErrorCodes.some(code => message.includes(code)) ||
           message.toLowerCase().includes('internal server error');
  }

  private isClientError(message: string): boolean {
    const clientErrorCodes = ['400', '401', '403', '404', '405', '409', '422'];
    return clientErrorCodes.some(code => message.includes(code)) &&
           !this.isAuthenticationError(message) &&
           !this.isRateLimitError(message);
  }

  /**
   * Initialize recovery strategies
   */
  private initializeRecoveryStrategies(): void {
    // Network error recovery
    this.recoveryStrategies.set(ErrorCategory.NETWORK, [
      {
        type: 'retry',
        description: 'Retry request with exponential backoff',
        action: async () => {
          console.log('Attempting network retry...');
          // Handled by the retry client
        }
      },
      {
        type: 'reconnect',
        description: 'Reconnect WebSocket connection',
        action: async () => {
          try {
            this.client.disconnectWebSocket();
            await this.client.connectWebSocket();
            console.log('WebSocket reconnection successful');
          } catch (error) {
            console.error('WebSocket reconnection failed:', error);
          }
        }
      }
    ]);

    // Timeout error recovery
    this.recoveryStrategies.set(ErrorCategory.TIMEOUT, [
      {
        type: 'retry',
        description: 'Retry with increased timeout',
        action: async () => {
          console.log('Retrying with extended timeout...');
          // This would be handled by increasing timeout in retry options
        }
      }
    ]);

    // Circuit breaker recovery
    this.recoveryStrategies.set(ErrorCategory.CIRCUIT_BREAKER, [
      {
        type: 'reset',
        description: 'Reset circuit breaker manually',
        action: async () => {
          try {
            this.client.resetCircuitBreaker();
            console.log('Circuit breaker reset successfully');
          } catch (error) {
            console.error('Failed to reset circuit breaker:', error);
          }
        }
      }
    ]);

    // Server error recovery
    this.recoveryStrategies.set(ErrorCategory.SERVER_ERROR, [
      {
        type: 'retry',
        description: 'Retry after server recovery period',
        action: async () => {
          console.log('Waiting for server recovery...');
          await new Promise(resolve => setTimeout(resolve, 5000));
        }
      }
    ]);
  }

  /**
   * Attempt automatic recovery
   */
  private async attemptRecovery(errorDetails: ErrorDetails): Promise<void> {
    const strategies = this.recoveryStrategies.get(errorDetails.category);
    if (!strategies || strategies.length === 0) {
      return;
    }

    console.log(`Attempting recovery for ${errorDetails.category} error...`);

    for (const strategy of strategies) {
      try {
        console.log(`Executing recovery action: ${strategy.description}`);
        await strategy.action();
        break; // Stop at first successful recovery
      } catch (error) {
        console.error(`Recovery action failed: ${strategy.description}`, error);
      }
    }
  }

  /**
   * Log error details
   */
  private logError(errorDetails: ErrorDetails): void {
    const logLevel = this.getLogLevel(errorDetails.severity);
    const logMessage = `[${errorDetails.correlationId}] ${errorDetails.code}: ${errorDetails.message}`;

    switch (logLevel) {
      case 'error':
        console.error(logMessage, errorDetails);
        break;
      case 'warn':
        console.warn(logMessage, errorDetails);
        break;
      default:
        console.log(logMessage, errorDetails);
    }

    // Also log to external monitoring if configured
    this.logToExternalService(errorDetails);
  }

  /**
   * Get log level based on error severity
   */
  private getLogLevel(severity: ErrorSeverity): 'error' | 'warn' | 'log' {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warn';
      default:
        return 'log';
    }
  }

  /**
   * Log to external monitoring service
   */
  private logToExternalService(errorDetails: ErrorDetails): void {
    // This would integrate with monitoring services like Sentry, DataDog, etc.
    // For now, just log to console
    console.debug('Error logged to external service:', errorDetails.correlationId);
  }

  /**
   * Generate correlation ID for error tracking
   */
  private generateCorrelationId(): string {
    return `ERR_${Date.now()}_${++this.correlationCounter}`;
  }

  /**
   * Public API methods
   */

  // Get error history
  getErrorHistory(limit = 50): ErrorDetails[] {
    return this.errorHistory.slice(0, limit);
  }

  // Get error statistics
  getErrorStatistics(): {
    total: number;
    byCategory: Record<ErrorCategory, number>;
    bySeverity: Record<ErrorSeverity, number>;
    byHour: Record<string, number>;
    topErrors: Array<{ count: number; code: string; message: string }>;
  } {
    const byCategory = Object.values(ErrorCategory).reduce((acc, category) => {
      acc[category] = 0;
      return acc;
    }, {} as Record<ErrorCategory, number>);

    const bySeverity = Object.values(ErrorSeverity).reduce((acc, severity) => {
      acc[severity] = 0;
      return acc;
    }, {} as Record<ErrorSeverity, number>);

    const byHour: Record<string, number> = {};

    const errorCounts: Record<string, { count: number; code: string; message: string }> = {};

    this.errorHistory.forEach(error => {
      // Count by category
      byCategory[error.category]++;

      // Count by severity
      bySeverity[error.severity]++;

      // Count by hour
      const hour = error.timestamp.getHours();
      byHour[hour.toString()] = (byHour[hour.toString()] || 0) + 1;

      // Count specific errors
      const key = error.code;
      if (!errorCounts[key]) {
        errorCounts[key] = {
          count: 0,
          code: error.code,
          message: error.message.substring(0, 100)
        };
      }
      errorCounts[key].count++;
    });

    const topErrors = Object.values(errorCounts)
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    return {
      total: this.errorHistory.length,
      byCategory,
      bySeverity,
      byHour,
      topErrors
    };
  }

  // Clear error history
  clearErrorHistory(): void {
    this.errorHistory = [];
  }

  // Get recommended actions for error
  getRecoveryActions(errorCategory: ErrorCategory): RecoveryAction[] {
    return this.recoveryStrategies.get(errorCategory) || [];
  }

  // Execute manual recovery action
  async executeRecoveryAction(errorCategory: ErrorCategory, actionIndex: number): Promise<boolean> {
    const strategies = this.recoveryStrategies.get(errorCategory);
    if (!strategies || actionIndex >= strategies.length) {
      return false;
    }

    try {
      await strategies[actionIndex].action();
      return true;
    } catch (error) {
      console.error('Manual recovery action failed:', error);
      return false;
    }
  }

  // Check if error is critical and needs escalation
  shouldEscalate(errorDetails: ErrorDetails): boolean {
    return errorDetails.severity === ErrorSeverity.CRITICAL ||
           (errorDetails.severity === ErrorSeverity.HIGH && this.getErrorHistory().filter(e => e.code === errorDetails.code).length > 3);
  }

  // Get system health summary based on recent errors
  getSystemHealth(): {
    status: 'healthy' | 'warning' | 'critical';
    errorRate: number;
    criticalIssues: number;
    recommendations: string[];
  } {
    const recentErrors = this.getErrorHistory(20); // Last 20 errors
    const criticalErrors = recentErrors.filter(e => e.severity === ErrorSeverity.CRITICAL);
    const highSeverityErrors = recentErrors.filter(e => e.severity === ErrorSeverity.HIGH);

    const errorRate = recentErrors.length > 0 ? (criticalErrors.length + highSeverityErrors.length) / recentErrors.length : 0;

    let status: 'healthy' | 'warning' | 'critical';
    if (criticalErrors.length > 0 || errorRate > 0.5) {
      status = 'critical';
    } else if (highSeverityErrors.length > 2 || errorRate > 0.2) {
      status = 'warning';
    } else {
      status = 'healthy';
    }

    const recommendations: string[] = [];
    if (criticalErrors.length > 0) {
      recommendations.push('Address critical system issues immediately');
    }
    if (errorRate > 0.3) {
      recommendations.push('Investigate high error rate patterns');
    }
    if (recentErrors.filter(e => e.category === ErrorCategory.NETWORK).length > 5) {
      recommendations.push('Check network infrastructure');
    }

    return {
      status,
      errorRate,
      criticalIssues: criticalErrors.length,
      recommendations
    };
  }
}

// Export singleton instance
export function createErrorHandler(client: FastAPIClient): EnhancedErrorHandler {
  return new EnhancedErrorHandler(client);
}

export default EnhancedErrorHandler;