/**
 * Morning Briefing Component
 * Displays automated daily business health analysis and executive summary
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MorningBriefingData } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface MorningBriefingProps {
  data?: MorningBriefingData;
  compact?: boolean;
  autoGenerate?: boolean;
  onGenerateNew?: () => void;
}

export function MorningBriefing({
  data: initialData,
  compact = false,
  autoGenerate = false,
  onGenerateNew,
}: MorningBriefingProps) {
  const [briefingData, setBriefingData] = useState<MorningBriefingData | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(compact ? null : 'summary');

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    if (autoGenerate && !briefingData) {
      generateMorningBriefing();
    }
  }, [autoGenerate, briefingData]);

  useEffect(() => {
    setBriefingData(initialData || null);
  }, [initialData]);

  useEffect(() => {
    // Subscribe to real-time briefing updates
    biService.subscribeToMorningBriefingUpdates((data) => {
      setBriefingData(data);
    });
  }, [biService]);

  const generateMorningBriefing = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.generateMorningBriefing();

      if (response.success && response.data) {
        setBriefingData(response.data);
        onGenerateNew?.();
      } else {
        throw new Error(response.error || 'Failed to generate morning briefing');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      Alert.alert('Error', 'Failed to generate morning briefing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return '#4CAF50'; // Green
    if (score >= 60) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#F44336';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#C5C6C7';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_track': return '#4CAF50';
      case 'at_risk': return '#FF9800';
      case 'delayed': return '#F44336';
      default: return '#C5C6C7';
    }
  };

  if (loading && !briefingData) {
    return (
      <ThemedView style={[styles.container, compact && styles.compactContainer]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size={compact ? "small" : "large"} color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Generating morning briefing...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !briefingData) {
    return (
      <ThemedView style={[styles.container, compact && styles.compactContainer]}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading briefing</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={generateMorningBriefing}>
            <ThemedText style={styles.retryButtonText}>Retry</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  if (!briefingData) {
    return (
      <ThemedView style={[styles.container, compact && styles.compactContainer]}>
        <View style={styles.emptyContainer}>
          <ThemedText style={styles.emptyText}>No briefing available</ThemedText>
          <TouchableOpacity style={styles.generateButton} onPress={generateMorningBriefing}>
            <ThemedText style={styles.generateButtonText}>Generate Briefing</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={[styles.container, compact && styles.compactContainer]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <ThemedText type={compact ? "subtitle" : "title"} style={styles.title}>
            {compact ? 'Daily Briefing' : briefingData.title}
          </ThemedText>
          <ThemedText style={styles.date}>
            {new Date(briefingData.date).toLocaleDateString()}
          </ThemedText>
        </View>

        {!compact && (
          <TouchableOpacity
            style={styles.refreshButton}
            onPress={generateMorningBriefing}
            disabled={loading}
          >
            <ThemedText style={styles.refreshButtonText}>
              {loading ? '...' : '↻'}
            </ThemedText>
          </TouchableOpacity>
        )}
      </View>

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        nestedScrollEnabled={true}
      >
        {/* Executive Summary */}
        <View style={styles.section}>
          <TouchableOpacity
            style={styles.sectionHeader}
            onPress={() => toggleSection('summary')}
          >
            <ThemedText style={styles.sectionTitle}>Executive Summary</ThemedText>
            <ThemedText style={styles.expandIcon}>
              {expandedSection === 'summary' ? '▼' : '▶'}
            </ThemedText>
          </TouchableOpacity>

          {expandedSection === 'summary' && (
            <View style={styles.sectionContent}>
              {/* Overall Health Score */}
              <View style={styles.healthScoreContainer}>
                <View style={[
                  styles.healthScoreCircle,
                  { borderColor: getHealthScoreColor(briefingData.executive_summary.overall_health_score) }
                ]}>
                  <ThemedText style={[
                    styles.healthScoreText,
                    { color: getHealthScoreColor(briefingData.executive_summary.overall_health_score) }
                  ]}>
                    {briefingData.executive_summary.overall_health_score}
                  </ThemedText>
                </View>
                <ThemedText style={styles.healthScoreLabel}>Overall Health</ThemedText>
              </View>

              {/* Key Insights */}
              <View style={styles.insightsContainer}>
                <View style={styles.insightGroup}>
                  <ThemedText style={styles.insightGroupTitle}>Key Priorities</ThemedText>
                  {briefingData.executive_summary.key_priorities.map((priority, index) => (
                    <View key={index} style={styles.insightItem}>
                      <ThemedText style={styles.bullet}>•</ThemedText>
                      <ThemedText style={styles.insightText}>{priority}</ThemedText>
                    </View>
                  ))}
                </View>

                {briefingData.executive_summary.critical_alerts.length > 0 && (
                  <View style={styles.insightGroup}>
                    <ThemedText style={[styles.insightGroupTitle, { color: '#F44336' }]}>Critical Alerts</ThemedText>
                    {briefingData.executive_summary.critical_alerts.map((alert, index) => (
                      <View key={index} style={[styles.insightItem, { borderLeftColor: '#F44336' }]}>
                        <ThemedText style={styles.bullet}>•</ThemedText>
                        <ThemedText style={styles.insightText}>{alert}</ThemedText>
                      </View>
                    ))}
                  </View>
                )}

                {briefingData.executive_summary.opportunities.length > 0 && (
                  <View style={styles.insightGroup}>
                    <ThemedText style={[styles.insightGroupTitle, { color: '#4CAF50' }]}>Opportunities</ThemedText>
                    {briefingData.executive_summary.opportunities.map((opportunity, index) => (
                      <View key={index} style={[styles.insightItem, { borderLeftColor: '#4CAF50' }]}>
                        <ThemedText style={styles.bullet}>•</ThemedText>
                        <ThemedText style={styles.insightText}>{opportunity}</ThemedText>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            </View>
          )}
        </View>

        {/* Business Health */}
        {!compact && (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.sectionHeader}
              onPress={() => toggleSection('business_health')}
            >
              <ThemedText style={styles.sectionTitle}>Business Health</ThemedText>
              <ThemedText style={styles.expandIcon}>
                {expandedSection === 'business_health' ? '▼' : '▶'}
              </ThemedText>
            </TouchableOpacity>

            {expandedSection === 'business_health' && (
              <View style={styles.sectionContent}>
                {/* Revenue Trends */}
                <View style={styles.metricGroup}>
                  <ThemedText style={styles.metricGroupTitle}>Revenue Trends</ThemedText>
                  <View style={styles.metricsGrid}>
                    <View style={styles.metricCard}>
                      <ThemedText style={styles.metricValue}>
                        ${(briefingData.business_health.revenue_trends.current_mrr / 1000).toFixed(1)}K
                      </ThemedText>
                      <ThemedText style={styles.metricLabel}>Current MRR</ThemedText>
                    </View>
                    <View style={styles.metricCard}>
                      <ThemedText style={styles.metricValue}>
                        {briefingData.business_health.revenue_trends.growth_rate.toFixed(1)}%
                      </ThemedText>
                      <ThemedText style={styles.metricLabel}>Growth Rate</ThemedText>
                    </View>
                  </View>
                </View>

                {/* Operational Metrics */}
                <View style={styles.metricGroup}>
                  <ThemedText style={styles.metricGroupTitle}>Operational Metrics</ThemedText>
                  <View style={styles.metricsGrid}>
                    <View style={styles.metricCard}>
                      <ThemedText style={styles.metricValue}>
                        {briefingData.business_health.operational_metrics.active_users}
                      </ThemedText>
                      <ThemedText style={styles.metricLabel}>Active Users</ThemedText>
                    </View>
                    <View style={styles.metricCard}>
                      <ThemedText style={styles.metricValue}>
                        {(briefingData.business_health.operational_metrics.conversion_rate * 100).toFixed(1)}%
                      </ThemedText>
                      <ThemedText style={styles.metricLabel}>Conversion</ThemedText>
                    </View>
                  </View>
                </View>
              </View>
            )}
          </View>
        )}

        {/* Strategic Priorities */}
        {briefingData.strategic_priorities.length > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.sectionHeader}
              onPress={() => toggleSection('priorities')}
            >
              <ThemedText style={styles.sectionTitle}>Strategic Priorities</ThemedText>
              <ThemedText style={styles.expandIcon}>
                {expandedSection === 'priorities' ? '▼' : '▶'}
              </ThemedText>
            </TouchableOpacity>

            {expandedSection === 'priorities' && (
              <View style={styles.sectionContent}>
                {briefingData.strategic_priorities.slice(0, compact ? 2 : undefined).map((priority, index) => (
                  <View key={index} style={styles.priorityCard}>
                    <View style={styles.priorityHeader}>
                      <ThemedText style={styles.priorityTitle}>{priority.priority}</ThemedText>
                      <View style={styles.priorityBadges}>
                        <View style={[
                          styles.priorityBadge,
                          { backgroundColor: getPriorityColor(priority.priority) }
                        ]}>
                          <ThemedText style={styles.priorityBadgeText}>
                            {priority.priority.toUpperCase()}
                          </ThemedText>
                        </View>
                        <View style={[
                          styles.statusBadge,
                          { backgroundColor: getStatusColor(priority.status) }
                        ]}>
                          <ThemedText style={styles.statusText}>
                            {priority.status.replace('_', ' ').toUpperCase()}
                          </ThemedText>
                        </View>
                      </View>
                    </View>
                    <View style={styles.priorityDetails}>
                      <ThemedText style={styles.priorityOwner}>Owner: {priority.owner}</ThemedText>
                      <ThemedText style={styles.priorityDeadline}>Deadline: {priority.deadline}</ThemedText>
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Competitive Insights */}
        {briefingData.competitive_insights.length > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.sectionHeader}
              onPress={() => toggleSection('competitive')}
            >
              <ThemedText style={styles.sectionTitle}>Competitive Intelligence</ThemedText>
              <ThemedText style={styles.expandIcon}>
                {expandedSection === 'competitive' ? '▼' : '▶'}
              </ThemedText>
            </TouchableOpacity>

            {expandedSection === 'competitive' && (
              <View style={styles.sectionContent}>
                {briefingData.competitive_insights.slice(0, compact ? 1 : undefined).map((insight, index) => (
                  <View key={index} style={styles.competitiveCard}>
                    <ThemedText style={styles.competitorName}>{insight.competitor}</ThemedText>
                    <ThemedText style={styles.competitiveDevelopment}>{insight.development}</ThemedText>
                    <ThemedText style={styles.competitiveImpact}>Impact: {insight.impact}</ThemedText>
                    <ThemedText style={styles.competitiveResponse}>
                      Recommended Response: {insight.recommended_response}
                    </ThemedText>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Market Opportunities */}
        {briefingData.market_opportunities.length > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.sectionHeader}
              onPress={() => toggleSection('opportunities')}
            >
              <ThemedText style={styles.sectionTitle}>Market Opportunities</ThemedText>
              <ThemedText style={styles.expandIcon}>
                {expandedSection === 'opportunities' ? '▼' : '▶'}
              </ThemedText>
            </TouchableOpacity>

            {expandedSection === 'opportunities' && (
              <View style={styles.sectionContent}>
                {briefingData.market_opportunities.slice(0, compact ? 2 : undefined).map((opportunity, index) => (
                  <View key={index} style={styles.opportunityCard}>
                    <ThemedText style={styles.opportunityTitle}>{opportunity.opportunity}</ThemedText>
                    <View style={styles.opportunityMetrics}>
                      <ThemedText style={styles.opportunityValue}>
                        Value: ${(opportunity.potential_value / 1000).toFixed(0)}K
                      </ThemedText>
                      <ThemedText style={styles.opportunityConfidence}>
                        Confidence: {(opportunity.confidence * 100).toFixed(0)}%
                      </ThemedText>
                      <ThemedText style={styles.opportunityTimeframe}>
                        Timeline: {opportunity.timeframe}
                      </ThemedText>
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    overflow: 'hidden',
  },
  compactContainer: {
    marginHorizontal: 0,
  },
  loadingContainer: {
    padding: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 15,
    color: '#C5C6C7',
    fontSize: 14,
  },
  errorContainer: {
    padding: 30,
    alignItems: 'center',
  },
  errorText: {
    color: '#F44336',
    fontSize: 14,
    marginBottom: 15,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#45A29E',
    borderRadius: 6,
  },
  retryButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  emptyContainer: {
    padding: 30,
    alignItems: 'center',
  },
  emptyText: {
    color: '#C5C6C7',
    fontSize: 14,
    marginBottom: 15,
  },
  generateButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#66FCF1',
    borderRadius: 6,
  },
  generateButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#45A29E',
  },
  headerLeft: {
    flex: 1,
  },
  title: {
    color: '#66FCF1',
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  date: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  refreshButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#45A29E',
    borderRadius: 4,
    minWidth: 40,
    alignItems: 'center',
  },
  refreshButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 16,
  },
  scrollView: {
    flex: 1,
  },
  section: {
    borderBottomWidth: 1,
    borderBottomColor: '#2A3F41',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    paddingVertical: 12,
    backgroundColor: '#0B0C10',
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
  },
  expandIcon: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  sectionContent: {
    padding: 15,
  },
  healthScoreContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  healthScoreCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  healthScoreText: {
    fontSize: 24,
    fontWeight: '700',
  },
  healthScoreLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  insightsContainer: {
    gap: 15,
  },
  insightGroup: {
    gap: 8,
  },
  insightGroupTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 2,
    paddingLeft: 4,
    borderLeftWidth: 3,
    borderLeftColor: '#45A29E',
  },
  bullet: {
    color: '#C5C6C7',
    marginRight: 8,
    fontSize: 12,
  },
  insightText: {
    color: '#C5C6C7',
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  metricGroup: {
    marginBottom: 20,
  },
  metricGroupTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
  },
  metricsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  metricCard: {
    flex: 1,
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  metricValue: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  metricLabel: {
    color: '#C5C6C7',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  priorityCard: {
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  priorityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  priorityTitle: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
    marginRight: 10,
  },
  priorityBadges: {
    gap: 6,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  priorityBadgeText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  statusText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  priorityDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  priorityOwner: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  priorityDeadline: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  competitiveCard: {
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  competitorName: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  competitiveDevelopment: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 6,
    lineHeight: 18,
  },
  competitiveImpact: {
    color: '#FF9800',
    fontSize: 12,
    marginBottom: 4,
  },
  competitiveResponse: {
    color: '#4CAF50',
    fontSize: 12,
    fontStyle: 'italic',
  },
  opportunityCard: {
    backgroundColor: '#0B0C10',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  opportunityTitle: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  opportunityMetrics: {
    gap: 4,
  },
  opportunityValue: {
    color: '#66FCF1',
    fontSize: 12,
  },
  opportunityConfidence: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.8,
  },
  opportunityTimeframe: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.8,
  },
});