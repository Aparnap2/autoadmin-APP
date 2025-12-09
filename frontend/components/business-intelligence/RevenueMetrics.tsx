/**
 * Revenue Metrics Component
 * Comprehensive revenue intelligence dashboard with forecasting, churn analysis,
 * and customer metrics visualization
 */

import React, { useState, useEffect, useMemo } from 'react';
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
import { RevenueMetrics as RevenueMetricsType } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface RevenueMetricsProps {
  data?: RevenueMetricsType;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const { width: screenWidth } = Dimensions.get('window');

export function RevenueMetrics({
  data: initialData,
  autoRefresh = false,
  refreshInterval = 300000, // 5 minutes
}: RevenueMetricsProps) {
  const [revenueData, setRevenueData] = useState<RevenueMetricsType | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedView, setSelectedView] = useState<'overview' | 'forecast' | 'churn' | 'customers' | 'pricing'>('overview');
  const [forecastPeriods, setForecastPeriods] = useState(12);

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    if (autoRefresh && !initialData) {
      loadRevenueMetrics();
    }
  }, [autoRefresh, initialData]);

  useEffect(() => {
    setRevenueData(initialData || null);
  }, [initialData]);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadRevenueMetrics, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  useEffect(() => {
    // Subscribe to revenue updates
    biService.addListener('revenue_update', (data) => {
      setRevenueData(data);
    });
  }, [biService]);

  const loadRevenueMetrics = async (params?: any) => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getRevenueIntelligence({
        forecast_periods: forecastPeriods,
        include_churn_analysis: true,
        ...params
      });

      if (response.success && response.data) {
        setRevenueData(response.data);
      } else {
        throw new Error(response.error || 'Failed to load revenue metrics');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const generateForecast = async () => {
    try {
      setLoading(true);
      await biService.generateRevenueForecast(forecastPeriods);
      await loadRevenueMetrics();
      Alert.alert('Success', 'Revenue forecast generated successfully');
    } catch (err) {
      Alert.alert('Error', 'Failed to generate revenue forecast');
    } finally {
      setLoading(false);
    }
  };

  const analyzeChurn = async () => {
    try {
      setLoading(true);
      await biService.analyzeChurnRisk();
      Alert.alert('Success', 'Churn analysis completed');
    } catch (err) {
      Alert.alert('Error', 'Failed to analyze churn risk');
    } finally {
      setLoading(false);
    }
  };

  const optimizePricing = async () => {
    try {
      setLoading(true);
      await biService.optimizePricing();
      Alert.alert('Success', 'Pricing optimization completed');
      await loadRevenueMetrics();
    } catch (err) {
      Alert.alert('Error', 'Failed to optimize pricing');
    } finally {
      setLoading(false);
    }
  };

  // Chart data transformations
  const revenueForecastData = useMemo(() => {
    if (!revenueData?.revenue_forecast) return null;

    return {
      labels: revenueData.revenue_forecast.map(f =>
        new Date(f.period).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      ),
      datasets: [
        {
          data: revenueData.revenue_forecast.map(f => f.forecasted / 1000),
          color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
          strokeWidth: 3,
        },
        ...(revenueData.revenue_forecast.some(f => f.actual) ? [{
          data: revenueData.revenue_forecast.map(f => (f.actual || 0) / 1000),
          color: (opacity = 1) => `rgba(69, 162, 158, ${opacity})`,
          strokeWidth: 2,
        }] : [])
      ],
    };
  }, [revenueData]);

  const revenueBreakdownData = useMemo(() => {
    if (!revenueData?.revenue_breakdown?.by_plan) return null;

    return revenueData.revenue_breakdown.by_plan.map(item => ({
      name: item.plan,
      population: item.percentage,
      color: ['#66FCF1', '#45A29E', '#1F2833', '#C5C6C7'][Math.floor(Math.random() * 4)],
      legendFontColor: '#C5C6C7',
      legendFontSize: 11,
    }));
  }, [revenueData]);

  const cohortRevenueData = useMemo(() => {
    if (!revenueData?.revenue_breakdown?.by_cohort) return null;

    return {
      labels: revenueData.revenue_breakdown.by_cohort.map(c => c.cohort),
      datasets: [{
        data: revenueData.revenue_breakdown.by_cohort.map(c => c.revenue / 1000),
      }],
    };
  }, [revenueData]);

  const getGrowthRateColor = (rate: number) => {
    if (rate >= 10) return '#4CAF50';
    if (rate >= 0) return '#FF9800';
    return '#F44336';
  };

  const getChurnRateColor = (rate: number) => {
    if (rate <= 3) return '#4CAF50';
    if (rate <= 7) return '#FF9800';
    return '#F44336';
  };

  const renderOverviewTab = () => {
    if (!revenueData) return null;

    return (
      <View style={styles.tabContent}>
        {/* Key Metrics Grid */}
        <View style={styles.metricsGrid}>
          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Monthly Recurring Revenue</ThemedText>
            <ThemedText style={styles.metricValue}>
              ${(revenueData.current_mrr / 1000).toFixed(1)}K
            </ThemedText>
            <ThemedText style={[
              styles.metricChange,
              { color: getGrowthRateColor(revenueData.mrr_growth.rate) }
            ]}>
              {revenueData.mrr_growth.rate >= 0 ? '+' : ''}{revenueData.mrr_growth.rate.toFixed(1)}%
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Annual Recurring Revenue</ThemedText>
            <ThemedText style={styles.metricValue}>
              ${(revenueData.arr / 1000).toFixed(0)}K
            </ThemedText>
            <ThemedText style={[
              styles.metricChange,
              { color: getGrowthRateColor(revenueData.arr_growth.rate) }
            ]}>
              {revenueData.arr_growth.rate >= 0 ? '+' : ''}{revenueData.arr_growth.rate.toFixed(1)}%
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>Customer Acquisition Cost</ThemedText>
            <ThemedText style={styles.metricValue}>
              ${revenueData.customer_metrics.cac.toFixed(0)}
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              LTV: ${(revenueData.customer_metrics.ltv / 1000).toFixed(1)}K
            </ThemedText>
          </View>

          <View style={styles.metricCard}>
            <ThemedText style={styles.metricLabel}>LTV:CAC Ratio</ThemedText>
            <ThemedText style={styles.metricValue}>
              {revenueData.customer_metrics.ltv_cac_ratio.toFixed(1)}x
            </ThemedText>
            <ThemedText style={styles.metricSubtitle}>
              Payback: {revenueData.customer_metrics.payback_period}mo
            </ThemedText>
          </View>
        </View>

        {/* Revenue Breakdown Chart */}
        {revenueBreakdownData && (
          <View style={styles.chartSection}>
            <ThemedText style={styles.chartTitle}>Revenue by Plan</ThemedText>
            <PieChart
              data={revenueBreakdownData}
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

        {/* Cohort Analysis */}
        {cohortRevenueData && (
          <View style={styles.chartSection}>
            <ThemedText style={styles.chartTitle}>Revenue by Cohort</ThemedText>
            <BarChart
              data={cohortRevenueData}
              width={screenWidth - 60}
              height={220}
              chartConfig={{
                backgroundColor: '#1F2833',
                backgroundGradientFrom: '#1F2833',
                backgroundGradientTo: '#1F2833',
                decimalPlaces: 1,
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
      </View>
    );
  };

  const renderForecastTab = () => {
    if (!revenueData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.sectionHeader}>
          <ThemedText style={styles.sectionTitle}>Revenue Forecast</ThemedText>
          <View style={styles.forecastControls}>
            <TouchableOpacity
              style={styles.periodButton}
              onPress={() => {
                setForecastPeriods(6);
                loadRevenueMetrics();
              }}
            >
              <ThemedText style={[
                styles.periodButtonText,
                forecastPeriods === 6 && styles.activePeriodButton
              ]}>
                6mo
              </ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.periodButton}
              onPress={() => {
                setForecastPeriods(12);
                loadRevenueMetrics();
              }}
            >
              <ThemedText style={[
                styles.periodButtonText,
                forecastPeriods === 12 && styles.activePeriodButton
              ]}>
                12mo
              </ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.periodButton}
              onPress={() => {
                setForecastPeriods(24);
                loadRevenueMetrics();
              }}
            >
              <ThemedText style={[
                styles.periodButtonText,
                forecastPeriods === 24 && styles.activePeriodButton
              ]}>
                24mo
              </ThemedText>
            </TouchableOpacity>
          </View>
        </View>

        {revenueForecastData && (
          <LineChart
            data={revenueForecastData}
            width={screenWidth - 40}
            height={300}
            chartConfig={{
              backgroundColor: '#1F2833',
              backgroundGradientFrom: '#1F2833',
              backgroundGradientTo: '#0B0C10',
              decimalPlaces: 1,
              color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(197, 198, 199, ${opacity})`,
              style: {
                borderRadius: 16,
              },
              propsForDots: {
                r: "4",
                strokeWidth: "2",
                stroke: "#66FCF1"
              },
              propsForBackgroundLines: {
                strokeDasharray: "", // no background lines
              },
            }}
            bezier
            style={styles.chart}
          />
        )}

        <View style={styles.forecastStats}>
          <View style={styles.forecastStat}>
            <ThemedText style={styles.forecastStatLabel}>Avg. Confidence</ThemedText>
            <ThemedText style={styles.forecastStatValue}>
              {(
                revenueData.revenue_forecast.reduce((acc, f) => acc + f.confidence, 0) /
                revenueData.revenue_forecast.length * 100
              ).toFixed(0)}%
            </ThemedText>
          </View>
          <View style={styles.forecastStat}>
            <ThemedText style={styles.forecastStatLabel}>Projected ARR</ThemedText>
            <ThemedText style={styles.forecastStatValue}>
              ${(revenueData.revenue_forecast[revenueData.revenue_forecast.length - 1]?.forecasted * 12 / 1000).toFixed(0)}K
            </ThemedText>
          </View>
        </View>

        <TouchableOpacity style={styles.actionButton} onPress={generateForecast}>
          <ThemedText style={styles.actionButtonText}>Generate New Forecast</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  const renderChurnTab = () => {
    if (!revenueData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.churnMetrics}>
          <View style={styles.churnCard}>
            <ThemedText style={styles.churnTitle}>Monthly Churn Rate</ThemedText>
            <ThemedText style={[
              styles.churnValue,
              { color: getChurnRateColor(revenueData.churn_analysis.monthly_rate) }
            ]}>
              {revenueData.churn_analysis.monthly_rate.toFixed(1)}%
            </ThemedText>
            <ThemedText style={styles.churnSubtitle}>
              Annual: {revenueData.churn_analysis.annual_rate.toFixed(1)}%
            </ThemedText>
          </View>

          <View style={styles.churnCard}>
            <ThemedText style={styles.churnTitle}>Revenue Impact</ThemedText>
            <ThemedText style={styles.churnValue}>
              -${(revenueData.churn_analysis.revenue_impact / 1000).toFixed(1)}K
            </ThemedText>
            <ThemedText style={styles.churnSubtitle}>
              Risk Customers: {revenueData.churn_analysis.risk_customers}
            </ThemedText>
          </View>
        </View>

        <View style={styles.churnAnalysis}>
          <ThemedText style={styles.analysisTitle}>Churn Analysis</ThemedText>
          <ThemedText style={styles.analysisText}>
            Current churn rate is {revenueData.churn_analysis.monthly_rate.toFixed(1)}% monthly,
            which is {revenueData.churn_analysis.monthly_rate <= 3 ? 'within healthy range' : 'above industry average'}.
            Estimated monthly revenue impact is ${(revenueData.churn_analysis.revenue_impact / 1000).toFixed(1)}K.
          </ThemedText>
        </View>

        <TouchableOpacity style={styles.actionButton} onPress={analyzeChurn}>
          <ThemedText style={styles.actionButtonText}>Analyze Churn Risk</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  const renderCustomersTab = () => {
    if (!revenueData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.customerMetrics}>
          <View style={styles.customerCard}>
            <ThemedText style={styles.customerTitle}>Lifetime Value</ThemedText>
            <ThemedText style={styles.customerValue}>
              ${(revenueData.customer_metrics.ltv / 1000).toFixed(1)}K
            </ThemedText>
            <ThemedText style={styles.customerSubtitle}>
              CAC: ${revenueData.customer_metrics.cac.toFixed(0)}
            </ThemedText>
          </View>

          <View style={styles.customerCard}>
            <ThemedText style={styles.customerTitle}>LTV:CAC Ratio</ThemedText>
            <ThemedText style={styles.customerValue}>
              {revenueData.customer_metrics.ltv_cac_ratio.toFixed(1)}x
            </ThemedText>
            <ThemedText style={styles.customerSubtitle}>
              Payback: {revenueData.customer_metrics.payback_period} months
            </ThemedText>
          </View>
        </View>

        <View style={styles.customerAnalysis}>
          <ThemedText style={styles.analysisTitle}>Unit Economics Analysis</ThemedText>
          <ThemedText style={styles.analysisText}>
            Current LTV:CAC ratio of {revenueData.customer_metrics.ltv_cac_ratio.toFixed(1)}x is
            {revenueData.customer_metrics.ltv_cac_ratio >= 3 ? ' healthy and sustainable' : ' below optimal range (3x)'}.
            Customer payback period is {revenueData.customer_metrics.payback_period} months.
          </ThemedText>
        </View>

        {/* Regional Revenue Breakdown */}
        {revenueData.revenue_breakdown?.by_region && (
          <View style={styles.regionalSection}>
            <ThemedText style={styles.sectionTitle}>Revenue by Region</ThemedText>
            {revenueData.revenue_breakdown.by_region.map((region, index) => (
              <View key={index} style={styles.regionItem}>
                <ThemedText style={styles.regionName}>{region.region}</ThemedText>
                <View style={styles.regionMetrics}>
                  <ThemedText style={styles.regionRevenue}>
                    ${(region.revenue / 1000).toFixed(1)}K
                  </ThemedText>
                  <ThemedText style={[
                    styles.regionGrowth,
                    { color: getGrowthRateColor(region.growth) }
                  ]}>
                    {region.growth >= 0 ? '+' : ''}{region.growth.toFixed(1)}%
                  </ThemedText>
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderPricingTab = () => {
    if (!revenueData) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.pricingMetrics}>
          <View style={styles.pricingCard}>
            <ThemedText style={styles.pricingTitle}>Optimal ARPU</ThemedText>
            <ThemedText style={styles.pricingValue}>
              ${revenueData.pricing_analysis.optimal_arpu.toFixed(0)}
            </ThemedText>
            <ThemedText style={styles.pricingSubtitle}>
              Sensitivity: {(revenueData.pricing_analysis.price_sensitivity * 100).toFixed(0)}%
            </ThemedText>
          </View>
        </View>

        {revenueData.pricing_analysis.recommended_changes.length > 0 && (
          <View style={styles.pricingRecommendations}>
            <ThemedText style={styles.sectionTitle}>Pricing Recommendations</ThemedText>
            {revenueData.pricing_analysis.recommended_changes.map((change, index) => (
              <View key={index} style={styles.pricingRecommendation}>
                <View style={styles.recommendationHeader}>
                  <ThemedText style={styles.planName}>{change.plan}</ThemedText>
                  <View style={styles.priceChange}>
                    <ThemedText style={styles.currentPrice}>
                      ${change.current_price}
                    </ThemedText>
                    <ThemedText style={styles.arrow}>→</ThemedText>
                    <ThemedText style={styles.recommendedPrice}>
                      ${change.recommended_price}
                    </ThemedText>
                  </View>
                </View>
                <ThemedText style={styles.expectedImpact}>
                  Expected Impact: {(change.expected_impact * 100).toFixed(0)}% revenue change
                </ThemedText>
              </View>
            ))}
          </View>
        )}

        <TouchableOpacity style={styles.actionButton} onPress={optimizePricing}>
          <ThemedText style={styles.actionButtonText}>Run Pricing Optimization</ThemedText>
        </TouchableOpacity>
      </View>
    );
  };

  if (loading && !revenueData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading revenue metrics...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !revenueData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading revenue metrics</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={() => loadRevenueMetrics()}>
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
          { key: 'forecast', label: 'Forecast' },
          { key: 'churn', label: 'Churn' },
          { key: 'customers', label: 'Customers' },
          { key: 'pricing', label: 'Pricing' },
        ].map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              selectedView === tab.key && styles.activeTab
            ]}
            onPress={() => setSelectedView(tab.key as any)}
          >
            <ThemedText style={[
              styles.tabText,
              selectedView === tab.key && styles.activeTabText
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
        {selectedView === 'overview' && renderOverviewTab()}
        {selectedView === 'forecast' && renderForecastTab()}
        {selectedView === 'churn' && renderChurnTab()}
        {selectedView === 'customers' && renderCustomersTab()}
        {selectedView === 'pricing' && renderPricingTab()}
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
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 10,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
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
  metricChange: {
    fontSize: 14,
    fontWeight: '600',
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
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
  },
  forecastControls: {
    flexDirection: 'row',
    gap: 8,
  },
  periodButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#1F2833',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  periodButtonText: {
    color: '#C5C6C7',
    fontSize: 12,
    fontWeight: '500',
  },
  activePeriodButton: {
    color: '#66FCF1',
  },
  forecastStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginVertical: 20,
  },
  forecastStat: {
    alignItems: 'center',
  },
  forecastStatLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    marginBottom: 5,
  },
  forecastStatValue: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '700',
  },
  churnMetrics: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  churnCard: {
    flex: 1,
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  churnTitle: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  churnValue: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 4,
  },
  churnSubtitle: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  churnAnalysis: {
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 20,
  },
  customerMetrics: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  customerCard: {
    flex: 1,
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  customerTitle: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  customerValue: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  customerSubtitle: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  customerAnalysis: {
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 20,
  },
  analysisTitle: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
  },
  analysisText: {
    color: '#C5C6C7',
    fontSize: 14,
    lineHeight: 20,
  },
  regionalSection: {
    marginBottom: 20,
  },
  regionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 8,
  },
  regionName: {
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
  },
  regionMetrics: {
    flexDirection: 'row',
    gap: 15,
    alignItems: 'center',
  },
  regionRevenue: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
  },
  regionGrowth: {
    fontSize: 12,
    fontWeight: '600',
  },
  pricingMetrics: {
    marginBottom: 20,
  },
  pricingCard: {
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  pricingTitle: {
    color: '#C5C6C7',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  pricingValue: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  pricingSubtitle: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  pricingRecommendations: {
    marginBottom: 20,
  },
  pricingRecommendation: {
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  recommendationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  planName: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
  },
  priceChange: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  currentPrice: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  arrow: {
    color: '#45A29E',
    fontSize: 14,
  },
  recommendedPrice: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: '600',
  },
  expectedImpact: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  actionButton: {
    backgroundColor: '#66FCF1',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
});