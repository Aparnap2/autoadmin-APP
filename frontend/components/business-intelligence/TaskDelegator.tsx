/**
 * Task Delegator Component
 * Intelligent task delegation system with business impact assessment
 * and context-aware agent recommendation
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { TaskDelegationResult } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface TaskDelegatorProps {
  onTaskCreated?: (task: any) => void;
}

interface TaskFormData {
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  required_capabilities: string[];
}

export function TaskDelegator({ onTaskCreated }: TaskDelegatorProps) {
  const [formData, setFormData] = useState<TaskFormData>({
    title: '',
    description: '',
    priority: 'medium',
    required_capabilities: [],
  });
  const [capabilityInput, setCapabilityInput] = useState('');
  const [evaluationResult, setEvaluationResult] = useState<TaskDelegationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [delegating, setDelegating] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(true);

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    loadDelegationHistory();
  }, []);

  const loadDelegationHistory = async () => {
    try {
      const response = await biService.getDelegationHistory({ limit: 10 });
      if (response.success && response.data) {
        setHistory(response.data.items || []);
      }
    } catch (err) {
      console.error('Failed to load delegation history:', err);
    }
  };

  const updateFormData = (field: keyof TaskFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addCapability = () => {
    if (capabilityInput.trim() && !formData.required_capabilities.includes(capabilityInput.trim())) {
      updateFormData('required_capabilities', [
        ...formData.required_capabilities,
        capabilityInput.trim()
      ]);
      setCapabilityInput('');
    }
  };

  const removeCapability = (capability: string) => {
    updateFormData('required_capabilities',
      formData.required_capabilities.filter(c => c !== capability)
    );
  };

  const evaluateTask = async () => {
    if (!formData.title.trim() || !formData.description.trim()) {
      Alert.alert('Validation Error', 'Please provide both title and description');
      return;
    }

    try {
      setEvaluating(true);
      setEvaluationResult(null);

      const response = await biService.evaluateTaskForDelegation(formData);

      if (response.success && response.data) {
        setEvaluationResult(response.data);
        setShowForm(false);
      } else {
        throw new Error(response.error || 'Failed to evaluate task');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      Alert.alert('Error', errorMessage);
    } finally {
      setEvaluating(false);
    }
  };

  const delegateTask = async (targetAgent?: string) => {
    if (!evaluationResult) return;

    try {
      setDelegating(true);

      const response = await biService.delegateTask(
        evaluationResult.original_task.id,
        targetAgent || evaluationResult.delegation_decision.target_agent
      );

      if (response.success) {
        Alert.alert(
          'Success',
          `Task delegated to ${targetAgent || evaluationResult.delegation_decision.target_agent}`
        );
        resetForm();
        loadDelegationHistory();
        onTaskCreated?.(response.data);
      } else {
        throw new Error(response.error || 'Failed to delegate task');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      Alert.alert('Error', errorMessage);
    } finally {
      setDelegating(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      priority: 'medium',
      required_capabilities: [],
    });
    setCapabilityInput('');
    setEvaluationResult(null);
    setShowForm(true);
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'critical': return '#F44336';
      case 'high': return '#FF9800';
      case 'medium': return '#2196F3';
      case 'low': return '#4CAF50';
      default: return '#C5C6C7';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#F44336';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#C5C6C7';
    }
  };

  if (loading && history.length === 0) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading task delegator...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <ThemedText type="title" style={styles.title}>Intelligent Task Delegator</ThemedText>
        <ThemedText style={styles.subtitle}>
          AI-powered task evaluation and delegation to the most suitable agent
        </ThemedText>

        {/* Task Form */}
        {showForm ? (
          <View style={styles.formSection}>
            <View style={styles.formGroup}>
              <ThemedText style={styles.label}>Task Title *</ThemedText>
              <TextInput
                style={styles.input}
                value={formData.title}
                onChangeText={(value) => updateFormData('title', value)}
                placeholder="Enter task title"
                placeholderTextColor="#666"
                multiline
              />
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.label}>Description *</ThemedText>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={formData.description}
                onChangeText={(value) => updateFormData('description', value)}
                placeholder="Describe the task requirements and expected outcomes"
                placeholderTextColor="#666"
                multiline
                numberOfLines={4}
              />
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.label}>Priority</ThemedText>
              <View style={styles.priorityButtons}>
                {(['low', 'medium', 'high'] as const).map(priority => (
                  <TouchableOpacity
                    key={priority}
                    style={[
                      styles.priorityButton,
                      formData.priority === priority && styles.activePriorityButton,
                      { borderColor: getPriorityColor(priority) }
                    ]}
                    onPress={() => updateFormData('priority', priority)}
                  >
                    <ThemedText style={[
                      styles.priorityButtonText,
                      formData.priority === priority && {
                        color: getPriorityColor(priority)
                      }
                    ]}>
                      {priority.toUpperCase()}
                    </ThemedText>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.label}>Required Capabilities</ThemedText>
              <View style={styles.capabilityInput}>
                <TextInput
                  style={styles.capabilityTextInput}
                  value={capabilityInput}
                  onChangeText={setCapabilityInput}
                  placeholder="Add a required capability"
                  placeholderTextColor="#666"
                  onSubmitEditing={addCapability}
                />
                <TouchableOpacity
                  style={styles.addCapabilityButton}
                  onPress={addCapability}
                >
                  <ThemedText style={styles.addCapabilityText}>Add</ThemedText>
                </TouchableOpacity>
              </View>
              <View style={styles.capabilitiesList}>
                {formData.required_capabilities.map((capability, index) => (
                  <View key={index} style={styles.capabilityTag}>
                    <ThemedText style={styles.capabilityText}>{capability}</ThemedText>
                    <TouchableOpacity
                      style={styles.removeCapabilityButton}
                      onPress={() => removeCapability(capability)}
                    >
                      <ThemedText style={styles.removeCapabilityText}>×</ThemedText>
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            </View>

            <TouchableOpacity
              style={[styles.evaluateButton, evaluating && styles.disabledButton]}
              onPress={evaluateTask}
              disabled={evaluating}
            >
              <ThemedText style={styles.evaluateButtonText}>
                {evaluating ? 'Evaluating...' : 'Evaluate Task for Delegation'}
              </ThemedText>
            </TouchableOpacity>
          </View>
        ) : evaluationResult ? (
          <View style={styles.evaluationResult}>
            <View style={styles.resultHeader}>
              <ThemedText style={styles.resultTitle}>Task Evaluation Results</ThemedText>
              <TouchableOpacity style={styles.resetButton} onPress={resetForm}>
                <ThemedText style={styles.resetButtonText}>New Task</ThemedText>
              </TouchableOpacity>
            </View>

            {/* Business Impact Assessment */}
            <View style={styles.resultSection}>
              <ThemedText style={styles.sectionTitle}>Business Impact Assessment</ThemedText>
              <View style={styles.impactMetrics}>
                <View style={styles.impactCard}>
                  <ThemedText style={styles.impactLabel}>Impact Level</ThemedText>
                  <ThemedText style={[
                    styles.impactValue,
                    { color: getImpactColor(evaluationResult.evaluation.business_impact) }
                  ]}>
                    {evaluationResult.evaluation.business_impact.toUpperCase()}
                  </ThemedText>
                </View>
                <View style={styles.impactCard}>
                  <ThemedText style={styles.impactLabel}>Urgency Score</ThemedText>
                  <ThemedText style={styles.impactValue}>
                    {evaluationResult.evaluation.urgency_score}/10
                  </ThemedText>
                </View>
                <View style={styles.impactCard}>
                  <ThemedText style={styles.impactLabel}>Complexity</ThemedText>
                  <ThemedText style={styles.impactValue}>
                    {evaluationResult.evaluation.complexity_score}/10
                  </ThemedText>
                </View>
                <View style={styles.impactCard}>
                  <ThemedText style={styles.impactLabel}>Business Value</ThemedText>
                  <ThemedText style={styles.impactValue}>
                    {evaluationResult.evaluation.business_value}/10
                  </ThemedText>
                </View>
              </View>
            </View>

            {/* Delegation Recommendation */}
            <View style={styles.resultSection}>
              <ThemedText style={styles.sectionTitle}>Delegation Recommendation</ThemedText>
              <View style={[
                styles.delegationCard,
                { borderColor: evaluationResult.delegation_decision.should_delegate ? '#4CAF50' : '#F44336' }
              ]}>
                <View style={styles.delegationHeader}>
                  <ThemedText style={styles.delegationDecision}>
                    {evaluationResult.delegation_decision.should_delegate ? 'DELEGATE' : 'HANDLE MANUALLY'}
                  </ThemedText>
                  <ThemedText style={styles.confidenceScore}>
                    {Math.round(evaluationResult.delegation_decision.confidence * 100)}% confidence
                  </ThemedText>
                </View>

                {evaluationResult.delegation_decision.should_delegate ? (
                  <>
                    <View style={styles.recommendedAgent}>
                      <ThemedText style={styles.agentLabel}>Recommended Agent:</ThemedText>
                      <ThemedText style={styles.agentName}>
                        {evaluationResult.delegation_decision.target_agent}
                      </ThemedText>
                    </View>
                    <ThemedText style={styles.reasoning}>
                      {evaluationResult.delegation_decision.reasoning}
                    </ThemedText>

                    <TouchableOpacity
                      style={[styles.delegateButton, delegating && styles.disabledButton]}
                      onPress={() => delegateTask()}
                      disabled={delegating}
                    >
                      <ThemedText style={styles.delegateButtonText}>
                        {delegating ? 'Delegating...' : `Delegate to ${evaluationResult.delegation_decision.target_agent}`}
                      </ThemedText>
                    </TouchableOpacity>
                  </>
                ) : (
                  <>
                    <ThemedText style={styles.reasoning}>
                      {evaluationResult.delegation_decision.reasoning}
                    </ThemedText>
                    <ThemedText style={styles.manualHandlingNote}>
                      This task requires manual review and assignment due to its complexity or specialized requirements.
                    </ThemedText>
                  </>
                )}
              </View>
            </View>

            {/* Context Analysis */}
            <View style={styles.resultSection}>
              <ThemedText style={styles.sectionTitle}>Context Analysis</ThemedText>
              <View style={styles.contextGrid}>
                <View style={styles.contextCard}>
                  <ThemedText style={styles.contextTitle}>Business Goals</ThemedText>
                  {evaluationResult.context_analysis.relevant_business_goals.map((goal, index) => (
                    <ThemedText key={index} style={styles.contextItem}>• {goal}</ThemedText>
                  ))}
                </View>
                <View style={styles.contextCard}>
                  <ThemedText style={styles.contextTitle}>Dependencies</ThemedText>
                  {evaluationResult.context_analysis.dependencies.map((dep, index) => (
                    <ThemedText key={index} style={styles.contextItem}>• {dep}</ThemedText>
                  ))}
                </View>
                <View style={styles.contextCard}>
                  <ThemedText style={styles.contextTitle}>Risk Factors</ThemedText>
                  {evaluationResult.context_analysis.risk_factors.map((risk, index) => (
                    <ThemedText key={index} style={[styles.contextItem, { color: '#FF9800' }]}>
                      ⚠ {risk}
                    </ThemedText>
                  ))}
                </View>
              </View>
            </View>
          </View>
        ) : null}

        {/* Recent Delegations */}
        {history.length > 0 && (
          <View style={styles.historySection}>
            <ThemedText style={styles.sectionTitle}>Recent Delegations</ThemedText>
            {history.slice(0, 5).map((item, index) => (
              <View key={index} style={styles.historyItem}>
                <View style={styles.historyInfo}>
                  <ThemedText style={styles.historyTask}>{item.original_task?.title || 'Unknown Task'}</ThemedText>
                  <ThemedText style={styles.historyDetails}>
                    {item.evaluation?.business_impact && (
                      <ThemedText style={[
                        styles.impactBadge,
                        { color: getImpactColor(item.evaluation.business_impact) }
                      ]}>
                        {item.evaluation.business_impact}
                      </ThemedText>
                    )}
                    {item.delegation_decision?.target_agent && (
                      <ThemedText style={styles.historyAgent}>
                        → {item.delegation_decision.target_agent}
                      </ThemedText>
                    )}
                  </ThemedText>
                </View>
                <ThemedText style={styles.historyTime}>
                  {new Date(item.created_at).toLocaleDateString()}
                </ThemedText>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0C10',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 15,
    color: '#C5C6C7',
    fontSize: 16,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  title: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 8,
  },
  subtitle: {
    color: '#C5C6C7',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 30,
    opacity: 0.8,
  },
  formSection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 30,
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 8,
    color: '#C5C6C7',
    fontSize: 16,
    padding: 15,
  },
  textArea: {
    minHeight: 100,
    textAlignVertical: 'top',
  },
  priorityButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  priorityButton: {
    flex: 1,
    paddingVertical: 12,
    borderWidth: 1,
    borderRadius: 8,
    alignItems: 'center',
  },
  activePriorityButton: {
    backgroundColor: '#45A29E',
  },
  priorityButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  capabilityInput: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 10,
  },
  capabilityTextInput: {
    flex: 1,
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 8,
    color: '#C5C6C7',
    fontSize: 16,
    padding: 15,
  },
  addCapabilityButton: {
    backgroundColor: '#45A29E',
    paddingHorizontal: 20,
    borderRadius: 8,
    justifyContent: 'center',
  },
  addCapabilityText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  capabilitiesList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  capabilityTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 6,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  capabilityText: {
    color: '#C5C6C7',
    fontSize: 14,
    marginRight: 8,
  },
  removeCapabilityButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#F44336',
    justifyContent: 'center',
    alignItems: 'center',
  },
  removeCapabilityText: {
    color: '#0B0C10',
    fontSize: 12,
    fontWeight: '600',
  },
  evaluateButton: {
    backgroundColor: '#66FCF1',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  disabledButton: {
    opacity: 0.5,
  },
  evaluateButtonText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
  evaluationResult: {
    flex: 1,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  resultTitle: {
    color: '#66FCF1',
    fontSize: 20,
    fontWeight: '600',
  },
  resetButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    backgroundColor: '#45A29E',
    borderRadius: 6,
  },
  resetButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  resultSection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
  },
  impactMetrics: {
    flexDirection: 'row',
    gap: 12,
  },
  impactCard: {
    flex: 1,
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  impactLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 5,
  },
  impactValue: {
    fontSize: 20,
    fontWeight: '700',
  },
  delegationCard: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    borderWidth: 1,
    padding: 20,
  },
  delegationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  delegationDecision: {
    fontSize: 18,
    fontWeight: '700',
  },
  confidenceScore: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  recommendedAgent: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  agentLabel: {
    color: '#C5C6C7',
    fontSize: 14,
    marginRight: 8,
  },
  agentName: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
  },
  reasoning: {
    color: '#C5C6C7',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 15,
  },
  manualHandlingNote: {
    color: '#FF9800',
    fontSize: 14,
    lineHeight: 20,
    fontStyle: 'italic',
  },
  delegateButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  delegateButtonText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
  contextGrid: {
    gap: 15,
  },
  contextCard: {
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  contextTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  contextItem: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 4,
  },
  historySection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
  },
  historyItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  historyInfo: {
    flex: 1,
  },
  historyTask: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
  },
  historyDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  impactBadge: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  historyAgent: {
    color: '#66FCF1',
    fontSize: 12,
  },
  historyTime: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
});