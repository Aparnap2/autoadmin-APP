/**
 * Task Status Tracker Service - Tracks and manages task status, progress, and results
 * Provides real-time updates and comprehensive task monitoring
 */

import { z } from 'zod';
import { TaskDelegation, TaskResult } from './task-delegation.service';
import { Message } from './communication-protocol.service';
import FirestoreService from '../firebase/firestore.service';
import GraphMemoryService from '../../utils/firebase/graph-memory';

// Task status schemas
export const TaskProgressSchema = z.object({
  taskId: z.string(),
  currentStep: z.string(),
  totalSteps: z.number(),
  completedSteps: z.number(),
  percentage: z.number().min(0).max(100),
  estimatedTimeRemaining: z.number().optional(), // seconds
  currentActivity: z.string(),
  lastUpdate: z.date(),
  milestones: z.array(z.object({
    name: z.string(),
    completed: z.boolean(),
    timestamp: z.date().optional(),
    details: z.string().optional()
  })).optional(),
  metrics: z.record(z.number()).optional(),
  subtasks: z.array(z.object({
    id: z.string(),
    name: z.string(),
    status: z.enum(['pending', 'processing', 'completed', 'failed']),
    progress: z.number().min(0).max(100),
    assignedTo: z.string(),
    startTime: z.date().optional(),
    endTime: z.date().optional()
  })).optional()
});

export type TaskProgress = z.infer<typeof TaskProgressSchema>;

export const TaskStatusHistorySchema = z.object({
  taskId: z.string(),
  status: z.enum(['pending', 'processing', 'completed', 'failed', 'cancelled']),
  timestamp: z.date(),
  message: z.string(),
  metadata: z.record(z.any()).optional(),
  agentId: z.string(),
  duration?: z.number() // time since last status change in seconds
});

export type TaskStatusHistory = z.infer<typeof TaskStatusHistorySchema>;

export interface TaskAnalytics {
  taskId: string;
  totalDuration: number; // seconds
  processingDuration: number; // seconds
  waitingDuration: number; // seconds
  retryCount: number;
  successRate: number; // for this specific task type
  averageResponseTime: number; // milliseconds
  resourceUsage: {
    compute: number; // CPU units
    memory: number; // MB
    network: number; // MB transferred
    storage: number; // MB used
  };
  qualityMetrics: {
    accuracy?: number; // 0-1
    completeness?: number; // 0-1
    relevance?: number; // 0-1
    userSatisfaction?: number; // 0-1
  };
  performanceComparison: {
    betterThanAverage: boolean;
    percentile: number; // 0-100
    rank: number;
    totalTasks: number;
  };
}

export interface StatusTrackerConfig {
  userId: string;
  enableRealtimeUpdates: boolean;
  updateInterval: number; // seconds
  historyRetention: number; // days
  enableAnalytics: boolean;
  enableNotifications: boolean;
  notificationThresholds: {
    longRunningTask: number; // seconds
    failureRate: number; // percentage
    resourceUsage: number; // percentage of limits
  };
}

export interface TaskFilter {
  status?: string[];
  type?: string[];
  category?: string[];
  assignedTo?: string[];
  priority?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  complexityRange?: {
    min: number;
    max: number;
  };
  durationRange?: {
    min: number;
    max: number;
  };
}

export interface TaskStatistics {
  totalTasks: number;
  pendingTasks: number;
  processingTasks: number;
  completedTasks: number;
  failedTasks: number;
  cancelledTasks: number;
  averageProcessingTime: number; // seconds
  successRate: number; // percentage
  failureRate: number; // percentage
  averageComplexity: number;
  mostCommonType: string;
  busiestAgent: string;
  tasksByType: Record<string, number>;
  tasksByStatus: Record<string, number>;
  tasksByPriority: Record<string, number>;
  performanceMetrics: {
    totalProcessingTime: number;
    averageResponseTime: number;
    throughput: number; // tasks per hour
  };
}

export class TaskStatusTrackerService {
  private config: StatusTrackerConfig;
  private firestoreService: FirestoreService;
  private graphMemory: GraphMemoryService;
  private activeProgress: Map<string, TaskProgress> = new Map();
  private statusHistory: Map<string, TaskStatusHistory[]> = new Map();
  private updateInterval: NodeJS.Timeout | null = null;
  private listeners: Map<string, (update: any) => void> = new Map();

  constructor(config: StatusTrackerConfig) {
    this.config = config;
    this.firestoreService = FirestoreService.getInstance();
    this.graphMemory = new GraphMemoryService();

    // Set user context for services
    this.firestoreService.setUserId(config.userId);
  }

