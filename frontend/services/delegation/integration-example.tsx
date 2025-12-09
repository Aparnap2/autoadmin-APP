/**
 * AutoAdmin Delegation System - Complete Integration Example
 * Demonstrates how to use the task delegation system in a real Expo application
 */

import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import AutoAdminDelegationService, { DelegationOptions } from './index';

// Example UI Components for demonstration
const TaskCard = ({ task, onPress, onCancel }: {
  task: any;
  onPress: (taskId: string) => void;
  onCancel: (taskId: string) => void;
}) => (
  <View style={{
    backgroundColor: '#f5f5f5',
    padding: 16,
    margin: 8,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: task.status === 'completed' ? '#4CAF50' :
                     task.status === 'processing' ? '#2196F3' :
                     task.status === 'failed' ? '#F44336' : '#FF9800'
  }}>
    <Text style={{ fontSize: 16, fontWeight: 'bold' }}>{task.title}</Text>
    <Text style={{ fontSize: 14, color: '#666', marginTop: 4 }}>{task.description}</Text>

    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 }}>
      <Text style={{ fontSize: 12, color: '#999' }}>
        Status: {task.status} | Priority: {task.priority}
      </Text>
      <Text style={{ fontSize: 12, color: '#999' }}>
        Agent: {task.assignedTo}
      </Text>
    </View>

    <View style={{ flexDirection: 'row', marginTop: 12 }}>
      <TouchableOpacity
        style={{
          backgroundColor: '#2196F3',
          padding: 8,
          borderRadius: 4,
          marginRight: 8
        }}
        onPress={() => onPress(task.id)}
      >
        <Text style={{ color: 'white', fontSize: 12 }}>View Details</Text>
      </TouchableOpacity>

      {['pending', 'processing'].includes(task.status) && (
        <TouchableOpacity
          style={{
            backgroundColor: '#F44336',
            padding: 8,
            borderRadius: 4
          }}
          onPress={() => onCancel(task.id)}
        >
          <Text style={{ color: 'white', fontSize: 12 }}>Cancel</Text>
        </TouchableOpacity>
      )}
    </View>
  </View>
);

const ProgressIndicator = ({ task }: { task: any }) => {
  if (!task.progress) return null;

  return (
    <View style={{ margin: 8 }}>
      <Text style={{ fontSize: 12, marginBottom: 4 }}>
        {task.progress.currentActivity} ({task.progress.percentage.toFixed(1)}%)
      </Text>
      <View style={{
        height: 4,
        backgroundColor: '#e0e0e0',
        borderRadius: 2,
        overflow: 'hidden'
      }}>
        <View style={{
          height: '100%',
          backgroundColor: '#4CAF50',
          width: `${task.progress.percentage}%`
        }} />
      </View>
    </View>
  );
};

