/**
 * Agent API Service
 * Specific API calls for agent operations
 * Integrates with existing agent orchestrator and FastAPI backend
 */

import { TaskStatus, TaskType, AgentResponse } from '../agents/types';
import FastAPIClient, { AgentTaskRequest, AgentTaskResponse, AgentStatus } from './fastapi-client';
import { RequestValidators } from './api-validator';
import { ValidationError } from './api-validator';

export interface TaskManagerConfig {
  syncWithBackend: boolean;
  enableRealTimeUpdates: boolean;
  autoRetryFailedTasks: boolean;
  maxConcurrentTasks: number;
}

export interface TaskFilter {
  status?: TaskStatus['status'][];
  type?: TaskType[];
  priority?: TaskStatus['priority'][];
  agent?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface TaskStats {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  delegated: number;
  successRate: number;
  averageProcessingTime: number;
}

class AgentAPIService {
  private fastapiClient: FastAPIClient;
  private config: TaskManagerConfig;
  private taskCache: Map<string, AgentTaskResponse> = new Map();
  private agentCache: Map<string, AgentStatus> = new Map();

  constructor(config: Partial<TaskManagerConfig> = {}) {
    this.fastapiClient = new FastAPIClient();
    this.config = {
      syncWithBackend: false, // Changed from true to false to disable backend sync by default
      enableRealTimeUpdates: false, // Changed from true to false to disable real-time updates by default
      autoRetryFailedTasks: false,
      maxConcurrentTasks: 5,
      ...config
    };

    // Set up real-time listeners if real-time updates are enabled
    if (this.config.enableRealTimeUpdates) {
      this.setupRealtimeListeners();
    }
  }

  private setupRealtimeListeners(): void {
    this.fastapiClient.addRealtimeListener('task_update', (data) => {
      if (Array.isArray(data?.tasks)) {
        // Handle polling-style task updates
        data.tasks.forEach(task => this.updateTaskCache(task));
      } else {
        // Handle individual task updates
        this.updateTaskCache(data);
      }
    });

    this.fastapiClient.addRealtimeListener('agent_status', (data) => {
      if (Array.isArray(data?.agents)) {
        // Handle polling-style agent updates
        data.agents.forEach(agent => this.updateAgentCache(agent));
      } else {
        // Handle individual agent updates
        this.updateAgentCache(data);
      }
    });
  }

  private updateTaskCache(taskData: AgentTaskResponse): void {
    this.taskCache.set(taskData.id, taskData);
  }

  private updateAgentCache(agentData: AgentStatus): void {
    this.agentCache.set(agentData.id, agentData);
  }

  /**
   * Task Management Operations
   */

  // Get all tasks with optional filtering
  async getTasks(filter?: TaskFilter): Promise<AgentTaskResponse[]> {
    // Only fetch from backend if sync is enabled
    if (!this.config.syncWithBackend) {
      // Return cached/local tasks only
      return this.getCachedTasks();
    }

    try {
      const params: any = {};

      if (filter?.status) {
        params.status = filter.status.join(',');
      }
      if (filter?.type) {
        params.type = filter.type.join(',');
      }
      if (filter?.priority) {
        params.priority = filter.priority.join(',');
      }
      if (filter?.agent) {
        params.agent_id = filter.agent.join(',');
      }

      const response = await this.fastapiClient.getTasks(params);

      if (response.success && response.data) {
        const tasks = response.data.tasks;

        // Update cache
        tasks.forEach(task => this.updateTaskCache(task));

        // Apply additional filtering for date range
        let filteredTasks = tasks;
        if (filter?.dateRange) {
          filteredTasks = tasks.filter(task => {
            const taskDate = new Date(task.created_at);
            return taskDate >= filter.dateRange!.start && taskDate <= filter.dateRange!.end;
          });
        }

        return filteredTasks;
      }

      throw new Error(response.error || 'Failed to fetch tasks');
    } catch (error) {
      console.error('Error fetching tasks:', error);
      throw error;
    }
  }

