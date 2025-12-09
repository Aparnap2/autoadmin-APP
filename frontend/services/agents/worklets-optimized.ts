/**
 * Performance-optimized AutoAdmin Agents using react-native-worklets-core
 * Moves heavy computations to worklets for better UI performance
 */

import { runOnJS, runOnUI } from 'react-native-worklets-core';
import { BaseMessage } from '@langchain/core/messages';

import {
  AgentState,
  AgentResponse,
  TaskStatus,
  WorkletAgentConfig
} from './types';

// Worklet-compatible data structures
export interface WorkletAgentState {
  messages: Array<{
    type: 'human' | 'ai';
    content: string;
    timestamp: number;
  }>;
  currentAgent: string;
  taskStatus: {
    id: string;
    type: string;
    status: string;
    priority: string;
    createdAt: number;
    updatedAt: number;
  };
  performance: {
    startTime: number;
    responseTime?: number;
    operationsCompleted: number;
  };
}

export interface WorkletMetrics {
  cpuUsage: number;
  memoryUsage: number;
  processingTime: number;
  queueLength: number;
  throughput: number;
}

export interface WorkletTask {
  id: string;
  type: string;
  data: any;
  priority: number;
  createdAt: number;
  callback: (result: any) => void;
}

export class WorkletOptimizedAgents {
  private taskQueue: WorkletTask[] = [];
  private isProcessing = false;
  private metrics: WorkletMetrics = {
    cpuUsage: 0,
    memoryUsage: 0,
    processingTime: 0,
    queueLength: 0,
    throughput: 0
  };
  private config: WorkletAgentConfig;
  private callbacks: Map<string, Function> = new Map();

  constructor(config: WorkletAgentConfig) {
    this.config = config;
    this.setupPerformanceMonitoring();
  }

  /**
   * Process agent state in worklet for better performance
   */
  processAgentStateInWorklet = (
    state: AgentState,
    onComplete: (response: AgentResponse) => void
  ) => {
    'worklet';

    const startTime = Date.now();

    // Convert to worklet-compatible format
    const workletState: WorkletAgentState = {
      messages: state.messages.map(msg => ({
        type: msg.getType() === 'human' ? 'human' : 'ai',
        content: msg.content as string,
        timestamp: Date.now()
      })),
      currentAgent: state.currentAgent || 'ceo',
      taskStatus: {
        id: state.taskStatus?.id || '',
        type: state.taskStatus?.type || 'unknown',
        status: state.taskStatus?.status || 'pending',
        priority: state.taskStatus?.priority || 'medium',
        createdAt: state.taskStatus?.createdAt?.getTime() || Date.now(),
        updatedAt: state.taskStatus?.updatedAt?.getTime() || Date.now()
      },
      performance: {
        startTime: state.executionContext?.performance?.startTime?.getTime() || Date.now(),
        responseTime: state.executionContext?.performance?.responseTime,
        operationsCompleted: state.executionContext?.performance?.operationsCompleted || 0
      }
    };

    // Simulate processing with worklet optimization
    const response = this.simulateAgentProcessing(workletState);

    const processingTime = Date.now() - startTime;

    // Call completion callback on JS thread
    runOnJS(onComplete)({
      ...response,
      processingTime
    });
  };

  /**
   * Process message queue in worklet
   */
  processQueueInWorklet = () => {
    'worklet';

    if (this.isProcessing || this.taskQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.taskQueue.length > 0) {
      const task = this.taskQueue.shift();
      if (!task) continue;

      const startTime = Date.now();

      try {
        // Process task based on type
        let result;
        switch (task.type) {
          case 'message_processing':
            result = this.processMessageInWorklet(task.data);
            break;
          case 'task_delegation':
            result = this.delegateTaskInWorklet(task.data);
            break;
          case 'memory_search':
            result = this.searchMemoryInWorklet(task.data);
            break;
          case 'file_operation':
            result = this.performFileOperationInWorklet(task.data);
            break;
          default:
            result = { success: false, message: 'Unknown task type' };
        }

        const processingTime = Date.now() - startTime;

        // Update metrics
        this.updateMetrics(processingTime);

        // Call callback on JS thread
        runOnJS(task.callback)({
          ...result,
          processingTime,
          taskId: task.id
        });

      } catch (error) {
        runOnJS(task.callback)({
          success: false,
          error: error as string,
          taskId: task.id
        });
      }
    }

    this.isProcessing = false;
  };

  /**
   * Add task to queue with worklet processing
   */
  addTaskToQueue = (
    type: string,
    data: any,
    callback: (result: any) => void,
    priority: number = 0
  ): string => {
    const task: WorkletTask = {
      id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      data,
      priority,
      createdAt: Date.now(),
      callback
    };

    // Insert task based on priority
    const insertIndex = this.taskQueue.findIndex(t => t.priority < priority);
    if (insertIndex === -1) {
      this.taskQueue.push(task);
    } else {
      this.taskQueue.splice(insertIndex, 0, task);
    }

    // Process queue in worklet
    runOnUI(this.processQueueInWorklet)();

    return task.id;
  };

