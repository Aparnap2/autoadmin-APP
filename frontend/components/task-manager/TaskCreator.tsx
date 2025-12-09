/**
 * Task Creator Component
 * Interface for creating new tasks with agent assignment
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useThemeColor } from '@/hooks/use-theme-color';
import { TaskType } from '@/services/agents/types';
import { AgentAPIService } from '@/services/api/agent-api';
import { AgentTaskRequest } from '@/services/api/fastapi-client';

interface TaskCreatorProps {
  agentService: AgentAPIService;
  onTaskCreated?: (task: AgentTaskRequest) => void;
  onCancel?: () => void;
  initialData?: Partial<AgentTaskRequest>;
}

const taskTypeOptions: { value: TaskType; label: string; description: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  {
    value: 'market_research',
    label: 'Market Research',
    description: 'Analyze market trends, competitors, and opportunities',
    icon: 'trending-up-outline',
  },
  {
    value: 'financial_analysis',
    label: 'Financial Analysis',
    description: 'Budget analysis, revenue projections, cost optimization',
    icon: 'wallet-outline',
  },
  {
    value: 'code_analysis',
    label: 'Code Analysis',
    description: 'Review code quality, performance, and best practices',
    icon: 'code-outline',
  },
  {
    value: 'ui_ux_review',
    label: 'UI/UX Review',
    description: 'Evaluate user interface and user experience',
    icon: 'eye-outline',
  },
  {
    value: 'strategic_planning',
    label: 'Strategic Planning',
    description: 'Develop business strategies and action plans',
    icon: 'bulb-outline',
  },
  {
    value: 'technical_decision',
    label: 'Technical Decision',
    description: 'Make technical architecture and implementation decisions',
    icon: 'cog-outline',
  },
  {
    value: 'github_actions_delegation',
    label: 'GitHub Actions',
    description: 'Delegate tasks to GitHub Actions workflows',
    icon: 'git-branch-outline',
  },
  {
    value: 'virtual_file_operation',
    label: 'File Operations',
    description: 'Manage virtual file system operations',
    icon: 'folder-outline',
  },
];

const priorityLevels = [
  { value: 'low', label: 'Low', color: '#6B7280', description: 'Can be addressed later' },
  { value: 'medium', label: 'Medium', color: '#F59E0B', description: 'Standard priority' },
  { value: 'high', label: 'High', color: '#EF4444', description: 'Requires immediate attention' },
];

export default function TaskCreator({
  agentService,
  onTaskCreated,
  onCancel,
  initialData,
}: TaskCreatorProps) {
  const [taskData, setTaskData] = useState<Partial<AgentTaskRequest>>({
    type: '',
    description: '',
    priority: 'medium',
    ...initialData,
  });
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedSection, setExpandedSection] = useState<'type' | 'priority' | 'agent' | null>(null);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const borderColor = useThemeColor({ light: '#E5E7EB', dark: '#374151' }, 'border');
  const inputBackgroundColor = useThemeColor({ light: '#F9FAFB', dark: '#1F2937' }, 'background');

  // Load available agents
  useEffect(() => {
    const loadAgents = async () => {
      try {
        const availableAgents = await agentService.getAgents();
        setAgents(availableAgents);
      } catch (error) {
        console.error('Error loading agents:', error);
      }
    };

    loadAgents();
  }, [agentService]);

  const handleCreateTask = async () => {
    if (!taskData.type || !taskData.description?.trim()) {
      Alert.alert('Error', 'Please select a task type and provide a description');
      return;
    }

    setLoading(true);

    try {
      const taskRequest: Omit<AgentTaskRequest, 'id' | 'created_at' | 'updated_at'> = {
        type: taskData.type!,
        title: taskData.description?.substring(0, 50) || taskData.type!, // Use description as title, or type as fallback
        description: taskData.description!,
        priority: taskData.priority as any,
        assigned_to: taskData.assigned_to,
        metadata: taskData.metadata || {},
        input_data: taskData.input_data,
      };

      await agentService.createTask(taskRequest);
      Alert.alert('Success', 'Task created successfully');
      onTaskCreated?.(taskRequest as AgentTaskRequest);
    } catch (error) {
      console.error('Error creating task:', error);
      Alert.alert('Error', 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  const updateTaskData = (field: keyof AgentTaskRequest, value: any) => {
    setTaskData(prev => ({ ...prev, [field]: value }));
  };

  const selectedTaskType = taskTypeOptions.find(option => option.value === taskData.type);
  const selectedPriority = priorityLevels.find(option => option.value === taskData.priority);

  const renderTaskTypeSelector = () => (
    <View style={[styles.section, { backgroundColor, borderColor }]}>
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => setExpandedSection(expandedSection === 'type' ? null : 'type')}
      >
        <ThemedText style={styles.sectionTitle}>Task Type</ThemedText>
        <Ionicons
          name={expandedSection === 'type' ? 'chevron-up-outline' : 'chevron-down-outline'}
          size={20}
          color={textColor}
        />
      </TouchableOpacity>

      {selectedTaskType && (
        <View style={styles.selectedItem}>
          <Ionicons name={selectedTaskType.icon} size={20} color="#3B82F6" />
          <View style={styles.selectedItemContent}>
            <Text style={[styles.selectedItemLabel, { color: textColor }]}>
              {selectedTaskType.label}
            </Text>
            <Text style={styles.selectedItemDescription}>
              {selectedTaskType.description}
            </Text>
          </View>
        </View>
      )}

      {expandedSection === 'type' && (
        <ScrollView style={styles.optionsContainer} showsVerticalScrollIndicator={false}>
          {taskTypeOptions.map(option => (
            <TouchableOpacity
              key={option.value}
              style={[
                styles.optionItem,
                {
                  backgroundColor: taskData.type === option.value
                    ? '#EFF6FF'
                    : inputBackgroundColor,
                  borderColor,
                }
              ]}
              onPress={() => {
                updateTaskData('type', option.value);
                setExpandedSection(null);
              }}
            >
              <Ionicons
                name={option.icon}
                size={20}
                color={taskData.type === option.value ? '#3B82F6' : '#6B7280'}
              />
              <View style={styles.optionContent}>
                <Text style={[
                  styles.optionLabel,
                  { color: textColor }
                ]}>
                  {option.label}
                </Text>
                <Text style={styles.optionDescription}>
                  {option.description}
                </Text>
              </View>
              {taskData.type === option.value && (
                <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
              )}
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}
    </View>
  );

  const renderPrioritySelector = () => (
    <View style={[styles.section, { backgroundColor, borderColor }]}>
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => setExpandedSection(expandedSection === 'priority' ? null : 'priority')}
      >
        <ThemedText style={styles.sectionTitle}>Priority</ThemedText>
        <Ionicons
          name={expandedSection === 'priority' ? 'chevron-up-outline' : 'chevron-down-outline'}
          size={20}
          color={textColor}
        />
      </TouchableOpacity>

      {selectedPriority && (
        <View style={styles.selectedItem}>
          <View style={[styles.priorityIndicator, { backgroundColor: selectedPriority.color }]} />
          <View style={styles.selectedItemContent}>
            <Text style={[styles.selectedItemLabel, { color: textColor }]}>
              {selectedPriority.label} Priority
            </Text>
            <Text style={styles.selectedItemDescription}>
              {selectedPriority.description}
            </Text>
          </View>
        </View>
      )}

      {expandedSection === 'priority' && (
        <View style={styles.optionsContainer}>
          {priorityLevels.map(option => (
            <TouchableOpacity
              key={option.value}
              style={[
                styles.optionItem,
                {
                  backgroundColor: taskData.priority === option.value
                    ? '#FEF2F2'
                    : inputBackgroundColor,
                  borderColor,
                }
              ]}
              onPress={() => {
                updateTaskData('priority', option.value as any);
                setExpandedSection(null);
              }}
            >
              <View style={[styles.priorityIndicator, { backgroundColor: option.color }]} />
              <View style={styles.optionContent}>
                <Text style={[
                  styles.optionLabel,
                  { color: textColor }
                ]}>
                  {option.label}
                </Text>
                <Text style={styles.optionDescription}>
                  {option.description}
                </Text>
              </View>
              {taskData.priority === option.value && (
                <Ionicons name="checkmark-circle" size={20} color={option.color} />
              )}
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );

  const renderAgentSelector = () => (
    <View style={[styles.section, { backgroundColor, borderColor }]}>
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => setExpandedSection(expandedSection === 'agent' ? null : 'agent')}
      >
        <ThemedText style={styles.sectionTitle}>Agent Assignment</ThemedText>
        <Ionicons
          name={expandedSection === 'agent' ? 'chevron-up-outline' : 'chevron-down-outline'}
          size={20}
          color={textColor}
        />
      </TouchableOpacity>

      {taskData.assigned_to && (
        <View style={styles.selectedItem}>
          <Ionicons name="person-outline" size={20} color="#10B981" />
          <Text style={[styles.selectedItemLabel, { color: textColor }]}>
            {taskData.assigned_to}
          </Text>
        </View>
      )}

      {expandedSection === 'agent' && (
        <View style={styles.optionsContainer}>
          <TouchableOpacity
            style={[
              styles.optionItem,
              {
                backgroundColor: !taskData.assigned_to
                  ? '#EFF6FF'
                  : inputBackgroundColor,
                borderColor,
              }
            ]}
            onPress={() => {
              updateTaskData('assigned_to', undefined);
              setExpandedSection(null);
            }}
          >
            <Ionicons name="flash-outline" size={20} color="#3B82F6" />
            <View style={styles.optionContent}>
              <Text style={[
                styles.optionLabel,
                { color: textColor }
              ]}>
                Auto-assign
              </Text>
              <Text style={styles.optionDescription}>
                Let the system choose the best agent
              </Text>
            </View>
            {!taskData.assigned_to && (
              <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
            )}
          </TouchableOpacity>

          {agents.map(agent => (
            <TouchableOpacity
              key={agent.id}
              style={[
                styles.optionItem,
                {
                  backgroundColor: taskData.assigned_to === agent.id
                    ? '#EFF6FF'
                    : inputBackgroundColor,
                  borderColor,
                }
              ]}
              onPress={() => {
                updateTaskData('assigned_to', agent.id);
                setExpandedSection(null);
              }}
            >
              <Ionicons name="person-outline" size={20} color="#6B7280" />
              <View style={styles.optionContent}>
                <Text style={[
                  styles.optionLabel,
                  { color: textColor }
                ]}>
                  {agent.name}
                </Text>
                <Text style={styles.optionDescription}>
                  {agent.status} • {agent.capabilities?.slice(0, 2).join(', ')}
                </Text>
              </View>
              {taskData.assigned_to === agent.id && (
                <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
              )}
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ThemedView style={styles.content}>
        <View style={styles.header}>
          <ThemedText style={styles.title}>Create New Task</ThemedText>
          {onCancel && (
            <TouchableOpacity onPress={onCancel} style={styles.cancelButton}>
              <Ionicons name="close-outline" size={24} color={textColor} />
            </TouchableOpacity>
          )}
        </View>

        <ScrollView style={styles.form} showsVerticalScrollIndicator={false}>
          {/* Task Type Selection */}
          {renderTaskTypeSelector()}

          {/* Task Description */}
          <View style={[styles.section, { backgroundColor, borderColor }]}>
            <ThemedText style={styles.sectionTitle}>Description</ThemedText>
            <TextInput
              style={[
                styles.descriptionInput,
                { backgroundColor: inputBackgroundColor, color: textColor, borderColor }
              ]}
              placeholder="Describe what you need done..."
              placeholderTextColor="#6B7280"
              multiline
              numberOfLines={4}
              textAlignVertical="top"
              value={taskData.description}
              onChangeText={(text) => updateTaskData('description', text)}
            />
          </View>

          {/* Priority Selection */}
          {renderPrioritySelector()}

          {/* Agent Assignment */}
          {renderAgentSelector()}

          {/* Additional Input Data */}
          <View style={[styles.section, { backgroundColor, borderColor }]}>
            <ThemedText style={styles.sectionTitle}>Additional Information</ThemedText>
            <TextInput
              style={[
                styles.input,
                { backgroundColor: inputBackgroundColor, color: textColor, borderColor }
              ]}
              placeholder="Any additional context or requirements (optional)"
              placeholderTextColor="#6B7280"
              value={taskData.metadata?.context || ''}
              onChangeText={(text) => updateTaskData('metadata', { ...taskData.metadata, context: text })}
            />
          </View>
        </ScrollView>

        {/* Action Buttons */}
        <View style={styles.actions}>
          {onCancel && (
            <TouchableOpacity
              style={[styles.actionButton, styles.cancelButton, { borderColor }]}
              onPress={onCancel}
              disabled={loading}
            >
              <Text style={[styles.actionButtonText, { color: textColor }]}>Cancel</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={[
              styles.actionButton,
              styles.createButton,
              { opacity: loading || !taskData.type || !taskData.description?.trim() ? 0.5 : 1 }
            ]}
            onPress={handleCreateTask}
            disabled={loading || !taskData.type || !taskData.description?.trim()}
          >
            {loading ? (
              <Text style={styles.actionButtonText}>Creating...</Text>
            ) : (
              <>
                <Ionicons name="add-circle-outline" size={20} color="#FFFFFF" />
                <Text style={styles.actionButtonText}>Create Task</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </ThemedView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
  },
  cancelButton: {
    padding: 4,
  },
  form: {
    flex: 1,
    paddingHorizontal: 20,
  },
  section: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  selectedItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  selectedItemContent: {
    flex: 1,
  },
  selectedItemLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  selectedItemDescription: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  priorityIndicator: {
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  optionsContainer: {
    maxHeight: 200,
  },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 8,
  },
  optionContent: {
    flex: 1,
  },
  optionLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  optionDescription: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  descriptionInput: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    height: 100,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    padding: 20,
    paddingTop: 10,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 8,
  },
  createButton: {
    backgroundColor: '#3B82F6',
  },
  cancelButton: {
    borderWidth: 1,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});