  /**
   * Initialize the status tracker
   */
  async initialize(): Promise<void> {
    try {
      // Load existing task data
      await this.loadExistingTasks();

      // Start real-time updates if enabled
      if (this.config.enableRealtimeUpdates) {
        this.startRealtimeUpdates();
      }

      console.log('Task Status Tracker initialized successfully');
    } catch (error) {
      console.error('Error initializing Task Status Tracker:', error);
      throw error;
    }
  }

  /**
   * Update task progress
   */
  async updateProgress(progress: TaskProgress): Promise<void> {
    try {
      // Validate progress
      TaskProgressSchema.parse(progress);

      // Store progress locally
      this.activeProgress.set(progress.taskId, progress);

      // Save progress to Firestore
      await this.saveProgress(progress);

      // Check for milestones and notifications
      await this.checkMilestones(progress);

      // Notify listeners
      this.notifyListeners('progress_update', { taskId: progress.taskId, progress });

      console.log(`Updated progress for task ${progress.taskId}: ${progress.percentage}%`);
    } catch (error) {
      console.error('Error updating progress:', error);
      throw error;
    }
  }

  /**
   * Update task status
   */
  async updateStatus(
    taskId: string,
    status: TaskStatusHistory['status'],
    message: string,
    agentId: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    try {
      const now = new Date();

      // Calculate duration since last status change
      const lastHistory = this.statusHistory.get(taskId)?.[0];
      const duration = lastHistory ? (now.getTime() - lastHistory.timestamp.getTime()) / 1000 : undefined;

      // Create status history entry
      const statusEntry: TaskStatusHistory = {
        taskId,
        status,
        timestamp: now,
        message,
        metadata,
        agentId,
        duration
      };

      // Validate status entry
      TaskStatusHistorySchema.parse(statusEntry);

      // Update history
      if (!this.statusHistory.has(taskId)) {
        this.statusHistory.set(taskId, []);
      }
      this.statusHistory.get(taskId)!.unshift(statusEntry);

      // Save to Firestore
      await this.saveStatusHistory(statusEntry);

      // Update task in database
      await this.updateTaskStatus(taskId, status, message);

      // Notify listeners
      this.notifyListeners('status_update', { taskId, status, message, agentId });

      // Handle special status transitions
      await this.handleStatusTransition(taskId, status, statusEntry);

      console.log(`Updated status for task ${taskId} to ${status}: ${message}`);
    } catch (error) {
      console.error('Error updating status:', error);
      throw error;
    }
  }

  /**
   * Record task result
   */
  async recordResult(result: TaskResult): Promise<void> {
    try {
      // Get the original task for context
      const task = await this.getTask(result.taskId);
      if (!task) {
        throw new Error(`Task ${result.taskId} not found`);
      }

      // Calculate analytics
      const analytics = await this.calculateAnalytics(result, task);

      // Save result
      await this.saveTaskResult(result, analytics);

      // Update final status
      const finalStatus = result.success ? 'completed' : 'failed';
      await this.updateStatus(
        result.taskId,
        finalStatus,
        result.success ? 'Task completed successfully' : `Task failed: ${result.error}`,
        'status_tracker',
        {
          result: result.data,
          error: result.error,
          metrics: result.metrics,
          analytics
        }
      );

      // Clean up progress
      this.activeProgress.delete(result.taskId);

      // Notify listeners
      this.notifyListeners('task_completed', { taskId: result.taskId, result, success: result.success });

      // Send notifications if enabled
      if (this.config.enableNotifications) {
        await this.sendTaskCompletionNotification(result, task);
      }

      console.log(`Recorded result for task ${result.taskId}: ${result.success ? 'SUCCESS' : 'FAILURE'}`);
    } catch (error) {
      console.error('Error recording result:', error);
      throw error;
    }
  }

  /**
   * Get task progress
   */
  getProgress(taskId: string): TaskProgress | null {
    return this.activeProgress.get(taskId) || null;
  }

  /**
   * Get task status history
   */
  getStatusHistory(taskId: string): TaskStatusHistory[] {
    return this.statusHistory.get(taskId) || [];
  }

  /**
   * Get task analytics
   */
  async getAnalytics(taskId: string): Promise<TaskAnalytics | null> {
    try {
      // Look for stored analytics
      const result = await this.getTaskResult(taskId);
      if (result && result.metadata?.analytics) {
        return result.metadata.analytics;
      }

      // Calculate analytics on the fly
      const task = await this.getTask(taskId);
      if (task) {
        const history = this.getStatusHistory(taskId);
        return this.calculateBasicAnalytics(task, history);
      }

      return null;
    } catch (error) {
      console.error('Error getting analytics:', error);
      return null;
    }
  }

