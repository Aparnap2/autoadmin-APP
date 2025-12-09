/**
 * CRM Intelligence Component
 * Comprehensive CRM analytics and intelligence with HubSpot integration
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { LineChart, BarChart, PieChart } from 'react-native-chart-kit';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { CRMAnalysisData } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface CRMIntelligenceProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const { width: screenWidth } = Dimensions.get('window');

export function CRMIntelligence({
  autoRefresh = false,
  refreshInterval = 300000, // 5 minutes
}: CRMIntelligenceProps) {
  const [crmData, setCRMData] = useState<CRMAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'pipeline' | 'health' | 'segments' | 'engagement'>('overview');
  const [selectedDealIds, setSelectedDealIds] = useState<string[]>([]);

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    loadCRMAnalysis();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadCRMAnalysis, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  const loadCRMAnalysis = async (params?: any) => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getCRMAnalysis({
        include_forecasts: true,
        ...params
      });

      if (response.success && response.data) {
        setCRMData(response.data);
      } else {
        throw new Error(response.error || 'Failed to load CRM analysis');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const analyzeDealHealth = async () => {
    try {
      setLoading(true);
      await biService.analyzeDealHealth(selectedDealIds);
      Alert.alert('Success', 'Deal health analysis completed');
      await loadCRMAnalysis();
    } catch (err) {
      Alert.alert('Error', 'Failed to analyze deal health');
    } finally {
      setLoading(false);
    }
  };

  const optimizePipeline = async () => {
    try {
      setLoading(true);
      await biService.optimizePipeline();
      Alert.alert('Success', 'Pipeline optimization completed');
      await loadCRMAnalysis();
    } catch (err) {
      Alert.alert('Error', 'Failed to optimize pipeline');
    } finally {
      setLoading(false);
    }
  };

  const analyzeCustomerSegments = async () => {
    try {
      setLoading(true);
      await biService.analyzeCustomerSegments();
      Alert.alert('Success', 'Customer segmentation analysis completed');
      await loadCRMAnalysis();
    } catch (err) {
      Alert.alert('Error', 'Failed to analyze customer segments');
    } finally {
      setLoading(false);
    }
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return '#4CAF50';
    if (score >= 60) return '#FF9800';
    return '#F44336';
  };

  const getWinRateColor = (rate: number) => {
    if (rate >= 40) return '#4CAF50';
    if (rate >= 25) return '#FF9800';
    return '#F44336';
  };

  // Chart data transformations
  const pipelineData = useMemo(() => {
    if (!crmData) return null;

    return {
      labels: ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closing'],
      datasets: [{
        data: [15, 12, 8, 5, 3], // Mock data - should come from API
      }],
    };
  }, [crmData]);

  const segmentData = useMemo(() => {
    if (!crmData?.customer_segments) return null;

    return crmData.customer_segments.map(segment => ({
      name: segment.segment,
      population: segment.size,
      color: ['#66FCF1', '#45A29E', '#1F2833', '#C5C6C7'][Math.floor(Math.random() * 4)],
      legendFontColor: '#C5C6C7',
      legendFontSize: 11,
    }));
  }, [crmData]);

  const engagementData = useMemo(() => {
    if (!crmData?.engagement_patterns) return null;

    return {
      labels: crmData.engagement_patterns.communication_frequency.map(cf => cf.type),
      datasets: [{
        data: crmData.engagement_patterns.communication_frequency.map(cf => cf.effectiveness),
      }],
    };
  }, [crmData]);

  const renderOverviewTab = () => {
    if (!crmData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Overall Health Metrics */}
        <View style={styles.metricsGrid}>
          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Total Pipeline Value</ThemedText>
            <ThemedText style={styles.metricValue}>
              ${(crmData.overall_health.total_pipeline_value / 1000).toFixed(1)}K
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              Weighted: ${(crmData.overall_health.weighted_pipeline / 1000).toFixed(1)}K
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Total Deals</ThemedText>
            <ThemedText style={styles.metricValue}>
              {crmData.overall_health.total_deals}
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              Win Rate: {(crmData.overall_health.conversion_rate * 100).toFixed(1)}%
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Sales Cycle</ThemedText>
            <ThemedText style={styles.metricValue}>
              {crmData.overall_health.sales_cycle_length} days
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              Avg. per deal
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Forecast Accuracy</ThemedText>
            <ThemedText style={[
              styles.metricValue,
              { color: getWinRateColor(crmData.pipeline_optimization.forecast_accuracy.current_quarter * 100) }
            ]}>
              {(crmData.pipeline_optimization.forecast_accuracy.current_quarter * 100).toFixed(1)}%
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              Current quarter
            </ThemedText>
          </View>
        </View>

        {/* Customer Segments Chart */}
        {segmentData && (
          <View style={styles.chartSection}>
            <ThemedText style={styles.chartTitle}>Customer Segments</ThemedText>
            <PieChart
              data={segmentData}
              width={screenWidth - 60}
              height={200}
              chartConfig={{
                color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
              }}
              accessor="population"
              backgroundColor="transparent"
              paddingLeft="15"
            />
          </View>
        )}
      </View>
    );
  };

  const renderPipelineTab = () => {
    if (!crmData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Pipeline Stages Chart */}
        {pipelineData && (
          <View style={styles.chartSection}>
            <ThemedText style={styles.chartTitle}>Pipeline by Stage</ThemedText>
            <BarChart
              data={pipelineData}
              width={screenWidth - 40}
              height={220}
              chartConfig={{
                backgroundColor: '#1F2833',
                backgroundGradientFrom: '#1F2833',
                backgroundGradientTo: '#1F2833',
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(197, 198, 199, ${opacity})`,
                style: {
                  borderRadius: 16,
                },
              }}
              style={styles.chart}
            />
          </View>
        )}

        {/* Pipeline Bottlenecks */}
        <View style={styles.bottlenecksSection}>
          <ThemedText style={styles.sectionTitle}>Pipeline Bottlenecks</ThemedText>
          {crmData.pipeline_optimization.bottleneck_stages.map((bottleneck, index) => (
            <View key={index} style={styles.bottleneckCard}>
              <View style={styles.bottleneckHeader}>
                <ThemedText style={styles.bottleneckStage}>{bottleneck.stage}</ThemedText>
                <ThemedText style={[
                  styles.conversionRate,
                  { color: getWinRateColor(bottleneck.conversion_rate * 100) }
                ]}>
                  {(bottleneck.conversion_rate * 100).toFixed(1)}%
                </ThemedText>
              </View>
              <ThemedText style={styles.bottleneckDays}>
                {bottleneck.avg_days_in_stage} days avg
              </ThemedText>
              <View style={styles.recommendedActions}>
                <ThemedText style={styles.actionsTitle}>Recommended Actions:</ThemedText>
                {bottleneck.recommended_actions.map((action, actionIndex) => (
                  <ThemedText key={actionIndex} style={styles.actionItem}>• {action}</ThemedText>
                ))}
              </View>
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.actionButton} onPress={optimizePipeline}>
          <ThemedText style={styles.actionButtonText}>Optimize Pipeline</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  const renderHealthTab = () => {
    if (!crmData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Deal Health Scores */}
        <View style={styles.healthSection}>
          <ThemedText style={styles.sectionTitle}>Deal Health Analysis</ThemedText>
          {crmData.deal_health_scores.slice(0, 5).map((deal, index) => (
            <View key={index} style={[
              styles.dealHealthCard,
              { borderLeftColor: getHealthScoreColor(deal.health_score) }
            ]}>
              <View style={styles.dealHeader}>
                <ThemedText style={styles.dealName}>{deal.deal_name}</ThemedText>
                <View style={styles.healthScore}>
                  <ThemedText style={[
                    styles.healthScoreText,
                    { color: getHealthScoreColor(deal.health_score) }
                  ]}>
                    {deal.health_score}
                  </ThemedText>
                  <ThemedText style={styles.healthScoreLabel}>/100</ThemedText>
                </View>
              </View>
              <View style={styles.dealDetails}>
                <ThemedText style={styles.dealDays}>
                  {deal.days_in_stage} days in current stage
                </ThemedText>
                {deal.risk_factors.length > 0 && (
                  <View style={styles.riskFactors}>
                    <ThemedText style={styles.riskTitle}>Risk Factors:</ThemedText>
                    {deal.risk_factors.map((risk, riskIndex) => (
                      <ThemedText key={riskIndex} style={styles.riskItem}>• {risk}</ThemedText>
                    ))}
                  </View>
                )}
                {deal.recommendations.length > 0 && (
                  <View style={styles.recommendations}>
                    <ThemedText style={styles.recommendationsTitle}>Recommendations:</ThemedText>
                    {deal.recommendations.map((rec, recIndex) => (
                      <ThemedText key={recIndex} style={styles.recommendationItem}>• {rec}</ThemedText>
                    ))}
                  </View>
                )}
              </View>
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.actionButton} onPress={analyzeDealHealth}>
          <ThemedText style={styles.actionButtonText}>Analyze Deal Health</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  const renderSegmentsTab = () => {
    if (!crmData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Customer Segments Analysis */}
        <View style={styles.segmentsSection}>
          <ThemedText style={styles.sectionTitle}>Customer Segments Analysis</ThemedText>
          {crmData.customer_segments.map((segment, index) => (
            <View key={index} style={styles.segmentCard}>
              <View style={styles.segmentHeader}>
                <ThemedText style={styles.segmentName}>{segment.segment}</ThemedText>
                <View style={styles.segmentMetrics}>
                  <ThemedText style={styles.segmentSize}>{segment.size} customers</ThemedText>
                  <ThemedText style={styles.segmentLTV}>
                    LTV: ${(segment.ltv / 1000).toFixed(1)}K
                  </ThemedText>
                </View>
              </View>
              <View style={styles.segmentDetails}>
                <ThemedText style={styles.segmentDealSize}>
                  Avg Deal Size: ${(segment.avg_deal_size / 1000).toFixed(1)}K
                </ThemedText>
                <ThemedText style={[
                  styles.segmentConversion,
                  { color: getWinRateColor(segment.conversion_rate * 100) }
                ]}>
                  Conversion: {(segment.conversion_rate * 100).toFixed(1)}%
                </ThemedText>
              </View>
              <View style={styles.segmentCharacteristics}>
                {segment.characteristics.map((characteristic, charIndex) => (
                  <View key={charIndex} style={styles.characteristicTag}>
                    <ThemedText style={styles.characteristicText}>{characteristic}</ThemedText>
                  </View>
                ))}
              </View>
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.actionButton} onPress={analyzeCustomerSegments}>
          <ThemedText style={styles.actionButtonText}>Analyze Segments</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  const renderEngagementTab = () => {
    if (!crmData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Engagement Patterns */}
        <View style={styles.engagementSection}>
          <ThemedText style={styles.sectionTitle}>Engagement Patterns</ThemedText>

          {/* Communication Effectiveness */}
          {engagementData && (
            <View style={styles.chartSection}>
              <ThemedText style={styles.chartTitle}>Communication Effectiveness</ThemedText>
              <BarChart
                data={engagementData}
                width={screenWidth - 40}
                height={200}
                chartConfig={{
                  backgroundColor: '#1F2833',
                  backgroundGradientFrom: '#1F2833',
                  backgroundGradientTo: '#1F2833',
                  decimalPlaces: 0,
                  color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
                  labelColor: (opacity = 1) => `rgba(197, 198, 199, ${opacity})`,
                  style: {
                    borderRadius: 16,
                  },
                }}
                style={styles.chart}
              />
            </View>
          )}

          {/* Best Practices */}
          {crmData.engagement_patterns.best_practices.length > 0 && (
            <View style={styles.bestPracticesSection}>
              <ThemedText style={styles.sectionSubTitle}>Best Practices</ThemedText>
              {crmData.engagement_patterns.best_practices.map((practice, index) => (
                <View key={index} style={styles.practiceItem}>
                  <ThemedText style={styles.practiceText}>✓ {practice}</ThemedText>
                </View>
              ))}
            </View>
          )}

          {/* Risk Indicators */}
          {crmData.engagement_patterns.risk_indicators.length > 0 && (
            <View style={styles.riskIndicatorsSection}>
              <ThemedText style={styles.sectionSubTitle}>Risk Indicators</ThemedText>
              {crmData.engagement_patterns.risk_indicators.map((risk, index) => (
                <View key={index} style={styles.riskIndicator}>
                  <ThemedText style={styles.riskIndicatorText}>⚠ {risk}</ThemedText>
                </View>
              ))}
            </View>
          )}
        </View>
      </View>
    );
  };

  if (loading && !crmData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading CRM intelligence...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !crmData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading CRM intelligence</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={() => loadCRMAnalysis()}>
            <ThemedText style={styles.retryButtonText}>Retry</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <ThemedText type="title" style={styles.title}>CRM Intelligence</ThemedText>
        <ThemedText style={styles.subtitle}>
          HubSpot-powered customer relationship analytics
        </ThemedText>
      </View>

      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'pipeline', label: 'Pipeline' },
          { key: 'health', label: 'Health' },
          { key: 'segments', label: 'Segments' },
          { key: 'engagement', label: 'Engagement' },
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
        {activeTab === 'pipeline' && renderPipelineTab()}
        {activeTab === 'health' && renderHealthTab()}
        {activeTab === 'segments' && renderSegmentsTab()}
        {activeTab === 'engagement' && renderEngagementTab()}
      </ScrollView>
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
  header: {
    padding: 20,
    paddingBottom: 15,
  },
  title: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    color: '#C5C6C7',
    fontSize: 14,
    opacity: 0.8,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 10,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    alignItems: 'center',
  },
  activeTab: {
    borderBottomColor: '#66FCF1',
    backgroundColor: '#0B0C10',
  },
  tabText: {
    fontSize: 12,
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
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 25,
  },
  metricCard: {
    width: '48%',
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
    marginBottom: 5,
  },
  metricLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    textAlign: 'center',
  },
  metricValue: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  metricSubtitle: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  chartSection: {
    marginBottom: 25,
    alignItems: 'center',
  },
  chartTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 15,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  bottlenecksSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
  },
  sectionSubTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  bottleneckCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  bottleneckHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  bottleneckStage: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '600',
  },
  conversionRate: {
    fontSize: 16,
    fontWeight: '700',
  },
  bottleneckDays: {
    color: '#C5C6C7',
    fontSize: 12,
    marginBottom: 10,
  },
  recommendedActions: {
    gap: 4,
  },
  actionsTitle: {
    color: '#66FCF1',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
  },
  actionItem: {
    color: '#C5C6C7',
    fontSize: 12,
    marginLeft: 8,
  },
  actionButton: {
    backgroundColor: '#66FCF1',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 20,
  },
  actionButtonText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
  healthSection: {
    marginBottom: 20,
  },
  dealHealthCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    borderLeftWidth: 4,
    padding: 15,
    marginBottom: 10,
  },
  dealHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  dealName: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  healthScore: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  healthScoreText: {
    fontSize: 20,
    fontWeight: '700',
  },
  healthScoreLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    marginLeft: 2,
  },
  dealDetails: {
    gap: 8,
  },
  dealDays: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  riskFactors: {
    gap: 4,
  },
  riskTitle: {
    color: '#FF9800',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 2,
  },
  riskItem: {
    color: '#C5C6C7',
    fontSize: 11,
    marginLeft: 8,
  },
  recommendations: {
    gap: 4,
  },
  recommendationsTitle: {
    color: '#4CAF50',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 2,
  },
  recommendationItem: {
    color: '#C5C6C7',
    fontSize: 11,
    marginLeft: 8,
  },
  segmentsSection: {
    marginBottom: 20,
  },
  segmentCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  segmentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  segmentName: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
  },
  segmentMetrics: {
    alignItems: 'flex-end',
  },
  segmentSize: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  segmentLTV: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
  },
  segmentDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  segmentDealSize: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  segmentConversion: {
    fontSize: 12,
    fontWeight: '600',
  },
  segmentCharacteristics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  characteristicTag: {
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  characteristicText: {
    color: '#C5C6C7',
    fontSize: 10,
  },
  engagementSection: {
    marginBottom: 20,
  },
  bestPracticesSection: {
    marginBottom: 20,
  },
  practiceItem: {
    backgroundColor: '#1F2833',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 12,
    marginBottom: 8,
  },
  practiceText: {
    color: '#4CAF50',
    fontSize: 13,
  },
  riskIndicatorsSection: {
    marginBottom: 20,
  },
  riskIndicator: {
    backgroundColor: '#1F2833',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#F44336',
    padding: 12,
    marginBottom: 8,
  },
  riskIndicatorText: {
    color: '#FF9800',
    fontSize: 13,
  },
});