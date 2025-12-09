/**
 * Executive Dashboard Component
 * The Founder's Command Center - A comprehensive business intelligence dashboard
 * providing real-time insights, KPI monitoring, and strategic recommendations
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MorningBriefing } from './MorningBriefing';
import { RevenueMetrics } from './RevenueMetrics';
import { KPIDashboard } from './KPIDashboard';
import { TaskDelegator } from './TaskDelegator';
import { CompetitiveInsights } from './CompetitiveInsights';
import { CRMIntelligence } from './CRMIntelligence';
import { StrategicPlanner } from './StrategicPlanner';
import { AlertCenter } from './AlertCenter';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';
import { MorningBriefingData, RevenueMetrics, KPIMetrics, AlertData } from '@/services/business-intelligence/api';

interface ExecutiveDashboardProps {
  userId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface DashboardData {
  morning_briefing?: MorningBriefingData;
  revenue_metrics?: RevenueMetrics;
  kpi_summary?: KPIMetrics;
  active_alerts?: AlertData;
  recent_tasks?: any[];
  system_health?: any;
}

export function ExecutiveDashboard({
  userId,
  autoRefresh = true,
  refreshInterval = 300000 // 5 minutes
}: ExecutiveDashboardProps) {
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData>({});
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'revenue' | 'kpi' | 'strategy' | 'alerts'>('overview');

  const biService = useMemo(() => getBusinessIntelligenceService(), []);

  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load comprehensive dashboard data
      const response = await biService.getExecutiveDashboardData();

      if (response.success && response.data) {
        setDashboardData(response.data);
        setLastRefresh(new Date());
      } else {
        throw new Error(response.error || 'Failed to load dashboard data');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Executive Dashboard Error:', err);
    } finally {
      setLoading(false);
    }
  }, [biService]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      // Trigger backend refresh
      await biService.refreshDashboardData();
      // Reload data
      await loadDashboardData();
    } catch (err) {
      console.error('Error refreshing dashboard:', err);
      Alert.alert('Refresh Error', 'Failed to refresh dashboard data');
    } finally {
      setRefreshing(false);
    }
  }, [biService, loadDashboardData]);

  // Set up real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    const connectRealtime = async () => {
      try {
        await biService.connectRealtimeUpdates();

        // Subscribe to various update streams
        biService.addListener('kpi_update', (data) => {
          setDashboardData(prev => ({
            ...prev,
            kpi_summary: data
          }));
        });

        biService.addListener('alert_update', (data) => {
          setDashboardData(prev => ({
            ...prev,
            active_alerts: data
          }));
        });

        biService.addListener('revenue_update', (data) => {
          setDashboardData(prev => ({
            ...prev,
            revenue_metrics: data
          }));
        });

        biService.addListener('briefing_update', (data) => {
          setDashboardData(prev => ({
            ...prev,
            morning_briefing: data
          }));
        });
      } catch (err) {
        console.error('Failed to connect real-time updates:', err);
      }
    };

    connectRealtime();

    // Set up periodic refresh
    const refreshTimer = setInterval(() => {
      if (!refreshing) {
        handleRefresh();
      }
    }, refreshInterval);

    return () => {
      biService.disconnectRealtimeUpdates();
      clearInterval(refreshTimer);
    };
  }, [autoRefresh, refreshInterval, refreshing, handleRefresh, biService]);

  // Load data on component mount and focus
  useFocusEffect(
    useCallback(() => {
      loadDashboardData();
    }, [loadDashboardData])
  );

  const renderTabContent = () => {
    switch (selectedTab) {
      case 'overview':
        return (
          <View style={styles.tabContent}>
            {/* Quick Stats Overview */}
            <View style={styles.quickStatsContainer}>
              <ThemedText type="subtitle" style={styles.sectionTitle}>Executive Overview</ThemedText>

              <View style={styles.statsGrid}>
                <View style={styles.statCard}>
                  <ThemedText style={styles.statValue}>
                    {dashboardData.revenue_metrics?.current_mrr ?
                      `$${(dashboardData.revenue_metrics.current_mrr / 1000).toFixed(1)}K` :
                      'N/A'
                    }
                  </ThemedText>
                  <ThemedText style={styles.statLabel}>MRR</ThemedText>
                </View>

                <View style={styles.statCard}>
                  <ThemedText style={styles.statValue}>
                    {dashboardData.kpi_summary?.overall_health?.overall_score ?
                      `${dashboardData.kpi_summary.overall_health.overall_score}%` :
                      'N/A'
                    }
                  </ThemedText>
                  <ThemedText style={styles.statLabel}>Health Score</ThemedText>
                </View>

                <View style={styles.statCard}>
                  <ThemedText style={styles.statValue}>
                    {dashboardData.active_alerts?.active_alerts ?
                      dashboardData.active_alerts.active_alerts.length.toString() :
                      '0'
                    }
                  </ThemedText>
                  <ThemedText style={styles.statLabel}>Active Alerts</ThemedText>
                </View>

                <View style={styles.statCard}>
                  <ThemedText style={styles.statValue}>
                    {dashboardData.revenue_metrics?.mrr_growth?.rate ?
                      `${dashboardData.revenue_metrics.mrr_growth.rate.toFixed(1)}%` :
                      'N/A'
                    }
                  </ThemedText>
                  <ThemedText style={styles.statLabel}>Growth Rate</ThemedText>
                </View>
              </View>
            </View>

            {/* Morning Briefing Preview */}
            {dashboardData.morning_briefing && (
              <View style={styles.section}>
                <MorningBriefing
                  data={dashboardData.morning_briefing}
                  compact={true}
                />
              </View>
            )}

            {/* Recent Tasks */}
            {dashboardData.recent_tasks && dashboardData.recent_tasks.length > 0 && (
              <View style={styles.section}>
                <ThemedText type="subtitle" style={styles.sectionTitle}>Recent Activities</ThemedText>
                <View style={styles.taskList}>
                  {dashboardData.recent_tasks.slice(0, 3).map((task, index) => (
                    <View key={index} style={styles.taskItem}>
                      <ThemedText style={styles.taskTitle}>{task.title}</ThemedText>
                      <ThemedText style={styles.taskStatus}>{task.status}</ThemedText>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </View>
        );

      case 'revenue':
        return (
          <View style={styles.tabContent}>
            <RevenueMetrics data={dashboardData.revenue_metrics} />
          </View>
        );

      case 'kpi':
        return (
          <View style={styles.tabContent}>
            <KPIDashboard data={dashboardData.kpi_summary} />
          </View>
        );

      case 'strategy':
        return (
          <View style={styles.tabContent}>
            <StrategicPlanner />
          </View>
        );

      case 'alerts':
        return (
          <View style={styles.tabContent}>
            <AlertCenter data={dashboardData.active_alerts} />
          </View>
        );

      default:
        return null;
    }
  };

  if (loading && !dashboardData.morning_briefing) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading Executive Dashboard...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !dashboardData.morning_briefing) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading dashboard</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={handleRefresh}
          >
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
        <View style={styles.headerTop}>
          <ThemedText type="title" style={styles.title}>Executive Dashboard</ThemedText>
          <TouchableOpacity
            style={styles.refreshButton}
            onPress={handleRefresh}
            disabled={refreshing}
          >
            <ThemedText style={styles.refreshButtonText}>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </ThemedText>
          </TouchableOpacity>
        </View>

        {lastRefresh && (
          <ThemedText style={styles.lastRefreshText}>
            Last updated: {lastRefresh.toLocaleTimeString()}
          </ThemedText>
        )}
      </View>

      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'revenue', label: 'Revenue' },
          { key: 'kpi', label: 'KPIs' },
          { key: 'strategy', label: 'Strategy' },
          { key: 'alerts', label: 'Alerts' },
        ].map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              selectedTab === tab.key && styles.activeTab
            ]}
            onPress={() => setSelectedTab(tab.key as any)}
          >
            <ThemedText style={[
              styles.tabText,
              selectedTab === tab.key && styles.activeTabText
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
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        {renderTabContent()}
      </ScrollView>

      {/* Quick Actions Bar */}
      <View style={styles.quickActionsBar}>
        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={() => setSelectedTab('strategy')}
        >
          <ThemedText style={styles.quickActionText}>New Initiative</ThemedText>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={() => setSelectedTab('alerts')}
        >
          <ThemedText style={styles.quickActionText}>View Alerts</ThemedText>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={async () => {
            try {
              await biService.generateMorningBriefing();
              await loadDashboardData();
              Alert.alert('Success', 'Morning briefing generated successfully');
            } catch (err) {
              Alert.alert('Error', 'Failed to generate morning briefing');
            }
          }}
        >
          <ThemedText style={styles.quickActionText}>Generate Briefing</ThemedText>
        </TouchableOpacity>
      </View>
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
    fontSize: 16,
    color: '#C5C6C7',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FF6B6B',
    marginBottom: 8,
  },
  errorSubtext: {
    fontSize: 14,
    color: '#C5C6C7',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#66FCF1',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
  },
  header: {
    padding: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#1F2833',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    color: '#66FCF1',
    fontSize: 24,
    fontWeight: '700',
  },
  refreshButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    backgroundColor: '#45A29E',
    borderRadius: 6,
  },
  refreshButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  lastRefreshText: {
    fontSize: 12,
    color: '#C5C6C7',
    opacity: 0.7,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 20,
  },
  tab: {
    flex: 1,
    paddingVertical: 15,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    alignItems: 'center',
  },
  activeTab: {
    borderBottomColor: '#66FCF1',
    backgroundColor: '#0B0C10',
  },
  tabText: {
    fontSize: 14,
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
    paddingBottom: 80, // Account for quick actions bar
  },
  tabContent: {
    padding: 20,
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    marginBottom: 15,
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
  },
  quickStatsContainer: {
    marginBottom: 25,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 15,
  },
  statCard: {
    width: '48%',
    backgroundColor: '#1F2833',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    alignItems: 'center',
    marginBottom: 10,
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#66FCF1',
    marginBottom: 5,
  },
  statLabel: {
    fontSize: 12,
    color: '#C5C6C7',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  taskList: {
    gap: 10,
  },
  taskItem: {
    backgroundColor: '#1F2833',
    padding: 15,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#45A29E',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  taskTitle: {
    flex: 1,
    color: '#C5C6C7',
    fontSize: 14,
    fontWeight: '500',
  },
  taskStatus: {
    fontSize: 12,
    color: '#66FCF1',
    fontWeight: '500',
  },
  quickActionsBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#1F2833',
    borderTopWidth: 1,
    borderTopColor: '#45A29E',
    flexDirection: 'row',
    padding: 15,
    gap: 10,
  },
  quickActionButton: {
    flex: 1,
    backgroundColor: '#45A29E',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  quickActionText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 12,
  },
});