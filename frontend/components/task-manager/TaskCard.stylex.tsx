/**
 * Task Card Component - StyleX Version
 * Individual task display with status, actions, and details
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { ThemedText } from '@/components/themed-text.stylex';
import { ThemedView } from '@/components/themed-view.stylex';
import { TaskStatus, TaskType } from '@/services/agents/types';
import { AgentTaskResponse } from '@/services/api/fastapi-client';

interface TaskCardProps {
  task: AgentTaskResponse;
  onPress?: (task: AgentTaskResponse) => void;
  onCancel?: (taskId: string) => void;
  onRetry?: (taskId: string) => void;
  onStatusUpdate?: (taskId: string, status: string) => void;
  showActions?: boolean;
  compact?: boolean;
}

const taskCardStyles = stylex.create({
  container: {
    marginHorizontal: tokens.spacing.md,
    marginVertical: 6,
    padding: tokens.spacing.md,
    borderRadius: tokens.borderRadius.lg,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    ...tokens.shadow.md,
  },
  compactContainer: {
    marginHorizontal: tokens.spacing.md,
    marginVertical: 4,
    padding: tokens.spacing.md,
    borderRadius: tokens.borderRadius.md,
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  compactHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  leftSection: {
    flexDirection: 'row',
    flex: 1,
  },
  compactLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  typeIndicator: {
    width: 4,
    borderRadius: 2,
    marginRight: 12,
  },
  titleSection: {
    flex: 1,
  },
  title: {
    fontSize: tokens.fontSize.md,
    fontWeight: '600',
    marginBottom: 4,
    lineHeight: 22,
    color: tokens.colors.text,
  },
  compactTitle: {
    fontSize: tokens.fontSize.sm,
    fontWeight: '600',
    flex: 1,
    lineHeight: 20,
    color: tokens.colors.text,
  },
  type: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusIcon: {
    marginRight: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  meta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 8,
  },
  compactMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: 12,
    color: '#6B7280', // Secondary gray
  },
  compactMetaText: {
    fontSize: 11,
    fontWeight: '500',
  },
  errorSection: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    padding: 8,
    borderRadius: 6,
    marginBottom: 8,
    backgroundColor: '#FEE2E2', // Light red background
  },
  errorText: {
    fontSize: 12,
    flex: 1,
    lineHeight: 16,
    color: '#991B1B', // Dark red text
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: tokens.colors.border,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
  },
  cancelButton: {
    backgroundColor: '#FEF2F2',
    borderColor: '#FECACA',
  },
  retryButton: {
    backgroundColor: '#EFF6FF',
    borderColor: '#BFDBFE',
  },
  actionText: {
    fontSize: 12,
    fontWeight: '600',
  },
  loader: {
    position: 'absolute',
    right: 12,
    top: '50%',
    marginTop: -10,
  },
});

const taskTypeColors: Record<TaskType, string> = {
  market_search: '#8B5CF6',
  financial_analysis: '#10B981',
  code_analysis: '#3B82F6',
  ui_ux_review: '#F59E0B',
  strategic_planning: '#EF4444',
  technical_decision: '#6366F1',
  github_actions_delegation: '#84CC16',
  virtual_file_operation: '#EC4899',
};

const statusIcons: Record<string, keyof typeof Ionicons.glyphMap> = {
  pending: 'time',
  processing: 'sync',
  completed: 'checkmark-circle',
  failed: 'close-circle',
  delegated: 'arrow-forward-circle',
};

const statusColors: Record<string, { bg: string; text: string }> = {
  pending: { bg: '#FEF3C7', text: '#92400E' },
  processing: { bg: '#DBEAFE', text: '#1E40AF' },
  completed: { bg: '#D1FAE5', text: '#065F46' },
  failed: { bg: '#FEE2E2', text: '#991B1B' },
  delegated: { bg: '#E9D5FF', text: '#6B21A8' },
};

export default function TaskCard({
  task,
  onPress,
  onCancel,
  onRetry,
  onStatusUpdate,
  showActions = true,
  compact = false,
}: TaskCardProps) {
  const [loading, setLoading] = useState(false);

  const typeColor = taskTypeColors[task.type as TaskType] || '#6B7280';
  const statusConfig = statusColors[task.status] || statusColors.pending;
  const statusIcon = statusIcons[task.status] || 'help-circle';

  const handleCancel = async () => {
    if (!onCancel) return;

    Alert.alert(
      'Cancel Task',
      'Are you sure you want to cancel this task?',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes',
          style: 'destructive',
          onPress: async () => {
            setLoading(true);
            try {
              await onCancel(task.id);
            } catch (error) {
              Alert.alert('Error', 'Failed to cancel task');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const handleRetry = async () => {
    if (!onRetry || task.status !== 'failed') return;

    setLoading(true);
    try {
      await onRetry(task.id);
    } catch (error) {
      Alert.alert('Error', 'Failed to retry task');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const canCancel = task.status === 'pending' || task.status === 'processing';
  const canRetry = task.status === 'failed';

  if (compact) {
    return (
      <TouchableOpacity
        {...stylex.props(taskCardStyles.compactContainer)}
        onPress={() => onPress?.(task)}
        disabled={loading}
      >
        <View {...stylex.props(taskCardStyles.compactHeader)}>
          <View {...stylex.props(taskCardStyles.compactLeft)}>
            <Ionicons
              name={statusIcon}
              size={16}
              color={statusConfig.text}
              {...stylex.props(taskCardStyles.statusIcon)}
            />
            <ThemedText
              {...stylex.props(taskCardStyles.compactTitle)}
              numberOfLines={1}
            >
              {task.description || `${task.type} task`}
            </ThemedText>
          </View>
          <View
            {...stylex.props(taskCardStyles.statusBadge)}
            style={{
              backgroundColor: statusConfig.bg,
            }}
          >
            <ThemedText
              {...stylex.props(taskCardStyles.statusText)}
              style={{
                color: statusConfig.text,
              }}
            >
              {task.status}
            </ThemedText>
          </View>
        </View>

        <View {...stylex.props(taskCardStyles.compactMeta)}>
          <Text
            {...stylex.props(taskCardStyles.compactMetaText)}
            style={{
              color: typeColor,
            }}
          >
            {task.type.replace('_', ' ')}
          </Text>
          <Text {...stylex.props(taskCardStyles.compactMetaText)}>
            {formatDate(task.created_at)}
          </Text>
        </View>

        {loading && (
          <ActivityIndicator
            size="small"
            color={typeColor}
            {...stylex.props(taskCardStyles.loader)}
          />
        )}
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      {...stylex.props(taskCardStyles.container)}
      onPress={() => onPress?.(task)}
      disabled={loading}
    >
      <View {...stylex.props(taskCardStyles.header)}>
        <View {...stylex.props(taskCardStyles.leftSection)}>
          <View
            {...stylex.props(taskCardStyles.typeIndicator)}
            style={{
              backgroundColor: typeColor,
            }}
          />
          <View {...stylex.props(taskCardStyles.titleSection)}>
            <ThemedText
              {...stylex.props(taskCardStyles.title)}
              numberOfLines={2}
            >
              {task.description || `${task.type} task`}
            </ThemedText>
            <Text
              {...stylex.props(taskCardStyles.type)}
              style={{
                color: typeColor,
              }}
            >
              {task.type.replace('_', ' ').toUpperCase()}
            </Text>
          </View>
        </View>

        <View
          {...stylex.props(taskCardStyles.statusBadge)}
          style={{
            backgroundColor: statusConfig.bg,
          }}
        >
          <Ionicons
            name={statusIcon}
            size={14}
            color={statusConfig.text}
            {...stylex.props(taskCardStyles.statusIcon)}
          />
          <ThemedText
            {...stylex.props(taskCardStyles.statusText)}
            style={{
              color: statusConfig.text,
            }}
          >
            {task.status}
          </ThemedText>
        </View>
      </View>

      <View {...stylex.props(taskCardStyles.meta)}>
        <View {...stylex.props(taskCardStyles.metaItem)}>
          <Ionicons name="time-outline" size={14} color="#6B7280" />
          <Text {...stylex.props(taskCardStyles.metaText)}>
            Created {formatDate(task.created_at)}
          </Text>
        </View>

        {task.assigned_to && (
          <View {...stylex.props(taskCardStyles.metaItem)}>
            <Ionicons name="person-outline" size={14} color="#6B7280" />
            <Text {...stylex.props(taskCardStyles.metaText)}>
              {task.assigned_to}
            </Text>
          </View>
        )}

        <View {...stylex.props(taskCardStyles.metaItem)}>
          <Ionicons
            name="flag-outline"
            size={14}
            color={
              task.priority === 'high'
                ? '#EF4444'
                : task.priority === 'medium'
                ? '#F59E0B'
                : '#6B7280'
            }
          />
          <Text {...stylex.props(taskCardStyles.metaText)}>
            {task.priority.toUpperCase()}
          </Text>
        </View>
      </View>

      {task.error && (
        <View {...stylex.props(taskCardStyles.errorSection)}>
          <Ionicons name="warning-outline" size={14} color="#991B1B" />
          <Text
            {...stylex.props(taskCardStyles.errorText)}
            numberOfLines={2}
          >
            {task.error}
          </Text>
        </View>
      )}

      {showActions && (canCancel || canRetry) && (
        <View {...stylex.props(taskCardStyles.actions)}>
          {canCancel && (
            <TouchableOpacity
              {...stylex.props(
                taskCardStyles.actionButton,
                taskCardStyles.cancelButton
              )}
              onPress={handleCancel}
              disabled={loading}
            >
              <Ionicons name="close-outline" size={16} color="#991B1B" />
              <Text
                {...stylex.props(taskCardStyles.actionText)}
                style={{ color: '#991B1B' }}
              >
                Cancel
              </Text>
            </TouchableOpacity>
          )}

          {canRetry && (
            <TouchableOpacity
              {...stylex.props(
                taskCardStyles.actionButton,
                taskCardStyles.retryButton
              )}
              onPress={handleRetry}
              disabled={loading}
            >
              <Ionicons name="refresh-outline" size={16} color="#1E40AF" />
              <Text
                {...stylex.props(taskCardStyles.actionText)}
                style={{ color: '#1E40AF' }}
              >
                Retry
              </Text>
            </TouchableOpacity>
          )}

          {loading && (
            <ActivityIndicator
              size="small"
              color={typeColor}
            />
          )}
        </View>
      )}
    </TouchableOpacity>
  );
}