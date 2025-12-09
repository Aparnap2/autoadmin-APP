/**
 * Hook for AutoAdmin Dashboard integration
 * Provides a simplified interface for dashboard usage
 */

import { useState, useEffect } from 'react';
import { useAutoAdminAgents, UseAutoAdminAgentsOptions } from './useAutoAdminAgents';

export interface UseAutoAdminDashboardOptions extends Omit<UseAutoAdminAgentsOptions, 'userId'> {
  // Add dashboard-specific options here
  showDebugInfo?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export interface UseAutoAdminDashboardReturn {
  // Basic agent state
  isReady: boolean;
  isLoading: boolean;
  error: Error | null;

  // Dashboard-specific state
  hasActiveTask: boolean;
  agentCount: number;
  unreadMessages: number;

  // Simplified actions
  refresh: () => Promise<void>;
  sendQuickMessage: (message: string) => Promise<void>;

  // Agent hook return
  agents: ReturnType<typeof useAutoAdminAgents>;
}

/**
 * Simplified hook for AutoAdmin Dashboard usage
 */
export function useAutoAdminDashboard(
  userId: string,
  options: UseAutoAdminDashboardOptions = {}
): UseAutoAdminDashboardReturn {
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const {
    showDebugInfo = false,
    autoRefresh = false, // Changed from true to false to disable auto-refresh by default
    refreshInterval = 30000, // 30 seconds
    ...agentOptions
  } = options;

  // Use the main agents hook
  const agents = useAutoAdminAgents({
    userId,
    autoInitialize: true,
    enableStreaming: true,
    enableRealtimeSync: true,
    ...agentOptions,
  });

  // Calculate dashboard-specific derived state
  const hasActiveTask = !!(
    agents.state?.taskStatus &&
    agents.state.taskStatus.status !== 'completed' &&
    agents.state.taskStatus.status !== 'failed'
  );

  const agentCount = agents.state ? 3 : 0; // CEO, Strategy, DevOps

  const unreadMessages = agents.conversationHistory.filter(msg =>
    msg.getType() === 'ai' && !msg.content.includes('already seen')
  ).length;

  // Refresh function
  const refresh = async () => {
    try {
      if (showDebugInfo) {
        console.log('Dashboard: Refreshing data...');
      }

      await agents.getAgentMetrics();
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Dashboard: Failed to refresh:', error);
    }
  };

  // Quick message function
  const sendQuickMessage = async (message: string) => {
    try {
      await agents.sendMessage(message, {
        source: 'dashboard_quick_action',
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Dashboard: Failed to send quick message:', error);
      throw error;
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !agents.isInitialized) return;

    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, agents.isInitialized]);

  // Debug logging
  useEffect(() => {
    if (showDebugInfo && agents.error) {
      console.error('Dashboard: Agent error occurred:', agents.error);
    }
  }, [agents.error, showDebugInfo]);

  useEffect(() => {
    if (showDebugInfo && agents.isInitialized) {
      console.log('Dashboard: Agents initialized successfully');
    }
  }, [agents.isInitialized, showDebugInfo]);

  return {
    // Basic state
    isReady: agents.isInitialized && !agents.isLoading,
    isLoading: agents.isLoading,
    error: agents.error,

    // Dashboard-specific state
    hasActiveTask,
    agentCount,
    unreadMessages,

    // Actions
    refresh,
    sendQuickMessage,

    // Full agents hook
    agents,
  };
}

/**
 * Hook for dashboard analytics and metrics
 */
export function useDashboardAnalytics(userId: string) {
  const [analytics, setAnalytics] = useState({
    totalSessions: 0,
    totalTasks: 0,
    averageSessionDuration: 0,
    peakUsageTime: '',
  });

  useEffect(() => {
    // In a real implementation, this would fetch from your analytics service
    const fetchAnalytics = async () => {
      try {
        // Mock analytics data
        setAnalytics({
          totalSessions: 47,
          totalTasks: 156,
          averageSessionDuration: 12.5, // minutes
          peakUsageTime: '14:30',
        });
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      }
    };

    fetchAnalytics();
  }, [userId]);

  return analytics;
}

export default useAutoAdminDashboard;