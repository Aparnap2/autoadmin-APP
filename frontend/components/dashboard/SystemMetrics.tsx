import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

interface SystemMetricsProps {
  metrics: any;
  fileSystemStats: any;
}

interface MetricCard {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
  icon?: string;
}

export function SystemMetrics({ metrics, fileSystemStats }: SystemMetricsProps) {
  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const getTrendIcon = (trend?: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      default:
        return '➡️';
    }
  };

  const getSuccessRateColor = (rate: number): string => {
    if (rate >= 90) return '#10b981'; // green-500
    if (rate >= 75) return '#f59e0b'; // amber-500
    return '#ef4444'; // red-500
  };

  const performanceMetrics: MetricCard[] = [
    {
      title: 'Total Tasks',
      value: metrics?.totalTasks || 0,
      subtitle: 'All time',
      icon: '📋',
      trend: 'stable'
    },
    {
      title: 'Success Rate',
      value: metrics?.successRate ? `${Math.round(metrics.successRate)}%` : '0%',
      subtitle: 'Last 30 days',
      icon: '✅',
      color: getSuccessRateColor(metrics?.successRate || 0),
      trend: metrics?.successRate >= 90 ? 'up' : metrics?.successRate >= 75 ? 'stable' : 'down'
    },
    {
      title: 'Avg Response Time',
      value: metrics?.averageResponseTime
        ? `${Math.round(metrics.averageResponseTime / 1000)}s`
        : 'N/A',
      subtitle: 'Per task',
      icon: '⚡',
      trend: 'stable'
    },
    {
      title: 'Active Sessions',
      value: metrics?.activeSessions || 1,
      subtitle: 'Currently running',
      icon: '🔄',
      trend: 'stable'
    }
  ];

  const agentMetrics = [
    {
      name: 'CEO Agent',
      tasksCompleted: metrics?.agents?.ceo?.tasksCompleted || 0,
      avgResponseTime: metrics?.agents?.ceo?.avgResponseTime || 0,
      successRate: metrics?.agents?.ceo?.successRate || 0,
      icon: '👔',
      color: '#3b82f6'
    },
    {
      name: 'Strategy Agent',
      tasksCompleted: metrics?.agents?.strategy?.tasksCompleted || 0,
      avgResponseTime: metrics?.agents?.strategy?.avgResponseTime || 0,
      successRate: metrics?.agents?.strategy?.successRate || 0,
      icon: '📊',
      color: '#8b5cf6'
    },
    {
      name: 'DevOps Agent',
      tasksCompleted: metrics?.agents?.devops?.tasksCompleted || 0,
      avgResponseTime: metrics?.agents?.devops?.avgResponseTime || 0,
      successRate: metrics?.agents?.devops?.successRate || 0,
      icon: '⚙️',
      color: '#f59e0b'
    }
  ];

  const fileSystemMetrics: MetricCard[] = [
    {
      title: 'Total Files',
      value: fileSystemStats?.totalFiles || 0,
      subtitle: 'In virtual file system',
      icon: '📁',
      trend: 'up'
    },
    {
      title: 'Storage Used',
      value: formatBytes(fileSystemStats?.totalSize || 0),
      subtitle: 'Virtual storage',
      icon: '💾',
      trend: 'up'
    },
    {
      title: 'Operations',
      value: formatNumber(fileSystemStats?.totalOperations || 0),
      subtitle: 'File operations',
      icon: '🔧',
      trend: 'stable'
    },
    {
      title: 'Cache Hits',
      value: `${fileSystemStats?.cacheHitRate || 0}%`,
      subtitle: 'Performance metric',
      icon: '🎯',
      trend: 'stable'
    }
  ];

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={styles.container}>
        {/* Performance Metrics */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Performance</ThemedText>
          <View style={styles.metricsGrid}>
            {performanceMetrics.map((metric, index) => (
              <View key={index} style={styles.metricCard}>
                <View style={styles.metricHeader}>
                  <ThemedText style={styles.metricIcon}>{metric.icon}</ThemedText>
                  {metric.trend && (
                    <ThemedText style={styles.trendIcon}>
                      {getTrendIcon(metric.trend)}
                    </ThemedText>
                  )}
                </View>
                <ThemedText
                  style={[styles.metricValue, { color: metric.color }]}
                >
                  {metric.value}
                </ThemedText>
                <ThemedText style={styles.metricTitle}>{metric.title}</ThemedText>
                <ThemedText style={styles.metricSubtitle}>{metric.subtitle}</ThemedText>
              </View>
            ))}
          </View>
        </View>

        {/* Agent Performance */}
        <View style={[styles.section, styles.agentSection]}>
          <ThemedText style={styles.sectionTitle}>Agent Performance</ThemedText>
          {agentMetrics.map((agent, index) => (
            <View key={index} style={[styles.agentCard, { borderLeftColor: agent.color }]}>
              <View style={styles.agentHeader}>
                <View style={[styles.agentIconContainer, { backgroundColor: `${agent.color}20` }]}>
                  <ThemedText style={styles.agentIcon}>{agent.icon}</ThemedText>
                </View>
                <View style={styles.agentInfo}>
                  <ThemedText style={styles.agentName}>{agent.name}</ThemedText>
                  <ThemedText style={styles.agentStats}>
                    {agent.tasksCompleted} tasks • {Math.round(agent.avgResponseTime / 1000)}s avg
                  </ThemedText>
                </View>
              </View>
              <View style={styles.agentMetricsRow}>
                <View style={styles.agentMetric}>
                  <ThemedText style={styles.agentMetricValue}>
                    {Math.round(agent.successRate)}%
                  </ThemedText>
                  <ThemedText style={styles.agentMetricLabel}>Success</ThemedText>
                </View>
                <View style={styles.agentMetric}>
                  <ThemedText style={styles.agentMetricValue}>
                    {agent.tasksCompleted}
                  </ThemedText>
                  <ThemedText style={styles.agentMetricLabel}>Completed</ThemedText>
                </View>
                <View style={styles.agentMetric}>
                  <ThemedText style={styles.agentMetricValue}>
                    {Math.round(agent.avgResponseTime / 1000)}s
                  </ThemedText>
                  <ThemedText style={styles.agentMetricLabel}>Avg Time</ThemedText>
                </View>
              </View>
            </View>
          ))}
        </View>

        {/* File System Metrics */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>File System</ThemedText>
          <View style={styles.metricsGrid}>
            {fileSystemMetrics.map((metric, index) => (
              <View key={index} style={styles.metricCard}>
                <View style={styles.metricHeader}>
                  <ThemedText style={styles.metricIcon}>{metric.icon}</ThemedText>
                  {metric.trend && (
                    <ThemedText style={styles.trendIcon}>
                      {getTrendIcon(metric.trend)}
                    </ThemedText>
                  )}
                </View>
                <ThemedText style={styles.metricValue}>{metric.value}</ThemedText>
                <ThemedText style={styles.metricTitle}>{metric.title}</ThemedText>
                <ThemedText style={styles.metricSubtitle}>{metric.subtitle}</ThemedText>
              </View>
            ))}
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    padding: 4,
    gap: 12,
  },
  section: {
    minWidth: 300,
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
  },
  agentSection: {
    minWidth: 350,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metricCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 16,
    flex: 1,
    minWidth: 140,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  metricHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 8,
  },
  metricIcon: {
    fontSize: 20,
  },
  trendIcon: {
    fontSize: 14,
    opacity: 0.7,
  },
  metricValue: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  metricTitle: {
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 2,
  },
  metricSubtitle: {
    fontSize: 10,
    opacity: 0.6,
    textAlign: 'center',
  },
  agentCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  agentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  agentIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  agentIcon: {
    fontSize: 18,
  },
  agentInfo: {
    flex: 1,
  },
  agentName: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 2,
  },
  agentStats: {
    fontSize: 11,
    opacity: 0.6,
  },
  agentMetricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  agentMetric: {
    alignItems: 'center',
  },
  agentMetricValue: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  agentMetricLabel: {
    fontSize: 10,
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});