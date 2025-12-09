/**
 * Simple AutoAdmin Dashboard - Works completely offline
 * No backend dependencies, loads immediately
 */

import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useThemeColor } from '@/hooks/use-theme-color';
import ErrorBoundary from '@/components/ErrorBoundary';

interface SimpleDashboardProps {
  userId: string;
}

export function SimpleDashboard({ userId }: SimpleDashboardProps) {
  const [refreshing, setRefreshing] = useState(false);
  const borderColor = useThemeColor({}, 'border');
  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');

  const handleRefresh = async () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1000);
  };

  const handleQuickAction = (action: string) => {
    Alert.alert(
      'Feature Available',
      `${action} - This feature will connect to the backend when available. For now, you can explore the interface.`,
      [{ text: 'OK' }]
    );
  };

  const mockStats = {
    totalTasks: 12,
    completedTasks: 8,
    activeAgents: 3,
    uptime: '2d 14h'
  };

  return (
    <ErrorBoundary>
      <ThemedView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <ThemedText type="title">AutoAdmin Dashboard</ThemedText>
            <ThemedText style={styles.subtitle}>
              Intelligent Agent System - Ready
            </ThemedText>
          </View>
          <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh}>
            <Ionicons
              name={refreshing ? "refresh" : "refresh-outline"}
              size={20}
              color={textColor}
            />
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
          refreshControl={{
            refreshing,
            onRefresh: handleRefresh,
          }}
        >
          {/* Status Overview */}
          <View style={[styles.section, { borderColor }]}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              System Overview
            </ThemedText>
            <View style={styles.statsGrid}>
              <View style={styles.statItem}>
                <ThemedText style={styles.statNumber}>{mockStats.totalTasks}</ThemedText>
                <ThemedText style={styles.statLabel}>Total Tasks</ThemedText>
              </View>
              <View style={styles.statItem}>
                <ThemedText style={styles.statNumber}>{mockStats.completedTasks}</ThemedText>
                <ThemedText style={styles.statLabel}>Completed</ThemedText>
              </View>
              <View style={styles.statItem}>
                <ThemedText style={styles.statNumber}>{mockStats.activeAgents}</ThemedText>
                <ThemedText style={styles.statLabel}>Active Agents</ThemedText>
              </View>
              <View style={styles.statItem}>
                <ThemedText style={styles.statNumber}>{mockStats.uptime}</ThemedText>
                <ThemedText style={styles.statLabel}>Uptime</ThemedText>
              </View>
            </View>
          </View>

          {/* Quick Actions */}
          <View style={[styles.section, { borderColor }]}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Quick Actions
            </ThemedText>
            <View style={styles.actionsGrid}>
              <TouchableOpacity
                style={[styles.actionButton, { borderColor }]}
                onPress={() => handleQuickAction('Create New Task')}
              >
                <Ionicons name="add-circle-outline" size={24} color="#2196F3" />
                <ThemedText style={styles.actionText}>New Task</ThemedText>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, { borderColor }]}
                onPress={() => handleQuickAction('Chat with CEO Agent')}
              >
                <Ionicons name="chatbubble-outline" size={24} color="#4CAF50" />
                <ThemedText style={styles.actionText}>Chat CEO</ThemedText>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, { borderColor }]}
                onPress={() => handleQuickAction('View Analytics')}
              >
                <Ionicons name="bar-chart-outline" size={24} color="#FF9800" />
                <ThemedText style={styles.actionText}>Analytics</ThemedText>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, { borderColor }]}
                onPress={() => handleQuickAction('System Settings')}
              >
                <Ionicons name="settings-outline" size={24} color="#9C27B0" />
                <ThemedText style={styles.actionText}>Settings</ThemedText>
              </TouchableOpacity>
            </View>
          </View>

          {/* Recent Activity */}
          <View style={[styles.section, { borderColor }]}>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Recent Activity
            </ThemedText>
            <View style={styles.activityList}>
              <View style={styles.activityItem}>
                <View style={[styles.activityIcon, { backgroundColor: '#E3F2FD' }]}>
                  <Ionicons name="checkmark" size={16} color="#2196F3" />
                </View>
                <View style={styles.activityContent}>
                  <ThemedText style={styles.activityTitle}>Task completed</ThemedText>
                  <ThemedText style={styles.activityTime}>2 minutes ago</ThemedText>
                </View>
              </View>

              <View style={styles.activityItem}>
                <View style={[styles.activityIcon, { backgroundColor: '#E8F5E8' }]}>
                  <Ionicons name="chatbubble" size={16} color="#4CAF50" />
                </View>
                <View style={styles.activityContent}>
                  <ThemedText style={styles.activityTitle}>CEO Agent responded</ThemedText>
                  <ThemedText style={styles.activityTime}>15 minutes ago</ThemedText>
                </View>
              </View>

              <View style={styles.activityItem}>
                <View style={[styles.activityIcon, { backgroundColor: '#FFF3E0' }]}>
                  <Ionicons name="document" size={16} color="#FF9800" />
                </View>
                <View style={styles.activityContent}>
                  <ThemedText style={styles.activityTitle}>Report generated</ThemedText>
                  <ThemedText style={styles.activityTime}>1 hour ago</ThemedText>
                </View>
              </View>
            </View>
          </View>

          {/* Offline Notice */}
          <View style={[styles.section, styles.offlineNotice, { borderColor }]}>
            <View style={styles.offlineHeader}>
              <Ionicons name="information-circle-outline" size={20} color="#FF9800" />
              <ThemedText style={styles.offlineTitle}>Working Offline</ThemedText>
            </View>
            <ThemedText style={styles.offlineMessage}>
              AutoAdmin is ready to use. Advanced features will connect to the backend when you perform specific actions.
            </ThemedText>
          </View>
        </ScrollView>
      </ThemedView>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 20,
    paddingBottom: 10,
  },
  subtitle: {
    fontSize: 14,
    opacity: 0.7,
    marginTop: 4,
  },
  refreshButton: {
    padding: 8,
    borderRadius: 20,
  },
  scrollView: {
    flex: 1,
  },
  section: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  sectionTitle: {
    marginBottom: 16,
    fontWeight: '600',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statItem: {
    width: '48%',
    alignItems: 'center',
    marginBottom: 16,
    padding: 16,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.02)',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    opacity: 0.7,
    textAlign: 'center',
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    alignItems: 'center',
    padding: 16,
    marginBottom: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  actionText: {
    fontSize: 12,
    marginTop: 8,
    textAlign: 'center',
  },
  activityList: {
    gap: 12,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  activityIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  activityContent: {
    flex: 1,
  },
  activityTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 2,
  },
  activityTime: {
    fontSize: 12,
    opacity: 0.6,
  },
  offlineNotice: {
    backgroundColor: 'rgba(255, 152, 0, 0.05)',
  },
  offlineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  offlineTitle: {
    fontSize: 14,
    fontWeight: '600',
  },
  offlineMessage: {
    fontSize: 13,
    lineHeight: 18,
    opacity: 0.8,
  },
});

export default SimpleDashboard;