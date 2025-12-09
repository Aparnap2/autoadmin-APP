/**
 * Main Delegation Service - Orchestrates all delegation components
 * Provides unified interface for task delegation, communication, and tracking
 */

import TaskDelegationService, { TaskDelegation, DelegationConfig } from './task-delegation.service';
import CommunicationProtocolService, { CommunicationConfig } from './communication-protocol.service';
import TaskStatusTrackerService, { StatusTrackerConfig } from './task-status-tracker.service';
import SmartRoutingService, { RoutingConfig } from './smart-routing.service';
import { TaskResult } from './task-delegation.service';
import { UserContext } from '../agents/types';

export interface AutoAdminDelegationConfig {
  userId: string;
  sessionId: string;

  // Delegation settings
  delegation: {
    maxConcurrentTasks: number;
    enableSmartRouting: boolean;
    enableLoadBalancing: boolean;
    defaultTimeout: number;
    retryPolicy: {
      maxRetries: number;
      backoffMultiplier: number;
      maxDelay: number;
    };
    thresholds: {
      complexityForDelegation: number;
      durationForDelegation: number;
      resourceThresholds: {
        compute: number;
        memory: number;
      };
    };
  };

  // Communication settings
  communication: {
    enableRealtime: boolean;
    enableEncryption: boolean;
    heartbeatInterval: number;
    messageRetention: number;
    maxMessageSize: number;
    compressionThreshold: number;
  };

  // Tracking settings
  tracking: {
    enableRealtimeUpdates: boolean;
    updateInterval: number;
    historyRetention: number;
    enableAnalytics: boolean;
    enableNotifications: boolean;
    notificationThresholds: {
      longRunningTask: number;
      failureRate: number;
      resourceUsage: number;
    };
  };

  // Routing settings
  routing: {
    enableLoadBalancing: boolean;
    enablePredictiveRouting: boolean;
    enableCostOptimization: boolean;
    defaultStrategy: 'fastest' | 'cheapest' | 'reliable' | 'balanced';
    maxConcurrentTasksPerAgent: number;
    thresholdForDelegation: number;
    priorityWeights: {
      complexity: number;
      urgency: number;
      cost: number;
      reliability: number;
      speed: number;
    };
    fallbackStrategy: 'retry' | 'reassign' | 'fail';
  };
}

export interface DelegationOptions {
  autoClassify?: boolean;
  enableRetry?: boolean;
  enableNotifications?: boolean;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  deadline?: Date;
  scheduledAt?: Date;
  metadata?: Record<string, any>;
  customRouting?: {
    target?: string;
    bypassSmartRouting?: boolean;
  };
}

export interface DelegationSystemStatus {
  initialized: boolean;
  connected: boolean;
  activeTasks: number;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
  averageProcessingTime: number;
  successRate: number;
  systemHealth: {
    delegationService: 'healthy' | 'degraded' | 'down';
    communicationService: 'healthy' | 'degraded' | 'down';
    trackingService: 'healthy' | 'degraded' | 'down';
    routingService: 'healthy' | 'degraded' | 'down';
  };
  agentStatus: Record<string, {
    online: boolean;
    currentLoad: number;
    lastSeen: Date;
    capabilities: string[];
  }>;
}

export class AutoAdminDelegationService {
  private config: AutoAdminDelegationConfig;
  private delegationService: TaskDelegationService;
  private communicationService: CommunicationProtocolService;
  private trackingService: TaskStatusTrackerService;
  private routingService: SmartRoutingService;
  private initialized = false;
  private eventListeners: Map<string, Function[]> = new Map();

