import { useState, useEffect, useCallback, useRef } from 'react';
import { runOnUI } from 'react-native-worklets-core';
import LangGraphService, { AgentMessage, AgentConfig } from '../services/agents/langgraph.service';

export interface UseLangGraphAgentOptions {
  autoInitialize?: boolean;
  config?: AgentConfig;
  sessionId?: string;
  onSaveMessage?: (message: AgentMessage) => void;
  onError?: (error: Error) => void;
}

export interface AgentState {
  initialized: boolean;
  loading: boolean;
  processing: boolean;
  messages: AgentMessage[];
  error: string | null;
  conversationHistory: AgentMessage[];
}

const defaultConfig: AgentConfig = {
  model: 'gpt-4o-mini',
  temperature: 0.7,
  maxTokens: 2000,
};

export const useLangGraphAgent = (options: UseLangGraphAgentOptions = {}) => {
  const {
    autoInitialize = true,
    config = defaultConfig,
    sessionId,
    onSaveMessage,
    onError,
  } = options;

  const [state, setState] = useState<AgentState>({
    initialized: false,
    loading: false,
    processing: false,
    messages: [],
    error: null,
    conversationHistory: [],
  });

  const agentRef = useRef<LangGraphService | null>(null);
  const unsubscribeAuthRef = useRef<(() => void) | null>(null);

  // Initialize agent service
  const initializeAgent = useCallback(async () => {
    if (!agentRef.current) {
      agentRef.current = LangGraphService.getInstance();
    }

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      // Generate session ID if not provided
      const currentSessionId = sessionId || 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

      // Set session ID for the agent
      agentRef.current.setUserId(currentSessionId);

      // Initialize the agent
      await agentRef.current.initializeAgent(config);

      // Load conversation history
      const history = await agentRef.current.getConversationHistory(50);

      setState(prev => ({
        ...prev,
        initialized: true,
        loading: false,
        conversationHistory: history,
        messages: history.slice(-10), // Show last 10 messages by default
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));

      onError?.(error instanceof Error ? error : new Error(errorMessage));
    }
  }, [config, sessionId, onError]);

  // Process a message with the agent
  const processMessage = useCallback(async (message: string) => {
    if (!agentRef.current || !state.initialized) {
      const error = new Error('Agent not initialized');
      setState(prev => ({
        ...prev,
        processing: false,
        error: 'Agent not initialized',
      }));
      onError?.(error);
      return;
    }

    setState(prev => ({
      ...prev,
      processing: true,
      error: null,
    }));

    try {
      // Add user message to local state immediately for better UX
      const userMessage: AgentMessage = {
        id: Date.now().toString(),
        content: message,
        type: 'human',
        timestamp: new Date(),
      };

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      onSaveMessage?.(userMessage);

      // Process message with agent
      const response = await agentRef.current.processMessage(message);

      // Add agent response to state
      const agentMessage: AgentMessage = {
        id: (Date.now() + 1).toString(),
        content: response,
        type: 'ai',
        timestamp: new Date(),
      };

      setState(prev => ({
        ...prev,
        processing: false,
        messages: [...prev.messages, agentMessage],
        conversationHistory: [...prev.conversationHistory, userMessage, agentMessage],
      }));

      onSaveMessage?.(agentMessage);

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        processing: false,
        error: errorMessage,
      }));

      onError?.(error instanceof Error ? error : new Error(errorMessage));
      throw error;
    }
  }, [agentRef, state.initialized, onSaveMessage, onError]);

  // Worklet-optimized message processing
  const processMessageWorklet = useCallback((message: string) => {
    'worklet';

    return runOnUI(() => {
      console.log('Processing message in worklet:', message);
      // Additional UI-thread optimizations can be added here
    })();
  }, []);

  // Clear conversation history
  const clearConversation = useCallback(async () => {
    if (!agentRef.current) {
      return;
    }

    try {
      // This would need to be implemented in the agent service
      // For now, just clear local state
      setState(prev => ({
        ...prev,
        messages: [],
        conversationHistory: [],
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    }
  }, [onError]);

  // Load more conversation history
  const loadMoreHistory = useCallback(async (count: number = 20) => {
    if (!agentRef.current || !state.initialized) {
      return;
    }

    try {
      const currentHistoryLength = state.conversationHistory.length;
      const additionalHistory = await agentRef.current.getConversationHistory(
        currentHistoryLength + count
      );

      setState(prev => ({
        ...prev,
        conversationHistory: additionalHistory,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    }
  }, [agentRef, state.initialized, state.conversationHistory.length, onError]);

  // Save agent state
  const saveAgentState = useCallback(async (agentState: Record<string, any>) => {
    if (!agentRef.current || !state.initialized) {
      return;
    }

    try {
      await agentRef.current.saveAgentState(agentState);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    }
  }, [agentRef, state.initialized, onError]);

  // Load agent state
  const loadAgentState = useCallback(async () => {
    if (!agentRef.current || !state.initialized) {
      return null;
    }

    try {
      return await agentRef.current.loadAgentState();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      onError?.(error instanceof Error ? error : new Error(errorMessage));
      return null;
    }
  }, [agentRef, state.initialized, onError]);

  // Reset error state
  const clearError = useCallback(() => {
    setState(prev => ({
      ...prev,
      error: null,
    }));
  }, []);

  // Initialize on mount if autoInitialize is true
  useEffect(() => {
    if (autoInitialize) {
      initializeAgent();
    }

    return () => {
      if (unsubscribeAuthRef.current) {
        unsubscribeAuthRef.current();
      }
    };
  }, [autoInitialize, initializeAgent]);

  // Listen for auth state changes
  useEffect(() => {
    const authService = AuthService.getInstance();
    unsubscribeAuthRef.current = authService.onAuthStateChanged((user) => {
      if (user && agentRef.current) {
        agentRef.current.setUserId(user.uid);
        if (autoInitialize && !state.initialized) {
          initializeAgent();
        }
      } else if (!user) {
        // User signed out, reset state
        setState({
          initialized: false,
          loading: false,
          processing: false,
          messages: [],
          error: null,
          conversationHistory: [],
        });
      }
    });

    return () => {
      if (unsubscribeAuthRef.current) {
        unsubscribeAuthRef.current();
      }
    };
  }, [autoInitialize, initializeAgent, state.initialized]);

  return {
    // State
    ...state,

    // Actions
    initializeAgent,
    processMessage,
    processMessageWorklet,
    clearConversation,
    loadMoreHistory,
    saveAgentState,
    loadAgentState,
    clearError,

    // Computed values
    isReady: state.initialized && !state.loading,
    canProcess: state.initialized && !state.processing && !state.loading,
    hasMessages: state.messages.length > 0,
    lastMessage: state.messages[state.messages.length - 1] || null,
  };
};

export default useLangGraphAgent;