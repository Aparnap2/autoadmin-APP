/**
 * Task List Component
 * Lists all tasks with filtering and sorting capabilities
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Alert,
  TextInput,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useThemeColor } from '@/hooks/use-theme-color';
import TaskCard from './TaskCard';
import { AgentTaskResponse } from '@/services/api/fastapi-client';
import { TaskStatus, TaskType } from '@/services/agents/types';
import AgentAPIService, { TaskFilter, TaskStats } from '@/services/api/agent-api';

interface TaskListProps {
  onTaskPress?: (task: AgentTaskResponse) => void;
  onTaskCancel?: (taskId: string) => void;
  onTaskRetry?: (taskId: string) => void;
  agentService?: AgentAPIService;
  initialFilter?: TaskFilter;
  showStats?: boolean;
  showSearch?: boolean;
  showFilters?: boolean;
}

const taskTypeOptions: { value: TaskType; label: string }[] = [
  { value: 'market_research', label: 'Market Research' },
  { value: 'financial_analysis', label: 'Financial Analysis' },
  { value: 'code_analysis', label: 'Code Analysis' },
  { value: 'ui_ux_review', label: 'UI/UX Review' },
  { value: 'strategic_planning', label: 'Strategic Planning' },
  { value: 'technical_decision', label: 'Technical Decision' },
  { value: 'github_actions_delegation', label: 'GitHub Actions' },
  { value: 'virtual_file_operation', label: 'File Operation' },
];

const statusOptions: { value: TaskStatus['status']; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'delegated', label: 'Delegated' },
];

const priorityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

export default function TaskList({
  onTaskPress,
  onTaskCancel,
  onTaskRetry,
  agentService,
  initialFilter,
  showStats = true,
  showSearch = true,
  showFilters = true,
}: TaskListProps) {
  const [tasks, setTasks] = useState<AgentTaskResponse[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<AgentTaskResponse[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<TaskFilter>(initialFilter || {});
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const borderColor = useThemeColor({ light: '#E5E7EB', dark: '#374151' }, 'border');
  const inputBackgroundColor = useThemeColor({ light: '#F9FAFB', dark: '#1F2937' }, 'background');

  // Load tasks from agent service
  const loadTasks = useCallback(async () => {
    if (!agentService) return;

    try {
      setLoading(true);
      const loadedTasks = await agentService.getTasks(filter);
      setTasks(loadedTasks);
      setFilteredTasks(loadedTasks);

      // Load stats
      if (showStats) {
        const taskStats = await agentService.getTaskStats(filter);
        setStats(taskStats);
      }
    } catch (error) {
      console.error('Error loading tasks:', error);
      Alert.alert('Error', 'Failed to load tasks');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [agentService, filter, showStats]);

  // Load tasks on mount and when filter changes
  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // Apply search filter
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredTasks(tasks);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = tasks.filter(task =>
        task.description?.toLowerCase().includes(query) ||
        task.type.toLowerCase().includes(query) ||
        task.assigned_to?.toLowerCase().includes(query) ||
        task.status.toLowerCase().includes(query)
      );
      setFilteredTasks(filtered);
    }
  }, [tasks, searchQuery]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadTasks();
  };

  const handleTaskCancel = async (taskId: string) => {
    if (!agentService) return;

    try {
      await agentService.cancelTask(taskId);
      Alert.alert('Success', 'Task cancelled successfully');
      loadTasks(); // Reload tasks
    } catch (error) {
      console.error('Error cancelling task:', error);
      Alert.alert('Error', 'Failed to cancel task');
    }
  };

  const handleTaskRetry = async (taskId: string) => {
    if (!agentService) return;

    try {
      await agentService.retryTask(taskId);
      Alert.alert('Success', 'Task retry initiated');
      loadTasks(); // Reload tasks
    } catch (error) {
      console.error('Error retrying task:', error);
      Alert.alert('Error', 'Failed to retry task');
    }
  };

  const updateFilter = (newFilter: Partial<TaskFilter>) => {
    setFilter(prev => ({ ...prev, ...newFilter }));
  };

  const clearFilter = () => {
    setFilter({});
    setSearchQuery('');
  };

  const renderTask = ({ item }: { item: AgentTaskResponse }) => (
    <TaskCard
      task={item}
      onPress={onTaskPress}
      onCancel={onTaskCancel || handleTaskCancel}
      onRetry={onTaskRetry || handleTaskRetry}
    />
  );

  const renderStats = () => {
    if (!stats || !showStats) return null;

    return (
      <View style={[styles.statsContainer, { backgroundColor, borderColor }]}>
        <ThemedText style={styles.statsTitle}>Task Overview</ThemedText>
        <View style={styles.statsGrid}>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: textColor }]}>{stats.total}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: '#3B82F6' }]}>{stats.processing}</Text>
            <Text style={styles.statLabel}>Processing</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: '#10B981' }]}>{stats.completed}</Text>
            <Text style={styles.statLabel}>Completed</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: '#EF4444' }]}>{stats.failed}</Text>
            <Text style={styles.statLabel}>Failed</Text>
          </View>
        </View>
        {stats.total > 0 && (
          <View style={styles.progressContainer}>
            <Text style={styles.progressLabel}>Success Rate</Text>
            <Text style={[styles.progressValue, { color: stats.successRate > 80 ? '#10B981' : '#F59E0B' }]}>
              {stats.successRate.toFixed(1)}%
            </Text>
          </View>
        )}
      </View>
    );
  };

  const renderFilterPanel = () => {
    if (!showFilters || !showFilterPanel) return null;

    return (
      <View style={[styles.filterPanel, { backgroundColor, borderColor }]}>
        <View style={styles.filterSection}>
          <ThemedText style={styles.filterTitle}>Status</ThemedText>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.filterOptions}>
              {statusOptions.map(option => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.filterChip,
                    {
                      backgroundColor: filter.status?.includes(option.value)
                        ? '#3B82F6'
                        : inputBackgroundColor,
                      borderColor,
                    }
                  ]}
                  onPress={() => {
                    const currentStatus = filter.status || [];
                    const newStatus = currentStatus.includes(option.value)
                      ? currentStatus.filter(s => s !== option.value)
                      : [...currentStatus, option.value];
                    updateFilter({ status: newStatus.length > 0 ? newStatus : undefined });
                  }}
                >
                  <Text style={[
                    styles.filterChipText,
                    { color: filter.status?.includes(option.value) ? '#FFFFFF' : textColor }
                  ]}>
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>
        </View>

        <View style={styles.filterSection}>
          <ThemedText style={styles.filterTitle}>Type</ThemedText>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.filterOptions}>
              {taskTypeOptions.map(option => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.filterChip,
                    {
                      backgroundColor: filter.type?.includes(option.value)
                        ? '#8B5CF6'
                        : inputBackgroundColor,
                      borderColor,
                    }
                  ]}
                  onPress={() => {
                    const currentTypes = filter.type || [];
                    const newTypes = currentTypes.includes(option.value)
                      ? currentTypes.filter(t => t !== option.value)
                      : [...currentTypes, option.value];
                    updateFilter({ type: newTypes.length > 0 ? newTypes : undefined });
                  }}
                >
                  <Text style={[
                    styles.filterChipText,
                    { color: filter.type?.includes(option.value) ? '#FFFFFF' : textColor }
                  ]}>
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>
        </View>

        <TouchableOpacity
          style={[styles.clearFilterButton, { borderColor }]}
          onPress={clearFilter}
        >
          <Ionicons name="close-outline" size={16} color={textColor} />
          <Text style={[styles.clearFilterText, { color: textColor }]}>Clear Filters</Text>
        </TouchableOpacity>
      </View>
    );
  };

  if (loading && tasks.length === 0) {
    return (
      <ThemedView style={styles.loadingContainer}>
        <Text>Loading tasks...</Text>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      {/* Stats Section */}
      {renderStats()}

      {/* Search and Filter Bar */}
      {(showSearch || showFilters) && (
        <View style={[styles.headerContainer, { backgroundColor, borderColor }]}>
          {showSearch && (
            <View style={styles.searchContainer}>
              <Ionicons name="search-outline" size={20} color="#6B7280" style={styles.searchIcon} />
              <TextInput
                style={[styles.searchInput, { backgroundColor: inputBackgroundColor, color: textColor }]}
                placeholder="Search tasks..."
                placeholderTextColor="#6B7280"
                value={searchQuery}
                onChangeText={setSearchQuery}
              />
            </View>
          )}

          {showFilters && (
            <TouchableOpacity
              style={[styles.filterButton, { borderColor }]}
              onPress={() => setShowFilterPanel(!showFilterPanel)}
            >
              <Ionicons name="filter-outline" size={20} color={textColor} />
              <Text style={[styles.filterButtonText, { color: textColor }]}>Filters</Text>
              {(filter.status || filter.type || filter.priority) && (
                <View style={styles.filterIndicator} />
              )}
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Filter Panel */}
      {renderFilterPanel()}

      {/* Task List */}
      <FlatList
        data={filteredTasks}
        renderItem={renderTask}
        keyExtractor={item => item.id}
        style={styles.taskList}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="list-outline" size={48} color="#9CA3AF" />
            <Text style={styles.emptyTitle}>
              {searchQuery ? 'No tasks found' : 'No tasks yet'}
            </Text>
            <Text style={styles.emptySubtitle}>
              {searchQuery
                ? 'Try adjusting your search or filters'
                : 'Tasks will appear here when created'}
            </Text>
          </View>
        }
      />
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statsContainer: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  statsTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  progressLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  progressValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: 16,
    marginBottom: 8,
    gap: 12,
  },
  searchContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    paddingVertical: 0,
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
  },
  filterButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  filterIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3B82F6',
  },
  filterPanel: {
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  filterSection: {
    marginBottom: 16,
  },
  filterTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  filterOptions: {
    flexDirection: 'row',
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
  },
  filterChipText: {
    fontSize: 12,
    fontWeight: '500',
  },
  clearFilterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 8,
    borderRadius: 6,
    borderWidth: 1,
  },
  clearFilterText: {
    fontSize: 12,
    fontWeight: '500',
  },
  taskList: {
    flex: 1,
    paddingHorizontal: 8,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#6B7280',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#9CA3AF',
    marginTop: 8,
    textAlign: 'center',
  },
});