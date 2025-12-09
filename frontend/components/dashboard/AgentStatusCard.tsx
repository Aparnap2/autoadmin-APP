import React from 'react';
import { View, StyleSheet } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

interface AgentStatusCardProps {
  state: any;
  metrics: any;
  isLoading?: boolean;
}

interface AgentStatus {
  id: string;
  name: string;
  type: 'ceo' | 'strategy' | 'devops';
  status: 'active' | 'idle' | 'processing' | 'error';
  lastActive?: string;
  tasksCompleted?: number;
  avatar?: string;
}

export function AgentStatusCard({ state, metrics, isLoading }: AgentStatusCardProps) {
  const getAgentStatus = (agentType: string): AgentStatus => {
    // Default agent configurations
    const agents: Record<string, AgentStatus> = {
      ceo: {
        id: 'ceo-agent',
        name: 'CEO Agent',
        type: 'ceo',
        status: state?.currentAgent === 'ceo' ? 'active' : 'idle',
        lastActive: metrics?.agents?.ceo?.lastActive || 'Never',
        tasksCompleted: metrics?.agents?.ceo?.tasksCompleted || 0,
        avatar: '👔'
      },
      strategy: {
        id: 'strategy-agent',
        name: 'Strategy Agent (CMO/CFO)',
        type: 'strategy',
        status: state?.currentAgent === 'strategy' ? 'active' : 'idle',
        lastActive: metrics?.agents?.strategy?.lastActive || 'Never',
        tasksCompleted: metrics?.agents?.strategy?.tasksCompleted || 0,
        avatar: '📊'
      },
      devops: {
        id: 'devops-agent',
        name: 'DevOps Agent (CTO)',
        type: 'devops',
        status: state?.currentAgent === 'devops' ? 'active' : 'idle',
        lastActive: metrics?.agents?.devops?.lastActive || 'Never',
        tasksCompleted: metrics?.agents?.devops?.tasksCompleted || 0,
        avatar: '⚙️'
      }
    };

    return agents[agentType] || agents.ceo;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#10b981'; // green-500
      case 'processing':
        return '#f59e0b'; // amber-500
      case 'error':
        return '#ef4444'; // red-500
      default:
        return '#6b7280'; // gray-500
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Active';
      case 'processing':
        return 'Processing';
      case 'error':
        return 'Error';
      default:
        return 'Idle';
    }
  };

  const agents: AgentStatus[] = ['ceo', 'strategy', 'devops'].map(getAgentStatus);

  if (isLoading) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingState}>
          <ThemedText>Loading agent status...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <View style={styles.agentsGrid}>
        {agents.map((agent) => (
          <View key={agent.id} style={styles.agentCard}>
            {/* Agent Avatar and Name */}
            <View style={styles.agentHeader}>
              <View style={styles.avatarContainer}>
                <ThemedText style={styles.avatar}>{agent.avatar}</ThemedText>
              </View>
              <View style={styles.agentInfo}>
                <ThemedText style={styles.agentName} numberOfLines={1}>
                  {agent.name}
                </ThemedText>
                <View style={styles.statusRow}>
                  <View
                    style={[
                      styles.statusDot,
                      { backgroundColor: getStatusColor(agent.status) }
                    ]}
                  />
                  <ThemedText style={styles.statusText}>
                    {getStatusText(agent.status)}
                  </ThemedText>
                </View>
              </View>
            </View>

            {/* Agent Metrics */}
            <View style={styles.metricsContainer}>
              <View style={styles.metricItem}>
                <ThemedText style={styles.metricLabel}>Tasks</ThemedText>
                <ThemedText style={styles.metricValue}>
                  {agent.tasksCompleted}
                </ThemedText>
              </View>
              <View style={styles.metricItem}>
                <ThemedText style={styles.metricLabel}>Last Active</ThemedText>
                <ThemedText style={styles.metricSubtext} numberOfLines={1}>
                  {formatLastActive(agent.lastActive)}
                </ThemedText>
              </View>
            </View>

            {/* Current Task */}
            {state?.taskStatus?.assignedTo === agent.id && (
              <View style={styles.currentTask}>
                <ThemedText style={styles.taskLabel}>Current Task:</ThemedText>
                <ThemedText style={styles.taskText} numberOfLines={2}>
                  {formatTaskType(state.taskStatus.type)}
                </ThemedText>
              </View>
            )}
          </View>
        ))}
      </View>

      {/* Overall System Status */}
      <View style={styles.systemStatus}>
        <ThemedText style={styles.systemStatusTitle}>System Overview</ThemedText>
        <View style={styles.systemMetrics}>
          <View style={styles.systemMetric}>
            <ThemedText style={styles.systemMetricLabel}>Total Tasks</ThemedText>
            <ThemedText style={styles.systemMetricValue}>
              {metrics?.totalTasks || 0}
            </ThemedText>
          </View>
          <View style={styles.systemMetric}>
            <ThemedText style={styles.systemMetricLabel}>Success Rate</ThemedText>
            <ThemedText style={styles.systemMetricValue}>
              {metrics?.successRate ? `${Math.round(metrics.successRate)}%` : 'N/A'}
            </ThemedText>
          </View>
          <View style={styles.systemMetric}>
            <ThemedText style={styles.systemMetricLabel}>Avg Response</ThemedText>
            <ThemedText style={styles.systemMetricValue}>
              {metrics?.averageResponseTime
                ? `${Math.round(metrics.averageResponseTime / 1000)}s`
                : 'N/A'}
            </ThemedText>
          </View>
        </View>
      </View>
    </ThemedView>
  );
}

// Helper functions
function formatLastActive(lastActive: string): string {
  if (!lastActive || lastActive === 'Never') return 'Never';

  try {
    const date = new Date(lastActive);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  } catch {
    return 'Unknown';
  }
}

function formatTaskType(taskType: string): string {
  const taskNames: Record<string, string> = {
    market_research: 'Market Research Analysis',
    financial_analysis: 'Financial Analysis',
    code_analysis: 'Code Analysis',
    ui_ux_review: 'UI/UX Review',
    strategic_planning: 'Strategic Planning',
    technical_decision: 'Technical Decision',
    github_actions_delegation: 'GitHub Actions Task',
    virtual_file_operation: 'File System Operation'
  };

  return taskNames[taskType] || taskType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
  },
  loadingState: {
    alignItems: 'center',
    padding: 20,
  },
  agentsGrid: {
    gap: 12,
  },
  agentCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  agentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatar: {
    fontSize: 24,
  },
  agentInfo: {
    flex: 1,
  },
  agentName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  metricsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  metricItem: {
    alignItems: 'center',
    flex: 1,
  },
  metricLabel: {
    fontSize: 11,
    opacity: 0.6,
    marginBottom: 2,
  },
  metricValue: {
    fontSize: 18,
    fontWeight: '600',
  },
  metricSubtext: {
    fontSize: 11,
    opacity: 0.7,
  },
  currentTask: {
    backgroundColor: '#fef3c7',
    borderRadius: 6,
    padding: 10,
    borderLeftWidth: 3,
    borderLeftColor: '#f59e0b',
  },
  taskLabel: {
    fontSize: 11,
    opacity: 0.7,
    marginBottom: 2,
  },
  taskText: {
    fontSize: 13,
    fontWeight: '500',
  },
  systemStatus: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  systemStatusTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
  },
  systemMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  systemMetric: {
    alignItems: 'center',
    flex: 1,
  },
  systemMetricLabel: {
    fontSize: 11,
    opacity: 0.6,
    marginBottom: 2,
  },
  systemMetricValue: {
    fontSize: 16,
    fontWeight: '600',
  },
});