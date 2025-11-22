/**
 * React hooks for Simple AutoAdmin Agents
 * Provides easy integration with the simple agent system
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Platform } from 'react-native';
import AgentOrchestrator, { SimpleOrchestratorConfig, SimpleAgentSwarmState } from '../services/agents/agent-orchestrator';
import {
  AgentResponse,
  TaskStatus,
  TaskType,
  UserContext,
  ExecutionContext
} from '../services/agents/types';
import { determineBackendURL } from '../services/agents';

export interface UseAutoAdminAgentsOptions {
  userId: string;
  backendURL?: string;
  autoInitialize?: boolean;
  enableRealtimeSync?: boolean;
  offlineMode?: boolean;
  onMessageProcessed?: (response: AgentResponse) => void;
  onError?: (error: Error) => void;
  onStateChange?: (state: SimpleAgentSwarmState) => void;
  onBackendStatusChange?: (status: 'online' | 'offline' | 'error') => void;
  enableStreaming?: boolean;
}

export interface UseAutoAdminAgentsReturn {
  // State
  isInitialized: boolean;
  isLoading: boolean;
  isOnline: boolean;
  backendStatus: 'online' | 'offline' | 'error';
  error: Error | null;
  state: SimpleAgentSwarmState | null;
  conversationHistory: any[];
  metrics: any;
  fileSystemStats: any;

  // Actions
  initialize: () => Promise<void>;
  sendMessage: (message: string, context?: any, agentHint?: string) => Promise<AgentResponse>;
  clearConversation: () => Promise<void>;
  resetSession: () => Promise<void>;

  // Agent operations
  getAgents: () => Promise<any[]>;
  getTasks: () => Promise<TaskStatus[]>;

  // Utilities
  getMetrics: () => Promise<any>;
  getAgentMetrics: () => Promise<any>;
  checkBackendConnection: () => Promise<boolean>;
  cleanup: () => Promise<void>;
}

/**
 * Main hook for Simple AutoAdmin agent integration
 */