  // Get specific task
  async getTask(taskId: string): Promise<AgentTaskResponse> {
    try {
      // Check cache first
      if (this.taskCache.has(taskId)) {
        return this.taskCache.get(taskId)!;
      }

      const response = await this.fastapiClient.getTask(taskId);

      if (response.success && response.data) {
        this.updateTaskCache(response.data);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch task');
    } catch (error) {
      console.error(`Error fetching task ${taskId}:`, error);
      throw error;
    }
  }

  // Create new task
  async createTask(request: Omit<AgentTaskRequest, 'id' | 'created_at' | 'updated_at'>): Promise<AgentTaskResponse> {
    try {
      // Validate request data
      const validation = RequestValidators.validateAgentTaskRequest(request);
      if (!validation.isValid) {
        throw new ValidationError(validation.errors);
      }

      // Use sanitized data
      const response = await this.fastapiClient.createTask(validation.sanitized as AgentTaskRequest);

      if (response.success && response.data) {
        this.updateTaskCache(response.data);
        return response.data;
      }

      throw new Error(response.error || 'Failed to create task');
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    }
  }

  // Update task
  async updateTask(taskId: string, updates: Partial<AgentTaskRequest>): Promise<AgentTaskResponse> {
    try {
      const response = await this.fastapiClient.updateTask(taskId, updates);

      if (response.success && response.data) {
        this.updateTaskCache(response.data);
        return response.data;
      }

      throw new Error(response.error || 'Failed to update task');
    } catch (error) {
      console.error(`Error updating task ${taskId}:`, error);
      throw error;
    }
  }

  // Cancel task
  async cancelTask(taskId: string): Promise<void> {
    try {
      const response = await this.fastapiClient.cancelTask(taskId);

      if (response.success) {
        // Update cache to reflect cancellation
        const cachedTask = this.taskCache.get(taskId);
        if (cachedTask) {
          cachedTask.status = 'failed';
          cachedTask.error = 'Task cancelled by user';
          this.updateTaskCache(cachedTask);
        }
        return;
      }

      throw new Error(response.error || 'Failed to cancel task');
    } catch (error) {
      console.error(`Error cancelling task ${taskId}:`, error);
      throw error;
    }
  }

  // Retry failed task
  async retryTask(taskId: string): Promise<AgentTaskResponse> {
    try {
      const task = await this.getTask(taskId);

      if (task.status !== 'failed') {
        throw new Error('Only failed tasks can be retried');
      }

      const retryRequest: Omit<AgentTaskRequest, 'id' | 'created_at' | 'updated_at'> = {
        type: task.type,
        description: task.description || '',
        priority: task.priority as any,
        assigned_to: task.assigned_to,
        metadata: { ...task.metadata, original_task_id: taskId, is_retry: true },
        input_data: task.metadata?.input_data
      };

      return await this.createTask(retryRequest);
    } catch (error) {
      console.error(`Error retrying task ${taskId}:`, error);
      throw error;
    }
  }

  /**
   * Agent Operations
   */

  // Get all agents
  async getAgents(): Promise<AgentStatus[]> {
    // Only fetch from backend if sync is enabled
    if (!this.config.syncWithBackend) {
      // Return cached agents only
      return this.getCachedAgents();
    }

    try {
      const response = await this.fastapiClient.getAgents();

      if (response.success && response.data) {
        // Update cache
        response.data.forEach(agent => this.updateAgentCache(agent));
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch agents');
    } catch (error) {
      console.error('Error fetching agents:', error);
      throw error;
    }
  }

  // Get specific agent
  async getAgent(agentId: string): Promise<AgentStatus> {
    try {
      // Check cache first
      if (this.agentCache.has(agentId)) {
        return this.agentCache.get(agentId)!;
      }

      const response = await this.fastapiClient.getAgent(agentId);

      if (response.success && response.data) {
        this.updateAgentCache(response.data);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch agent');
    } catch (error) {
      console.error(`Error fetching agent ${agentId}:`, error);
      throw error;
    }
  }

  // Get agent status
  async getAgentStatus(agentId: string): Promise<AgentStatus> {
    try {
      const response = await this.fastapiClient.getAgentStatus(agentId);

      if (response.success && response.data) {
        this.updateAgentCache(response.data);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch agent status');
    } catch (error) {
      console.error(`Error fetching agent status ${agentId}:`, error);
      throw error;
    }
  }

  // Trigger agent task
  async triggerAgentTask(request: Omit<AgentTaskRequest, 'id' | 'created_at' | 'updated_at'>): Promise<AgentTaskResponse> {
    try {
      // Validate request data
      const validation = RequestValidators.validateAgentTaskRequest(request);
      if (!validation.isValid) {
        throw new ValidationError(validation.errors);
      }

      // Use swarm process with validated data
      const response = await this.fastapiClient.processWithSwarm({
        message: validation.sanitized.description,
        context: { ...validation.sanitized.metadata, task_type: validation.sanitized.type }
      });

      if (response.success && response.data) {
        // Cache the task if it exists in response
        if (response.data.task) {
          this.updateTaskCache(response.data.task);
        }
        return response.data.task || response.data;
      }

      throw new Error(response.error || 'Failed to trigger agent task');
    } catch (error) {
      console.error('Error triggering agent task:', error);
      throw error;
    }
  }

  /**
   * Analytics and Statistics
   */

  // Get task statistics
  async getTaskStats(filter?: TaskFilter): Promise<TaskStats> {
    try {
      const tasks = await this.getTasks(filter);

      const stats: TaskStats = {
        total: tasks.length,
        pending: tasks.filter(t => t.status === 'pending').length,
        processing: tasks.filter(t => t.status === 'processing').length,
        completed: tasks.filter(t => t.status === 'completed').length,
        failed: tasks.filter(t => t.status === 'failed').length,
        delegated: tasks.filter(t => t.status === 'delegated').length,
        successRate: 0,
        averageProcessingTime: 0
      };

      // Calculate success rate
      const finishedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'failed');
      if (finishedTasks.length > 0) {
        stats.successRate = (stats.completed / finishedTasks.length) * 100;
      }

      // Calculate average processing time
      const completedTasks = tasks.filter(t => t.status === 'completed');
      if (completedTasks.length > 0) {
        const totalTime = completedTasks.reduce((sum, task) => {
          const created = new Date(task.created_at).getTime();
          const updated = new Date(task.updated_at).getTime();
          return sum + (updated - created);
        }, 0);
        stats.averageProcessingTime = totalTime / completedTasks.length;
      }

      return stats;
    } catch (error) {
      console.error('Error calculating task stats:', error);
      throw error;
    }
  }

  /**
   * Integration with Local Agent System
   */

  // Sync local agent state with backend
  async syncWithBackend(localAgentSystem: any): Promise<void> {
    try {
      if (!this.config.syncWithBackend) {
        return;
      }

      // Get local agent state
      const localState = localAgentSystem.getState();
      const localTasks = localState.taskStatus || [];

      // Sync each local task with backend
      for (const localTask of localTasks) {
        if (localTask.id && !this.taskCache.has(localTask.id)) {
          // Task exists locally but not in backend, create it
          await this.createTask({
            type: localTask.type,
            description: localTask.metadata?.description || 'Local task',
            priority: localTask.priority,
            metadata: { ...localTask.metadata, source: 'local' },
            input_data: localTask.metadata?.input_data
          });
        }
      }

      console.log('Backend sync completed');
    } catch (error) {
      console.error('Error syncing with backend:', error);
      throw error;
    }
  }

  // Bridge local agent execution with backend tracking
  async executeTaskWithBackendTracking(
    localAgentSystem: any,
    taskDescription: string,
    taskType: TaskType,
    context?: any
  ): Promise<AgentResponse> {
    try {
      // Create task in backend first
      const backendTask = await this.createTask({
        type: taskType,
        description: taskDescription,
        priority: 'medium',
        metadata: { context, source: 'local_orchestrator' }
      });

      // Execute task locally
      const response = await localAgentSystem.processUserMessage(taskDescription, context);

      // Update backend task with result
      if (response.success) {
        await this.updateTask(backendTask.id, {
          metadata: { ...backendTask.metadata, result: response.data, completed_at: new Date().toISOString() }
        });
      } else {
        await this.updateTask(backendTask.id, {
          metadata: { ...backendTask.metadata, error: response.message, failed_at: new Date().toISOString() }
        });
      }

      return response;
    } catch (error) {
      console.error('Error executing task with backend tracking:', error);
      throw error;
    }
  }

  /**
   * Utility Methods
   */

  // Clear caches
  clearCaches(): void {
    this.taskCache.clear();
    this.agentCache.clear();
  }

  // Get cached tasks
  getCachedTasks(): AgentTaskResponse[] {
    return Array.from(this.taskCache.values());
  }

  // Get cached agents
  getCachedAgents(): AgentStatus[] {
    const cached = Array.from(this.agentCache.values());
    if (cached.length === 0) {
      // Return default agents when cache is empty
      return [
        {
          id: 'ceo',
          type: 'ceo',
          name: 'CEO Agent',
          status: 'idle',
          capabilities: ['coordination', 'decision_making', 'general_assistance'],
          description: 'Coordinates tasks and provides general assistance'
        },
        {
          id: 'strategy',
          type: 'strategy',
          name: 'Strategy Agent',
          status: 'idle',
          capabilities: ['market_research', 'financial_analysis', 'strategic_planning'],
          description: 'Handles market research and strategic planning'
        },
        {
          id: 'devops',
          type: 'devops',
          name: 'DevOps Agent',
          status: 'idle',
          capabilities: ['code_analysis', 'ui_ux_review', 'technical_decisions'],
          description: 'Handles technical analysis and decisions'
        }
      ];
    }
    return cached;
  }

  // Connect real-time updates
  async connectRealtimeUpdates(): Promise<void> {
    await this.fastapiClient.connectRealtimeUpdates();
  }

  // Disconnect real-time updates
  disconnectRealtimeUpdates(): void {
    this.fastapiClient.disconnectRealtimeUpdates();
  }

  // Legacy WebSocket methods for backward compatibility
  async connectWebSocket(): Promise<void> {
    console.warn('connectWebSocket() is deprecated, use connectRealtimeUpdates() instead');
    return this.connectRealtimeUpdates();
  }

  disconnectWebSocket(): void {
    console.warn('disconnectWebSocket() is deprecated, use disconnectRealtimeUpdates() instead');
    this.disconnectRealtimeUpdates();
  }

  // Health check for backend connectivity
  async healthCheck(): Promise<{ success: boolean; status: string; timestamp: string }> {
    // Only check backend if sync is enabled
    if (!this.config.syncWithBackend) {
      return {
        success: true,
        status: 'local_only',
        timestamp: new Date().toISOString()
      };
    }

    try {
      const response = await this.fastapiClient.healthCheck();

      if (response.success) {
        return {
          success: true,
          status: response.data?.status || 'healthy',
          timestamp: response.timestamp
        };
      } else {
        return {
          success: false,
          status: response.error || 'unhealthy',
          timestamp: response.timestamp
        };
      }
    } catch (error) {
      console.error('Health check failed:', error);
      return {
        success: false,
        status: 'unhealthy',
        timestamp: new Date().toISOString()
      };
    }
  }

  // Update configuration
  updateConfig(newConfig: Partial<TaskManagerConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
}

// Singleton instance
let agentAPIService: AgentAPIService | null = null;

export function getAgentAPIService(config?: Partial<TaskManagerConfig>): AgentAPIService {
  if (!agentAPIService) {
    agentAPIService = new AgentAPIService(config);
  }
  return agentAPIService;
}

export default AgentAPIService;