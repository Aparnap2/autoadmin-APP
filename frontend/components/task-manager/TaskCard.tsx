/**
 * Task Card Component
 * Individual task display with status, actions, and details
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useThemeColor } from '@/hooks/use-theme-color';
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

const taskTypeColors: Record<TaskType, string> = {
  market_research: '#8B5CF6',
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
  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const borderColor = useThemeColor({ light: '#E5E7EB', dark: '#374151' }, 'border');

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
        style={[styles.compactContainer, { backgroundColor, borderColor }]}
        onPress={() => onPress?.(task)}
        disabled={loading}
      >
        <View style={styles.compactHeader}>
          <View style={styles.compactLeft}>
            <Ionicons
              name={statusIcon}
              size={16}
              color={statusConfig.text}
              style={styles.statusIcon}
            />
            <ThemedText
              style={[styles.compactTitle, { color: textColor }]}
              numberOfLines={1}
            >
              {task.description || `${task.type} task`}
            </ThemedText>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: statusConfig.bg }]}>
            <ThemedText style={[styles.statusText, { color: statusConfig.text }]}>
              {task.status}
            </ThemedText>
          </View>
        </View>

        <View style={styles.compactMeta}>
          <Text style={[styles.compactMetaText, { color: typeColor }]}>
            {task.type.replace('_', ' ')}
          </Text>
          <Text style={[styles.compactMetaText, { color: '#6B7280' }]}>
            {formatDate(task.created_at)}
          </Text>
        </View>

        {loading && (
          <ActivityIndicator size="small" color={typeColor} style={styles.loader} />
        )}
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      style={[styles.container, { backgroundColor, borderColor }]}
      onPress={() => onPress?.(task)}
      disabled={loading}
    >
      <View style={styles.header}>
        <View style={styles.leftSection}>
          <View style={[styles.typeIndicator, { backgroundColor: typeColor }]} />
          <View style={styles.titleSection}>
            <ThemedText
              style={[styles.title, { color: textColor }]}
              numberOfLines={2}
            >
              {task.description || `${task.type} task`}
            </ThemedText>
            <Text style={[styles.type, { color: typeColor }]}>
              {task.type.replace('_', ' ').toUpperCase()}
            </Text>
          </View>
        </View>

        <View style={[styles.statusBadge, { backgroundColor: statusConfig.bg }]}>
          <Ionicons
            name={statusIcon}
            size={14}
            color={statusConfig.text}
            style={styles.statusIcon}
          />
          <ThemedText style={[styles.statusText, { color: statusConfig.text }]}>
            {task.status}
          </ThemedText>
        </View>
      </View>

      <View style={styles.meta}>
        <View style={styles.metaItem}>
          <Ionicons name="time-outline" size={14} color="#6B7280" />
          <Text style={styles.metaText}>Created {formatDate(task.created_at)}</Text>
        </View>

        {task.assigned_to && (
          <View style={styles.metaItem}>
            <Ionicons name="person-outline" size={14} color="#6B7280" />
            <Text style={styles.metaText}>{task.assigned_to}</Text>
          </View>
        )}

        <View style={styles.metaItem}>
          <Ionicons
            name="flag-outline"
            size={14}
            color={task.priority === 'high' ? '#EF4444' : task.priority === 'medium' ? '#F59E0B' : '#6B7280'}
          />
          <Text style={styles.metaText}>{task.priority.toUpperCase()}</Text>
        </View>
      </View>

      {task.error && (
        <View style={[styles.errorSection, { backgroundColor: '#FEE2E2' }]}>
          <Ionicons name="warning-outline" size={14} color="#991B1B" />
          <Text style={[styles.errorText, { color: '#991B1B' }]} numberOfLines={2}>
            {task.error}
          </Text>
        </View>
      )}

      {showActions && (canCancel || canRetry) && (
        <View style={styles.actions}>
          {canCancel && (
            <TouchableOpacity
              style={[styles.actionButton, styles.cancelButton]}
              onPress={handleCancel}
              disabled={loading}
            >
              <Ionicons name="close-outline" size={16} color="#991B1B" />
              <Text style={[styles.actionText, { color: '#991B1B' }]}>Cancel</Text>
            </TouchableOpacity>
          )}

          {canRetry && (
            <TouchableOpacity
              style={[styles.actionButton, styles.retryButton]}
              onPress={handleRetry}
              disabled={loading}
            >
              <Ionicons name="refresh-outline" size={16} color="#1E40AF" />
              <Text style={[styles.actionText, { color: '#1E40AF' }]}>Retry</Text>
            </TouchableOpacity>
          )}

          {loading && (
            <ActivityIndicator size="small" color={typeColor} />
          )}
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  compactContainer: {
    marginHorizontal: 16,
    marginVertical: 4,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
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
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
    lineHeight: 22,
  },
  compactTitle: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
    lineHeight: 20,
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
    color: '#6B7280',
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
  },
  errorText: {
    fontSize: 12,
    flex: 1,
    lineHeight: 16,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
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