export const AutoAdminDelegationExample: React.FC = () => {
  // State management
  const [delegationService, setDelegationService] = useState<AutoAdminDelegationService | null>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Initialize delegation service
  useEffect(() => {
    const initializeService = async () => {
      try {
        const service = new AutoAdminDelegationService({
          userId: 'demo-user-123',
          sessionId: 'demo-session-' + Date.now(),

          delegation: {
            maxConcurrentTasks: 5,
            enableSmartRouting: true,
            enableLoadBalancing: true,
            defaultTimeout: 300, // 5 minutes
            retryPolicy: {
              maxRetries: 3,
              backoffMultiplier: 2,
              maxDelay: 60
            },
            thresholds: {
              complexityForDelegation: 7,
              durationForDelegation: 180, // 3 minutes
              resourceThresholds: {
                compute: 80,
                memory: 80
              }
            }
          },

          communication: {
            enableRealtime: true,
            enableEncryption: true,
            heartbeatInterval: 30, // seconds
            messageRetention: 7, // days
            maxMessageSize: 1024 * 1024, // 1MB
            compressionThreshold: 1024 * 10 // 10KB
          },

          tracking: {
            enableRealtimeUpdates: true,
            updateInterval: 5, // seconds
            historyRetention: 30, // days
            enableAnalytics: true,
            enableNotifications: true,
            notificationThresholds: {
              longRunningTask: 600, // 10 minutes
              failureRate: 20, // percentage
              resourceUsage: 90 // percentage
            }
          },

          routing: {
            enableLoadBalancing: true,
            enablePredictiveRouting: true,
            enableCostOptimization: true,
            defaultStrategy: 'balanced',
            maxConcurrentTasksPerAgent: 3,
            thresholdForDelegation: 7,
            priorityWeights: {
              complexity: 0.3,
              urgency: 0.4,
              cost: 0.1,
              reliability: 0.1,
              speed: 0.1
            },
            fallbackStrategy: 'reassign'
          }
        });

        await service.initialize();

        // Set up event listeners
        service.addEventListener('task:submitted', (event) => {
          console.log('Task submitted:', event.data);
          loadTasks(); // Refresh tasks list
        });

        service.addEventListener('task:completed', (event) => {
          console.log('Task completed:', event.data);
          loadTasks(); // Refresh tasks list
        });

        service.addEventListener('task:failed', (event) => {
          console.log('Task failed:', event.data);
          setError(`Task failed: ${event.data.error}`);
          loadTasks(); // Refresh tasks list
        });

        service.addEventListener('system:health_update', (event) => {
          setSystemStatus(event.data);
        });

        setDelegationService(service);

        // Load initial data
        await loadTasks();
        await loadSystemStatus();

      } catch (err) {
        console.error('Failed to initialize delegation service:', err);
        setError('Failed to initialize delegation service');
      }
    };

    initializeService();
  }, []);

  // Load tasks
  const loadTasks = useCallback(async () => {
    if (!delegationService) return;

    try {
      const activeTasks = await delegationService.getActiveTasks();
      setTasks(activeTasks);
      setError(null);
    } catch (err) {
      console.error('Failed to load tasks:', err);
      setError('Failed to load tasks');
    }
  }, [delegationService]);

  // Load system status
  const loadSystemStatus = useCallback(async () => {
    if (!delegationService) return;

    try {
      const status = await delegationService.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Failed to load system status:', err);
    }
  }, [delegationService]);

  // Submit example tasks
  const submitMarketResearchTask = async () => {
    if (!delegationService) return;

    setLoading(true);
    setError(null);

    try {
      const task = await delegationService.submitTask(
        'AI SaaS Market Research',
        'Conduct comprehensive market research on AI-powered SaaS tools in 2024. Focus on market size, key players, pricing models, and emerging trends.',
        {
          priority: 'high',
          autoClassify: true,
          enableRetry: true,
          metadata: {
            industry: 'Technology',
            market: 'AI SaaS',
            geographic_focus: 'global',
            time_period: '2024',
            research_depth: 'comprehensive'
          }
        }
      );

      console.log('Market research task submitted:', task.id);
      await loadTasks();

    } catch (err) {
      console.error('Failed to submit task:', err);
      setError('Failed to submit market research task');
    } finally {
      setLoading(false);
    }
  };

  const submitFinancialAnalysisTask = async () => {
    if (!delegationService) return;

    setLoading(true);
    setError(null);

    try {
      const task = await delegationService.submitTask(
        'SaaS Financial Modeling',
        'Create detailed financial models for a SaaS startup including revenue projections, customer acquisition costs, and lifetime value analysis.',
        {
          priority: 'high',
          autoClassify: true,
          metadata: {
            analysis_type: 'financial_modeling',
            company_stage: 'startup',
            time_horizon: '5_years',
            include_sensitivity_analysis: true
          }
        }
      );

      console.log('Financial analysis task submitted:', task.id);
      await loadTasks();

    } catch (err) {
      console.error('Failed to submit task:', err);
      setError('Failed to submit financial analysis task');
    } finally {
      setLoading(false);
    }
  };

  const submitTechnicalTask = async () => {
    if (!delegationService) return;

    setLoading(true);
    setError(null);

    try {
      const task = await delegationService.submitTask(
        'Code Architecture Review',
        'Review the current codebase architecture and provide recommendations for scalability, performance optimization, and best practices implementation.',
        {
          priority: 'medium',
          customRouting: {
            target: 'github_actions',
            bypassSmartRouting: false
          },
          metadata: {
            repository: 'current-codebase',
            focus_areas: ['scalability', 'performance', 'security'],
            languages: ['typescript', 'python']
          }
        }
      );

      console.log('Technical task submitted:', task.id);
      await loadTasks();

    } catch (err) {
      console.error('Failed to submit task:', err);
      setError('Failed to submit technical task');
    } finally {
      setLoading(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    if (!delegationService) return;

    try {
      const success = await delegationService.cancelTask(taskId, 'User cancelled');
      if (success) {
        await loadTasks();
      } else {
        setError('Failed to cancel task');
      }
    } catch (err) {
      console.error('Failed to cancel task:', err);
      setError('Failed to cancel task');
    }
  };

  const viewTaskDetails = async (taskId: string) => {
    if (!delegationService) return;

    try {
      const details = await delegationService.getTaskStatus(taskId);
      setSelectedTask(details);
    } catch (err) {
      console.error('Failed to get task details:', err);
      setError('Failed to load task details');
    }
  };

  // Refresh data
  const refreshData = async () => {
    await Promise.all([
      loadTasks(),
      loadSystemStatus()
    ]);
  };

  // Render system status
  const renderSystemStatus = () => {
    if (!systemStatus) return null;

    return (
      <View style={{
        backgroundColor: '#e8f5e8',
        padding: 12,
        margin: 8,
        borderRadius: 8,
        borderLeftWidth: 4,
        borderLeftColor: '#4CAF50'
      }}>
        <Text style={{ fontSize: 14, fontWeight: 'bold', marginBottom: 4 }}>
          System Status
        </Text>
        <Text style={{ fontSize: 12 }}>
          Active Tasks: {systemStatus.activeTasks} |
          Success Rate: {systemStatus.successRate.toFixed(1)}% |
          Connection: {systemStatus.connected ? 'Connected' : 'Disconnected'}
        </Text>
      </View>
    );
  };

  // Main render
  return (
    <ScrollView style={{ flex: 1, backgroundColor: '#fff' }}>
      <View style={{ padding: 16 }}>
        <Text style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 8 }}>
          AutoAdmin Delegation System
        </Text>
        <Text style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
          Intelligent task delegation between frontend and backend agents
        </Text>

        {error && (
          <View style={{
            backgroundColor: '#ffebee',
            padding: 12,
            borderRadius: 8,
            marginBottom: 16,
            borderLeftWidth: 4,
            borderLeftColor: '#F44336'
          }}>
            <Text style={{ color: '#c62828' }}>{error}</Text>
          </View>
        )}

        {renderSystemStatus()}

        {/* Task submission buttons */}
        <View style={{ marginBottom: 24 }}>
          <Text style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 12 }}>
            Submit Tasks
          </Text>

          <TouchableOpacity
            style={{
              backgroundColor: '#2196F3',
              padding: 12,
              borderRadius: 8,
              marginBottom: 8
            }}
            onPress={submitMarketResearchTask}
            disabled={loading}
          >
            <Text style={{ color: 'white', textAlign: 'center', fontWeight: 'bold' }}>
              📊 Market Research Task
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              backgroundColor: '#4CAF50',
              padding: 12,
              borderRadius: 8,
              marginBottom: 8
            }}
            onPress={submitFinancialAnalysisTask}
            disabled={loading}
          >
            <Text style={{ color: 'white', textAlign: 'center', fontWeight: 'bold' }}>
              💰 Financial Analysis Task
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={{
              backgroundColor: '#FF9800',
              padding: 12,
              borderRadius: 8,
              marginBottom: 8
            }}
            onPress={submitTechnicalTask}
            disabled={loading}
          >
            <Text style={{ color: 'white', textAlign: 'center', fontWeight: 'bold' }}>
              ⚙️ Technical Review Task
            </Text>
          </TouchableOpacity>

          {loading && (
            <ActivityIndicator style={{ marginTop: 8 }} size="small" color="#2196F3" />
          )}
        </View>

        {/* Tasks list */}
        <View style={{ marginBottom: 24 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Text style={{ fontSize: 18, fontWeight: 'bold' }}>
              Active Tasks ({tasks.length})
            </Text>
            <TouchableOpacity
              style={{
                backgroundColor: '#e0e0e0',
                paddingHorizontal: 12,
                paddingVertical: 6,
                borderRadius: 4
              }}
              onPress={refreshData}
            >
              <Text style={{ fontSize: 12 }}>🔄 Refresh</Text>
            </TouchableOpacity>
          </View>

          {tasks.length === 0 ? (
            <View style={{
              backgroundColor: '#f5f5f5',
              padding: 24,
              borderRadius: 8,
              alignItems: 'center'
            }}>
              <Text style={{ color: '#666', textAlign: 'center' }}>
                No active tasks. Submit a task to see it here.
              </Text>
            </View>
          ) : (
            tasks.map((task) => (
              <View key={task.id}>
                <TaskCard
                  task={task}
                  onPress={viewTaskDetails}
                  onCancel={cancelTask}
                />
                <ProgressIndicator task={task} />
              </View>
            ))
          )}
        </View>

        {/* Selected task details */}
        {selectedTask && (
          <View style={{
            backgroundColor: '#f8f9fa',
            padding: 16,
            borderRadius: 8,
            marginBottom: 24,
            borderLeftWidth: 4,
            borderLeftColor: '#2196F3'
          }}>
            <Text style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 8 }}>
              Task Details
            </Text>
            <Text style={{ fontSize: 12, color: '#666' }}>
              ID: {selectedTask.task?.id}
            </Text>
            <Text style={{ fontSize: 12, color: '#666' }}>
              Type: {selectedTask.task?.type}
            </Text>
            <Text style={{ fontSize: 12, color: '#666' }}>
              Category: {selectedTask.task?.category}
            </Text>
            <Text style={{ fontSize: 12, color: '#666' }}>
              Created: {selectedTask.task?.createdAt}
            </Text>

            {selectedTask.analytics && (
              <View style={{ marginTop: 12 }}>
                <Text style={{ fontSize: 14, fontWeight: 'bold', marginBottom: 4 }}>
                  Analytics
                </Text>
                <Text style={{ fontSize: 12, color: '#666' }}>
                  Duration: {selectedTask.analytics.totalDuration}s
                </Text>
                <Text style={{ fontSize: 12, color: '#666' }}>
                  Success Rate: {(selectedTask.analytics.successRate * 100).toFixed(1)}%
                </Text>
              </View>
            )}

            <TouchableOpacity
              style={{
                backgroundColor: '#6c757d',
                padding: 8,
                borderRadius: 4,
                marginTop: 12,
                alignSelf: 'flex-start'
              }}
              onPress={() => setSelectedTask(null)}
            >
              <Text style={{ color: 'white', fontSize: 12 }}>Close Details</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </ScrollView>
  );
};

export default AutoAdminDelegationExample;