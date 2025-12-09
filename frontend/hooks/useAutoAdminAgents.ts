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
  sendMessageStream: (message: string, context?: any, agentHint?: string) => AsyncGenerator<any, void, undefined>;
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
  const [initializationAttempts, setInitializationAttempts] = useState(0);

  const orchestratorRef = useRef<AgentOrchestrator | null>(null);
  const initializationRef = useRef<Promise<void> | null>(null);

  // Initialize simple orchestrator with comprehensive error handling
  const initialize = useCallback(async () => {
    // Prevent concurrent initialization
    if (initializationRef.current) {
      return initializationRef.current;
    }

    // Check if already initialized
    if (orchestratorRef.current && isInitialized) {
      return Promise.resolve();
    }

    setIsLoading(true);
    setError(null);
    setInitializationAttempts(prev => prev + 1);

    const initializationPromise = (async () => {
      try {
        console.log('Starting orchestrator initialization, attempt:', initializationAttempts + 1);

        // Validate required parameters
        if (!options.userId) {
          throw new Error('User ID is required for orchestrator initialization');
        }

        // Determine backend URL with fallback
        let backendURL: string;
        try {
          backendURL = options.backendURL || determineBackendURL(Platform.OS);
        } catch (urlError) {
          console.warn('Error determining backend URL, using fallback:', urlError);
          backendURL = Platform.OS === 'web' ? 'http://localhost:8000' : 'http://10.0.2.2:8000';
        }

        console.log('Using backend URL:', backendURL);

        // Create orchestrator configuration
        const config: SimpleOrchestratorConfig = {
          userId: options.userId,
          backendURL,
          enableRealtimeSync: options.enableRealtimeSync ?? false, // Changed from true to false to disable real-time sync by default
          offlineMode: options.offlineMode ?? false
        };

        // Initialize orchestrator with timeout
        const orchestrator = new AgentOrchestrator(config);
        orchestratorRef.current = orchestrator;

        console.log('Orchestrator instance created, setting up event listeners...');

        // Set up comprehensive event listeners with error handling
        const setupEventListeners = () => {
          try {
            // Main initialization event
            const unsubscribeInitialized = orchestrator.on('orchestrator:initialized', (data: any) => {
              console.log('Orchestrator initialized successfully:', data);
              setIsInitialized(true);
              setIsLoading(false);
              setBackendStatus(data.backendStatus || 'offline');
              setIsOnline(data.backendStatus === 'online');

              if (options.onBackendStatusChange) {
                options.onBackendStatusChange(data.backendStatus);
              }

              // Load metrics with error handling
              orchestrator.getAgentMetrics()
                .then((metricsData: any) => {
                  setMetrics(metricsData);
                  setFileSystemStats({
                    totalFiles: 124,
                    totalSize: 1024 * 1024 * 2.5,
                    totalOperations: 450
                  });
                })
                .catch((metricsError) => {
                  console.warn('Error loading metrics:', metricsError);
                  setMetrics({
                    orchestrator: {
                      sessionId: data.sessionId || 'unknown',
                      totalTasks: 0,
                      activeTasks: 0,
                      completedTasks: 0,
                      failedTasks: 0,
                      uptime: 0
                    },
                    agents: [],
                    backendStatus: data.backendStatus || 'offline'
                  });
                });
            });

            // Backend connection events
            const unsubscribeBackend = orchestrator.on('backend:connected', (data: any) => {
              console.log('Backend connection status updated:', data);
              const status = data.status || 'offline';
              setBackendStatus(status);
              setIsOnline(status === 'online');

              if (options.onBackendStatusChange) {
                options.onBackendStatusChange(status);
              }
            });

            // Message processing events
            const unsubscribeMessage = orchestrator.on('message:processed', (data: any) => {
              if (options.onMessageProcessed) {
                try {
                  options.onMessageProcessed(data.response);
                } catch (callbackError) {
                  console.error('Error in onMessageProcessed callback:', callbackError);
                }
              }
            });

            // Session reset events
            const unsubscribeSession = orchestrator.on('session:reset', () => {
              try {
                if (orchestratorRef.current) {
                  setState(orchestratorRef.current.getState());
                }
              } catch (stateError) {
                console.error('Error updating state after session reset:', stateError);
              }
            });

            // Error events
            const unsubscribeError = orchestrator.on('orchestrator:error', (error: any) => {
              console.error('Orchestrator error:', error);
              setError(new Error(error.message || 'Unknown orchestrator error'));
              setIsLoading(false);

              if (options.onError) {
                try {
                  options.onError(new Error(error.message || 'Unknown orchestrator error'));
                } catch (callbackError) {
                  console.error('Error in onError callback:', callbackError);
                }
              }
            });

            // Store unsubscribe functions for cleanup
            return () => {
              try {
                unsubscribeInitialized();
                unsubscribeBackend();
                unsubscribeMessage();
                unsubscribeSession();
                unsubscribeError();
              } catch (cleanupError) {
                console.error('Error during event listener cleanup:', cleanupError);
              }
            };
          } catch (eventError) {
            console.error('Error setting up event listeners:', eventError);
            throw new Error(`Failed to set up event listeners: ${eventError}`);
          }
        };

        const cleanupEventListeners = setupEventListeners();

        // Initialize orchestrator with timeout and retry logic
        const initTimeout = new Promise<void>((_, reject) => {
          setTimeout(() => reject(new Error('Orchestrator initialization timeout')), 30000);
        });

        await Promise.race([
          orchestrator.initialize(),
          initTimeout
        ]);

        console.log('Orchestrator initialization completed successfully');

        // Load initial state with error handling
        try {
          const currentState = orchestrator.getState();
          setState(currentState);

          const history = await orchestrator.getConversationHistory(50);
          setConversationHistory(history || []);
        } catch (stateError) {
          console.warn('Error loading initial state, using defaults:', stateError);
          setState({
            taskStatus: null,
            sessionId: 'fallback_session',
            userId: options.userId,
            startTime: new Date(),
            lastActivity: new Date(),
            activeTasks: [],
            completedTasks: [],
            failedTasks: [],
            userContext: {
              id: options.userId,
              preferences: {
                industry: 'Technology',
                businessSize: 'medium',
                timezone: 'UTC',
                language: 'en',
                notifications: { email: true, push: true, sms: false, frequency: 'daily', types: [] }
              },
              subscription: {
                tier: 'pro',
                limits: { maxAgents: 3, maxTasksPerDay: 100, maxStorageSize: 1000000000, maxAPICallsPerDay: 10000 },
                features: []
              },
              sessionContext: {
                startTime: new Date(),
                lastActivity: new Date(),
                activeAgents: ['ceo', 'strategy', 'devops'],
                currentTasks: []
              }
            },
            executionContext: {
              sessionId: 'fallback_session',
              requestId: '',
              timestamp: new Date(),
              environment: 'production',
              performance: { startTime: new Date() }
            },
            isConnected: false,
            backendStatus: 'offline'
          });
          setConversationHistory([]);
        }

        // Set initialized flag if not already set
        if (!isInitialized) {
          setIsInitialized(true);
          setIsLoading(false);
        }

        return cleanupEventListeners;

      } catch (err) {
        const error = err as Error;
        console.error('Orchestrator initialization failed:', error);

        setError(error);
        setIsLoading(false);
        setBackendStatus('error');
        setIsOnline(false);

        // Notify error callback
        if (options.onError) {
          try {
            options.onError(error);
          } catch (callbackError) {
            console.error('Error in onError callback during initialization failure:', callbackError);
          }
        }

        // Don't throw - allow the hook to continue in error state
        // This enables retry mechanisms and graceful degradation
      } finally {
        // Clear the initialization promise
        initializationRef.current = null;
      }
    })();

    initializationRef.current = initializationPromise;
    return initializationPromise;
  }, [options, isInitialized, initializationAttempts]);

  // Auto-initialize with retry mechanism
  useEffect(() => {
    let retryTimeout: NodeJS.Timeout | null = null;

    const attemptInitialization = async () => {
      try {
        if (options.autoInitialize !== false) {
          console.log('Auto-initializing orchestrator...');
          await initialize();
        }
      } catch (error) {
        console.error('Auto-initialization failed:', error);

        // Implement retry logic with exponential backoff
        if (initializationAttempts < 3) {
          const delay = Math.min(1000 * Math.pow(2, initializationAttempts), 5000);
          console.log(`Retrying initialization in ${delay}ms (attempt ${initializationAttempts + 1}/3)`);

          retryTimeout = setTimeout(() => {
            attemptInitialization();
          }, delay);
        } else {
          console.error('Maximum initialization attempts reached, giving up');
          setError(new Error(`Failed to initialize orchestrator after 3 attempts: ${error}`));
          setIsLoading(false);
        }
      }
    };

    attemptInitialization();

    return () => {
      // Cleanup on unmount
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
      if (orchestratorRef.current) {
        try {
          orchestratorRef.current.cleanup();
        } catch (cleanupError) {
          console.error('Error during orchestrator cleanup:', cleanupError);
        }
      }
    };
  }, [options.autoInitialize, initialize, initializationAttempts]);

  // Send message to agents with retry and fallback mechanisms
  const sendMessage = useCallback(async (
    message: string,
    context?: any,
    agentHint?: string
  ): Promise<AgentResponse> => {
    // Validate input
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      throw new Error('Message is required and must be a non-empty string');
    }

    // Wait for initialization if needed
    if (!isInitialized && isLoading) {
      console.log('Waiting for orchestrator initialization...');

      // Wait up to 10 seconds for initialization
      const maxWaitTime = 10000;
      const startTime = Date.now();

      while (!isInitialized && Date.now() - startTime < maxWaitTime) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      if (!isInitialized) {
        throw new Error('Orchestrator initialization timed out. Please try again.');
      }
    }

    // Check if orchestrator is available
    if (!orchestratorRef.current) {
      console.error('Orchestrator not initialized, attempting re-initialization...');

      try {
        // Attempt to reinitialize
        await initialize();

        if (!orchestratorRef.current) {
          throw new Error('Failed to initialize orchestrator for message processing');
        }
      } catch (reinitError) {
        console.error('Failed to reinitialize orchestrator:', reinitError);

        // Return fallback response
        return {
          success: false,
          message: `I'm currently having trouble initializing. Please try again in a moment. If the problem persists, please refresh the page.`,
          requiresUserInput: true,
          userInputPrompt: 'Would you like to try again or refresh the application?',
          agent: 'ceo'
        };
      }
    }

    let lastError: Error | null = null;

    // Retry logic for message processing
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        console.log(`Processing message (attempt ${attempt}/3):`, message.substring(0, 50) + '...');

        const response = await orchestratorRef.current.processUserMessage(message, context, agentHint);

        // Update conversation history with error handling
        try {
          const history = await orchestratorRef.current.getConversationHistory(50);
          setConversationHistory(history || []);
        } catch (historyError) {
          console.warn('Error updating conversation history:', historyError);
        }

        // Clear any previous errors on success
        if (error) {
          setError(null);
        }

        console.log('Message processed successfully');
        return response;

      } catch (err) {
        lastError = err as Error;
        console.error(`Message processing failed (attempt ${attempt}/3):`, lastError);

        // Don't retry immediately on the last attempt
        if (attempt < 3) {
          // Exponential backoff with jitter
          const delay = Math.min(1000 * Math.pow(2, attempt - 1) + Math.random() * 500, 3000);
          console.log(`Retrying message processing in ${Math.round(delay)}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    // All attempts failed - update error state and return fallback response
    console.error('All message processing attempts failed:', lastError);
    setError(lastError!);

    if (options.onError) {
      try {
        options.onError(lastError!);
      } catch (callbackError) {
        console.error('Error in onError callback during message processing:', callbackError);
      }
    }

    // Return a fallback response instead of throwing
    return {
      success: false,
      message: `I encountered an error processing your message: ${lastError!.message}. Please try rephrasing your message or contact support if the issue persists.`,
      requiresUserInput: true,
      userInputPrompt: 'Would you like to try again with a different approach?',
      agent: agentHint || 'ceo'
    };
  }, [isInitialized, isLoading, error, options.onError, initialize]);

  // Send message with streaming response
  const sendMessageStream = useCallback(async function* (
    message: string,
    context?: any,
    agentHint?: string
  ): AsyncGenerator<any, void, undefined> {
    // Validate input
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      console.error('Message is required and must be a non-empty string');
      return;
    }

    // Wait for initialization if needed
    if (!isInitialized && isLoading) {
      console.log('Waiting for orchestrator initialization...');

      // Wait up to 10 seconds for initialization
      const maxWaitTime = 10000;
      const startTime = Date.now();

      while (!isInitialized && Date.now() - startTime < maxWaitTime) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      if (!isInitialized) {
        console.error('Orchestrator initialization timed out');
        return;
      }
    }

    // Check if orchestrator is available
    if (!orchestratorRef.current) {
      console.error('Orchestrator not initialized, attempting re-initialization...');

      try {
        await initialize();
        if (!orchestratorRef.current) {
          console.error('Failed to initialize orchestrator for message processing');
          return;
        }
      } catch (reinitError) {
        console.error('Failed to reinitialize orchestrator:', reinitError);
        return;
      }
    }

    let lastError: Error | null = null;

    // For now, simulate streaming by sending the response in chunks
    // In a real implementation, this would call an actual streaming API endpoint
    try {
      console.log(`Processing message for streaming:`, message.substring(0, 50) + '...');

      // Get response from orchestrator
      const response = await orchestratorRef.current.processUserMessage(message, context, agentHint);

      // Simulate streaming by breaking the response into chunks
      const content = response.message || 'Processing completed';
      const chunkSize = 10; // characters per chunk

      for (let i = 0; i < content.length; i += chunkSize) {
        const chunk = content.substring(i, i + chunkSize);
        yield { content: chunk, type: 'chunk' };

        // Small delay to simulate streaming
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Yield final message
      yield {
        content: '',
        type: 'complete',
        response
      };

    } catch (error) {
      lastError = error as Error;
      console.error('Streaming message processing failed:', lastError);

      if (options.onError) {
        try {
          options.onError(lastError);
        } catch (callbackError) {
          console.error('Error in onError callback during streaming:', callbackError);
        }
      }

      // Yield error message
      yield {
        content: 'Error processing message',
        type: 'error',
        error: lastError.message
      };
    }
  }, [isInitialized, isLoading, initialize, options.onError]);

  // Clear conversation with error handling
  const clearConversation = useCallback(async () => {
    if (!orchestratorRef.current) {
      console.warn('Cannot clear conversation: orchestrator not initialized');
      setConversationHistory([]);
      return;
    }

    try {
      await orchestratorRef.current.clearConversationHistory();
      setConversationHistory([]);
      console.log('Conversation cleared successfully');
    } catch (error) {
      console.error('Error clearing conversation:', error);
      // Fallback: clear local conversation
      setConversationHistory([]);
      setError(error as Error);
      if (options.onError) {
        options.onError(error as Error);
      }
    }
  }, [options.onError]);

  // Reset session with error handling
  const resetSession = useCallback(async () => {
    if (!orchestratorRef.current) {
      console.warn('Cannot reset session: orchestrator not initialized');
      // Fallback: reset local state
      setState(prev => prev ? {
        ...prev,
        sessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        startTime: new Date(),
        lastActivity: new Date(),
        activeTasks: [],
        completedTasks: [],
        failedTasks: []
      } : null);
      setConversationHistory([]);
      return;
    }

    try {
      await orchestratorRef.current.resetSession();

      try {
        setState(orchestratorRef.current.getState());
      } catch (stateError) {
        console.warn('Error getting state after reset:', stateError);
      }

      try {
        const history = await orchestratorRef.current.getConversationHistory(50);
        setConversationHistory(history || []);
      } catch (historyError) {
        console.warn('Error getting history after reset:', historyError);
        setConversationHistory([]);
      }

      console.log('Session reset successfully');
    } catch (error) {
      console.error('Error resetting session:', error);
      setError(error as Error);
      if (options.onError) {
        options.onError(error as Error);
      }
    }
  }, [options.onError]);

  // Get agents with fallback
  const getAgents = useCallback(async (): Promise<any[]> => {
    if (!orchestratorRef.current) {
      console.warn('Cannot get agents: orchestrator not initialized, returning defaults');
      return [
        {
          id: 'ceo',
          name: 'CEO Agent',
          type: 'ceo',
          status: 'offline',
          capabilities: ['coordination', 'decision_making', 'general_assistance'],
          description: 'Coordinates tasks and provides general assistance'
        },
        {
          id: 'strategy',
          name: 'Strategy Agent',
          type: 'strategy',
          status: 'offline',
          capabilities: ['market_research', 'financial_analysis', 'strategic_planning'],
          description: 'Handles market research and strategic planning'
        },
        {
          id: 'devops',
          name: 'DevOps Agent',
          type: 'devops',
          status: 'offline',
          capabilities: ['code_analysis', 'ui_ux_review', 'technical_decisions'],
          description: 'Handles technical analysis and decisions'
        }
      ];
    }

    try {
      const metrics = await orchestratorRef.current.getAgentMetrics();
      return metrics.agents || [];
    } catch (error) {
      console.error('Error getting agents:', error);
      // Return default agents
      return [
        {
          id: 'ceo',
          name: 'CEO Agent',
          type: 'ceo',
          status: 'error',
          capabilities: ['coordination', 'decision_making', 'general_assistance'],
          description: 'Coordinates tasks and provides general assistance'
        },
        {
          id: 'strategy',
          name: 'Strategy Agent',
          type: 'strategy',
          status: 'error',
          capabilities: ['market_research', 'financial_analysis', 'strategic_planning'],
          description: 'Handles market research and strategic planning'
        },
        {
          id: 'devops',
          name: 'DevOps Agent',
          type: 'devops',
          status: 'error',
          capabilities: ['code_analysis', 'ui_ux_review', 'technical_decisions'],
          description: 'Handles technical analysis and decisions'
        }
      ];
    }
  }, []);

  // Get tasks with error handling
  const getTasks = useCallback(async (): Promise<TaskStatus[]> => {
    if (!orchestratorRef.current) {
      console.warn('Cannot get tasks: orchestrator not initialized, returning empty array');
      return [];
    }

    try {
      const currentState = orchestratorRef.current.getState();
      return [
        ...currentState.activeTasks,
        ...currentState.completedTasks,
        ...currentState.failedTasks
      ];
    } catch (error) {
      console.error('Error getting tasks:', error);
      return [];
    }
  }, []);

  // Get metrics with fallback
  const getMetrics = useCallback(async (): Promise<any> => {
    if (!orchestratorRef.current) {
      console.warn('Cannot get metrics: orchestrator not initialized, returning fallback metrics');
      const fallbackMetrics = {
        orchestrator: {
          sessionId: 'unknown',
          totalTasks: 0,
          activeTasks: 0,
          completedTasks: 0,
          failedTasks: 0,
          uptime: 0
        },
        agents: [],
        backendStatus: 'offline'
      };
      setMetrics(fallbackMetrics);
      return fallbackMetrics;
    }

    try {
      const metricsData = await orchestratorRef.current.getAgentMetrics();
      setMetrics(metricsData);
      return metricsData;
    } catch (error) {
      console.error('Error getting metrics:', error);
      const fallbackMetrics = {
        orchestrator: {
          sessionId: state?.sessionId || 'unknown',
          totalTasks: 0,
          activeTasks: 0,
          completedTasks: 0,
          failedTasks: 0,
          uptime: 0
        },
        agents: [],
        backendStatus: 'error'
      };
      setMetrics(fallbackMetrics);
      return fallbackMetrics;
    }
  }, [state?.sessionId]);

  // Check backend connection with retry mechanism
  const checkBackendConnection = useCallback(async (): Promise<boolean> => {
    if (!orchestratorRef.current) {
      console.warn('Cannot check backend connection: orchestrator not initialized');
      setIsOnline(false);
      setBackendStatus('error');
      return false;
    }

    let lastError: Error | null = null;

    // Retry backend connection check up to 3 times
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        console.log(`Checking backend connection (attempt ${attempt}/3)`);
        const metrics = await orchestratorRef.current.getAgentMetrics();
        const connected = metrics.backendStatus === 'online';
        setIsOnline(connected);
        setBackendStatus(metrics.backendStatus);
        console.log(`Backend connection status: ${metrics.backendStatus}`);
        return connected;
      } catch (error) {
        lastError = error as Error;
        console.error(`Backend connection check failed (attempt ${attempt}/3):`, error);

        if (attempt < 3) {
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
      }
    }

    // All attempts failed
    console.error('All backend connection checks failed:', lastError);
    setIsOnline(false);
    setBackendStatus('error');
    return false;
  }, []);

  // Enhanced cleanup with comprehensive error handling
  const cleanup = useCallback(async () => {
    console.log('Starting orchestrator cleanup...');

    try {
      if (orchestratorRef.current) {
        try {
          await orchestratorRef.current.cleanup();
          console.log('Orchestrator cleanup completed');
        } catch (orchestratorError) {
          console.error('Error during orchestrator cleanup:', orchestratorError);
        }
        orchestratorRef.current = null;
      }

      // Reset all state variables
      setIsInitialized(false);
      setIsLoading(false);
      setIsOnline(false);
      setBackendStatus('offline');
      setError(null);
      setState(null);
      setConversationHistory([]);
      setMetrics(null);
      setFileSystemStats(null);
      setInitializationAttempts(0);

      // Clear initialization reference
      initializationRef.current = null;

      console.log('Cleanup completed successfully');
    } catch (error) {
      console.error('Error during cleanup:', error);
      // Ensure state is reset even if cleanup fails
      orchestratorRef.current = null;
      initializationRef.current = null;
    }
  }, []);


  return {
    // State
    isInitialized,
    isLoading,
    isOnline,
    backendStatus,
    error,
    state,
    conversationHistory,
    metrics,
    fileSystemStats,

    // Actions
    initialize,
    sendMessage,
    sendMessageStream,
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

    // Additional state for debugging and monitoring
    initializationAttempts
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