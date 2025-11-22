import { useState, useEffect, useCallback, useRef } from 'react';
import { createFirebaseService, User } from '../lib/firebase';

export interface UseSessionOptions {
  onSessionChange?: (sessionId: string) => void;
  onError?: (error: Error) => void;
  autoInitialize?: boolean;
  sessionId?: string;
}

export interface SessionState {
  sessionUser: User | null;
  sessionId: string;
  loading: boolean;
  initialized: boolean;
  error: string | null;
}

export const useFirebaseSession = (options: UseSessionOptions = {}) => {
  const {
    onSessionChange,
    onError,
    autoInitialize = true,
    sessionId: providedSessionId,
  } = options;

  const [state, setState] = useState<SessionState>({
    sessionUser: null,
    sessionId: providedSessionId || '',
    loading: true,
    initialized: false,
    error: null,
  });

  // Use useRef to prevent infinite re-renders
  const firebaseServiceRef = useRef(createFirebaseService(state.sessionId));
  const firebaseService = firebaseServiceRef.current;

  const updateState = useCallback((updates: Partial<SessionState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const handleError = useCallback((error: Error) => {
    const errorMessage = error.message;
    updateState({
      loading: false,
      error: errorMessage,
    });
    onError?.(error);
  }, [onError, updateState]);

  // Create or get session
  const initializeSession = useCallback(async () => {
    updateState({ loading: true, error: null });

    try {
      const sessionId = providedSessionId || firebaseService.getSessionId();
      const sessionUser = firebaseService.createSession();

      updateState({
        sessionUser,
        sessionId,
        loading: false,
        initialized: true,
        error: null,
      });

      onSessionChange?.(sessionId);
      return { sessionId, sessionUser };
    } catch (error) {
      handleError(error instanceof Error ? error : new Error('Session initialization failed'));
      throw error;
    }
  }, [providedSessionId, updateState, handleError, onSessionChange]);

  // Clear session (equivalent to sign out)
  const clearSession = useCallback(async () => {
    updateState({ loading: true, error: null });

    try {
      // Create a new session
      const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      const newSessionUser = {
        id: newSessionId,
        session_id: newSessionId,
        created_at: { seconds: Math.floor(Date.now() / 1000) } as any,
        last_active: { seconds: Math.floor(Date.now() / 1000) } as any,
      };

      updateState({
        sessionUser: newSessionUser,
        sessionId: newSessionId,
        loading: false,
        error: null,
      });

      onSessionChange?.(newSessionId);
    } catch (error) {
      handleError(error instanceof Error ? error : new Error('Session clear failed'));
      throw error;
    }
  }, [updateState, handleError, onSessionChange]);

  // Reset error state
  const clearError = useCallback(() => {
    updateState({ error: null });
  }, [updateState]);

  // Initialize session on mount
  useEffect(() => {
    if (!autoInitialize) {
      updateState({ loading: false, initialized: true });
      return;
    }

    initializeSession();
  }, [autoInitialize, initializeSession]);

  return {
    // State
    ...state,

    // Actions
    initializeSession,
    clearSession,
    clearError,

    // Computed values
    hasSession: !!state.sessionId,
    isInitialized: state.initialized,
    isLoading: state.loading,
    hasError: !!state.error,
  };
};

// Export the old name for backward compatibility
export const useFirebaseAuth = useFirebaseSession;

export default useFirebaseSession;