  constructor(config: AutoAdminDelegationConfig) {
    this.config = config;

    // Initialize individual services with their respective configurations
    this.delegationService = new TaskDelegationService({
      userId: config.userId,
      maxConcurrentTasks: config.delegation.maxConcurrentTasks,
      enableSmartRouting: config.delegation.enableSmartRouting,
      enableLoadBalancing: config.delegation.enableLoadBalancing,
      defaultTimeout: config.delegation.defaultTimeout,
      retryPolicy: config.delegation.retryPolicy,
      thresholds: config.delegation.thresholds
    });

    this.communicationService = new CommunicationProtocolService({
      userId: config.userId,
      sessionId: config.sessionId,
      enableRealtime: config.communication.enableRealtime,
      enableEncryption: config.communication.enableEncryption,
      heartbeatInterval: config.communication.heartbeatInterval,
      messageRetention: config.communication.messageRetention,
      maxMessageSize: config.communication.maxMessageSize,
      compressionThreshold: config.communication.compressionThreshold
    });

    this.trackingService = new TaskStatusTrackerService({
      userId: config.userId,
      enableRealtimeUpdates: config.tracking.enableRealtimeUpdates,
      updateInterval: config.tracking.updateInterval,
      historyRetention: config.tracking.historyRetention,
      enableAnalytics: config.tracking.enableAnalytics,
      enableNotifications: config.tracking.enableNotifications,
      notificationThresholds: config.tracking.notificationThresholds
    });

    this.routingService = new SmartRoutingService({
      enableLoadBalancing: config.routing.enableLoadBalancing,
      enablePredictiveRouting: config.routing.enablePredictiveRouting,
      enableCostOptimization: config.routing.enableCostOptimization,
      defaultStrategy: config.routing.defaultStrategy,
      maxConcurrentTasksPerAgent: config.routing.maxConcurrentTasksPerAgent,
      thresholdForDelegation: config.routing.thresholdForDelegation,
      priorityWeights: config.routing.priorityWeights,
      fallbackStrategy: config.routing.fallbackStrategy
    });
  }

  /**
   * Initialize the entire delegation system
   */
  async initialize(): Promise<void> {
    try {
      console.log('Initializing AutoAdmin Delegation System...');

      // Initialize services in dependency order
      await this.communicationService.initialize();
      await this.trackingService.initialize();
      // Delegation and routing services don't require explicit initialization

      // Set up inter-service communication
      await this.setupInterServiceCommunication();

      this.initialized = true;

      // Emit initialization event
      this.emitEvent('system:initialized', {
        timestamp: new Date(),
        services: ['delegation', 'communication', 'tracking', 'routing']
      });

      console.log('AutoAdmin Delegation System initialized successfully');
    } catch (error) {
      console.error('Error initializing AutoAdmin Delegation System:', error);
      this.initialized = false;
      throw error;
    }
  }

  /**
   * Submit a task for delegation - Main entry point
   */
  async submitTask(
    title: string,
    description: string,
    options: DelegationOptions = {},
    userContext?: UserContext
  ): Promise<TaskDelegation> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      console.log(`Submitting task: ${title}`);

      // Classify the task first
      const classification = await this.delegationService.classifyTask(description, userContext);

      // Create initial task delegation
      let task = await this.delegationService.submitTask(title, description, options);

      // Apply smart routing if enabled and not bypassed
      if (this.config.delegation.enableSmartRouting && !options.customRouting?.bypassSmartRouting) {
        const routingDecision = await this.routingService.makeRoutingDecision(task, classification);

        // Update task with routing decision
        task.assignedTo = routingDecision.selectedAgent;
        task.metadata = {
          ...task.metadata,
          routingDecision,
          classification,
          customRouting: options.customRouting
        };

        // Update task in storage
        await this.updateTaskAssignment(task);
      } else if (options.customRouting?.target) {
        // Apply custom routing
        task.assignedTo = options.customRouting.target;
        task.metadata = {
          ...task.metadata,
          customRouting: options.customRouting,
          classification
        };

        await this.updateTaskAssignment(task);
      }

      // Send task to assigned agent
      await this.sendTaskToAgent(task);

      // Start tracking
      await this.trackingService.updateStatus(
        task.id,
        'pending',
        `Task submitted and assigned to ${task.assignedTo}`,
        'delegation_service'
      );

