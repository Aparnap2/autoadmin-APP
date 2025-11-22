/**
 * Task Filter Component
 * Filtering and sorting controls for tasks
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { useThemeColor } from '@/hooks/use-theme-color';
import { TaskFilter as ITaskFilter, TaskType } from '@/services/agents/types';

interface TaskFilterProps {
  filter: ITaskFilter;
  onFilterChange: (filter: ITaskFilter) => void;
  availableTaskTypes?: TaskType[];
}

const taskTypeOptions: { value: TaskType; label: string; color: string }[] = [
  { value: 'market_research', label: 'Market Research', color: '#8B5CF6' },
  { value: 'financial_analysis', label: 'Financial Analysis', color: '#10B981' },
  { value: 'code_analysis', label: 'Code Analysis', color: '#3B82F6' },
  { value: 'ui_ux_review', label: 'UI/UX Review', color: '#F59E0B' },
  { value: 'strategic_planning', label: 'Strategic Planning', color: '#EF4444' },
  { value: 'technical_decision', label: 'Technical Decision', color: '#6366F1' },
  { value: 'github_actions_delegation', label: 'GitHub Actions', color: '#84CC16' },
  { value: 'virtual_file_operation', label: 'File Operations', color: '#EC4899' },
];

const statusOptions = [
  { value: 'pending', label: 'Pending', color: '#F59E0B' },
  { value: 'processing', label: 'Processing', color: '#3B82F6' },
  { value: 'completed', label: 'Completed', color: '#10B981' },
  { value: 'failed', label: 'Failed', color: '#EF4444' },
  { value: 'delegated', label: 'Delegated', color: '#8B5CF6' },
];

const priorityOptions = [
  { value: 'low', label: 'Low', color: '#6B7280' },
  { value: 'medium', label: 'Medium', color: '#F59E0B' },
  { value: 'high', label: 'High', color: '#EF4444' },
];

export default function TaskFilter({ filter, onFilterChange, availableTaskTypes }: TaskFilterProps) {
  const [expandedSection, setExpandedSection] = useState<'status' | 'type' | 'priority' | null>(null);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const borderColor = useThemeColor({ light: '#E5E7EB', dark: '#374151' }, 'border');

  const toggleFilterSection = (section: 'status' | 'type' | 'priority') => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const updateFilter = (updates: Partial<ITaskFilter>) => {
    onFilterChange({ ...filter, ...updates });
  };

  const toggleArrayFilter = (
    field: 'status' | 'type' | 'priority',
    value: string
  ) => {
    const currentArray = filter[field] || [];
    const newArray = currentArray.includes(value)
      ? currentArray.filter(item => item !== value)
      : [...currentArray, value];

    updateFilter({
      [field]: newArray.length > 0 ? newArray : undefined
    });
  };

  const clearFilter = () => {
    onFilterChange({});
  };

  const hasActiveFilters = !!(filter.status || filter.type || filter.priority || filter.dateRange);

  return (
    <View style={[styles.container, { backgroundColor, borderColor }]}>
      <View style={styles.header}>
        <ThemedText style={styles.title}>Filters</ThemedText>
        {hasActiveFilters && (
          <TouchableOpacity onPress={clearFilter} style={styles.clearButton}>
            <Ionicons name="close-circle-outline" size={16} color={textColor} />
            <ThemedText style={[styles.clearText, { color: textColor }]}>Clear All</ThemedText>
          </TouchableOpacity>
        )}
      </View>

      {/* Status Filter */}
      <View style={styles.filterSection}>
        <TouchableOpacity
          style={styles.sectionHeader}
          onPress={() => toggleFilterSection('status')}
        >
          <ThemedText style={styles.sectionTitle}>Status</ThemedText>
          <Ionicons
            name={expandedSection === 'status' ? 'chevron-up-outline' : 'chevron-down-outline'}
            size={20}
            color={textColor}
          />
        </TouchableOpacity>

        {filter.status && filter.status.length > 0 && (
          <View style={styles.activeFilters}>
            {filter.status.map(status => {
              const option = statusOptions.find(o => o.value === status);
              return option ? (
                <View
                  key={status}
                  style={[
                    styles.activeFilterChip,
                    { backgroundColor: `${option.color}20`, borderColor: option.color }
                  ]}
                >
                  <ThemedText style={[styles.activeFilterText, { color: option.color }]}>
                    {option.label}
                  </ThemedText>
                  <TouchableOpacity
                    onPress={() => toggleArrayFilter('status', status)}
                    style={styles.removeFilter}
                  >
                    <Ionicons name="close" size={12} color={option.color} />
                  </TouchableOpacity>
                </View>
              ) : null;
            })}
          </View>
        )}

        {expandedSection === 'status' && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.optionsContainer}>
              {statusOptions.map(option => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.optionChip,
                    {
                      backgroundColor: filter.status?.includes(option.value)
                        ? `${option.color}20`
                        : 'transparent',
                      borderColor: option.color,
                    }
                  ]}
                  onPress={() => toggleArrayFilter('status', option.value)}
                >
                  <ThemedText style={[
                    styles.optionText,
                    { color: filter.status?.includes(option.value) ? option.color : textColor }
                  ]}>
                    {option.label}
                  </ThemedText>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>
        )}
      </View>

      {/* Type Filter */}
      <View style={styles.filterSection}>
        <TouchableOpacity
          style={styles.sectionHeader}
          onPress={() => toggleFilterSection('type')}
        >
          <ThemedText style={styles.sectionTitle}>Type</ThemedText>
          <Ionicons
            name={expandedSection === 'type' ? 'chevron-up-outline' : 'chevron-down-outline'}
            size={20}
            color={textColor}
          />
        </TouchableOpacity>

        {filter.type && filter.type.length > 0 && (
          <View style={styles.activeFilters}>
            {filter.type.map(type => {
              const option = taskTypeOptions.find(o => o.value === type);
              return option ? (
                <View
                  key={type}
                  style={[
                    styles.activeFilterChip,
                    { backgroundColor: `${option.color}20`, borderColor: option.color }
                  ]}
                >
                  <ThemedText style={[styles.activeFilterText, { color: option.color }]}>
                    {option.label}
                  </ThemedText>
                  <TouchableOpacity
                    onPress={() => toggleArrayFilter('type', type)}
                    style={styles.removeFilter}
                  >
                    <Ionicons name="close" size={12} color={option.color} />
                  </TouchableOpacity>
                </View>
              ) : null;
            })}
          </View>
        )}

        {expandedSection === 'type' && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.optionsContainer}>
              {taskTypeOptions
                .filter(option => !availableTaskTypes || availableTaskTypes.includes(option.value))
                .map(option => (
                  <TouchableOpacity
                    key={option.value}
                    style={[
                      styles.optionChip,
                      {
                        backgroundColor: filter.type?.includes(option.value)
                          ? `${option.color}20`
                          : 'transparent',
                        borderColor: option.color,
                      }
                    ]}
                    onPress={() => toggleArrayFilter('type', option.value)}
                  >
                    <ThemedText style={[
                      styles.optionText,
                      { color: filter.type?.includes(option.value) ? option.color : textColor }
                    ]}>
                      {option.label}
                    </ThemedText>
                  </TouchableOpacity>
                ))}
            </View>
          </ScrollView>
        )}
      </View>

      {/* Priority Filter */}
      <View style={styles.filterSection}>
        <TouchableOpacity
          style={styles.sectionHeader}
          onPress={() => toggleFilterSection('priority')}
        >
          <ThemedText style={styles.sectionTitle}>Priority</ThemedText>
          <Ionicons
            name={expandedSection === 'priority' ? 'chevron-up-outline' : 'chevron-down-outline'}
            size={20}
            color={textColor}
          />
        </TouchableOpacity>

        {filter.priority && filter.priority.length > 0 && (
          <View style={styles.activeFilters}>
            {filter.priority.map(priority => {
              const option = priorityOptions.find(o => o.value === priority);
              return option ? (
                <View
                  key={priority}
                  style={[
                    styles.activeFilterChip,
                    { backgroundColor: `${option.color}20`, borderColor: option.color }
                  ]}
                >
                  <ThemedText style={[styles.activeFilterText, { color: option.color }]}>
                    {option.label}
                  </ThemedText>
                  <TouchableOpacity
                    onPress={() => toggleArrayFilter('priority', priority)}
                    style={styles.removeFilter}
                  >
                    <Ionicons name="close" size={12} color={option.color} />
                  </TouchableOpacity>
                </View>
              ) : null;
            })}
          </View>
        )}

        {expandedSection === 'priority' && (
          <View style={styles.optionsContainer}>
            {priorityOptions.map(option => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.optionChip,
                  {
                    backgroundColor: filter.priority?.includes(option.value)
                      ? `${option.color}20`
                      : 'transparent',
                    borderColor: option.color,
                  }
                ]}
                onPress={() => toggleArrayFilter('priority', option.value)}
              >
                <ThemedText style={[
                  styles.optionText,
                  { color: filter.priority?.includes(option.value) ? option.color : textColor }
                ]}>
                  {option.label}
                </ThemedText>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    margin: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
  },
  clearButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  clearText: {
    fontSize: 12,
    fontWeight: '500',
  },
  filterSection: {
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
  },
  activeFilters: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8,
  },
  activeFilterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
  },
  activeFilterText: {
    fontSize: 12,
    fontWeight: '500',
  },
  removeFilter: {
    padding: 2,
  },
  optionsContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  optionChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
  },
  optionText: {
    fontSize: 12,
    fontWeight: '500',
  },
});