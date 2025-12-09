import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useAutoAdminAgents } from '@/hooks/useAutoAdminAgents';
import { useGlobalShortcuts } from '@/hooks/useKeyboardShortcuts';
import { getFastAPIClient } from '@/services/api/fastapi-client';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { AgentStatusCard } from './AgentStatusCard';
import { QuickActions } from './QuickActions';
import { ConversationPreview } from './ConversationPreview';
import { SystemMetrics } from './SystemMetrics';
import { TaskProgress } from './TaskProgress';
import { BackendStatus } from '@/components/BackendStatus';
import { CommandPalette } from './CommandPalette';
import { LogStream } from './LogStream';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Colors } from '@/constants/theme';

interface AutoAdminDashboardProps {
  userId: string;
}

export function AutoAdminDashboard({ userId }: AutoAdminDashboardProps) {
  const [refreshing, setRefreshing] = useState(false);
  const [hubspotData, setHubspotData] = useState({
    contacts: [],
    deals: [],
    companies: [],
    recentActivity: { contacts: [], deals: [], total_changes: 0 },
    loading: false,
    error: null as string | null
  });

  // Global shortcuts for "God Mode"
  const {
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    isLogStreamOpen,
    setIsLogStreamOpen,
  } = useGlobalShortcuts();

  // Mock logs for demonstration - in real app, these would come from SSE events
  const [mockLogs, setMockLogs] = useState([
    {
      id: '1',
      timestamp: new Date(Date.now() - 5000),
      level: 'info' as const,
      source: 'CEO Agent',
      message: 'System initialization complete',
      agent: 'ceo',
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 3000),
      level: 'success' as const,
      source: 'Marketing Agent',
      message: 'Campaign analysis completed successfully',
      agent: 'marketing',
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 1000),
      level: 'warning' as const,
      source: 'DevOps Agent',
      message: 'High memory usage detected in production',
      agent: 'devops',
    },
  ]);

  const {
    isInitialized,
    isLoading,
    error,
    state,
    metrics,
    conversationHistory,
    fileSystemStats,
    sendMessage,
    clearConversation,
    resetSession,
    getAgentMetrics,
    backendStatus,
    isOnline,
  } = useAutoAdminAgents({
    userId,
    autoInitialize: false, // Don't auto-initialize - only when user interacts
    enableStreaming: false,
    enableRealtimeSync: false,
    offlineMode: true, // Always work in offline mode
    onError: (err) => {
      console.error('AutoAdmin Dashboard Error:', err);
      // Don't show alert for every error - let the UI handle it gracefully
    },
  });

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await getAgentMetrics();
      // Also refresh HubSpot data
      await fetchHubSpotData();
    } catch (error) {
      console.error('Error refreshing metrics:', error);
    } finally {
      setRefreshing(false);
    }
  }, [getAgentMetrics]);

  // Fetch HubSpot data function
  const fetchHubSpotData = useCallback(async () => {
    try {
      setHubspotData(prev => ({ ...prev, loading: true, error: null }));

      const client = getFastAPIClient();

      // Fetch data in parallel
      const [contactsRes, dealsRes] = await Promise.allSettled([
        client.getHubSpotContacts(50),
        client.getHubSpotDeals(50)
      ]);

      const contacts = contactsRes.status === 'fulfilled' && contactsRes.value.success
        ? contactsRes.value.data || []
        : [];

      const deals = dealsRes.status === 'fulfilled' && dealsRes.value.success
        ? dealsRes.value.data || []
        : [];

      setHubspotData(prev => ({
        ...prev,
        contacts,
        deals,
        loading: false,
        error: null
      }));

    } catch (error) {
      console.error('Error fetching HubSpot data:', error);
      setHubspotData(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load HubSpot data'
      }));
    }
  }, []);

  // Fetch HubSpot data on app open
  useEffect(() => {
    fetchHubSpotData();
  }, [fetchHubSpotData]);

  const handleQuickAction = useCallback(async (action: string, params?: any) => {
    try {
      switch (action) {
        case 'new_task':
          // This would typically open a modal or navigate to task creation
          Alert.alert('Quick Action', 'Task creation interface would open here');
          break;
        case 'chat_with_ceo':
          await sendMessage('Please provide a status update on current system operations', {
            context: 'quick_status_check'
          });
          break;
        case 'market_analysis':
          await sendMessage('Can you analyze the current market trends and provide insights?', {
            context: 'market_analysis',
            agentType: 'strategy'
          });
          break;
        case 'code_review':
          await sendMessage('Please review the current codebase for optimization opportunities', {
            context: 'code_review',
            agentType: 'devops'
          });
          break;
        case 'clear_history':
          Alert.alert(
            'Clear Conversation History',
            'Are you sure you want to clear all conversation history?',
            [
              { text: 'Cancel', style: 'cancel' },
              {
                text: 'Clear',
                style: 'destructive',
                onPress: () => clearConversation(),
              },
            ]
          );
          break;
        case 'reset_session':
          Alert.alert(
            'Reset Session',
            'This will reset the current agent session. Continue?',
            [
              { text: 'Cancel', style: 'cancel' },
              {
                text: 'Reset',
                style: 'destructive',
                onPress: () => resetSession(),
              },
            ]
          );
          break;
        case 'open_chat':
          Alert.alert('Open Chat', 'Navigate to the full chat interface to interact with agents.');
          // In a real app, this would use navigation to navigate to chat tab
          break;
        default:
          await sendMessage(action, params);
      }
    } catch (error) {
      console.error('Error executing quick action:', error);
      Alert.alert('Error', 'Failed to execute action');
    }
  }, [sendMessage, clearConversation, resetSession]);

  // Command palette commands
  const commands = useMemo(() => [
    // Navigation Commands
    {
      id: 'nav-dashboard',
      title: 'Go to Dashboard',
      description: 'Navigate to the main dashboard',
      icon: '📊',
      keywords: ['dashboard', 'home', 'main'],
      action: () => console.log('Navigate to dashboard'),
      shortcut: '⌘D',
      category: 'navigation' as const,
    },
    {
      id: 'nav-chat',
      title: 'Open Chat',
      description: 'Navigate to the chat interface',
      icon: '💬',
      keywords: ['chat', 'conversation', 'talk'],
      action: () => console.log('Navigate to chat'),
      shortcut: '⌘C',
      category: 'navigation' as const,
    },

    // Agent Commands
    {
      id: 'agent-ceo-status',
      title: 'CEO Status Update',
      description: 'Get current system status from CEO agent',
      icon: '👔',
      keywords: ['ceo', 'status', 'system', 'update'],
      action: () => handleQuickAction('chat_with_ceo'),
      shortcut: '⌘S',
      category: 'agent' as const,
    },
    {
      id: 'agent-market-analysis',
      title: 'Market Analysis',
      description: 'Analyze market trends and competition',
      icon: '📊',
      keywords: ['market', 'analysis', 'trends', 'competition'],
      action: () => handleQuickAction('market_analysis'),
      shortcut: '⌘M',
      category: 'agent' as const,
    },
    {
      id: 'agent-code-review',
      title: 'Code Review',
      description: 'Analyze codebase for optimization',
      icon: '⚙️',
      keywords: ['code', 'review', 'analysis', 'optimization'],
      action: () => handleQuickAction('code_review'),
      shortcut: '⌘R',
      category: 'agent' as const,
    },

    // System Commands
    {
      id: 'system-refresh',
      title: 'Refresh Dashboard',
      description: 'Refresh all dashboard data',
      icon: '🔄',
      keywords: ['refresh', 'reload', 'update'],
      action: handleRefresh,
      shortcut: 'F5',
      category: 'system' as const,
    },
    {
      id: 'system-logs',
      title: 'Toggle Log Stream',
      description: 'Show/hide the real-time log stream',
      icon: '📡',
      keywords: ['logs', 'stream', 'matrix', 'console'],
      action: () => setIsLogStreamOpen(!isLogStreamOpen),
      shortcut: '⌘L',
      category: 'system' as const,
    },
    {
      id: 'system-clear-history',
      title: 'Clear Conversation History',
      description: 'Clear all conversation history',
      icon: '🗑️',
      keywords: ['clear', 'history', 'conversation', 'reset'],
      action: () => handleQuickAction('clear_history'),
      shortcut: '⌘⌫',
      category: 'system' as const,
    },

    // Task Commands
    {
      id: 'task-create',
      title: 'Create New Task',
      description: 'Start a new custom task',
      icon: '➕',
      keywords: ['task', 'create', 'new', 'custom'],
      action: () => handleQuickAction('new_task'),
      shortcut: '⌘T',
      category: 'task' as const,
    },
    {
      id: 'task-performance-audit',
      title: 'Performance Audit',
      description: 'Check system performance and bottlenecks',
      icon: '🚀',
      keywords: ['performance', 'audit', 'speed', 'bottleneck'],
      action: () => handleQuickAction('performance_audit'),
      shortcut: '⌘P',
      category: 'task' as const,
    },
  ], [handleQuickAction, handleRefresh, isLogStreamOpen, setIsLogStreamOpen]);

  // Simulate real-time log updates
  useEffect(() => {
    if (!isLogStreamOpen) return;

    const interval = setInterval(() => {
      const newLog = {
        id: Date.now().toString(),
        timestamp: new Date(),
        level: ['info', 'success', 'warning', 'error'][Math.floor(Math.random() * 4)] as const,
        source: ['CEO Agent', 'Strategy Agent', 'DevOps Agent', 'Marketing Agent'][Math.floor(Math.random() * 4)],
        message: [
          'Processing user request...',
          'Analyzing data patterns...',
          'Optimizing system performance...',
          'Generating insights...',
          'Checking system health...',
        ][Math.floor(Math.random() * 5)],
        agent: ['ceo', 'strategy', 'devops', 'marketing'][Math.floor(Math.random() * 4)],
      };

      setMockLogs(prev => [newLog, ...prev].slice(0, 50)); // Keep only last 50 logs
    }, 3000);

    return () => clearInterval(interval);
  }, [isLogStreamOpen]);

  if (isLoading) {
    return (
      <ErrorBoundary>
        <ThemedView style={styles.container}>
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#2196F3" />
            <ThemedText type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText style={styles.loadingText}>Initializing agent system...</ThemedText>
          </View>
        </ThemedView>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ThemedView style={styles.container} testID="autoadmin-dashboard">
        {/* Backend Status Indicator */}
        <BackendStatus
          testID="backend-status"
          status={backendStatus}
          isOnline={isOnline}
          onRetry={handleRefresh}
          message={
            backendStatus === 'offline'
              ? 'Backend is offline. Some features may be limited.'
              : backendStatus === 'error'
                ? error?.message || 'Connection error occurred'
                : undefined
          }
        />

        <ScrollView
          style={styles.scrollView}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <View style={styles.header} testID="dashboard-header">
            <ThemedText testID="dashboard-title" type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText testID="dashboard-subtitle" style={styles.subtitle}>
              Intelligent Agent System
            </ThemedText>
          </View>

          {/* System Status */}
          <View style={styles.section}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              System Status
            </ThemedText>
            <View style={styles.statusRow}>
              <View style={styles.statusItem}>
                <ThemedText style={styles.statusText}>
                  Status: {isInitialized ? 'Online' : 'Initializing'}
                </ThemedText>
              </View>
              <View style={styles.statusItem}>
                <ThemedText style={styles.statusText}>
                  Session: Active
                </ThemedText>
              </View>
            </View>
          </View>

          {/* Agent Status Cards */}
          <View style={styles.section}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Agent Swarm Status
            </ThemedText>
            <AgentStatusCard
              state={state}
              metrics={metrics}
              isLoading={!isInitialized}
            />
          </View>

          {/* System Metrics */}
          {metrics && (
            <View style={styles.section}>
              <ThemedText type="subtitle" style={styles.sectionTitle}>
                System Metrics
              </ThemedText>
              <SystemMetrics
                metrics={metrics}
                fileSystemStats={fileSystemStats}
              />
            </View>
          )}

          {/* Current Task Progress */}
          {state?.activeTasks && state.activeTasks.length > 0 && (
            <View style={styles.section}>
              <ThemedText type="subtitle" style={styles.sectionTitle}>
                Current Task Progress
              </ThemedText>
              <TaskProgress taskStatus={state.activeTasks[0]} />
            </View>
          )}

          {/* Quick Actions */}
          <View style={styles.section}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Quick Actions
            </ThemedText>
            <QuickActions
              onAction={handleQuickAction}
              isDisabled={!isInitialized}
            />
          </View>

          {/* Recent Conversations */}
          <View style={styles.section}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Recent Conversations
            </ThemedText>
            <ConversationPreview
              conversations={conversationHistory.slice(-5)}
              isLoading={!isInitialized}
            />
          </View>

          {/* HubSpot CRM Data */}
          <View style={styles.section}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              HubSpot CRM Data
            </ThemedText>
            {hubspotData.loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="small" color="#2196F3" />
                <ThemedText style={styles.loadingText}>Loading CRM data...</ThemedText>
              </View>
            ) : hubspotData.error ? (
              <View style={styles.errorContainer}>
                <ThemedText style={styles.errorText}>{hubspotData.error}</ThemedText>
              </View>
            ) : (
              <View style={styles.crmStatsContainer}>
                <View style={styles.crmStatItem}>
                  <ThemedText style={styles.crmStatLabel}>Contacts</ThemedText>
                  <ThemedText style={styles.crmStatValue}>
                    {hubspotData.contacts.length}
                  </ThemedText>
                </View>
                <View style={styles.crmStatItem}>
                  <ThemedText style={styles.crmStatLabel}>Deals</ThemedText>
                  <ThemedText style={styles.crmStatValue}>
                    {hubspotData.deals.length}
                  </ThemedText>
                </View>
                <View style={styles.crmStatItem}>
                  <ThemedText style={styles.crmStatLabel}>Recent Activity</ThemedText>
                  <ThemedText style={styles.crmStatValue}>
                    {hubspotData.recentActivity.total_changes}
                  </ThemedText>
                </View>
              </View>
            )}
          </View>

          {/* File System Stats */}
          {fileSystemStats && (
            <View style={styles.section}>
              <ThemedText type="subtitle" style={styles.sectionTitle}>
                Virtual File System
              </ThemedText>
              <View style={styles.fsStatsContainer}>
                <View style={styles.fsStatItem}>
                  <ThemedText style={styles.fsStatLabel}>Files</ThemedText>
                  <ThemedText style={styles.fsStatValue}>
                    {fileSystemStats.totalFiles || 0}
                  </ThemedText>
                </View>
                <View style={styles.fsStatItem}>
                  <ThemedText style={styles.fsStatLabel}>Size</ThemedText>
                  <ThemedText style={styles.fsStatValue}>
                    {Math.round((fileSystemStats.totalSize || 0) / 1024)}KB
                  </ThemedText>
                </View>
                <View style={styles.fsStatItem}>
                  <ThemedText style={styles.fsStatLabel}>Operations</ThemedText>
                  <ThemedText style={styles.fsStatValue}>
                    {fileSystemStats.totalOperations || 0}
                  </ThemedText>
                </View>
              </View>
            </View>
          )}
        </ScrollView>

        {/* Command Palette */}
        <CommandPalette
          isVisible={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
          commands={commands}
        />

        {/* Log Stream - "The Matrix" */}
        <LogStream
          isVisible={isLogStreamOpen}
          onClose={() => setIsLogStreamOpen(false)}
          logs={mockLogs}
        />
      </ThemedView>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    textAlign: 'center',
    opacity: 0.7,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    marginTop: 10,
    textAlign: 'center',
    opacity: 0.7,
  },
  retryButton: {
    marginTop: 20,
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#66FCF1',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
  },
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  subtitle: {
    marginTop: 5,
    opacity: 0.7,
  },
  section: {
    marginHorizontal: 20,
    marginVertical: 10,
  },
  sectionTitle: {
    marginBottom: 15,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  statusItem: {
    flex: 1,
  },
  statusText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#66FCF1',
  },
  fsStatsContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  fsStatItem: {
    flex: 1,
    alignItems: 'center',
  },
  fsStatLabel: {
    fontSize: 12,
    opacity: 0.7,
    marginBottom: 5,
    color: '#C5C6C7',
  },
  fsStatValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#66FCF1',
  },
  crmStatsContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  crmStatItem: {
    flex: 1,
    alignItems: 'center',
  },
  crmStatLabel: {
    fontSize: 12,
    opacity: 0.7,
    marginBottom: 5,
    color: '#C5C6C7',
  },
  crmStatValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#66FCF1',
  },
});