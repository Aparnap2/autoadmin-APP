import React from 'react';
import { View, StyleSheet } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

interface TaskProgressProps {
  taskStatus: any;
}

export function TaskProgress({ taskStatus }: TaskProgressProps) {
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending':
        return '#f59e0b'; // amber-500
      case 'processing':
        return '#3b82f6'; // blue-500
      case 'completed':
        return '#10b981'; // green-500
      case 'failed':
        return '#ef4444'; // red-500
      case 'delegated':
        return '#8b5cf6'; // violet-500
      default:
        return '#6b7280'; // gray-500
    }
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'delegated':
        return 'Delegated';
      default:
        return 'Unknown';
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'high':
        return '#ef4444'; // red-500
      case 'medium':
        return '#f59e0b'; // amber-500
      case 'low':
        return '#10b981'; // green-500
      default:
        return '#6b7280'; // gray-500
    }
  };

  const getAgentIcon = (agentType?: string): string => {
    switch (agentType) {
      case 'ceo':
        return '👔';
      case 'strategy':
        return '📊';
      case 'devops':
        return '⚙️';
      default:
        return '🤖';
    }
  };

  const getTaskTypeIcon = (taskType: string): string => {
    const iconMap: Record<string, string> = {
      market_research: '📈',
      financial_analysis: '💰',
      code_analysis: '💻',
      ui_ux_review: '🎨',
      strategic_planning: '🎯',
      technical_decision: '⚡',
      github_actions_delegation: '🔄',
      virtual_file_operation: '📁'
    };
    return iconMap[taskType] || '📋';
  };

  const formatTaskType = (taskType: string): string => {
    const taskNames: Record<string, string> = {
      market_research: 'Market Research',
      financial_analysis: 'Financial Analysis',
      code_analysis: 'Code Analysis',
      ui_ux_review: 'UI/UX Review',
      strategic_planning: 'Strategic Planning',
      technical_decision: 'Technical Decision',
      github_actions_delegation: 'GitHub Actions',
      virtual_file_operation: 'File Operation'
    };
    return taskNames[taskType] || taskType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatDuration = (createdAt: Date, updatedAt: Date): string => {
    const durationMs = updatedAt.getTime() - createdAt.getTime();
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const getProgressPercentage = (status: string): number => {
    switch (status) {
      case 'pending':
        return 0;
      case 'processing':
        return 50;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      case 'delegated':
        return 25;
      default:
        return 0;
    }
  };

  const progressPercentage = getProgressPercentage(taskStatus?.status);
  const isCompleted = taskStatus?.status === 'completed';
  const isFailed = taskStatus?.status === 'failed';

  return (
    <ThemedView style={styles.container}>
      {/* Task Header */}
      <View style={styles.taskHeader}>
        <View style={styles.taskInfo}>
          <View style={styles.taskIconContainer}>
            <ThemedText style={styles.taskIcon}>
              {getTaskTypeIcon(taskStatus?.type)}
            </ThemedText>
          </View>
          <View style={styles.taskMeta}>
            <ThemedText style={styles.taskTitle} numberOfLines={1}>
              {formatTaskType(taskStatus?.type)}
            </ThemedText>
            <View style={styles.taskBadges}>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor(taskStatus?.status) }]}>
                <ThemedText style={styles.statusText}>
                  {getStatusText(taskStatus?.status)}
                </ThemedText>
              </View>
              <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(taskStatus?.priority) }]}>
                <ThemedText style={styles.priorityText}>
                  {taskStatus?.priority?.toUpperCase()}
                </ThemedText>
              </View>
            </View>
          </View>
        </View>

        <View style={styles.agentInfo}>
          {taskStatus?.assignedTo && (
            <View style={styles.assignedAgent}>
              <ThemedText style={styles.agentIcon}>
                {getAgentIcon(taskStatus.assignedTo)}
              </ThemedText>
              <ThemedText style={styles.agentName} numberOfLines={1}>
                {taskStatus.assignedTo.replace('-agent', '').toUpperCase()}
              </ThemedText>
            </View>
          )}
        </View>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${progressPercentage}%`,
                backgroundColor: isCompleted ? '#10b981' : isFailed ? '#ef4444' : '#3b82f6'
              }
            ]}
          />
        </View>
        <ThemedText style={styles.progressText}>
          {progressPercentage}% Complete
        </ThemedText>
      </View>

      {/* Task Details */}
      <View style={styles.taskDetails}>
        <View style={styles.detailRow}>
          <ThemedText style={styles.detailLabel}>Created:</ThemedText>
          <ThemedText style={styles.detailValue}>
            {taskStatus?.createdAt ? new Date(taskStatus.createdAt).toLocaleTimeString() : 'Unknown'}
          </ThemedText>
        </View>

        <View style={styles.detailRow}>
          <ThemedText style={styles.detailLabel}>Duration:</ThemedText>
          <ThemedText style={styles.detailValue}>
            {taskStatus?.createdAt && taskStatus?.updatedAt
              ? formatDuration(new Date(taskStatus.createdAt), new Date(taskStatus.updatedAt))
              : 'In progress'}
          </ThemedText>
        </View>

        {taskStatus?.delegatedTo && (
          <View style={styles.detailRow}>
            <ThemedText style={styles.detailLabel}>Delegated to:</ThemedText>
            <ThemedText style={styles.detailValue}>
              {taskStatus.delegatedTo}
            </ThemedText>
          </View>
        )}

        {taskStatus?.metadata && Object.keys(taskStatus.metadata).length > 0 && (
          <View style={styles.metadataContainer}>
            <ThemedText style={styles.metadataTitle}>Additional Info:</ThemedText>
            {Object.entries(taskStatus.metadata).map(([key, value]) => (
              <View key={key} style={styles.metadataRow}>
                <ThemedText style={styles.metadataKey}>
                  {key.replace(/_/g, ' ').toUpperCase()}:
                </ThemedText>
                <ThemedText style={styles.metadataValue}>
                  {String(value)}
                </ThemedText>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Status Message */}
      {isCompleted && (
        <View style={styles.statusMessage}>
          <ThemedText style={styles.successMessage}>
            ✅ Task completed successfully
          </ThemedText>
        </View>
      )}

      {isFailed && (
        <View style={styles.statusMessage}>
          <ThemedText style={styles.errorMessage}>
            ❌ Task failed to complete
          </ThemedText>
        </View>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
    marginVertical: 4,
  },
  taskHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  taskInfo: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
  },
  taskIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#e5e7eb',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  taskIcon: {
    fontSize: 24,
  },
  taskMeta: {
    flex: 1,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  taskBadges: {
    flexDirection: 'row',
    gap: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  priorityText: {
    color: 'white',
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  agentInfo: {
    alignItems: 'flex-end',
  },
  assignedAgent: {
    alignItems: 'center',
  },
  agentIcon: {
    fontSize: 20,
    marginBottom: 4,
  },
  agentName: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    opacity: 0.7,
  },
  progressContainer: {
    marginBottom: 16,
  },
  progressBar: {
    height: 8,
    backgroundColor: '#e5e7eb',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
  taskDetails: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  detailLabel: {
    fontSize: 12,
    opacity: 0.7,
    flex: 1,
  },
  detailValue: {
    fontSize: 12,
    fontWeight: '500',
    flex: 2,
    textAlign: 'right',
  },
  metadataContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  metadataTitle: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
  },
  metadataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  metadataKey: {
    fontSize: 11,
    opacity: 0.7,
    flex: 1,
  },
  metadataValue: {
    fontSize: 11,
    fontWeight: '500',
    flex: 2,
    textAlign: 'right',
  },
  statusMessage: {
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
  },
  successMessage: {
    color: '#10b981',
    fontSize: 14,
    fontWeight: '500',
  },
  errorMessage: {
    color: '#ef4444',
    fontSize: 14,
    fontWeight: '500',
  },
});