  /**
   * Process messages in chunks for better performance
   */
  processMessagesInChunks = (
    messages: BaseMessage[],
    chunkSize: number = this.config.chunkSize,
    onChunkComplete: (chunk: AgentResponse, index: number) => void
  ) => {
    'worklet';

    const chunks = [];
    for (let i = 0; i < messages.length; i += chunkSize) {
      chunks.push(messages.slice(i, i + chunkSize));
    }

    chunks.forEach((chunk, index) => {
      // Process each chunk in worklet
      const result = this.processMessageChunkInWorklet(chunk);

      // Call completion callback on JS thread
      runOnJS(onChunkComplete)(result, index);
    });
  };

  /**
   * Stream processing for large responses
   */
  streamProcessInWorklet = (
    input: string,
    onChunk: (chunk: string, isComplete: boolean) => void
  ) => {
    'worklet';

    const words = input.split(' ');
    const chunkSize = Math.max(1, Math.floor(words.length / 10)); // 10 chunks

    let currentIndex = 0;

    const processNextChunk = () => {
      if (currentIndex >= words.length) {
        runOnJS(onChunk)('', true); // Signal completion
        return;
      }

      const chunk = words.slice(currentIndex, currentIndex + chunkSize).join(' ');
      currentIndex += chunkSize;

      runOnJS(onChunk)(chunk, false);

      // Schedule next chunk
      setTimeout(processNextChunk, 50); // Small delay for UI responsiveness
    };

    processNextChunk();
  };

  /**
   * Private worklet methods
   */
  private simulateAgentProcessing = (state: WorkletAgentState): AgentResponse => {
    'worklet';

    // Simulate different processing based on current agent
    switch (state.currentAgent) {
      case 'strategy':
        return {
          success: true,
          message: `Strategy analysis completed for ${state.taskStatus.type}`,
          data: {
            insights: ['Market trend analysis', 'Competitive landscape review'],
            recommendations: ['Focus on mobile first', 'Increase marketing budget']
          },
          nextAction: {
            type: 'continue',
            target: 'ceo'
          }
        };

      case 'devops':
        return {
          success: true,
          message: `Technical analysis completed for ${state.taskStatus.type}`,
          data: {
            codeQuality: 85,
            performanceScore: 78,
            securityScore: 92,
            recommendations: ['Optimize bundle size', 'Add more tests']
          },
          nextAction: {
            type: 'continue',
            target: 'ceo'
          }
        };

      default:
        return {
          success: true,
          message: 'Task completed by CEO agent',
          nextAction: {
            type: 'complete'
          }
        };
    }
  };

  private processMessageInWorklet = (data: any): any => {
    'worklet';

    const { message, agent, context } = data;

    // Simulate message processing
    return {
      success: true,
      processed: true,
      response: `Processed message by ${agent}: ${message.substring(0, 50)}...`,
      timestamp: Date.now()
    };
  };

  private delegateTaskInWorklet = (data: any): any => {
    'worklet';

    const { task, targetAgent } = data;

    // Simulate task delegation
    return {
      success: true,
      delegated: true,
      targetAgent,
      taskId: `delegated_${Date.now()}`,
      estimatedTime: this.estimateProcessingTime(task.type, targetAgent)
    };
  };

  private searchMemoryInWorklet = (data: any): any => {
    'worklet';

    const { query, limit = 10 } = data;

    // Simulate memory search
    return {
      success: true,
      results: Array(Math.min(limit, 3)).fill(0).map((_, i) => ({
        id: `memory_${i}`,
        content: `Memory result ${i + 1} for query: ${query}`,
        relevance: 1 - (i * 0.2),
        timestamp: Date.now() - (i * 1000)
      }))
    };
  };

  private performFileOperationInWorklet = (data: any): any => {
    'worklet';

    const { operation, path, content } = data;

    // Simulate file operations
    return {
      success: true,
      operation,
      path,
      timestamp: Date.now(),
      size: content ? content.length : 0
    };
  };

  private processMessageChunkInWorklet = (chunk: BaseMessage[]): AgentResponse => {
    'worklet';

    return {
      success: true,
      message: `Processed chunk of ${chunk.length} messages`,
      processedCount: chunk.length,
      timestamp: Date.now()
    };
  };

  private estimateProcessingTime = (taskType: string, agentType: string): number => {
    'worklet';

    const baseTime = {
      'market_research': 15000,
      'financial_analysis': 10000,
      'code_analysis': 8000,
      'ui_ux_review': 6000,
      'technical_decision': 5000,
      'strategic_planning': 12000
    };

    const agentMultiplier = {
      'strategy': 1.2,
      'devops': 0.8,
      'ceo': 0.6
    };

    return (baseTime[taskType] || 8000) * (agentMultiplier[agentType] || 1);
  };