      // Emit task submission event
      this.emitEvent('task:submitted', {
        taskId: task.id,
        title,
        assignedTo: task.assignedTo,
        classification
      });

      console.log(`Task ${task.id} submitted successfully to ${task.assignedTo}`);
      return task;
    } catch (error) {
      console.error('Error submitting task:', error);
      throw error;
    }
  }

  /**
   * Get task status with comprehensive information
   */
  async getTaskStatus(taskId: string): Promise<{
    task: TaskDelegation | null;
    progress: any;
    history: any[];
    analytics: any;
    communication: any[];
  }> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      const task = await this.delegationService.getTaskStatus(taskId);
      const progress = this.trackingService.getProgress(taskId);
      const history = this.trackingService.getStatusHistory(taskId);
      const analytics = await this.trackingService.getAnalytics(taskId);
      const communication = await this.communicationService.getMessageHistory(50, undefined, 'all');

      return {
        task,
        progress,
        history,
        analytics,
        communication: communication.filter(msg =>
          msg.payload?.taskId === taskId
        )
      };
    } catch (error) {
      console.error('Error getting task status:', error);
      throw error;
    }
  }

  /**
   * Cancel a task with full cleanup
   */
  async cancelTask(taskId: string, reason?: string): Promise<boolean> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      // Cancel task in delegation service
      const success = await this.delegationService.cancelTask(taskId, reason);

      if (success) {
        // Send cancellation message
        await this.communicationService.sendMessage('cancellation', {
          taskId,
          reason,
          timestamp: new Date()
        }, 'all');

        // Update tracking
        await this.trackingService.updateStatus(
          taskId,
          'cancelled',
          reason || 'Task cancelled by user',
          'delegation_service'
        );

        // Emit cancellation event
        this.emitEvent('task:cancelled', { taskId, reason });
      }

      return success;
    } catch (error) {
      console.error('Error cancelling task:', error);
      return false;
    }
  }

  /**
   * Get system status and health
   */
  async getSystemStatus(): Promise<DelegationSystemStatus> {
    if (!this.initialized) {
      return {
        initialized: false,
        connected: false,
        activeTasks: 0,
        queuedTasks: 0,
        completedTasks: 0,
        failedTasks: 0,
        averageProcessingTime: 0,
        successRate: 0,
        systemHealth: {
          delegationService: 'down',
          communicationService: 'down',
          trackingService: 'down',
          routingService: 'down'
        },
        agentStatus: {}
      };
    }

    try {
      const statistics = await this.trackingService.getStatistics();
      const loadBalancing = this.routingService.getLoadBalancingMetrics();
      const connectionStatus = this.communicationService.getConnectionStatus();

      return {
        initialized: true,
        connected: connectionStatus === 'connected',
        activeTasks: statistics.processingTasks,
        queuedTasks: statistics.pendingTasks,
        completedTasks: statistics.completedTasks,
        failedTasks: statistics.failedTasks,
        averageProcessingTime: statistics.averageProcessingTime,
        successRate: statistics.successRate,
        systemHealth: {
          delegationService: 'healthy',
          communicationService: connectionStatus === 'connected' ? 'healthy' : 'degraded',
          trackingService: 'healthy',
          routingService: 'healthy'
        },
        agentStatus: Object.fromEntries(
          Object.entries(loadBalancing.loadDistribution).map(([agentId, load]) => [
            agentId,
            {
              online: true,
              currentLoad: load,
              lastSeen: new Date(),
              capabilities: [] // Would be populated from agent capabilities
            }
          ])
        )
      };
    } catch (error) {
      console.error('Error getting system status:', error);
      throw error;
    }
  }

  /**
   * Add event listener for system events
   */
  addEventListener(event: string, listener: Function): () => void {
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
   * Update agent capabilities for routing
   */
  async updateAgentCapabilities(
    agentId: string,
    capabilities: {
      agentType: 'expo_agent' | 'python_agent' | 'github_actions' | 'netlify_functions';
      capabilities: string[];
      maxConcurrentTasks: number;
      currentLoad: number;
      successRate: number;
      specialties?: string[];
    }
  ): Promise<void> {
    await this.routingService.updateAgentCapabilities(agentId, capabilities);
  }

  /**
   * Get comprehensive analytics and insights
   */
  async getAnalytics(timeRange?: { start: Date; end: Date }): Promise<{
    performance: any;
    routing: any;
    communication: any;
    trends: any;
  }> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      const performance = await this.trackingService.getStatistics();
      const routing = this.routingService.getLoadBalancingMetrics();
      const communication = await this.communicationService.getMessageHistory(100);
      const trends = this.calculateTrends(performance, routing, communication);

      return {
        performance,
        routing,
        communication: {
          totalMessages: communication.length,
          messageTypes: this.countMessageTypes(communication),
          averageLatency: this.calculateAverageLatency(communication)
        },
        trends
      };
    } catch (error) {
      console.error('Error getting analytics:', error);
      throw error;
    }
  }

  /**
   * Clean up and shutdown the delegation system
   */
  async cleanup(): Promise<void> {
    try {
      console.log('Cleaning up AutoAdmin Delegation System...');

      // Clean up services in reverse order
      await this.communicationService.cleanup();
      await this.trackingService.cleanup();

      // Clear event listeners
      this.eventListeners.clear();

      this.initialized = false;

      console.log('AutoAdmin Delegation System cleaned up successfully');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  /**
   * Private methods
   */

  private async setupInterServiceCommunication(): Promise<void> {
    // Set up communication between services

    // Listen for status updates from communication service
    this.communicationService.subscribe('status_update', async (message) => {
      if (message.payload?.taskId) {
        await this.trackingService.updateStatus(
          message.payload.taskId,
          message.payload.status,
          message.payload.message,
          message.source
        );
      }
    });

    // Listen for progress updates
    this.communicationService.subscribe('progress_update', async (message) => {
      if (message.payload?.progress) {
        await this.trackingService.updateProgress(message.payload.progress);
      }
    });

    // Listen for task results
    this.communicationService.subscribe('task_response', async (message) => {
      if (message.payload?.result) {
        await this.trackingService.recordResult(message.payload.result);
      }
    });

    console.log('Inter-service communication established');
  }

  private async updateTaskAssignment(task: TaskDelegation): Promise<void> {
    // Update task assignment in storage
    // This would integrate with the actual database/storage system
    console.log(`Updating task ${task.id} assignment to ${task.assignedTo}`);
  }

  private async sendTaskToAgent(task: TaskDelegation): Promise<void> {
    // Send task to the assigned agent via communication service
    await this.communicationService.sendTaskRequest(task, task.assignedTo as any);
  }

  private emitEvent(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener({ event, data, timestamp: new Date() });
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  private calculateTrends(performance: any, routing: any, communication: any[]): any {
    // Calculate trends and insights from the data
    return {
      taskVolumeTrend: 'increasing', // Would be calculated from historical data
      averageCompletionTimeTrend: 'stable',
      successRateTrend: 'improving',
      resourceUtilizationTrend: 'optimal'
    };
  }

  private countMessageTypes(messages: any[]): Record<string, number> {
    const types: Record<string, number> = {};
    messages.forEach(msg => {
      types[msg.type] = (types[msg.type] || 0) + 1;
    });
    return types;
  }

  private calculateAverageLatency(messages: any[]): number {
    if (messages.length === 0) return 0;

    // This would calculate actual latency from message timestamps
    // For now, return a placeholder
    return 150; // milliseconds
  }
}

// Export individual services for advanced usage
export {
  TaskDelegationService,
  CommunicationProtocolService,
  TaskStatusTrackerService,
  SmartRoutingService
};

// Export types
export type {
  TaskDelegation,
  TaskResult,
  DelegationOptions,
  DelegationSystemStatus
};

// Default export
export default AutoAdminDelegationService;