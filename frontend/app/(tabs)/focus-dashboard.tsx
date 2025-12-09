/**
 * Focus-First Dashboard Component
 * Shows only the active task with WIP enforcement and Git integration
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect } from '@react-navigation/native';

// Types
interface ActiveTask {
  task_id: string;
  title: string;
  project_id?: string;
  project_name?: string;
  started_at: string;
  estimated_duration_minutes?: number;
  time_spent_minutes: number;
  progress_percentage: number;
  priority: string;
  git_branch?: string;
  pr_status?: string;
  blockers: string[];
  next_action?: string;
}

interface DashboardData {
  active_task?: ActiveTask;
  active_tasks_count: number;
  wip_limit: number;
  wip_violations_today: number;
  focus_sessions_today: number;
  total_focus_time_today: number;
  focus_score_today: number;
  upcoming_tasks: any[];
  recent_completions: any[];
  momentum_score: number;
  git_integration_status: any;
}

export default function FocusDashboard({ navigation }: any) {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load dashboard data
  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch dashboard data from WIP API
      const response = await fetch('http://localhost:8000/api/wip/dashboard', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers as needed
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setDashboardData(result.dashboard);
        }
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      Alert.alert('Error', 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh dashboard
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  }, [loadDashboardData]);

  // Start focus session
  const startFocusSession = useCallback(async (taskId: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/wip/focus/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: taskId,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          Alert.alert('Success', 'Focus session started!');
          await loadDashboardData(); // Refresh data
        }
      }
    } catch (error) {
      console.error('Error starting focus session:', error);
      Alert.alert('Error', 'Failed to start focus session');
    }
  }, [loadDashboardData]);

  // End focus session
  const endFocusSession = useCallback(async (sessionId: string, notes?: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/wip/focus/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          notes: notes,
        }),
      });

      if (response.ok) {
        Alert.alert('Success', 'Focus session completed!');
        await loadDashboardData(); // Refresh data
      }
    } catch (error) {
      console.error('Error ending focus session:', error);
      Alert.alert('Error', 'Failed to end focus session');
    }
  }, [loadDashboardData]);

  // Activate a task
  const activateTask = useCallback(async (taskId: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/wip/activate-task', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: taskId,
        }),
      });

      const result = await response.json();

      if (result.success) {
        Alert.alert('Success', 'Task activated successfully!');
        await loadDashboardData();
      } else {
        Alert.alert('Cannot Activate Task', result.reason || 'WIP limit exceeded');
      }
    } catch (error) {
      console.error('Error activating task:', error);
      Alert.alert('Error', 'Failed to activate task');
    }
  }, [loadDashboardData]);

  // Get AI guidance for active task
  const getAIGuidance = useCallback(async (taskId: string, guidanceType: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/ai-execution/guidance/${taskId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          guidance_type: guidanceType,
          context: {
            current_progress: dashboardData?.active_task?.progress_percentage || 0,
            blockers: dashboardData?.active_task?.blockers || [],
          },
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          // Navigate to guidance screen or show modal
          navigation.navigate('AIGuidance', {
            guidance: result.guidance,
            taskId: taskId,
          });
        }
      }
    } catch (error) {
      console.error('Error getting AI guidance:', error);
      Alert.alert('Error', 'Failed to get AI guidance');
    }
  }, [dashboardData, navigation]);

  // Load data on focus
  useFocusEffect(
    useCallback(() => {
      loadDashboardData();
    }, [loadDashboardData])
  );

  // Loading state
  if (loading && !dashboardData) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading your focus dashboard...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Active Task Card - The Main Focus */}
      {dashboardData?.active_task ? (
        <LinearGradient
          colors={['#667eea', '#764ba2']}
          style={styles.activeTaskCard}
        >
          <View style={styles.activeTaskHeader}>
            <Text style={styles.activeTaskTitle}>
              🎯 Your Active Task
            </Text>
            <View style={styles.priorityBadge}>
              <Text style={styles.priorityText}>
                {dashboardData.active_task.priority.toUpperCase()}
              </Text>
            </View>
          </View>

          <Text style={styles.taskTitle}>
            {dashboardData.active_task.title}
          </Text>

          {dashboardData.active_task.project_name && (
            <Text style={styles.projectName}>
              📁 {dashboardData.active_task.project_name}
            </Text>
          )}

          {/* Progress Bar */}
          <View style={styles.progressContainer}>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${dashboardData.active_task.progress_percentage * 100}%` }
                ]}
              />
            </View>
            <Text style={styles.progressText}>
              {Math.round(dashboardData.active_task.progress_percentage * 100)}% Complete
            </Text>
          </View>

          {/* Time Tracking */}
          <View style={styles.timeContainer}>
            <Text style={styles.timeText}>
              ⏱️ Time Spent: {Math.floor(dashboardData.active_task.time_spent_minutes / 60)}h {dashboardData.active_task.time_spent_minutes % 60}m
            </Text>
            {dashboardData.active_task.estimated_duration_minutes && (
              <Text style={styles.timeText}>
                🎯 Estimated: {Math.floor(dashboardData.active_task.estimated_duration_minutes / 60)}h {dashboardData.active_task.estimated_duration_minutes % 60}m
              </Text>
            )}
          </View>

          {/* Git Integration Status */}
          {dashboardData.active_task.git_branch && (
            <View style={styles.gitContainer}>
              <Text style={styles.gitText}>
                🌿 Branch: {dashboardData.active_task.git_branch}
              </Text>
              {dashboardData.active_task.pr_status && (
                <Text style={styles.gitText}>
                  🔗 PR: {dashboardData.active_task.pr_status}
                </Text>
              )}
            </View>
          )}

          {/* Blockers */}
          {dashboardData.active_task.blockers.length > 0 && (
            <View style={styles.blockersContainer}>
              <Text style={styles.blockersTitle}>🚧 Blockers:</Text>
              {dashboardData.active_task.blockers.map((blocker, index) => (
                <Text key={index} style={styles.blockerText}>
                  • {blocker}
                </Text>
              ))}
            </View>
          )}

          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <TouchableOpacity
              style={[styles.actionButton, styles.primaryButton]}
              onPress={() => getAIGuidance(dashboardData.active_task!.task_id, 'next_steps')}
            >
              <Text style={styles.primaryButtonText}>🤖 Get AI Help</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.secondaryButton]}
              onPress={() => endFocusSession('current_session')} // Would need actual session ID
            >
              <Text style={styles.secondaryButtonText}>✅ Complete Task</Text>
            </TouchableOpacity>
          </View>
        </LinearGradient>
      ) : (
        /* No Active Task State */
        <View style={styles.noActiveTaskCard}>
          <Text style={styles.noActiveTaskTitle}>
            🎯 No Active Task
          </Text>
          <Text style={styles.noActiveTaskSubtitle}>
            Choose a task to focus on and start making progress!
          </Text>

          {/* Quick Task Activation */}
          {dashboardData?.upcoming_tasks && dashboardData.upcoming_tasks.length > 0 && (
            <View style={styles.quickTasksContainer}>
              <Text style={styles.quickTasksTitle}>Suggested Tasks:</Text>
              {dashboardData.upcoming_tasks.slice(0, 3).map((task: any, index: number) => (
                <TouchableOpacity
                  key={index}
                  style={styles.quickTaskItem}
                  onPress={() => activateTask(task.id)}
                >
                  <Text style={styles.quickTaskText}>{task.title}</Text>
                  <Text style={styles.quickTaskPriority}>{task.priority}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      )}

      {/* WIP Status */}
      <View style={styles.wipStatusCard}>
        <Text style={styles.wipStatusTitle}>📊 WIP Status</Text>
        <View style={styles.wipStats}>
          <View style={styles.wipStat}>
            <Text style={styles.wipStatValue}>{dashboardData?.active_tasks_count || 0}</Text>
            <Text style={styles.wipStatLabel}>Active Tasks</Text>
          </View>
          <View style={styles.wipStat}>
            <Text style={styles.wipStatValue}>{dashboardData?.wip_limit || 2}</Text>
            <Text style={styles.wipStatLabel}>Limit</Text>
          </View>
          <View style={styles.wipStat}>
            <Text style={[styles.wipStatValue, dashboardData?.wip_violations_today ? styles.warningText : {}]}>
              {dashboardData?.wip_violations_today || 0}
            </Text>
            <Text style={styles.wipStatLabel}>Violations Today</Text>
          </View>
        </View>
      </View>

      {/* Today's Focus Stats */}
      <View style={styles.focusStatsCard}>
        <Text style={styles.focusStatsTitle}>⚡ Today's Focus</Text>
        <View style={styles.focusStats}>
          <View style={styles.focusStat}>
            <Text style={styles.focusStatValue}>{dashboardData?.focus_sessions_today || 0}</Text>
            <Text style={styles.focusStatLabel}>Sessions</Text>
          </View>
          <View style={styles.focusStat}>
            <Text style={styles.focusStatValue}>
              {Math.floor((dashboardData?.total_focus_time_today || 0) / 60)}h {(dashboardData?.total_focus_time_today || 0) % 60}m
            </Text>
            <Text style={styles.focusStatLabel}>Focus Time</Text>
          </View>
          <View style={styles.focusStat}>
            <Text style={[styles.focusStatValue, { color: getFocusScoreColor(dashboardData?.focus_score_today || 0) }]}>
              {Math.round((dashboardData?.focus_score_today || 0) * 100)}%
            </Text>
            <Text style={styles.focusStatLabel}>Focus Score</Text>
          </View>
        </View>
      </View>

      {/* Momentum Score */}
      <View style={styles.momentumCard}>
        <Text style={styles.momentumTitle}>📈 Weekly Momentum</Text>
        <View style={styles.momentumScore}>
          <Text style={[styles.momentumValue, { color: getMomentumColor(dashboardData?.momentum_score || 0) }]}>
            {Math.round(dashboardData?.momentum_score || 0)}
          </Text>
          <Text style={styles.momentumLabel}>/100</Text>
        </View>
        <Text style={styles.momentumGrade}>
          {getMomentumGrade(dashboardData?.momentum_score || 0)}
        </Text>
      </View>

      {/* Recent Completions */}
      {dashboardData?.recent_completions && dashboardData.recent_completions.length > 0 && (
        <View style={styles.recentCompletionsCard}>
          <Text style={styles.recentCompletionsTitle}>✅ Recent Completions</Text>
          {dashboardData.recent_completions.slice(0, 3).map((completion: any, index: number) => (
            <View key={index} style={styles.completionItem}>
              <Text style={styles.completionText}>{completion.title}</Text>
              <Text style={styles.completionTime}>{completion.completed_at}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

// Helper functions
function getFocusScoreColor(score: number): string {
  if (score >= 0.8) return '#4CAF50'; // Green
  if (score >= 0.6) return '#FF9800'; // Orange
  return '#F44336'; // Red
}

function getMomentumColor(score: number): string {
  if (score >= 80) return '#4CAF50';
  if (score >= 60) return '#FF9800';
  return '#F44336';
}

function getMomentumGrade(score: number): string {
  if (score >= 90) return 'A+';
  if (score >= 80) return 'A';
  if (score >= 70) return 'B';
  if (score >= 60) return 'C';
  if (score >= 50) return 'D';
  return 'F';
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  activeTaskCard: {
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  activeTaskHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  activeTaskTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
  },
  priorityBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  priorityText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  taskTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 8,
  },
  projectName: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
    marginBottom: 16,
  },
  progressContainer: {
    marginBottom: 16,
  },
  progressBar: {
    height: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 4,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: 'white',
    borderRadius: 4,
  },
  progressText: {
    color: 'white',
    fontSize: 14,
    textAlign: 'center',
  },
  timeContainer: {
    marginBottom: 16,
  },
  timeText: {
    color: 'white',
    fontSize: 14,
    marginBottom: 4,
  },
  gitContainer: {
    marginBottom: 16,
  },
  gitText: {
    color: 'white',
    fontSize: 14,
    marginBottom: 4,
  },
  blockersContainer: {
    marginBottom: 16,
  },
  blockersTitle: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  blockerText: {
    color: 'white',
    fontSize: 14,
    marginBottom: 4,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginHorizontal: 4,
  },
  primaryButton: {
    backgroundColor: 'white',
  },
  primaryButtonText: {
    color: '#667eea',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  secondaryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderWidth: 1,
    borderColor: 'white',
  },
  secondaryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  noActiveTaskCard: {
    margin: 16,
    padding: 20,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    alignItems: 'center',
  },
  noActiveTaskTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  noActiveTaskSubtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
  },
  quickTasksContainer: {
    width: '100%',
  },
  quickTasksTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  quickTaskItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    marginBottom: 8,
  },
  quickTaskText: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  quickTaskPriority: {
    fontSize: 12,
    color: '#666',
    backgroundColor: '#e9ecef',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  wipStatusCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  wipStatusTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  wipStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  wipStat: {
    alignItems: 'center',
  },
  wipStatValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  wipStatLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  warningText: {
    color: '#FF6B6B',
  },
  focusStatsCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  focusStatsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  focusStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  focusStat: {
    alignItems: 'center',
  },
  focusStatValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  focusStatLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  momentumCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    alignItems: 'center',
  },
  momentumTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  momentumScore: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  momentumValue: {
    fontSize: 48,
    fontWeight: 'bold',
  },
  momentumLabel: {
    fontSize: 24,
    color: '#666',
    marginLeft: 8,
  },
  momentumGrade: {
    fontSize: 16,
    color: '#666',
    fontWeight: 'bold',
  },
  recentCompletionsCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  recentCompletionsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  completionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  completionText: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  completionTime: {
    fontSize: 12,
    color: '#666',
  },
});