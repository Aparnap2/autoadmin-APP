/**
 * Task Manager Hook
 * Integrates local agent system with FastAPI backend for unified task management
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { BaseMessage } from '@langchain/core/messages';

import { useAutoAdminAgents, UseAutoAdminAgentsOptions } from './useAutoAdminAgents';
import { getAgentAPIService, AgentAPIService } from '@/services/api/agent-api';
import { AgentTaskResponse } from '@/services/api/fastapi-client';
import { TaskStatus, TaskType, AgentResponse } from '@/services/agents/types';

export interface UseTaskManagerOptions extends UseAutoAdminAgentsOptions {
  syncWithBackend?: boolean;
  enableRealtimeSync?: boolean;
  backendURL?: string;
  autoSyncInterval?: number; // milliseconds
}

export interface UseTaskManagerReturn {
  // Existing agent system
  agents: ReturnType<typeof useAutoAdminAgents>;

  // Backend tasks
  backendTasks: AgentTaskResponse[];
  backendStats: any;
  backendLoading: boolean;
  backendError: Error | null;

  // Unified tasks (local + backend)
  allTasks: Array<TaskStatus | AgentTaskResponse>;
  unifiedStats: {
    totalTasks: number;
    pendingTasks: number;
    processingTasks: number;
    completedTasks: number;
    failedTasks: number;
    successRate: number;
  };

  // Backend operations
  createBackendTask: (task: any) => Promise<AgentTaskResponse>;
  cancelBackendTask: (taskId: string) => Promise<void>;
  retryBackendTask: (taskId: string) => Promise<AgentTaskResponse>;
  refreshBackendTasks: () => Promise<void>;

  // Unified operations
  executeTaskWithTracking: (description: string, taskType: TaskType, context?: any) => Promise<AgentResponse>;
  syncLocalToBackend: () => Promise<void>;
  cancelAllTasks: () => Promise<void>;

  // Connection status
  backendConnected: boolean;
  syncStatus: 'idle' | 'syncing' | 'error' | 'success';

  // Cleanup
  cleanup: () => Promise<void>;
}

export function useTaskManager(options: UseTaskManagerOptions): UseTaskManagerReturn {
  const [backendTasks, setBackendTasks] = useState<AgentTaskResponse[]>([]);
  const [backendStats, setBackendStats] = useState<any>(null);
  const [backendLoading, setBackendLoading] = useState(false);
  const [backendError, setBackendError] = useState<Error | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error' | 'success'>('idle');

  const agents = useAutoAdminAgents(options);
  const agentServiceRef = useRef<AgentAPIService | null>(null);
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize agent service
  useEffect(() => {
    const initService = async () => {
      try {
        const service = getAgentAPIService({
          syncWithBackend: options.syncWithBackend ?? false, // Changed from true to false to disable backend sync by default
          enableRealTimeUpdates: options.enableRealtimeSync ?? false, // Changed from true to false to disable real-time updates by default
        });

        agentServiceRef.current = service;

        // Check backend connection
        await service.healthCheck();
        setBackendConnected(true);
        setBackendError(null);

        // Set up real-time listeners
        if (options.enableRealtimeSync) {
          await service.connectRealtimeUpdates();

          service.addRealtimeListener('task_update', (data) => {
            if (Array.isArray(data?.tasks)) {
              // Handle polling-style task updates
              setBackendTasks(data.tasks);
            } else {
              // Handle individual task updates
              setBackendTasks(prev => {
                const index = prev.findIndex(t => t.id === data.id);
                if (index >= 0) {
                  const newTasks = [...prev];
                  newTasks[index] = data;
                  return newTasks;
                }
                return [...prev, data];
              });
            }
          });

          service.addRealtimeListener('agent_status', (data) => {
            console.log('Agent status update:', data);
          });
        }

        // Load initial tasks
        await refreshBackendTasks();

      } catch (error) {
        console.warn('Backend connection failed, using local agents only:', error);
        setBackendConnected(false);
        setBackendError(error as Error);
      }
    };

    initService();

    return () => {
      if (agentServiceRef.current) {
        agentServiceRef.current.disconnectRealtimeUpdates();
      }
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    };
  }, [options.syncWithBackend, options.enableRealtimeSync]);

  // Set up auto-sync interval
  useEffect(() => {
    if (options.syncWithBackend && options.autoSyncInterval && backendConnected) {
      syncIntervalRef.current = setInterval(() => {
        refreshBackendTasks().catch(console.error);
      }, options.autoSyncInterval);

      return () => {
        if (syncIntervalRef.current) {
          clearInterval(syncIntervalRef.current);
        }
      };
    }
  }, [options.syncWithBackend, options.autoSyncInterval, backendConnected]);

  // Refresh backend tasks
  const refreshBackendTasks = useCallback(async () => {
    if (!agentServiceRef.current || !backendConnected) return;

    try {
      setBackendLoading(true);
      const tasks = await agentServiceRef.current.getTasks();
      setBackendTasks(tasks);

      const stats = await agentServiceRef.current.getTaskStats();
      setBackendStats(stats);

      setBackendError(null);
    } catch (error) {
      console.error('Error refreshing backend tasks:', error);
      setBackendError(error as Error);
    } finally {
      setBackendLoading(false);
    }
  }, [backendConnected]);

  // Create backend task
  const createBackendTask = useCallback(async (taskData: any): Promise<AgentTaskResponse> => {
    if (!agentServiceRef.current) {
      throw new Error('Agent service not initialized');
    }

    try {
      const task = await agentServiceRef.current.createTask(taskData);
      await refreshBackendTasks();
      return task;
    } catch (error) {
      console.error('Error creating backend task:', error);
      throw error;
    }
  }, [refreshBackendTasks]);

  // Cancel backend task
  const cancelBackendTask = useCallback(async (taskId: string): Promise<void> => {
    if (!agentServiceRef.current) {
      throw new Error('Agent service not initialized');
    }

    try {
      await agentServiceRef.current.cancelTask(taskId);
      await refreshBackendTasks();
    } catch (error) {
      console.error('Error cancelling backend task:', error);
      throw error;
    }
  }, [refreshBackendTasks]);

  // Retry backend task
  const retryBackendTask = useCallback(async (taskId: string): Promise<AgentTaskResponse> => {
    if (!agentServiceRef.current) {
      throw new Error('Agent service not initialized');
    }

    try {
      const task = await agentServiceRef.current.retryTask(taskId);
      await refreshBackendTasks();
      return task;
    } catch (error) {
      console.error('Error retrying backend task:', error);
      throw error;
    }
  }, [refreshBackendTasks]);

  // Execute task with backend tracking
  const executeTaskWithTracking = useCallback(async (
    description: string,
    taskType: TaskType,
    context?: any
  ): Promise<AgentResponse> => {
    if (!agentServiceRef.current) {
      throw new Error('Agent service not initialized');
    }

    try {
      if (backendConnected) {
        // Create task in backend first
        const backendTask = await createBackendTask({
          type: taskType,
          description,
          priority: 'medium',
          metadata: { context, source: 'local_orchestrator' },
        });

        // Execute locally
        const response = await agents.sendMessage(description, context);

        // Update backend task with result
        if (response.success) {
          await agentServiceRef.current!.updateTask(backendTask.id, {
            metadata: {
              ...backendTask.metadata,
              result: response.data,
              completed_at: new Date().toISOString()
            }
          });
        } else {
          await agentServiceRef.current!.updateTask(backendTask.id, {
            metadata: {
              ...backendTask.metadata,
              error: response.message,
              failed_at: new Date().toISOString()
            }
          });
        }

        return response;
      } else {
        // Execute locally only
        return await agents.sendMessage(description, context);
      }
    } catch (error) {
      console.error('Error executing task with tracking:', error);
      throw error;
    }
  }, [backendConnected, createBackendTask, agents.sendMessage]);

  // Sync local tasks to backend
  const syncLocalToBackend = useCallback(async (): Promise<void> => {
    if (!agentServiceRef.current || !backendConnected) {
      console.warn('Cannot sync: backend not connected');
      return;
    }

    try {
      setSyncStatus('syncing');

      // Get local agent state
      const localState = agents.state;
      const localTasks = localState?.taskStatus || [];

      // Sync each local task with backend
      for (const localTask of localTasks) {
        if (localTask.id && !backendTasks.find(t => t.id === localTask.id)) {
          // Task exists locally but not in backend, create it
          await createBackendTask({
            type: localTask.type,
            description: localTask.metadata?.description || 'Local task',
            priority: localTask.priority,
            metadata: {
              ...localTask.metadata,
              source: 'local_sync',
              local_task_id: localTask.id
            },
            input_data: localTask.metadata?.input_data
          });
        }
      }

      setSyncStatus('success');
      setTimeout(() => setSyncStatus('idle'), 3000);
    } catch (error) {
      console.error('Error syncing local to backend:', error);
      setSyncStatus('error');
      setTimeout(() => setSyncStatus('idle'), 3000);
    }
  }, [backendConnected, agents.state, backendTasks, createBackendTask]);

  // Cancel all tasks
  const cancelAllTasks = useCallback(async (): Promise<void> => {
    try {
      // Cancel local agent operations
      // (Implementation depends on your agent system)

      // Cancel backend tasks
      const pendingTasks = backendTasks.filter(t => t.status === 'pending' || t.status === 'processing');
      await Promise.all(
        pendingTasks.map(task => cancelBackendTask(task.id))
      );

      await refreshBackendTasks();
    } catch (error) {
      console.error('Error cancelling all tasks:', error);
      throw error;
    }
  }, [backendTasks, cancelBackendTask, refreshBackendTasks]);

  // Combine local and backend tasks
  const allTasks = Array<TaskStatus | AgentTaskResponse>();
  if (agents.state?.taskStatus) {
    allTasks.push(...agents.state.taskStatus);
  }
  allTasks.push(...backendTasks);

  // Calculate unified stats
  const unifiedStats = {
    totalTasks: allTasks.length,
    pendingTasks: allTasks.filter(t => t.status === 'pending').length,
    processingTasks: allTasks.filter(t => t.status === 'processing').length,
    completedTasks: allTasks.filter(t => t.status === 'completed').length,
    failedTasks: allTasks.filter(t => t.status === 'failed').length,
    successRate: 0,
  };

  const finishedTasks = allTasks.filter(t => t.status === 'completed' || t.status === 'failed');
  if (finishedTasks.length > 0) {
    unifiedStats.successRate = (unifiedStats.completedTasks / finishedTasks.length) * 100;
  }

  // Cleanup
  const cleanup = useCallback(async (): Promise<void> => {
    if (agentServiceRef.current) {
      agentServiceRef.current.disconnectRealtimeUpdates();
    }
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
    }
    await agents.cleanup();
  }, [agents.cleanup]);

  return {
    agents,
    backendTasks,
    backendStats,
    backendLoading,
    backendError,
    allTasks,
    unifiedStats,
    createBackendTask,
    cancelBackendTask,
    retryBackendTask,
    refreshBackendTasks,
    executeTaskWithTracking,
    syncLocalToBackend,
    cancelAllTasks,
    backendConnected,
    syncStatus,
    cleanup,
  };
}

export default useTaskManager;