  /**
   * Get task statistics
   */
  async getStatistics(filter?: TaskFilter): Promise<TaskStatistics> {
    try {
      // Get all tasks for the user
      const tasks = await this.getAllTasks(filter);

      // Calculate statistics
      const stats: TaskStatistics = {
        totalTasks: tasks.length,
        pendingTasks: 0,
        processingTasks: 0,
        completedTasks: 0,
        failedTasks: 0,
        cancelledTasks: 0,
        averageProcessingTime: 0,
        successRate: 0,
        failureRate: 0,
        averageComplexity: 0,
        mostCommonType: '',
        busiestAgent: '',
        tasksByType: {},
        tasksByStatus: {},
        tasksByPriority: {},
        performanceMetrics: {
          totalProcessingTime: 0,
          averageResponseTime: 0,
          throughput: 0
        }
      };

      let totalProcessingTime = 0;
      let totalComplexity = 0;
      const agentTaskCounts: Record<string, number> = {};

      for (const task of tasks) {
        // Count by status
        stats.tasksByStatus[task.status] = (stats.tasksByStatus[task.status] || 0) + 1;
        switch (task.status) {
          case 'pending':
            stats.pendingTasks++;
            break;
          case 'processing':
            stats.processingTasks++;
            break;
          case 'completed':
            stats.completedTasks++;
            totalProcessingTime += this.getTaskDuration(task);
            break;
          case 'failed':
            stats.failedTasks++;
            break;
          case 'cancelled':
            stats.cancelledTasks++;
            break;
        }

        // Count by type
        stats.tasksByType[task.type] = (stats.tasksByType[task.type] || 0) + 1;

        // Count by priority
        stats.tasksByPriority[task.priority] = (stats.tasksByPriority[task.priority] || 0) + 1;

        // Track complexity
        totalComplexity += task.complexity;

        // Track agent assignments
        agentTaskCounts[task.assignedTo] = (agentTaskCounts[task.assignedTo] || 0) + 1;
      }

      // Calculate derived statistics
      stats.averageProcessingTime = stats.completedTasks > 0 ? totalProcessingTime / stats.completedTasks : 0;
      stats.successRate = stats.totalTasks > 0 ? (stats.completedTasks / stats.totalTasks) * 100 : 0;
      stats.failureRate = stats.totalTasks > 0 ? (stats.failedTasks / stats.totalTasks) * 100 : 0;
      stats.averageComplexity = stats.totalTasks > 0 ? totalComplexity / stats.totalTasks : 0;

      // Find most common type
      stats.mostCommonType = Object.entries(stats.tasksByType)
        .sort(([,a], [,b]) => b - a)[0]?.[0] || '';

      // Find busiest agent
      stats.busiestAgent = Object.entries(agentTaskCounts)
        .sort(([,a], [,b]) => b - a)[0]?.[0] || '';

      // Calculate performance metrics
      stats.performanceMetrics.totalProcessingTime = totalProcessingTime;
      stats.performanceMetrics.averageResponseTime = stats.averageProcessingTime * 1000; // Convert to milliseconds

      // Calculate throughput (tasks per hour) - consider last 24 hours
      const now = new Date();
      const last24Hours = tasks.filter(task =>
        new Date(task.createdAt) >= new Date(now.getTime() - 24 * 60 * 60 * 1000)
      );
      stats.performanceMetrics.throughput = last24Hours.length / 24;

      return stats;
    } catch (error) {
      console.error('Error getting statistics:', error);
      throw error;
    }
  }

  /**
   * Add status change listener
   */
  addListener(id: string, callback: (update: any) => void): void {
    this.listeners.set(id, callback);
  }

