import React, { useState } from 'react';
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
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
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
    autoInitialize: false, // Don't auto-initialize - only when user interacts
    enableStreaming: false,
    enableRealtimeSync: false,
    offlineMode: true, // Always work in offline mode
    onError: (err) => {
      console.error('AutoAdmin Dashboard Error:', err);
      // Don't show alert for every error - let the UI handle it gracefully
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
  };

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
      <ThemedView style={styles.container}>
        {/* Backend Status Indicator */}
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
          style={styles.scrollView}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <View style={styles.header}>
            <ThemedText type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText style={styles.subtitle}>
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
});