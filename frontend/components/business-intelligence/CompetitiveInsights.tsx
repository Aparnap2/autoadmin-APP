/**
 * Competitive Insights Component
 * Comprehensive competitive intelligence monitoring and analysis dashboard
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
  Dimensions,
} from 'react-native';
import { LineChart, BarChart } from 'react-native-chart-kit';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { CompetitorAnalysis } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface CompetitiveInsightsProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const { width: screenWidth } = Dimensions.get('window');

export function CompetitiveInsights({
  autoRefresh = false,
  refreshInterval = 600000, // 10 minutes
}: CompetitiveInsightsProps) {
  const [competitors, setCompetitors] = useState<CompetitorAnalysis[]>([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState<CompetitorAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newCompetitorName, setNewCompetitorName] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [monitoring, setMonitoring] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'analysis' | 'positioning' | 'opportunities'>('overview');

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    loadCompetitorAnalysis();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadCompetitorAnalysis, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  const loadCompetitorAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getCompetitorAnalysis({
        include_market_intelligence: true,
      });

      if (response.success && response.data) {
        setCompetitors(response.data);
        if (response.data.length > 0 && !selectedCompetitor) {
          setSelectedCompetitor(response.data[0]);
        }
      } else {
        throw new Error(response.error || 'Failed to load competitor analysis');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const analyzeNewCompetitor = async () => {
    if (!newCompetitorName.trim()) {
      Alert.alert('Validation Error', 'Please enter a competitor name');
      return;
    }

    try {
      setAnalyzing(true);

      const response = await biService.analyzeCompetitor(newCompetitorName.trim());

      if (response.success && response.data) {
        Alert.alert('Success', `Analysis completed for ${newCompetitorName}`);
        setNewCompetitorName('');
        await loadCompetitorAnalysis();
        setSelectedCompetitor(response.data);
      } else {
        throw new Error(response.error || 'Failed to analyze competitor');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      Alert.alert('Error', errorMessage);
    } finally {
      setAnalyzing(false);
    }
  };

  const startMonitoring = async () => {
    try {
      setMonitoring(true);

      const response = await biService.monitorCompetitors();

      if (response.success) {
        Alert.alert('Success', 'Competitor monitoring started');
      } else {
        throw new Error(response.error || 'Failed to start monitoring');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      Alert.alert('Error', errorMessage);
    } finally {
      setMonitoring(false);
    }
  };

  const getMarketPositioning = async () => {
    try {
      const response = await biService.getMarketPositioning();

      if (response.success) {
        Alert.alert('Success', 'Market positioning analysis completed');
        await loadCompetitorAnalysis();
      } else {
        throw new Error(response.error || 'Failed to get market positioning');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to get market positioning');
    }
  };

  const getAdvantageColor = (advantage: string) => {
    switch (advantage) {
      case 'them': return '#F44336';
      case 'us': return '#4CAF50';
      case 'neutral': return '#FF9800';
      default: return '#C5C6C7';
    }
  };

  const getThreatLevelColor = (level: string) => {
    switch (level) {
      case 'high': return '#F44336';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#C5C6C7';
    }
  };

  const getOpportunityTypeColor = (type: string) => {
    switch (type) {
      case 'feature': return '#2196F3';
      case 'pricing': return '#4CAF50';
      case 'marketing': return '#9C27B0';
      case 'strategic': return '#FF9800';
      default: return '#C5C6C7';
    }
  };

  const renderCompetitorSelector = () => (
    <View style={styles.competitorSelector}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {competitors.map((competitor, index) => (
          <TouchableOpacity
            key={index}
            style={[
              styles.competitorTab,
              selectedCompetitor?.competitor_profile.name === competitor.competitor_profile.name &&
              styles.activeCompetitorTab
            ]}
            onPress={() => setSelectedCompetitor(competitor)}
          >
            <ThemedText style={[
              styles.competitorTabText,
              selectedCompetitor?.competitor_profile.name === competitor.competitor_profile.name &&
              styles.activeCompetitorTabText
            ]}>
              {competitor.competitor_profile.name}
            </ThemedText>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderOverviewTab = () => {
    if (!selectedCompetitor) return null;

    return (
      <View style={styles.tabContent}>
        {/* Competitor Profile */}
        <View style={styles.profileSection}>
          <ThemedText style={styles.sectionTitle}>Competitor Profile</ThemedText>
          <View style={styles.profileCard}>
            <View style={styles.profileHeader}>
              <ThemedText style={styles.competitorName}>
                {selectedCompetitor.competitor_profile.name}
              </ThemedText>
              <ThemedText style={styles.marketPosition}>
                {selectedCompetitor.competitor_profile.market_position}
              </ThemedText>
            </View>
            <View style={styles.profileDetails}>
              <View style={styles.profileDetail}>
                <ThemedText style={styles.detailLabel}>Industry</ThemedText>
                <ThemedText style={styles.detailValue}>
                  {selectedCompetitor.competitor_profile.industry}
                </ThemedText>
              </View>
              <View style={styles.profileDetail}>
                <ThemedText style={styles.detailLabel}>Size</ThemedText>
                <ThemedText style={styles.detailValue}>
                  {selectedCompetitor.competitor_profile.size}
                </ThemedText>
              </View>
            </View>
            <View style={styles.strengthsWeaknesses}>
              <View style={styles.traitsColumn}>
                <ThemedText style={styles.traitsTitle}>Strengths</ThemedText>
                {selectedCompetitor.competitor_profile.strengths.map((strength, index) => (
                  <ThemedText key={index} style={styles.strengthText}>• {strength}</ThemedText>
                ))}
              </View>
              <View style={styles.traitsColumn}>
                <ThemedText style={styles.traitsTitle}>Weaknesses</ThemedText>
                {selectedCompetitor.competitor_profile.weaknesses.map((weakness, index) => (
                  <ThemedText key={index} style={styles.weaknessText}>• {weakness}</ThemedText>
                ))}
              </View>
            </View>
          </View>
        </View>

        {/* Recent Developments */}
        {selectedCompetitor.market_intelligence.recent_developments.length > 0 && (
          <View style={styles.developmentsSection}>
            <ThemedText style={styles.sectionTitle}>Recent Developments</ThemedText>
            {selectedCompetitor.market_intelligence.recent_developments.map((dev, index) => (
              <View key={index} style={styles.developmentCard}>
                <View style={styles.developmentHeader}>
                  <ThemedText style={styles.developmentDate}>
                    {new Date(dev.date).toLocaleDateString()}
                  </ThemedText>
                  <ThemedText style={[
                    styles.impactLevel,
                    { color: getThreatLevelColor(dev.potential_impact.toLowerCase() as any) }
                  ]}>
                    {dev.potential_impact} Impact
                  </ThemedText>
                </View>
                <ThemedText style={styles.developmentText}>{dev.development}</ThemedText>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderAnalysisTab = () => {
    if (!selectedCompetitor) return null;

    return (
      <View style={styles.tabContent}>
        {/* Feature Comparison */}
        <View style={styles.comparisonSection}>
          <ThemedText style={styles.sectionTitle}>Feature Comparison</ThemedText>
          {selectedCompetitor.product_comparison.feature_gaps.map((gap, index) => (
            <View key={index} style={styles.featureComparison}>
              <View style={styles.featureHeader}>
                <ThemedText style={styles.featureName}>{gap.competitor_feature}</ThemedText>
                <View style={[
                  styles.advantageBadge,
                  { backgroundColor: getAdvantageColor(gap.advantage) }
                ]}>
                  <ThemedText style={styles.advantageText}>
                    {gap.advantage.toUpperCase()}
                  </ThemedText>
                </View>
              </View>
              {gap.our_feature && (
                <ThemedText style={styles.ourFeature}>Our: {gap.our_feature}</ThemedText>
              )}
              <ThemedText style={styles.importanceLevel}>
                Importance: <ThemedText style={[
                  styles.importanceText,
                  { color: gap.importance === 'high' ? '#F44336' : gap.importance === 'medium' ? '#FF9800' : '#4CAF50' }
                ]}>
                  {gap.importance.toUpperCase()}
                </ThemedText>
              </ThemedText>
            </View>
          ))}
        </View>

        {/* Pricing Comparison */}
        {selectedCompetitor.product_comparison.pricing_comparison.length > 0 && (
          <View style={styles.pricingSection}>
            <ThemedText style={styles.sectionTitle}>Pricing Comparison</ThemedText>
            {selectedCompetitor.product_comparison.pricing_comparison.map((pricing, index) => (
              <View key={index} style={styles.pricingComparison}>
                <ThemedText style={styles.planName}>{pricing.plan}</ThemedText>
                <View style={styles.priceComparison}>
                  <ThemedText style={styles.theirPrice}>
                    Their: ${pricing.their_price}
                  </ThemedText>
                  <ThemedText style={styles.ourPrice}>
                    Our: ${pricing.our_price}
                  </ThemedText>
                  <ThemedText style={[
                    styles.priceDifference,
                    { color: pricing.difference_percentage > 0 ? '#4CAF50' : '#F44336' }
                  ]}>
                    {pricing.difference_percentage > 0 ? '+' : ''}{pricing.difference_percentage.toFixed(1)}%
                  </ThemedText>
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderPositioningTab = () => {
    if (!selectedCompetitor) return null;

    return (
      <View style={styles.tabContent}>
        {/* Market Positioning */}
        <View style={styles.positioningSection}>
          <ThemedText style={styles.sectionTitle}>Market Positioning</ThemedText>
          <View style={styles.positioningComparison}>
            <View style={styles.positioningColumn}>
              <ThemedText style={styles.positioningTitle}>Their Positioning</ThemedText>
              <ThemedText style={styles.positioningText}>
                {selectedCompetitor.product_comparison.market_positioning.their_positioning}
              </ThemedText>
            </View>
            <View style={styles.positioningColumn}>
              <ThemedText style={styles.positioningTitle}>Our Positioning</ThemedText>
              <ThemedText style={styles.positioningText}>
                {selectedCompetitor.product_comparison.market_positioning.our_positioning}
              </ThemedText>
            </View>
          </View>

          {selectedCompetitor.product_comparison.market_positioning.differentiation_opportunities.length > 0 && (
            <View style={styles.opportunitiesList}>
              <ThemedText style={styles.opportunitiesTitle}>Differentiation Opportunities</ThemedText>
              {selectedCompetitor.product_comparison.market_positioning.differentiation_opportunities.map((opportunity, index) => (
                <ThemedText key={index} style={styles.opportunityItem}>• {opportunity}</ThemedText>
              ))}
            </View>
          )}
        </View>

        {/* Strategic Moves */}
        {selectedCompetitor.market_intelligence.strategic_moves.length > 0 && (
          <View style={styles.strategicSection}>
            <ThemedText style={styles.sectionTitle}>Strategic Moves</ThemedText>
            {selectedCompetitor.market_intelligence.strategic_moves.map((move, index) => (
              <View key={index} style={styles.strategicMove}>
                <View style={styles.moveHeader}>
                  <ThemedText style={styles.moveType}>{move.move_type}</ThemedText>
                  <ThemedText style={[
                    styles.threatLevel,
                    { color: getThreatLevelColor(move.threat_level) }
                  ]}>
                    {move.threat_level.toUpperCase()}
                  </ThemedText>
                </View>
                <ThemedText style={styles.moveDescription}>{move.description}</ThemedText>
                <ThemedText style={styles.moveTimeline}>Timeline: {move.timeline}</ThemedText>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderOpportunitiesTab = () => {
    if (!selectedCompetitor) return null;

    return (
      <View style={styles.tabContent}>
        {/* Opportunities */}
        <View style={styles.opportunitiesSection}>
          <ThemedText style={styles.sectionTitle}>Strategic Opportunities</ThemedText>
          {selectedCompetitor.opportunities.map((opportunity, index) => (
            <View key={index} style={styles.opportunityCard}>
              <View style={styles.opportunityHeader}>
                <ThemedText style={styles.opportunityTitle}>{opportunity.opportunity}</ThemedText>
                <View style={[
                  styles.typeBadge,
                  { backgroundColor: getOpportunityTypeColor(opportunity.type) }
                ]}>
                  <ThemedText style={styles.typeText}>
                    {opportunity.type.toUpperCase()}
                  </ThemedText>
                </View>
              </View>
              <View style={styles.opportunityMetrics}>
                <ThemedText style={styles.opportunityImpact}>
                  Impact: <ThemedText style={[
                    styles.impactValue,
                    { color: getThreatLevelColor(opportunity.potential_impact) }
                  ]}>
                    {opportunity.potential_impact.toUpperCase()}
                  </ThemedText>
                </ThemedText>
                <ThemedText style={styles.opportunityEffort}>
                  Effort: {opportunity.effort_required}
                </ThemedText>
                <ThemedText style={styles.opportunityTimeframe}>
                  Timeline: {opportunity.timeline}
                </ThemedText>
              </View>
            </View>
          ))}
        </View>

        {/* Strategic Recommendations */}
        {selectedCompetitor.strategic_recommendations.length > 0 && (
          <View style={styles.recommendationsSection}>
            <ThemedText style={styles.sectionTitle}>Strategic Recommendations</ThemedText>
            {selectedCompetitor.strategic_recommendations.map((rec, index) => (
              <View key={index} style={styles.recommendationCard}>
                <ThemedText style={styles.recommendation}>{rec.recommendation}</ThemedText>
                <ThemedText style={styles.rationale}>Rationale: {rec.rationale}</ThemedText>
                <View style={styles.recommendationFooter}>
                  <ThemedText style={styles.expectedOutcome}>
                    Expected: {rec.expected_outcome}
                  </ThemedText>
                  <View style={[
                    styles.priorityBadge,
                    { backgroundColor: getThreatLevelColor(rec.priority) }
                  ]}>
                    <ThemedText style={styles.priorityText}>
                      {rec.priority.toUpperCase()}
                    </ThemedText>
                  </View>
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  if (loading && competitors.length === 0) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading competitive intelligence...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && competitors.length === 0) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading competitive intelligence</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={loadCompetitorAnalysis}>
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
        <ThemedText type="title" style={styles.title}>Competitive Intelligence</ThemedText>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={[styles.actionButton, monitoring && styles.disabledButton]}
            onPress={startMonitoring}
            disabled={monitoring}
          >
            <ThemedText style={styles.actionButtonText}>
              {monitoring ? 'Monitoring...' : 'Start Monitoring'}
            </ThemedText>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton} onPress={getMarketPositioning}>
            <ThemedText style={styles.actionButtonText}>Update Positioning</ThemedText>
          </TouchableOpacity>
        </View>
      </View>

      {/* New Competitor Analysis */}
      <View style={styles.newCompetitorSection}>
        <ThemedText style={styles.sectionTitle}>Analyze New Competitor</ThemedText>
        <View style={styles.newCompetitorForm}>
          <TextInput
            style={styles.competitorInput}
            value={newCompetitorName}
            onChangeText={setNewCompetitorName}
            placeholder="Enter competitor name"
            placeholderTextColor="#666"
          />
          <TouchableOpacity
            style={[styles.analyzeButton, analyzing && styles.disabledButton]}
            onPress={analyzeNewCompetitor}
            disabled={analyzing}
          >
            <ThemedText style={styles.analyzeButtonText}>
              {analyzing ? 'Analyzing...' : 'Analyze'}
            </ThemedText>
          </TouchableOpacity>
        </View>
      </View>

      {/* Competitor Selector */}
      {competitors.length > 0 && renderCompetitorSelector()}

      {/* Tab Navigation */}
      {selectedCompetitor && (
        <View style={styles.tabContainer}>
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'analysis', label: 'Analysis' },
            { key: 'positioning', label: 'Positioning' },
            { key: 'opportunities', label: 'Opportunities' },
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
      )}

      {/* Content */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {selectedCompetitor && (
          <>
            {activeTab === 'overview' && renderOverviewTab()}
            {activeTab === 'analysis' && renderAnalysisTab()}
            {activeTab === 'positioning' && renderPositioningTab()}
            {activeTab === 'opportunities' && renderOpportunitiesTab()}
          </>
        )}
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 15,
  },
  title: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
  },
  headerActions: {
    flexDirection: 'row',
    gap: 10,
  },
  actionButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    backgroundColor: '#45A29E',
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
  newCompetitorSection: {
    paddingHorizontal: 20,
    paddingBottom: 15,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
  },
  newCompetitorForm: {
    flexDirection: 'row',
    gap: 10,
  },
  competitorInput: {
    flex: 1,
    backgroundColor: '#1F2833',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 8,
    color: '#C5C6C7',
    fontSize: 16,
    padding: 15,
  },
  analyzeButton: {
    backgroundColor: '#66FCF1',
    paddingHorizontal: 20,
    borderRadius: 8,
    justifyContent: 'center',
  },
  analyzeButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  competitorSelector: {
    backgroundColor: '#1F2833',
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  competitorTab: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 6,
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  activeCompetitorTab: {
    backgroundColor: '#66FCF1',
  },
  competitorTabText: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
  },
  activeCompetitorTabText: {
    color: '#0B0C10',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 20,
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
  profileSection: {
    marginBottom: 30,
  },
  profileCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
  },
  profileHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  competitorName: {
    color: '#66FCF1',
    fontSize: 20,
    fontWeight: '600',
  },
  marketPosition: {
    color: '#C5C6C7',
    fontSize: 14,
    opacity: 0.8,
  },
  profileDetails: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  profileDetail: {
    alignItems: 'center',
  },
  detailLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 5,
  },
  detailValue: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
  },
  strengthsWeaknesses: {
    flexDirection: 'row',
    gap: 20,
  },
  traitsColumn: {
    flex: 1,
  },
  traitsTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  strengthText: {
    color: '#4CAF50',
    fontSize: 13,
    marginBottom: 4,
  },
  weaknessText: {
    color: '#F44336',
    fontSize: 13,
    marginBottom: 4,
  },
  developmentsSection: {
    marginBottom: 30,
  },
  developmentCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  developmentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  developmentDate: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  impactLevel: {
    fontSize: 12,
    fontWeight: '600',
  },
  developmentText: {
    color: '#C5C6C7',
    fontSize: 14,
    lineHeight: 20,
  },
  comparisonSection: {
    marginBottom: 30,
  },
  featureComparison: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  featureHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  featureName: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  advantageBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  advantageText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  ourFeature: {
    color: '#66FCF1',
    fontSize: 12,
    marginBottom: 4,
    fontStyle: 'italic',
  },
  importanceLevel: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  importanceText: {
    fontWeight: '600',
  },
  pricingSection: {
    marginBottom: 30,
  },
  pricingComparison: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  planName: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  priceComparison: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 15,
  },
  theirPrice: {
    color: '#F44336',
    fontSize: 14,
    fontWeight: '600',
  },
  ourPrice: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: '600',
  },
  priceDifference: {
    fontSize: 12,
    fontWeight: '600',
  },
  positioningSection: {
    marginBottom: 30,
  },
  positioningComparison: {
    flexDirection: 'row',
    gap: 15,
    marginBottom: 20,
  },
  positioningColumn: {
    flex: 1,
  },
  positioningTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  positioningText: {
    color: '#C5C6C7',
    fontSize: 13,
    lineHeight: 18,
  },
  opportunitiesList: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
  },
  opportunitiesTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
  },
  opportunityItem: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 4,
  },
  strategicSection: {
    marginBottom: 30,
  },
  strategicMove: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  moveHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  moveType: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
  },
  threatLevel: {
    fontSize: 12,
    fontWeight: '600',
  },
  moveDescription: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 5,
  },
  moveTimeline: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  opportunitiesSection: {
    marginBottom: 30,
  },
  opportunityCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  opportunityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  opportunityTitle: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
    marginRight: 10,
  },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  typeText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  opportunityMetrics: {
    gap: 4,
  },
  opportunityImpact: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  impactValue: {
    fontWeight: '600',
  },
  opportunityEffort: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  opportunityTimeframe: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  recommendationsSection: {
    marginBottom: 30,
  },
  recommendationCard: {
    backgroundColor: '#1F2833',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 15,
    marginBottom: 10,
  },
  recommendation: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  rationale: {
    color: '#C5C6C7',
    fontSize: 13,
    marginBottom: 10,
  },
  recommendationFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  expectedOutcome: {
    color: '#C5C6C7',
    fontSize: 12,
    flex: 1,
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
});