  /**
   * Remove status change listener
   */
  removeListener(id: string): boolean {
    return this.listeners.delete(id);
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    try {
      // Stop real-time updates
      if (this.updateInterval) {
        clearInterval(this.updateInterval);
        this.updateInterval = null;
      }

      // Clear listeners
      this.listeners.clear();

      // Save final state
      await this.saveCurrentState();

      console.log('Task Status Tracker cleaned up successfully');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  /**
   * Private methods
   */

  private async loadExistingTasks(): Promise<void> {
    try {
      // Load task history from Firestore
      const messages = await this.firestoreService.getMessages(this.config.userId, 'status_tracker');

      for (const message of messages) {
        try {
          if (message.metadata?.type === 'status_update') {
            const statusEntry = JSON.parse(message.content);
            TaskStatusHistorySchema.parse(statusEntry);

            if (!this.statusHistory.has(statusEntry.taskId)) {
              this.statusHistory.set(statusEntry.taskId, []);
            }
            this.statusHistory.get(statusEntry.taskId)!.push(statusEntry);
          } else if (message.metadata?.type === 'progress_update') {
            const progress = JSON.parse(message.content);
            TaskProgressSchema.parse(progress);
            this.activeProgress.set(progress.taskId, progress);
          }
        } catch (parseError) {
          console.warn('Could not parse status/tracking message:', parseError);
        }
      }
    } catch (error) {
      console.error('Error loading existing tasks:', error);
    }
  }

  private startRealtimeUpdates(): void {
    this.updateInterval = setInterval(async () => {
      try {
        // Update any long-running tasks
        for (const [taskId, progress] of this.activeProgress) {
          // Check if task is running longer than threshold
          const taskAge = (Date.now() - progress.lastUpdate.getTime()) / 1000;
          if (taskAge > this.config.notificationThresholds.longRunningTask) {
            await this.checkLongRunningTask(taskId, progress);
          }
        }
      } catch (error) {
        console.error('Error in real-time update:', error);
      }
    }, this.config.updateInterval * 1000);
  }

  private async saveProgress(progress: TaskProgress): Promise<void> {
    await this.firestoreService.saveMessage({
      userId: this.config.userId,
      agentId: 'status_tracker',
      content: JSON.stringify(progress),
      type: 'agent',
      metadata: {
        type: 'progress_update',
        taskId: progress.taskId,
        percentage: progress.percentage
      }
    });
  }

  private async saveStatusHistory(statusEntry: TaskStatusHistory): Promise<void> {
    await this.firestoreService.saveMessage({
      userId: this.config.userId,
      agentId: 'status_tracker',
      content: JSON.stringify(statusEntry),
      type: 'agent',
      metadata: {
        type: 'status_update',
        taskId: statusEntry.taskId,
        status: statusEntry.status
      }
    });
  }

  private async updateTaskStatus(taskId: string, status: string, message: string): Promise<void> {
    // This would update the actual task record in the database
    // Implementation depends on the specific database schema
    console.log(`Updating task ${taskId} status to ${status}`);
  }

  private async handleStatusTransition(taskId: string, status: string, statusEntry: TaskStatusHistory): Promise<void> {
    // Handle special cases for status transitions
    switch (status) {
      case 'processing':
        // Mark start time if not already set
        await this.markTaskStart(taskId);
        break;
      case 'completed':
      case 'failed':
        // Mark end time and calculate duration
        await this.markTaskEnd(taskId, status === 'completed');
        break;
      case 'cancelled':
        // Handle cancellation cleanup
        await this.handleTaskCancellation(taskId);
        break;
    }
  }

  private async checkMilestones(progress: TaskProgress): Promise<void> {
    // Check for important milestones (25%, 50%, 75%, 90%, 100%)
    const milestones = [25, 50, 75, 90, 100];
    for (const milestone of milestones) {
      if (progress.percentage >= milestone && progress.percentage < milestone + 5) {
        await this.notifyMilestone(progress.taskId, milestone);
        break;
      }
    }
  }

  private async notifyMilestone(taskId: string, percentage: number): Promise<void> {
    this.notifyListeners('milestone_reached', { taskId, percentage });
  }

  private async checkLongRunningTask(taskId: string, progress: TaskProgress): Promise<void> {
    const duration = (Date.now() - progress.lastUpdate.getTime()) / 1000;
    if (duration > this.config.notificationThresholds.longRunningTask) {
      this.notifyListeners('long_running_task', {
        taskId,
        duration,
        lastUpdate: progress.lastUpdate,
        currentStep: progress.currentStep
      });
    }
  }

  private async calculateAnalytics(result: TaskResult, task: TaskDelegation): Promise<TaskAnalytics> {
    const duration = result.metrics?.duration || 0;
    const history = this.getStatusHistory(task.id);

    // Get task statistics for comparison
    const allStats = await this.getStatistics({ category: [task.category] });

    return {
      taskId: task.id,
      totalDuration: duration,
      processingDuration: duration,
      waitingDuration: 0, // Would need more detailed tracking
      retryCount: task.retryCount,
      successRate: result.success ? 1 : 0,
      averageResponseTime: duration * 1000, // Convert to ms
      resourceUsage: result.metrics?.resourcesUsed || {
        compute: 0,
        memory: 0,
        network: 0,
        storage: 0
      },
      qualityMetrics: {
        accuracy: result.success ? 1 : 0,
        completeness: result.success ? 1 : 0,
        relevance: result.success ? 1 : 0
      },
      performanceComparison: {
        betterThanAverage: duration <= allStats.averageProcessingTime,
        percentile: this.calculatePercentile(duration, allStats.averageProcessingTime),
        rank: 0, // Would need more data
        totalTasks: allStats.totalTasks
      }
    };
  }

  private calculateBasicAnalytics(task: TaskDelegation, history: TaskStatusHistory[]): TaskAnalytics {
    const duration = this.getTaskDuration(task);

    return {
      taskId: task.id,
      totalDuration: duration,
      processingDuration: duration,
      waitingDuration: 0,
      retryCount: task.retryCount,
      successRate: task.status === 'completed' ? 1 : 0,
      averageResponseTime: duration * 1000,
      resourceUsage: {
        compute: 0,
        memory: 0,
        network: 0,
        storage: 0
      },
      qualityMetrics: {
        accuracy: task.status === 'completed' ? 1 : 0,
        completeness: task.status === 'completed' ? 1 : 0,
        relevance: task.status === 'completed' ? 1 : 0
      },
      performanceComparison: {
        betterThanAverage: true,
        percentile: 50,
        rank: 1,
        totalTasks: 1
      }
    };
  }

  private calculatePercentile(value: number, average: number): number {
    if (value === 0) return 50;
    const ratio = value / average;
    return Math.max(0, Math.min(100, 100 - (ratio - 1) * 50));
  }

  private getTaskDuration(task: TaskDelegation): number {
    if (task.status === 'completed' || task.status === 'failed') {
      return (task.updatedAt.getTime() - task.createdAt.getTime()) / 1000;
    }
    return (new Date().getTime() - task.createdAt.getTime()) / 1000;
  }

  private async getTask(taskId: string): Promise<TaskDelegation | null> {
    // Implementation to retrieve task from database
    // This would integrate with the task delegation service
    return null;
  }

  private async getAllTasks(filter?: TaskFilter): Promise<TaskDelegation[]> {
    // Implementation to retrieve all tasks with optional filtering
    // This would integrate with the task delegation service
    return [];
  }

  private async getTaskResult(taskId: string): Promise<TaskResult | null> {
    // Implementation to retrieve task result
    return null;
  }

  private async saveTaskResult(result: TaskResult, analytics: TaskAnalytics): Promise<void> {
    // Save result to database
    await this.firestoreService.saveMessage({
      userId: this.config.userId,
      agentId: 'status_tracker',
      content: JSON.stringify({ ...result, analytics }),
      type: 'agent',
      metadata: {
        type: 'task_result',
        taskId: result.taskId,
        success: result.success
      }
    });
  }

  private async markTaskStart(taskId: string): Promise<void> {
    // Mark task start time in database
    console.log(`Marking task ${taskId} as started`);
  }

  private async markTaskEnd(taskId: string, success: boolean): Promise<void> {
    // Mark task end time in database
    console.log(`Marking task ${taskId} as ended (${success ? 'success' : 'failure'})`);
  }

  private async handleTaskCancellation(taskId: string): Promise<void> {
    // Handle task cancellation cleanup
    this.activeProgress.delete(taskId);
    console.log(`Handling cancellation of task ${taskId}`);
  }

  private async sendTaskCompletionNotification(result: TaskResult, task: TaskDelegation): Promise<void> {
    // Send notification about task completion
    this.notifyListeners('task_completion_notification', { result, task });
  }

  private async saveCurrentState(): Promise<void> {
    // Save current state to database
    const state = {
      activeProgress: Array.from(this.activeProgress.entries()),
      statusHistory: Array.from(this.statusHistory.entries()),
      timestamp: new Date()
    };

    await this.firestoreService.saveMessage({
      userId: this.config.userId,
      agentId: 'status_tracker',
      content: JSON.stringify(state),
      type: 'agent',
      metadata: {
        type: 'state_snapshot',
        activeTasks: this.activeProgress.size
      }
    });
  }

  private notifyListeners(event: string, data: any): void {
    for (const [id, callback] of this.listeners) {
      try {
        callback({ event, data, timestamp: new Date() });
      } catch (error) {
        console.error(`Error in listener ${id}:`, error);
      }
    }
  }
}

export default TaskStatusTrackerService;