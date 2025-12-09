/**
 * KPI Dashboard Component
 * Comprehensive KPI monitoring dashboard with real-time updates,
 * trend analysis, and alert threshold management
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
import { LineChart, BarChart, ProgressChart } from 'react-native-chart-kit';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { KPIMetrics as KPIMetricsType } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface KPIDashboardProps {
  data?: KPIMetricsType;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onKPIUpdate?: (kpiId: string, value: number) => void;
}

const { width: screenWidth } = Dimensions.get('window');

export function KPIDashboard({
  data: initialData,
  autoRefresh = false,
  refreshInterval = 60000, // 1 minute for real-time updates
  onKPIUpdate,
}: KPIDashboardProps) {
  const [kpiData, setKPIData] = useState<KPIMetricsType | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedKPIs, setExpandedKPIs] = useState<Set<string>>(new Set());

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    if (autoRefresh && !initialData) {
      loadKPIMetrics();
    }
  }, [autoRefresh, initialData]);

  useEffect(() => {
    setKPIData(initialData || null);
  }, [initialData]);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadKPIMetrics, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  useEffect(() => {
    // Subscribe to KPI updates
    biService.addListener('kpi_update', (data) => {
      setKPIData(data);
    });

    biService.addListener('kpi_realtime_update', (data) => {
      // Handle individual KPI updates
      if (data.kpi_id && data.current_value !== undefined) {
        setKPIData(prev => {
          if (!prev) return prev;

          const updatedData = { ...prev };

          // Update the specific KPI value
          Object.keys(updatedData.kpi_categories).forEach(category => {
            const kpiIndex = updatedData.kpi_categories[category].kpis.findIndex(
              kpi => kpi.id === data.kpi_id
            );
            if (kpiIndex !== -1) {
              updatedData.kpi_categories[category].kpis[kpiIndex].current_value = data.current_value;
              updatedData.kpi_categories[category].kpis[kpiIndex].last_updated = data.timestamp;
            }
          });

          // Add to real-time updates
          if (updatedData.real_time_updates) {
            updatedData.real_time_updates.unshift({
              kpi_id: data.kpi_id,
              previous_value: data.previous_value,
              current_value: data.current_value,
              change_percentage: data.change_percentage,
              timestamp: data.timestamp,
            });
            // Keep only last 50 updates
            updatedData.real_time_updates = updatedData.real_time_updates.slice(0, 50);
          }

          return updatedData;
        });

        onKPIUpdate?.(data.kpi_id, data.current_value);
      }
    });
  }, [biService, onKPIUpdate]);

  const loadKPIMetrics = async (params?: any) => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getKPIs({
        include_trends: true,
        ...params
      });

      if (response.success && response.data) {
        setKPIData(response.data);
      } else {
        throw new Error(response.error || 'Failed to load KPI metrics');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateKPIValue = async (kpiId: string, value: number) => {
    try {
      await biService.updateKPI(kpiId, value);
      Alert.alert('Success', 'KPI value updated successfully');
      await loadKPIMetrics();
    } catch (err) {
      Alert.alert('Error', 'Failed to update KPI value');
    }
  };

  const getKPIForecast = async (kpiId: string, periods: number = 12) => {
    try {
      const response = await biService.getKPIForecast(kpiId, periods);
      if (response.success) {
        Alert.alert('Forecast Generated', `12-month forecast generated for KPI`);
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to generate KPI forecast');
    }
  };

  const calculateKPI = async (kpiId: string, params?: Record<string, any>) => {
    try {
      setLoading(true);
      const response = await biService.calculateKPI(kpiId, params);
      if (response.success) {
        Alert.alert('Success', 'KPI calculation completed');
        await loadKPIMetrics();
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to calculate KPI');
    } finally {
      setLoading(false);
    }
  };

  const toggleKPIExpansion = (kpiId: string) => {
    setExpandedKPIs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(kpiId)) {
        newSet.delete(kpiId);
      } else {
        newSet.add(kpiId);
      }
      return newSet;
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'critical': return '#F44336';
      default: return '#C5C6C7';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return '📈';
      case 'declining': return '📉';
      case 'stable': return '➡️';
      case 'volatile': return '📊';
      default: return '❓';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return '#4CAF50';
      case 'declining': return '#F44336';
      case 'stable': return '#FF9800';
      case 'volatile': return '#9C27B0';
      default: return '#C5C6C7';
    }
  };

  // Prepare chart data
  const overallHealthData = useMemo(() => {
    if (!kpiData) return null;

    const { overall_health } = kpiData;
    return {
      labels: ['Healthy', 'At Risk', 'Critical'],
      data: [
        overall_health.healthy_kpis / overall_health.total_kpis,
        overall_health.at_risk_kpis / overall_health.total_kpis,
        overall_health.critical_kpis / overall_health.total_kpis,
      ],
      colors: ['#4CAF50', '#FF9800', '#F44336'],
    };
  }, [kpiData]);

  const categoryHealthData = useMemo(() => {
    if (!kpiData) return null;

    return {
      labels: kpiData.kpi_categories.map(cat => cat.category),
      datasets: [{
        data: kpiData.kpi_categories.map(cat => cat.category_health_score / 100),
      }],
    };
  }, [kpiData]);

  const renderKPICard = (kpi: any, category: string) => {
    const isExpanded = expandedKPIs.has(kpi.id);
    const progressPercentage = (kpi.current_value / kpi.target_value) * 100;

    return (
      <View key={kpi.id} style={[
        styles.kpiCard,
        { borderLeftColor: getStatusColor(kpi.status) }
      ]}>
        <TouchableOpacity
          style={styles.kpiHeader}
          onPress={() => toggleKPIExpansion(kpi.id)}
        >
          <View style={styles.kpiInfo}>
            <ThemedText style={styles.kpiName}>{kpi.name}</ThemedText>
            <ThemedText style={styles.kpiDescription}>{kpi.description}</ThemedText>
          </View>
          <View style={styles.kpiStatus}>
            <ThemedText style={styles.kpiValue}>
              {kpi.current_value}{kpi.unit}
            </ThemedText>
            <ThemedText style={styles.kpiTarget}>
              / {kpi.target_value}{kpi.unit}
            </ThemedText>
            <ThemedText style={styles.kpiTrendIcon}>
              {getTrendIcon(kpi.trend)}
            </ThemedText>
          </View>
        </TouchableOpacity>

        {/* Progress Bar */}
        <View style={styles.progressBar}>
          <View style={[
            styles.progressFill,
            {
              width: `${Math.min(progressPercentage, 100)}%`,
              backgroundColor: getStatusColor(kpi.status)
            }
          ]} />
        </View>

        {isExpanded && (
          <View style={styles.kpiDetails}>
            <View style={styles.kpiMetrics}>
              <View style={styles.kpiMetric}>
                <ThemedText style={styles.kpiMetricLabel}>Status</ThemedText>
                <ThemedText style={[styles.kpiMetricValue, { color: getStatusColor(kpi.status) }]}>
                  {kpi.status.toUpperCase()}
                </ThemedText>
              </View>
              <View style={styles.kpiMetric}>
                <ThemedText style={styles.kpiMetricLabel}>Trend</ThemedText>
                <ThemedText style={[styles.kpiMetricValue, { color: getTrendColor(kpi.trend) }]}>
                  {kpi.trend.replace('_', ' ').toUpperCase()}
                </ThemedText>
              </View>
              <View style={styles.kpiMetric}>
                <ThemedText style={styles.kpiMetricLabel}>Progress</ThemedText>
                <ThemedText style={styles.kpiMetricValue}>
                  {progressPercentage.toFixed(1)}%
                </ThemedText>
              </View>
            </View>

            <View style={styles.kpiActions}>
              <TouchableOpacity
                style={styles.kpiActionButton}
                onPress={() => calculateKPI(kpi.id)}
              >
                <ThemedText style={styles.kpiActionText}>Recalculate</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.kpiActionButton}
                onPress={() => getKPIForecast(kpi.id)}
              >
                <ThemedText style={styles.kpiActionText}>Forecast</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.kpiActionButton}
                onPress={() => {
                  Alert.prompt(
                    'Update KPI Value',
                    `Enter new value for ${kpi.name}`,
                    [
                      { text: 'Cancel', style: 'cancel' },
                      {
                        text: 'Update',
                        onPress: (value) => {
                          if (value && !isNaN(Number(value))) {
                            updateKPIValue(kpi.id, Number(value));
                          }
                        }
                      }
                    ],
                    'plain-text',
                    kpi.current_value.toString()
                  );
                }}
              >
                <ThemedText style={styles.kpiActionText}>Update</ThemedText>
              </TouchableOpacity>
            </View>

            <ThemedText style={styles.kpiLastUpdated}>
              Last updated: {new Date(kpi.last_updated).toLocaleString()}
            </ThemedText>
          </View>
        )}
      </View>
    );
  };

  const renderCategorySection = (category: any) => {
    const isCategoryExpanded = selectedCategory === category.category;
    const healthPercentage = category.category_health_score;

    return (
      <View key={category.category} style={styles.categorySection}>
        <TouchableOpacity
          style={styles.categoryHeader}
          onPress={() => setSelectedCategory(isCategoryExpanded ? null : category.category)}
        >
          <View style={styles.categoryInfo}>
            <ThemedText style={styles.categoryName}>{category.category}</ThemedText>
            <ThemedText style={styles.categoryStats}>
              {category.kpis.length} KPIs • {healthPercentage.toFixed(0)}% healthy
            </ThemedText>
          </View>
          <View style={styles.categoryStatus}>
            <ThemedText style={[
              styles.healthScore,
              { color: healthPercentage >= 80 ? '#4CAF50' : healthPercentage >= 60 ? '#FF9800' : '#F44336' }
            ]}>
              {healthPercentage.toFixed(0)}%
            </ThemedText>
            <ThemedText style={styles.expandIcon}>
              {isCategoryExpanded ? '▼' : '▶'}
            </ThemedText>
          </View>
        </TouchableOpacity>

        {isCategoryExpanded && (
          <View style={styles.categoryContent}>
            {category.kpis.map(kpi => renderKPICard(kpi, category.category))}
          </View>
        )}
      </View>
    );
  };

  if (loading && !kpiData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading KPI metrics...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !kpiData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading KPI metrics</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={() => loadKPIMetrics()}>
            <ThemedText style={styles.retryButtonText}>Retry</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  if (!kpiData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.emptyContainer}>
          <ThemedText style={styles.emptyText}>No KPI data available</ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Overall Health Overview */}
        <View style={styles.overviewSection}>
          <ThemedText style={styles.sectionTitle}>Overall KPI Health</ThemedText>

          <View style={styles.healthStats}>
            <View style={styles.healthCard}>
              <ThemedText style={styles.healthValue}>
                {kpiData.overall_health.overall_score}%
              </ThemedText>
              <ThemedText style={styles.healthLabel}>Overall Score</ThemedText>
            </View>
            <View style={styles.healthCard}>
              <ThemedText style={[
                styles.healthValue,
                { color: getStatusColor(kpiData.overall_health.healthy_kpis > 0 ? 'healthy' : 'critical') }
              ]}>
                {kpiData.overall_health.healthy_kpis}
              </ThemedText>
              <ThemedText style={styles.healthLabel}>Healthy</ThemedText>
            </View>
            <View style={styles.healthCard}>
              <ThemedText style={[
                styles.healthValue,
                { color: getStatusColor('warning') }
              ]}>
                {kpiData.overall_health.at_risk_kpis}
              </ThemedText>
              <ThemedText style={styles.healthLabel}>At Risk</ThemedText>
            </View>
            <View style={styles.healthCard}>
              <ThemedText style={[
                styles.healthValue,
                { color: getStatusColor('critical') }
              ]}>
                {kpiData.overall_health.critical_kpis}
              </ThemedText>
              <ThemedText style={styles.healthLabel}>Critical</ThemedText>
            </View>
          </View>

          {overallHealthData && (
            <ProgressChart
              data={overallHealthData}
              width={screenWidth - 40}
              height={220}
              strokeWidth={16}
              radius={32}
              chartConfig={{
                backgroundColor: '#1F2833',
                backgroundGradientFrom: '#1F2833',
                backgroundGradientTo: '#0B0C10',
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(102, 252, 241, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(197, 198, 199, ${opacity})`,
                style: {
                  borderRadius: 16,
                },
              }}
              style={styles.chart}
              hideLegend={false}
            />
          )}
        </View>

        {/* Category Health Chart */}
        {categoryHealthData && (
          <View style={styles.chartSection}>
            <ThemedText style={styles.sectionTitle}>Category Performance</ThemedText>
            <BarChart
              data={categoryHealthData}
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

        {/* KPI Categories */}
        <View style={styles.categoriesSection}>
          <ThemedText style={styles.sectionTitle}>KPI Categories</ThemedText>
          {kpiData.kpi_categories.map(category => renderCategorySection(category))}
        </View>

        {/* Real-time Updates */}
        {kpiData.real_time_updates && kpiData.real_time_updates.length > 0 && (
          <View style={styles.realtimeSection}>
            <ThemedText style={styles.sectionTitle}>Recent Updates</ThemedText>
            {kpiData.real_time_updates.slice(0, 5).map((update, index) => (
              <View key={index} style={styles.updateItem}>
                <View style={styles.updateInfo}>
                  <ThemedText style={styles.updateKPI}>KPI #{update.kpi_id}</ThemedText>
                  <ThemedText style={styles.updateValues}>
                    {update.previous_value} → {update.current_value}
                    <ThemedText style={[
                      styles.updateChange,
                      { color: update.change_percentage >= 0 ? '#4CAF50' : '#F44336' }
                    ]}>
                      ({update.change_percentage >= 0 ? '+' : ''}{update.change_percentage.toFixed(1)}%)
                    </ThemedText>
                  </ThemedText>
                </View>
                <ThemedText style={styles.updateTime}>
                  {new Date(update.timestamp).toLocaleTimeString()}
                </ThemedText>
              </View>
            ))}
          </View>
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
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    color: '#C5C6C7',
    fontSize: 16,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  overviewSection: {
    marginBottom: 30,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 20,
  },
  healthStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 25,
  },
  healthCard: {
    width: '23%',
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
  },
  healthValue: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 5,
  },
  healthLabel: {
    color: '#C5C6C7',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  healthScore: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 5,
  },
  chartSection: {
    marginBottom: 30,
    alignItems: 'center',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  categoriesSection: {
    marginBottom: 30,
  },
  categorySection: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 15,
    overflow: 'hidden',
  },
  categoryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#0B0C10',
  },
  categoryInfo: {
    flex: 1,
  },
  categoryName: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  categoryStats: {
    color: '#C5C6C7',
    fontSize: 14,
    opacity: 0.8,
  },
  categoryStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  expandIcon: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  categoryContent: {
    padding: 20,
  },
  kpiCard: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    borderLeftWidth: 4,
    marginBottom: 15,
    overflow: 'hidden',
  },
  kpiHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
  },
  kpiInfo: {
    flex: 1,
  },
  kpiName: {
    color: '#C5C6C7',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  kpiDescription: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  kpiStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  kpiValue: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '700',
  },
  kpiTarget: {
    color: '#C5C6C7',
    fontSize: 14,
    opacity: 0.7,
  },
  kpiTrendIcon: {
    fontSize: 16,
  },
  progressBar: {
    height: 4,
    backgroundColor: '#2A3F41',
    marginHorizontal: 15,
    borderRadius: 2,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  kpiDetails: {
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#2A3F41',
  },
  kpiMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 15,
  },
  kpiMetric: {
    alignItems: 'center',
  },
  kpiMetricLabel: {
    color: '#C5C6C7',
    fontSize: 12,
    marginBottom: 4,
  },
  kpiMetricValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  kpiActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 10,
  },
  kpiActionButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#45A29E',
    borderRadius: 6,
  },
  kpiActionText: {
    color: '#0B0C10',
    fontSize: 12,
    fontWeight: '600',
  },
  kpiLastUpdated: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.6,
    textAlign: 'center',
  },
  realtimeSection: {
    marginBottom: 30,
  },
  updateItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    marginBottom: 10,
  },
  updateInfo: {
    flex: 1,
  },
  updateKPI: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 2,
  },
  updateValues: {
    color: '#C5C6C7',
    fontSize: 13,
  },
  updateChange: {
    fontSize: 12,
    fontWeight: '600',
  },
  updateTime: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
});