  private updateMetrics = (processingTime: number): void => {
    'worklet';

    this.metrics.processingTime = processingTime;
    this.metrics.queueLength = this.taskQueue.length;
    this.metrics.throughput = 1000 / processingTime; // Operations per second

    // Simulate CPU and memory usage
    this.metrics.cpuUsage = Math.min(100, this.metrics.cpuUsage + Math.random() * 10 - 5);
    this.metrics.memoryUsage = Math.min(100, this.metrics.memoryUsage + Math.random() * 5 - 2);
  };

  /**
   * Performance monitoring in worklet
   */
  private setupPerformanceMonitoring = (): void => {
    'worklet';

    // Monitor performance every second
    setInterval(() => {
      this.metrics.cpuUsage = Math.max(0, this.metrics.cpuUsage - 2);
      this.metrics.memoryUsage = Math.max(0, this.metrics.memoryUsage - 1);
    }, 1000);
  };

  /**
   * Get current metrics (called from JS thread)
   */
  getMetrics = (): WorkletMetrics => {
    return { ...this.metrics };
  };

  /**
   * Clear task queue
   */
  clearQueue = (): void => {
    this.taskQueue = [];
  };

  /**
   * Optimize performance based on metrics
   */
  optimizePerformance = (): void => {
    'worklet';

    if (this.metrics.cpuUsage > 80) {
      // Reduce concurrent operations
      this.config.maxWorkletConcurrency = Math.max(1, this.config.maxWorkletConcurrency - 1);
    }

    if (this.metrics.memoryUsage > 80) {
      // Reduce chunk size
      this.config.chunkSize = Math.max(100, this.config.chunkSize - 100);
    }

    if (this.metrics.throughput < 0.1 && this.metrics.queueLength > 10) {
      // Increase batch processing
      this.config.chunkSize = Math.min(1000, this.config.chunkSize + 100);
    }
  };

  /**
   * Reset to optimal configuration
   */
  resetConfiguration = (): void => {
    this.config = {
      useWorklets: true,
      maxWorkletConcurrency: 3,
      workletTimeout: 30000,
      enableStreaming: true,
      chunkSize: 1000
    };
  };
}

// Worklet utilities
export const WorkletUtils = {
  /**
   * Convert AgentState to worklet-compatible format
   */
  convertToWorkletState: (state: AgentState): WorkletAgentState => {
    'worklet';

    return {
      messages: state.messages.map(msg => ({
        type: msg.getType() === 'human' ? 'human' : 'ai',
        content: msg.content as string,
        timestamp: Date.now()
      })),
      currentAgent: state.currentAgent || 'ceo',
      taskStatus: {
        id: state.taskStatus?.id || '',
        type: state.taskStatus?.type || 'unknown',
        status: state.taskStatus?.status || 'pending',
        priority: state.taskStatus?.priority || 'medium',
        createdAt: state.taskStatus?.createdAt?.getTime() || Date.now(),
        updatedAt: state.taskStatus?.updatedAt?.getTime() || Date.now()
      },
      performance: {
        startTime: state.executionContext?.performance?.startTime?.getTime() || Date.now(),
        responseTime: state.executionContext?.performance?.responseTime,
        operationsCompleted: state.executionContext?.performance?.operationsCompleted || 0
      }
    };
  },

  /**
   * Validate worklet data
   */
  validateWorkletData: (data: any): boolean => {
    'worklet';

    return data && typeof data === 'object' && !Array.isArray(data);
  },

  /**
   * Create optimized task for worklet processing
   */
  createOptimizedTask: (
    type: string,
    data: any,
    priority: number = 0
  ): WorkletTask => {
    'worklet';

    return {
      id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      data: WorkletUtils.sanitizeData(data),
      priority,
      createdAt: Date.now(),
      callback: () => {} // Placeholder
    };
  },

  /**
   * Sanitize data for worklet processing
   */
  sanitizeData: (data: any): any => {
    'worklet';

    if (typeof data !== 'object' || data === null) {
      return data;
    }

    // Convert complex objects to simpler worklet-compatible format
    if (Array.isArray(data)) {
      return data.map(WorkletUtils.sanitizeData);
    }

    const sanitized: any = {};
    for (const key in data) {
      if (typeof data[key] === 'function') {
        continue; // Skip functions
      }
      if (typeof data[key] === 'object' && data[key] !== null) {
        sanitized[key] = WorkletUtils.sanitizeData(data[key]);
      } else {
        sanitized[key] = data[key];
      }
    }

    return sanitized;
  },

  /**
   * Batch process worklet tasks
   */
  batchProcess: (
    tasks: WorkletTask[],
    batchSize: number = 5,
    onBatchComplete: (results: any[]) => void
  ) => {
    'worklet';

    const results: any[] = [];

    for (let i = 0; i < tasks.length; i += batchSize) {
      const batch = tasks.slice(i, i + batchSize);
      const batchResults = batch.map(task => ({
        taskId: task.id,
        success: true,
        processed: true,
        timestamp: Date.now()
      }));

      results.push(...batchResults);

      // Call completion callback for each batch
      runOnJS(onBatchComplete)(batchResults);
    }

    return results;
  }
};

export default WorkletOptimizedAgents;