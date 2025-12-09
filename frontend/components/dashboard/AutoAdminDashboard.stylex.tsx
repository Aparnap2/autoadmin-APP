import React, { useState } from 'react';
import {
  View,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { useAutoAdminAgents } from '@/hooks/useAutoAdminAgents';
import { ThemedText } from '@/components/themed-text.stylex';
import { ThemedView } from '@/components/themed-view.stylex';
import { AgentStatusCard } from './AgentStatusCard';
import { QuickActions } from './QuickActions';
import { ConversationPreview } from './ConversationPreview';
import { SystemMetrics } from './SystemMetrics';
import { TaskProgress } from './TaskProgress';
import { BackendStatus } from '@/components/BackendStatus';
import ErrorBoundary from '@/components/ErrorBoundary';

interface AutoAdminDashboardProps {
  userId: string;
}

const dashboardStyles = stylex.create({
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
    padding: tokens.spacing.xl,
  },
  loadingText: {
    marginTop: tokens.spacing.sm,
    textAlign: 'center',
    opacity: 0.7,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: tokens.spacing.xl,
  },
  errorText: {
    marginTop: tokens.spacing.sm,
    textAlign: 'center',
    opacity: 0.7,
  },
  retryButton: {
    marginTop: tokens.spacing.lg,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.colors.tint,
    borderRadius: tokens.borderRadius.md,
  },
  retryButtonText: {
    color: tokens.colors.background,
    fontWeight: '600',
  },
  header: {
    padding: tokens.spacing.xl,
    paddingBottom: tokens.spacing.md,
  },
  subtitle: {
    marginTop: '5px',
    opacity: 0.7,
  },
  section: {
    marginHorizontal: tokens.spacing.xl,
    marginVertical: tokens.spacing.sm,
  },
  sectionTitle: {
    marginBottom: '15px',
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#1F2833', // Secondary background color
    padding: tokens.spacing.md,
    borderRadius: '10px',
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  statusItem: {
    flex: 1,
  },
  statusText: {
    fontSize: 14,
    fontWeight: '500',
    color: tokens.colors.tint,
  },
  fsStatsContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833', // Secondary background color
    padding: tokens.spacing.md,
    borderRadius: '10px',
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  fsStatItem: {
    flex: 1,
    alignItems: 'center',
  },
  fsStatLabel: {
    fontSize: 12,
    opacity: 0.7,
    marginBottom: '5px',
    color: tokens.colors.text,
  },
  fsStatValue: {
    fontSize: 18,
    fontWeight: '600',
    color: tokens.colors.tint,
  },
});

export function AutoAdminDashboard({ userId }: AutoAdminDashboardProps) {
  const [refreshing, setRefreshing] = useState(false);

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
    autoInitialize: false,
    enableStreaming: false,
    enableRealtimeSync: false,
    offlineMode: true,
    onError: (err) => {
      console.error('AutoAdmin Dashboard Error:', err);
    },
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await getAgentMetrics();
    } catch (error) {
      console.error('Error refreshing metrics:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleQuickAction = async (action: string, params?: any) => {
    try {
      switch (action) {
        case 'new_task':
          Alert.alert('Quick Action', 'Task creation interface would open here');
          break;
        case 'chat_with_ceo':
          await sendMessage('Please provide a status update on current system operations', {
            context: 'quick_status_check'
          });
          break;
        case 'market_analysis':
          await sendMessage('Can you analyze current market trends and provide insights?', {
            context: 'market_analysis',
            agentType: 'strategy'
          });
          break;
        case 'code_review':
          await sendMessage('Please review current codebase for optimization opportunities', {
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
            'This will reset current agent session. Continue?',
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
          Alert.alert('Open Chat', 'Navigate to full chat interface to interact with agents.');
          break;
        default:
          await sendMessage(action, params);
      }
    } catch (error) {
      console.error('Error executing quick action:', error);
      Alert.alert('Error', 'Failed to execute action');
    }
  };

  if (isLoading) {
    return (
      <ErrorBoundary>
        <ThemedView {...stylex.props(dashboardStyles.container)}>
          <View {...stylex.props(dashboardStyles.loadingContainer)}>
            <ActivityIndicator size="large" color={tokens.colors.tint} />
            <ThemedText type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText {...stylex.props(dashboardStyles.loadingText)}>
              Initializing agent system...
            </ThemedText>
          </View>
        </ThemedView>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ThemedView {...stylex.props(dashboardStyles.container)}>
        <BackendStatus
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
          {...stylex.props(dashboardStyles.scrollView)}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          <View {...stylex.props(dashboardStyles.header)}>
            <ThemedText type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText {...stylex.props(dashboardStyles.subtitle)}>
              Intelligent Agent System
            </ThemedText>
          </View>

          <View {...stylex.props(dashboardStyles.section)}>
            <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
              System Status
            </ThemedText>
            <View {...stylex.props(dashboardStyles.statusRow)}>
              <View {...stylex.props(dashboardStyles.statusItem)}>
                <ThemedText {...stylex.props(dashboardStyles.statusText)}>
                  Status: {isInitialized ? 'Online' : 'Initializing'}
                </ThemedText>
              </View>
              <View {...stylex.props(dashboardStyles.statusItem)}>
                <ThemedText {...stylex.props(dashboardStyles.statusText)}>
                  Session: Active
                </ThemedText>
              </View>
            </View>
          </View>

          <View {...stylex.props(dashboardStyles.section)}>
            <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
              Agent Swarm Status
            </ThemedText>
            <AgentStatusCard
              state={state}
              metrics={metrics}
              isLoading={!isInitialized}
            />
          </View>

          {metrics && (
            <View {...stylex.props(dashboardStyles.section)}>
              <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
                System Metrics
              </ThemedText>
              <SystemMetrics
                metrics={metrics}
                fileSystemStats={fileSystemStats}
              />
            </View>
          )}

          {state?.activeTasks && state.activeTasks.length > 0 && (
            <View {...stylex.props(dashboardStyles.section)}>
              <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
                Current Task Progress
              </ThemedText>
              <TaskProgress taskStatus={state.activeTasks[0]} />
            </View>
          )}

          <View {...stylex.props(dashboardStyles.section)}>
            <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
              Quick Actions
            </ThemedText>
            <QuickActions
              onAction={handleQuickAction}
              isDisabled={!isInitialized}
            />
          </View>

          <View {...stylex.props(dashboardStyles.section)}>
            <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
              Recent Conversations
            </ThemedText>
            <ConversationPreview
              conversations={conversationHistory.slice(-5)}
              isLoading={!isInitialized}
            />
          </View>

          {fileSystemStats && (
            <View {...stylex.props(dashboardStyles.section)}>
              <ThemedText type="subtitle" {...stylex.props(dashboardStyles.sectionTitle)}>
                Virtual File System
              </ThemedText>
              <View {...stylex.props(dashboardStyles.fsStatsContainer)}>
                <View {...stylex.props(dashboardStyles.fsStatItem)}>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatLabel)}>Files</ThemedText>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatValue)}>
                    {fileSystemStats.totalFiles || 0}
                  </ThemedText>
                </View>
                <View {...stylex.props(dashboardStyles.fsStatItem)}>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatLabel)}>Size</ThemedText>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatValue)}>
                    {Math.round((fileSystemStats.totalSize || 0) / 1024)}KB
                  </ThemedText>
                </View>
                <View {...stylex.props(dashboardStyles.fsStatItem)}>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatLabel)}>Operations</ThemedText>
                  <ThemedText {...stylex.props(dashboardStyles.fsStatValue)}>
                    {fileSystemStats.totalOperations || 0}
                  </ThemedText>
                </View>
              </View>
            </View>
          )}
        </ScrollView>
      </ThemedView>
    </ErrorBoundary>
  );
}