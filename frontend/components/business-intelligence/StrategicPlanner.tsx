/**
 * Strategic Planner Component
 * Comprehensive strategic planning dashboard with OKRs, initiatives, and scenario analysis
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
  Modal,
} from 'react-native';
import { LineChart, BarChart, ProgressChart } from 'react-native-chart-kit';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { StrategicPlanData } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface StrategicPlannerProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function StrategicPlanner({
  autoRefresh = false,
  refreshInterval = 300000, // 5 minutes
}: StrategicPlannerProps) {
  const [planData, setPlanData] = useState<StrategicPlanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'initiatives' | 'okrs' | 'scenarios' | 'recommendations'>('overview');
  const [selectedInitiative, setSelectedInitiative] = useState<any>(null);
  const [progressModalVisible, setProgressModalVisible] = useState(false);
  const [progressValue, setProgressValue] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    loadStrategicPlan();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadStrategicPlan, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  const loadStrategicPlan = async (params?: any) => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getStrategicPlan({
        include_okrs: true,
        include_scenarios: true,
        ...params
      });

      if (response.success && response.data) {
        setPlanData(response.data);
      } else {
        throw new Error(response.error || 'Failed to load strategic plan');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const generateRecommendations = async () => {
    try {
      setGenerating(true);

      const response = await biService.generateRecommendations();

      if (response.success) {
        Alert.alert('Success', 'Strategic recommendations generated');
        await loadStrategicPlan();
      } else {
        throw new Error(response.error || 'Failed to generate recommendations');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to generate recommendations');
    } finally {
      setGenerating(false);
    }
  };

  const analyzeScenarios = async () => {
    try {
      setAnalyzing(true);

      const response = await biService.analyzeScenarios();

      if (response.success) {
        Alert.alert('Success', 'Scenario analysis completed');
        await loadStrategicPlan();
      } else {
        throw new Error(response.error || 'Failed to analyze scenarios');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to analyze scenarios');
    } finally {
      setAnalyzing(false);
    }
  };

  const updateProgress = async () => {
    if (!selectedInitiative) return;

    try {
      await biService.updateProgress(selectedInitiative.id, progressValue);
      Alert.alert('Success', 'Progress updated successfully');
      setProgressModalVisible(false);
      await loadStrategicPlan();
    } catch (err) {
      Alert.alert('Error', 'Failed to update progress');
    }
  };

  const openProgressModal = (initiative: any) => {
    setSelectedInitiative(initiative);
    setProgressValue(initiative.current_progress);
    setProgressModalVisible(true);
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'growth': return '#4CAF50';
      case 'efficiency': return '#2196F3';
      case 'innovation': return '#9C27B0';
      case 'retention': return '#FF9800';
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

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return '#4CAF50';
    if (progress >= 50) return '#FF9800';
    return '#F44336';
  };

  const renderOverviewTab = () => {
    if (!planData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Current Status */}
        <View style={styles.statusSection}>
          <ThemedText style={styles.sectionTitle}>Strategic Overview</ThemedText>
          <View style={styles.statusGrid}>
            <View style={styles.statusCard}>
              <ThemedText style={styles.statusLabel}>Overall Progress</ThemedText>
              <ThemedText style={[
                styles.statusValue,
                { color: getProgressColor(planData.current_status.overall_progress) }
              ]}>
                {planData.current_status.overall_progress}%
              </ThemedText>
            </View>
            <View style={styles.statusCard}>
              <ThemedText style={styles.statusLabel}>Milestone Completion</ThemedText>
              <ThemedText style={[
                styles.statusValue,
                { color: getProgressColor(planData.current_status.milestone_completion) }
              ]}>
                {planData.current_status.milestone_completion}%
              </ThemedText>
            </View>
          </View>

          <View style={styles.achievementsSection}>
            <ThemedText style={styles.subsectionTitle}>Key Achievements</ThemedText>
            {planData.current_status.key_achievements.map((achievement, index) => (
              <View key={index} style={styles.achievementItem}>
                <ThemedText style={styles.achievementText}>✓ {achievement}</ThemedText>
              </View>
            ))}
          </View>

          <View style={styles.challengesSection}>
            <ThemedText style={styles.subsectionTitle}>Current Challenges</ThemedText>
            {planData.current_status.current_challenges.map((challenge, index) => (
              <View key={index} style={styles.challengeItem}>
                <ThemedText style={styles.challengeText}>⚠ {challenge}</ThemedText>
              </View>
            ))}
          </View>
        </View>
      </View>
    );
  };

  const renderInitiativesTab = () => {
    if (!planData) return null;

    return (
      <View style={styles.tabContent}>
        <ThemedText style={styles.sectionTitle}>Strategic Initiatives</ThemedText>
        {planData.strategic_initiatives.map((initiative, index) => (
          <View key={index} style={styles.initiativeCard}>
            <View style={styles.initiativeHeader}>
              <View style={styles.initiativeInfo}>
                <ThemedText style={styles.initiativeTitle}>{initiative.title}</ThemedText>
                <View style={styles.initiativeMeta}>
                  <View style={[
                    styles.categoryBadge,
                    { backgroundColor: getCategoryColor(initiative.category) }
                  ]}>
                    <ThemedText style={styles.categoryText}>
                      {initiative.category.toUpperCase()}
                    </ThemedText>
                  </View>
                  <View style={[
                    styles.priorityBadge,
                    { backgroundColor: getPriorityColor(initiative.priority) }
                  ]}>
                    <ThemedText style={styles.priorityText}>
                      {initiative.priority.toUpperCase()}
                    </ThemedText>
                  </View>
                </View>
              </View>
              <View style={styles.initiativeProgress}>
                <ThemedText style={[
                  styles.progressPercentage,
                  { color: getProgressColor(initiative.current_progress) }
                ]}>
                  {initiative.current_progress}%
                </ThemedText>
                <TouchableOpacity
                  style={styles.updateProgressButton}
                  onPress={() => openProgressModal(initiative)}
                >
                  <ThemedText style={styles.updateProgressText}>Update</ThemedText>
                </TouchableOpacity>
              </View>
            </View>

            <ThemedText style={styles.initiativeDescription}>{initiative.description}</ThemedText>

            {/* Progress Bar */}
            <View style={styles.progressBar}>
              <View style={[
                styles.progressFill,
                {
                  width: `${initiative.current_progress}%`,
                  backgroundColor: getProgressColor(initiative.current_progress)
                }
              ]} />
            </View>

            {/* KPIs */}
            <View style={styles.kpisSection}>
              <ThemedText style={styles.kpisTitle}>Key Performance Indicators</ThemedText>
              {initiative.kpis.map((kpi, kpiIndex) => (
                <View key={kpiIndex} style={styles.kpiItem}>
                  <ThemedText style={styles.kpiName}>{kpi.metric}</ThemedText>
                  <View style={styles.kpiProgress}>
                    <ThemedText style={[
                      styles.kpiCurrent,
                      { color: getProgressColor((kpi.current / kpi.target) * 100) }
                    ]}>
                      {kpi.current}
                    </ThemedText>
                    <ThemedText style={styles.kpiTarget}>/ {kpi.target}</ThemedText>
                    <ThemedText style={[
                      styles.kpiTrend,
                      { color: kpi.trend === 'improving' ? '#4CAF50' : kpi.trend === 'declining' ? '#F44336' : '#FF9800' }
                    ]}>
                      {kpi.trend === 'improving' ? '↑' : kpi.trend === 'declining' ? '↓' : '→'}
                    </ThemedText>
                  </View>
                </View>
              ))}
            </View>

            {/* Next Milestones */}
            {initiative.next_milestones.length > 0 && (
              <View style={styles.milestonesSection}>
                <ThemedText style={styles.milestonesTitle}>Next Milestones</ThemedText>
                {initiative.next_milestones.map((milestone, milestoneIndex) => (
                  <View key={milestoneIndex} style={styles.milestoneItem}>
                    <ThemedText style={styles.milestoneText}>{milestone.milestone}</ThemedText>
                    <ThemedText style={styles.milestoneDue}>Due: {milestone.due_date}</ThemedText>
                  </View>
                ))}
              </View>
            )}
          </View>
        ))}
      </View>
    );
  };

  const renderOKRsTab = () => {
    if (!planData) return null;

    return (
      <View style={styles.tabContent}>
        <ThemedText style={styles.sectionTitle}>Objectives and Key Results</ThemedText>
        {planData.okrs.map((okr, index) => (
          <View key={index} style={styles.okrCard}>
            <View style={styles.okrHeader}>
              <ThemedText style={styles.okrObjective}>{okr.objective}</ThemedText>
              <View style={styles.okrProgress}>
                <ThemedText style={[
                  styles.okrProgressPercentage,
                  { color: getProgressColor(okr.progress_percentage) }
                ]}>
                  {okr.progress_percentage}%
                </ThemedText>
                <ThemedText style={styles.okrConfidence}>
                  {Math.round(okr.confidence_level * 100)}% confidence
                </ThemedText>
              </View>
            </View>

            {/* Progress Bar */}
            <View style={styles.progressBar}>
              <View style={[
                styles.progressFill,
                {
                  width: `${okr.progress_percentage}%`,
                  backgroundColor: getProgressColor(okr.progress_percentage)
                }
              ]} />
            </View>

            <View style={styles.keyResults}>
              {okr.key_results.map((kr, krIndex) => (
                <View key={krIndex} style={styles.keyResultItem}>
                  <View style={styles.krHeader}>
                    <ThemedText style={styles.krText}>{kr.key_result}</ThemedText>
                    <ThemedText style={[
                      styles.krProgress,
                      { color: getProgressColor(kr.progress_percentage) }
                    ]}>
                      {kr.current_value}/{kr.target_value} ({kr.progress_percentage}%)
                    </ThemedText>
                  </View>
                  <ThemedText style={styles.krDue}>Due: {kr.due_date}</ThemedText>
                </View>
              ))}
            </View>
          </View>
        ))}
      </View>
    );
  };

  const renderScenariosTab = () => {
    if (!planData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.scenariosHeader}>
          <ThemedText style={styles.sectionTitle}>Scenario Analysis</ThemedText>
          <TouchableOpacity
            style={[styles.actionButton, analyzing && styles.disabledButton]}
            onPress={analyzeScenarios}
            disabled={analyzing}
          >
            <ThemedText style={styles.actionButtonText}>
              {analyzing ? 'Analyzing...' : 'Run Analysis'}
            </ThemedText>
          </TouchableOpacity>
        </View>

        {planData.scenario_analysis.map((scenario, index) => (
          <View key={index} style={[
            styles.scenarioCard,
            { borderColor: scenario.scenario === 'best_case' ? '#4CAF50' :
                       scenario.scenario === 'worst_case' ? '#F44336' : '#FF9800' }
          ]}>
            <View style={styles.scenarioHeader}>
              <ThemedText style={styles.scenarioTitle}>
                {scenario.scenario.replace('_', ' ').toUpperCase()}
              </ThemedText>
              <ThemedText style={styles.scenarioProbability}>
                {Math.round(scenario.probability * 100)}% probability
              </ThemedText>
            </View>

            <View style={styles.scenarioOutcomes}>
              <View style={styles.outcomeItem}>
                <ThemedText style={styles.outcomeLabel}>Revenue</ThemedText>
                <ThemedText style={styles.outcomeValue}>
                  ${(scenario.projected_outcomes.revenue / 1000).toFixed(0)}K
                </ThemedText>
              </View>
              <View style={styles.outcomeItem}>
                <ThemedText style={styles.outcomeLabel}>Growth Rate</ThemedText>
                <ThemedText style={styles.outcomeValue}>
                  {scenario.projected_outcomes.growth_rate.toFixed(1)}%
                </ThemedText>
              </View>
              <View style={styles.outcomeItem}>
                <ThemedText style={styles.outcomeLabel}>Market Share</ThemedText>
                <ThemedText style={styles.outcomeValue}>
                  {(scenario.projected_outcomes.market_share * 100).toFixed(1)}%
                </ThemedText>
              </View>
            </View>

            <View style={styles.scenarioDetails}>
              <ThemedText style={styles.scenarioSubsection}>Key Assumptions</ThemedText>
              {scenario.key_assumptions.map((assumption, assumptionIndex) => (
                <ThemedText key={assumptionIndex} style={styles.assumptionText}>
                  • {assumption}
                </ThemedText>
              ))}

              <ThemedText style={styles.scenarioSubsection}>Risk Factors</ThemedText>
              {scenario.risk_factors.map((risk, riskIndex) => (
                <ThemedText key={riskIndex} style={styles.riskText}>
                  ⚠ {risk}
                </ThemedText>
              ))}

              <ThemedText style={styles.scenarioSubsection}>Recommended Actions</ThemedText>
              {scenario.recommended_actions.map((action, actionIndex) => (
                <ThemedText key={actionIndex} style={styles.actionItemText}>
                  → {action}
                </ThemedText>
              ))}
            </View>
          </View>
        ))}
      </View>
    );
  };

  const renderRecommendationsTab = () => {
    if (!planData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.recommendationsHeader}>
          <ThemedText style={styles.sectionTitle}>Strategic Recommendations</ThemedText>
          <TouchableOpacity
            style={[styles.actionButton, generating && styles.disabledButton]}
            onPress={generateRecommendations}
            disabled={generating}
          >
            <ThemedText style={styles.actionButtonText}>
              {generating ? 'Generating...' : 'Generate New'}
            </ThemedText>
          </TouchableOpacity>
        </View>

        {planData.recommendations.map((rec, index) => (
          <View key={index} style={styles.recommendationCard}>
            <View style={styles.recommendationHeader}>
              <ThemedText style={styles.recommendationTitle}>{rec.recommendation}</ThemedText>
              <View style={[
                styles.priorityBadge,
                { backgroundColor: getPriorityColor(rec.priority) }
              ]}>
                <ThemedText style={styles.priorityText}>
                  {rec.priority.toUpperCase()}
                </ThemedText>
              </View>
            </View>

            <ThemedText style={styles.recommendationRationale}>{rec.rationale}</ThemedText>

            <View style={styles.recommendationDetails}>
              <View style={styles.recommendationDetail}>
                <ThemedText style={styles.detailLabel}>Expected Outcome</ThemedText>
                <ThemedText style={styles.detailValue}>{rec.expected_outcome}</ThemedText>
              </View>
              <View style={styles.recommendationDetail}>
                <ThemedText style={styles.detailLabel}>Timeline</ThemedText>
                <ThemedText style={styles.detailValue}>{rec.implementation_timeline}</ThemedText>
              </View>
            </View>

            <View style={styles.recommendationResources}>
              <ThemedText style={styles.resourcesTitle}>Required Resources</ThemedText>
              {rec.required_resources.map((resource, resourceIndex) => (
                <View key={resourceIndex} style={styles.resourceItem}>
                  <ThemedText style={styles.resourceText}>• {resource}</ThemedText>
                </View>
              ))}
            </View>

            <View style={styles.recommendationMetrics}>
              <ThemedText style={styles.metricsTitle}>Success Metrics</ThemedText>
              {rec.success_metrics.map((metric, metricIndex) => (
                <View key={metricIndex} style={styles.metricItem}>
                  <ThemedText style={styles.metricText}>✓ {metric}</ThemedText>
                </View>
              ))}
            </View>
          </View>
        ))}
      </View>
    );
  };

  if (loading && !planData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading strategic plan...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !planData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading strategic plan</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={() => loadStrategicPlan()}>
            <ThemedText style={styles.retryButtonText}>Retry</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'initiatives', label: 'Initiatives' },
          { key: 'okrs', label: 'OKRs' },
          { key: 'scenarios', label: 'Scenarios' },
          { key: 'recommendations', label: 'Recommendations' },
        ].map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              activeTab === tab.key && styles.activeTab
            ]}
            onPress={() => setActiveTab(tab.key as any)}
          >
            <ThemedText style={[
              styles.tabText,
              activeTab === tab.key && styles.activeTabText
            ]}>
              {tab.label}
            </ThemedText>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {activeTab === 'overview' && renderOverviewTab()}
        {activeTab === 'initiatives' && renderInitiativesTab()}
        {activeTab === 'okrs' && renderOKRsTab()}
        {activeTab === 'scenarios' && renderScenariosTab()}
        {activeTab === 'recommendations' && renderRecommendationsTab()}
      </ScrollView>

      {/* Progress Update Modal */}
      <Modal
        visible={progressModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setProgressModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ThemedText style={styles.modalTitle}>Update Progress</ThemedText>
            {selectedInitiative && (
              <ThemedText style={styles.modalInitiative}>{selectedInitiative.title}</ThemedText>
            )}

            <ThemedText style={styles.modalLabel}>Progress (%)</ThemedText>
            <TextInput
              style={styles.progressInput}
              value={progressValue.toString()}
              onChangeText={(value) => setProgressValue(Math.max(0, Math.min(100, Number(value) || 0)))}
              keyboardType="numeric"
              placeholder="0-100"
              placeholderTextColor="#666"
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setProgressModalVisible(false)}
              >
                <ThemedText style={styles.modalCancelText}>Cancel</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalUpdateButton}
                onPress={updateProgress}
              >
                <ThemedText style={styles.modalUpdateText}>Update</ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ThemedView>
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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: '#F44336',
    fontSize: 16,
    marginBottom: 8,
  },
  errorSubtext: {
    color: '#C5C6C7',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#45A29E',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 5,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    alignItems: 'center',
  },
  activeTab: {
    borderBottomColor: '#66FCF1',
    backgroundColor: '#0B0C10',
  },
  tabText: {
    fontSize: 11,
    fontWeight: '500',
    color: '#C5C6C7',
  },
  activeTabText: {
    color: '#66FCF1',
    fontWeight: '600',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  tabContent: {
    flex: 1,
  },
  statusSection: {
    marginBottom: 30,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 20,
  },
  statusGrid: {
    flexDirection: 'row',
    gap: 15,
    marginBottom: 25,
  },
  statusCard: {
    flex: 1,
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  statusLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  statusValue: {
    fontSize: 28,
    fontWeight: '700',
  },
  achievementsSection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#4CAF50',
    padding: 20,
    marginBottom: 20,
  },
  subsectionTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 15,
  },
  achievementItem: {
    marginBottom: 8,
  },
  achievementText: {
    color: '#4CAF50',
    fontSize: 14,
  },
  challengesSection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#F44336',
    padding: 20,
  },
  challengeItem: {
    marginBottom: 8,
  },
  challengeText: {
    color: '#FF9800',
    fontSize: 14,
  },
  initiativeCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 20,
  },
  initiativeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 15,
  },
  initiativeInfo: {
    flex: 1,
  },
  initiativeTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  initiativeMeta: {
    flexDirection: 'row',
    gap: 8,
  },
  categoryBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  categoryText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  priorityText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  initiativeProgress: {
    alignItems: 'flex-end',
  },
  progressPercentage: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 4,
  },
  updateProgressButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#45A29E',
    borderRadius: 6,
  },
  updateProgressText: {
    color: '#0B0C10',
    fontSize: 12,
    fontWeight: '600',
  },
  initiativeDescription: {
    color: '#C5C6C7',
    fontSize: 14,
    marginBottom: 15,
    lineHeight: 20,
  },
  progressBar: {
    height: 6,
    backgroundColor: '#2A3F41',
    borderRadius: 3,
    marginBottom: 15,
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  kpisSection: {
    marginBottom: 15,
  },
  kpisTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
  },
  kpiItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2A3F41',
  },
  kpiName: {
    color: '#C5C6C7',
    fontSize: 13,
    flex: 1,
  },
  kpiProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  kpiCurrent: {
    fontSize: 14,
    fontWeight: '600',
  },
  kpiTarget: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  kpiTrend: {
    fontSize: 12,
    fontWeight: '600',
  },
  milestonesSection: {
    marginTop: 15,
  },
  milestonesTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
  },
  milestoneItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  milestoneText: {
    color: '#C5C6C7',
    fontSize: 13,
    flex: 1,
  },
  milestoneDue: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  okrCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 20,
  },
  okrHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 15,
  },
  okrObjective: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    marginRight: 15,
  },
  okrProgress: {
    alignItems: 'flex-end',
  },
  okrProgressPercentage: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 4,
  },
  okrConfidence: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  keyResults: {
    marginTop: 15,
  },
  keyResultItem: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  krHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  krText: {
    color: '#C5C6C7',
    fontSize: 13,
    flex: 1,
  },
  krProgress: {
    fontSize: 12,
    fontWeight: '600',
  },
  krDue: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  scenariosHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  actionButton: {
    backgroundColor: '#66FCF1',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 6,
  },
  disabledButton: {
    opacity: 0.5,
  },
  actionButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  scenarioCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 2,
    padding: 20,
    marginBottom: 20,
  },
  scenarioHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  scenarioTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '700',
  },
  scenarioProbability: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  scenarioOutcomes: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    padding: 15,
    marginBottom: 15,
  },
  outcomeItem: {
    alignItems: 'center',
  },
  outcomeLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 5,
  },
  outcomeValue: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '700',
  },
  scenarioDetails: {
    gap: 12,
  },
  scenarioSubsection: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  assumptionText: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 4,
    marginLeft: 8,
  },
  riskText: {
    color: '#FF9800',
    fontSize: 13,
    marginBottom: 4,
  },
  actionItemText: {
    color: '#4CAF50',
    fontSize: 13,
    marginBottom: 4,
    marginLeft: 8,
  },
  recommendationsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  recommendationCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 20,
  },
  recommendationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  recommendationTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    marginRight: 10,
  },
  recommendationRationale: {
    color: '#C5C6C7',
    fontSize: 14,
    marginBottom: 15,
    lineHeight: 20,
  },
  recommendationDetails: {
    flexDirection: 'row',
    gap: 20,
    marginBottom: 15,
  },
  recommendationDetail: {
    flex: 1,
  },
  detailLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  detailValue: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
  },
  recommendationResources: {
    marginBottom: 15,
  },
  resourcesTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  resourceItem: {
    marginBottom: 4,
  },
  resourceText: {
    color: '#C5C6C7',
    fontSize: 13,
    marginLeft: 8,
  },
  recommendationMetrics: {
    marginBottom: 15,
  },
  metricsTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  metricItem: {
    marginBottom: 4,
  },
  metricText: {
    color: '#4CAF50',
    fontSize: 13,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    padding: 25,
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  modalTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 5,
    textAlign: 'center',
  },
  modalInitiative: {
    color: '#C5C6C7',
    fontSize: 14,
    marginBottom: 20,
    textAlign: 'center',
  },
  modalLabel: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  progressInput: {
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 8,
    color: '#C5C6C7',
    fontSize: 16,
    padding: 15,
    marginBottom: 20,
    textAlign: 'center',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 10,
  },
  modalCancelButton: {
    flex: 1,
    backgroundColor: '#45A29E',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalCancelText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
  modalUpdateButton: {
    flex: 1,
    backgroundColor: '#66FCF1',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalUpdateText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
});