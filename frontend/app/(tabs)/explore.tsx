import React, { useState, useEffect, useCallback } from 'react';
import { Platform, StyleSheet, View, Modal, Alert, TouchableOpacity, Text } from 'react-native';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';

import ParallaxScrollView from '@/components/parallax-scroll-view';
import { getRoundedFontFamily } from '@/utils/fonts';

// Task Manager Components
import TaskList from '@/components/task-manager/TaskList';
import TaskCreator from '@/components/task-manager/TaskCreator';
import TaskCard from '@/components/task-manager/TaskCard';

// Services
import { getAgentAPIService } from '@/services/api/agent-api';
import { AgentTaskResponse } from '@/services/api/fastapi-client';

// Hooks
import { useFirebaseAuth } from '@/hooks/useFirebaseAuth';
import { useTaskManager } from '@/hooks/useTaskManager';

export default function TaskManagerScreen() {
  const colorScheme = useColorScheme() ?? 'dark';
  const [showTaskCreator, setShowTaskCreator] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AgentTaskResponse | null>(null);
  const [showTaskDetail, setShowTaskDetail] = useState(false);

  const { user } = useFirebaseAuth();
  const taskManager = useTaskManager({
    userId: user?.uid || 'anonymous',
    autoInitialize: true,
    enableRealtimeSync: false, // Changed from true to false to disable real-time sync
    syncWithBackend: false,    // Changed from true to false to disable backend sync
    autoSyncInterval: 30000, // This won't be used since syncWithBackend is false
    onError: (error) => console.error('Task manager error:', error),
  });

  const agentService = getAgentAPIService();

  // Handle task creation
  const handleTaskCreated = useCallback(async () => {
    setShowTaskCreator(false);
    // Task will be automatically synced through the task manager
  }, []);

  // Handle task press
  const handleTaskPress = useCallback((task: AgentTaskResponse) => {
    setSelectedTask(task);
    setShowTaskDetail(true);
  }, []);

  // Handle task cancellation
  const handleTaskCancel = useCallback(async (taskId: string) => {
    try {
      await taskManager.cancelBackendTask(taskId);
      Alert.alert('Success', 'Task cancelled successfully');
    } catch (error) {
      console.error('Error cancelling task:', error);
      Alert.alert('Error', 'Failed to cancel task');
    }
  }, [taskManager]);

  // Handle task retry
  const handleTaskRetry = useCallback(async (taskId: string) => {
    try {
      await taskManager.retryBackendTask(taskId);
      Alert.alert('Success', 'Task retry initiated');
    } catch (error) {
      console.error('Error retrying task:', error);
      Alert.alert('Error', 'Failed to retry task');
    }
  }, [taskManager]);

  return (
    <>
      <ParallaxScrollView
        testID="task-manager-screen"
        headerBackgroundColor={{ light: '#3B82F6', dark: '#1E40AF' }}
        headerImage={
          <IconSymbol
            size={310}
            color="#FFFFFF"
            name="list.bullet.clipboard"
            style={styles.headerImage}
          />
        }>
        <View style={styles.titleContainer} testID="task-manager-header">
          <Text
            testID="task-manager-title"
            style={{
              fontSize: 28,
              fontWeight: 'bold',
              fontFamily: getRoundedFontFamily(),
              color: '#FFFFFF',
            }}>
            Task Manager
          </Text>
          <View style={styles.statusIndicators}>
            <View style={[styles.statusIndicator, taskManager.backendConnected ? styles.connected : styles.disconnected]}>
              <IconSymbol
                name={taskManager.backendConnected ? "wifi" : "wifi.off"}
                size={14}
                color={taskManager.backendConnected ? "#10B981" : "#EF4444"}
              />
              <Text style={[
                styles.statusText,
                { color: taskManager.backendConnected ? "#10B981" : "#EF4444" }
              ]}>
                {taskManager.backendConnected ? "Backend" : "Local"}
              </Text>
            </View>
            {taskManager.agents.isInitialized && (
              <View style={styles.statusIndicator}>
                <IconSymbol name="pulse" size={14} color="#3B82F6" />
                <Text style={[styles.statusText, { color: "#3B82F6" }]}>
                  Agents Ready
                </Text>
              </View>
            )}
            {taskManager.syncStatus !== 'idle' && (
              <View style={[styles.statusIndicator, styles.syncIndicator]}>
                <IconSymbol
                  name={taskManager.syncStatus === 'syncing' ? "sync" :
                        taskManager.syncStatus === 'error' ? "close-circle" : "checkmark-circle"}
                  size={14}
                  color={taskManager.syncStatus === 'syncing' ? "#F59E0B" :
                        taskManager.syncStatus === 'error' ? "#EF4444" : "#10B981"}
                />
                <Text style={[
                  styles.statusText,
                  {
                    color: taskManager.syncStatus === 'syncing' ? "#F59E0B" :
                          taskManager.syncStatus === 'error' ? "#EF4444" : "#10B981"
                  }
                ]}>
                  {taskManager.syncStatus === 'syncing' ? "Syncing..." :
                   taskManager.syncStatus === 'error' ? "Sync Error" : "Synced"}
                </Text>
              </View>
            )}
          </View>
        </View>

        <Text style={[styles.subtitle, { color: Colors[colorScheme].text, opacity: 0.8 }]}>
          Manage and track AI agent tasks across your AutoAdmin system
        </Text>
      </ParallaxScrollView>

      {/* Task List */}
      <TaskList
        agentService={agentService}
        onTaskPress={handleTaskPress}
        onTaskCancel={handleTaskCancel}
        onTaskRetry={handleTaskRetry}
        showStats={true}
        showSearch={true}
        showFilters={true}
      />

      {/* Floating Action Button */}
      <TouchableOpacity
        testID="fab-create-task"
        style={styles.fab}
        onPress={() => setShowTaskCreator(true)}
      >
        <IconSymbol name="add" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      {/* Task Creator Modal */}
      <Modal
        visible={showTaskCreator}
        animationType="slide"
        presentationStyle="pageSheet"
      >
        <TaskCreator
          agentService={agentService}
          onTaskCreated={handleTaskCreated}
          onCancel={() => setShowTaskCreator(false)}
        />
      </Modal>

      {/* Task Detail Modal */}
      <Modal
        visible={showTaskDetail}
        animationType="slide"
        presentationStyle="pageSheet"
      >
        <View style={[styles.detailContainer, { backgroundColor: Colors[colorScheme].background }]}>
          <View style={styles.detailHeader}>
            <Text style={[styles.detailTitle, { color: Colors[colorScheme].text }]}>Task Details</Text>
            <TouchableOpacity
              style={styles.detailCloseButton}
              onPress={() => setShowTaskDetail(false)}
            >
              <IconSymbol name="close-outline" size={24} color={Colors[colorScheme].text} />
            </TouchableOpacity>
          </View>

          {selectedTask && (
            <View style={styles.detailContent}>
              <TaskCard
                task={selectedTask}
                compact={false}
                showActions={false}
              />

              {/* Additional task details can be added here */}
              {selectedTask.metadata && Object.keys(selectedTask.metadata).length > 0 && (
                <View style={[styles.metadataContainer, { borderColor: Colors[colorScheme].border }]}>
                  <Text style={[styles.metadataTitle, { color: Colors[colorScheme].text }]}>Additional Information</Text>
                  {Object.entries(selectedTask.metadata).map(([key, value]) => (
                    <View key={key} style={styles.metadataItem}>
                      <Text style={[styles.metadataKey, { color: Colors[colorScheme].text }]}>{key}:</Text>
                      <Text style={[styles.metadataValue, { color: Colors[colorScheme].text, opacity: 0.7 }]}>
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          )}
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  headerImage: {
    color: '#FFFFFF',
    bottom: -90,
    left: -35,
    position: 'absolute',
  },
  titleContainer: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusIndicators: {
    flexDirection: 'row',
    gap: 8,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  connected: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
  },
  disconnected: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  syncIndicator: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 8,
    marginBottom: 20,
  },
  fab: {
    position: 'absolute',
    bottom: 30,
    right: 30,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  detailContainer: {
    flex: 1,
    padding: 20,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  detailTitle: {
    fontSize: 24,
    fontWeight: '700',
  },
  detailCloseButton: {
    padding: 4,
  },
  detailContent: {
    flex: 1,
  },
  metadataContainer: {
    marginTop: 20,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  metadataTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  metadataItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  metadataKey: {
    fontSize: 14,
    fontWeight: '600',
    marginRight: 8,
    flex: 1,
  },
  metadataValue: {
    fontSize: 14,
    flex: 2,
    color: '#6B7280',
  },
});