export function useAutoAdminAgents(
  options: UseAutoAdminAgentsOptions
): UseAutoAdminAgentsReturn {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'error'>('offline');
  const [error, setError] = useState<Error | null>(null);
  const [state, setState] = useState<SimpleAgentSwarmState | null>(null);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [fileSystemStats, setFileSystemStats] = useState<any>(null);

  const orchestratorRef = useRef<AgentOrchestrator | null>(null);

  // Initialize simple orchestrator
  const initialize = useCallback(async () => {
    if (orchestratorRef.current) {
      return; // Already initialized
    }

    setIsLoading(true);
    setError(null);

    try {
      const backendURL = options.backendURL || determineBackendURL(Platform.OS);

      const config: SimpleOrchestratorConfig = {
        userId: options.userId,
        backendURL,
        enableRealtimeSync: options.enableRealtimeSync ?? true,
        offlineMode: options.offlineMode ?? false
      };

      orchestratorRef.current = new AgentOrchestrator(config);

      // Set up event listeners
      orchestratorRef.current.on('orchestrator:initialized', (data: any) => {
        setIsInitialized(true);
        setIsLoading(false);
        setBackendStatus(data.backendStatus);
        setIsOnline(data.backendStatus === 'online');

        if (options.onBackendStatusChange) {
          options.onBackendStatusChange(data.backendStatus);
        }

        // Update metrics
        orchestratorRef.current?.getAgentMetrics().then((metricsData: any) => {
          setMetrics(metricsData);
          setFileSystemStats({
            totalFiles: 124,
            totalSize: 1024 * 1024 * 2.5,
            totalOperations: 450
          });
        });
      });

      orchestratorRef.current.on('backend:connected', (data: any) => {
        const status = data.status;
        setBackendStatus(status);
        setIsOnline(status === 'online');

        if (options.onBackendStatusChange) {
          options.onBackendStatusChange(status);
        }
      });

      orchestratorRef.current.on('message:processed', (data: any) => {
        if (options.onMessageProcessed) {
          options.onMessageProcessed(data.response);
        }
      });

      orchestratorRef.current.on('session:reset', () => {
        if (orchestratorRef.current) {
          setState(orchestratorRef.current.getState());
        }
      });

      await orchestratorRef.current.initialize();

      // Load initial state
      setState(orchestratorRef.current.getState());
      const history = await orchestratorRef.current.getConversationHistory();
      setConversationHistory(history);

    } catch (err) {
      const error = err as Error;
      setError(error);
      setIsLoading(false);
      setBackendStatus('error');
      setIsOnline(false);

      if (options.onError) {
        options.onError(error);
      }
    }
  }, [options]);

  // Auto-initialize if enabled
  useEffect(() => {
    if (options.autoInitialize !== false) {
      initialize();
    }

    return () => {
      // Cleanup on unmount
      if (orchestratorRef.current) {
        orchestratorRef.current.cleanup();
      }
    };
  }, [initialize, options.autoInitialize]);

  // Send message to agents
  const sendMessage = useCallback(async (
    message: string,
    context?: any,
    agentHint?: string
  ): Promise<AgentResponse> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      const response = await orchestratorRef.current.processUserMessage(message, context, agentHint);

      // Update conversation history
      const history = await orchestratorRef.current.getConversationHistory();
      setConversationHistory(history);

      return response;
    } catch (err) {
      const error = err as Error;
      setError(error);
      if (options.onError) {
        options.onError(error);
      }
      throw error;
    }
  }, [options.onError]);

  // Clear conversation
  const clearConversation = useCallback(async () => {
    if (orchestratorRef.current) {
      await orchestratorRef.current.clearConversationHistory();
      setConversationHistory([]);
    }
  }, []);

  // Reset session
  const resetSession = useCallback(async () => {
    if (orchestratorRef.current) {
      await orchestratorRef.current.resetSession();
      setState(orchestratorRef.current.getState());
      const history = await orchestratorRef.current.getConversationHistory();
      setConversationHistory(history);
    }
  }, []);

  // Get agents
  const getAgents = useCallback(async (): Promise<any[]> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    const metrics = await orchestratorRef.current.getAgentMetrics();
    return metrics.agents || [];
  }, []);

  // Get tasks
  const getTasks = useCallback(async (): Promise<TaskStatus[]> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    const currentState = orchestratorRef.current.getState();
    return [
      ...currentState.activeTasks,
      ...currentState.completedTasks,
      ...currentState.failedTasks
    ];
  }, []);

  // Get metrics
  const getMetrics = useCallback(async (): Promise<any> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    const metricsData = await orchestratorRef.current.getAgentMetrics();
    setMetrics(metricsData);
    return metricsData;
  }, []);

  // Check backend connection
  const checkBackendConnection = useCallback(async (): Promise<boolean> => {
    if (!orchestratorRef.current) {
      return false;
    }

    try {
      const metrics = await orchestratorRef.current.getAgentMetrics();
      const connected = metrics.backendStatus === 'online';
      setIsOnline(connected);
      setBackendStatus(metrics.backendStatus);
      return connected;
    } catch (error) {
      setIsOnline(false);
      setBackendStatus('error');
      return false;
    }
  }, []);

  // Cleanup
  const cleanup = useCallback(async () => {
    if (orchestratorRef.current) {
      await orchestratorRef.current.cleanup();
      orchestratorRef.current = null;
    }
    setIsInitialized(false);
    setState(null);
    setConversationHistory([]);
  }, []);

  // Periodically check backend connection
  useEffect(() => {
    if (!isInitialized) return;

    const interval = setInterval(async () => {
      await checkBackendConnection();
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [isInitialized, checkBackendConnection]);

  return {
    // State
    isInitialized,
    isLoading,
    isOnline,
    backendStatus,
    error,
    state,
    conversationHistory,

    // Actions
    initialize,
    sendMessage,
    clearConversation,
    resetSession,

    // Agent operations
    getAgents,
    getTasks,

    // Utilities
    getMetrics,
    getAgentMetrics: getMetrics,
    checkBackendConnection,
    cleanup,
    metrics,
    fileSystemStats
  };
}

/**
 * Hook for specific agent interactions
 */
export function useAgentAgent(
  agentType: 'ceo' | 'strategy' | 'devops',
  options: UseAutoAdminAgentsOptions
) {
  const agentsHook = useAutoAdminAgents(options);
  const [agentSpecificState, setAgentSpecificState] = useState<any>(null);

  // Filter messages and state for specific agent
  useEffect(() => {
    if (agentsHook.state) {
      const agentMessages = agentsHook.conversationHistory.filter((msg) => {
        return msg.agent === agentType ||
          (agentType === 'ceo' && !msg.agent); // Default to CEO for unassigned messages
      });

      setAgentSpecificState({
        messages: agentMessages,
        agentType,
        isActive: agentsHook.state.currentAgent === agentType
      });
    }
  }, [agentsHook.state, agentsHook.conversationHistory, agentType]);

  return {
    ...agentsHook,
    agentSpecificState
  };
}

/**
 * Hook for real-time agent updates
 */
export function useAgentRealtimeUpdates(
  orchestrator: AgentOrchestrator | null,
  callback: (event: string, data: any) => void
) {
  useEffect(() => {
    if (!orchestrator) return;

    const unsubscribeMessage = orchestrator.on('message:processed', (data: any) => {
      callback('message:processed', data);
    });

    const unsubscribeBackend = orchestrator.on('backend:connected', (data: any) => {
      callback('backend:connected', data);
    });

    return () => {
      unsubscribeMessage();
      unsubscribeBackend();
    };
  }, [orchestrator, callback]);
}

export default useAutoAdminAgents;