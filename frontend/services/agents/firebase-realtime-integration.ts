/**
 * Firebase Real-time Integration for AutoAdmin Agents
 * Provides real-time synchronization and live updates
 */

import {
  collection,
  doc,
  setDoc,
  updateDoc,
  deleteDoc,
  getDoc,
  getDocs,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  serverTimestamp,
  Timestamp,
  DocumentData,
  Query
} from '../firebase/config';

import {
  SyncEvent,
  AgentState,
  TaskStatus,
  RealtimeConfig,
  UserContext,
  ExecutionContext
} from './types';

export interface RealtimeMessage {
  id: string;
  userId: string;
  sessionId: string;
  type: 'user' | 'agent' | 'system';
  content: string;
  agent?: string;
  timestamp: Timestamp;
  metadata?: Record<string, any>;
  read: boolean;
}

export interface RealtimeTask {
  id: string;
  userId: string;
  sessionId: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'delegated';
  priority: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  assignedTo?: string;
  delegatedTo?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
  completedAt?: Timestamp;
  result?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export interface RealtimeSession {
  id: string;
  userId: string;
  status: 'active' | 'paused' | 'completed';
  startTime: Timestamp;
  lastActivity: Timestamp;
  endTime?: Timestamp;
  agentStates: Record<string, any>;
  userContext: UserContext;
  metrics: {
    totalMessages: number;
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    averageResponseTime: number;
  };
  settings: {
    enableRealtimeSync: boolean;
    autoSave: boolean;
    notifications: boolean;
  };
}

export interface RealtimeNotification {
  id: string;
  userId: string;
  sessionId?: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Timestamp;
  read: boolean;
  metadata?: Record<string, any>;
  actionUrl?: string;
  expiresAt?: Timestamp;
}

export type RealtimeEventListener<T> = (data: T) => void;

export class FirebaseRealtimeIntegration {
  private userId: string;
  private sessionId: string;
  private listeners: Map<string, () => void> = new Map();
  private config: RealtimeConfig;

  constructor(userId: string, sessionId: string, config: RealtimeConfig) {
    this.userId = userId;
    this.sessionId = sessionId;
    this.config = config;
  }

  /**
   * Initialize session in Firebase
   */
  async initializeSession(userContext: UserContext): Promise<void> {
    try {
      const sessionRef = doc(collection(doc(collection(collection(collection(this.getDb(), 'users'), this.userId), 'sessions'), this.sessionId)));

      const sessionData: RealtimeSession = {
        id: this.sessionId,
        userId: this.userId,
        status: 'active',
        startTime: serverTimestamp() as Timestamp,
        lastActivity: serverTimestamp() as Timestamp,
        agentStates: {},
        userContext,
        metrics: {
          totalMessages: 0,
          totalTasks: 0,
          completedTasks: 0,
          failedTasks: 0,
          averageResponseTime: 0
        },
        settings: {
          enableRealtimeSync: this.config.enabled,
          autoSave: true,
          notifications: true
        }
      };

      await setDoc(sessionRef, sessionData);
    } catch (error) {
      console.error('Error initializing session:', error);
      throw error;
    }
  }

  /**
   * Update session activity
   */
  async updateSessionActivity(): Promise<void> {
    try {
      const sessionRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId);
      await updateDoc(sessionRef, {
        lastActivity: serverTimestamp()
      });
    } catch (error) {
      console.error('Error updating session activity:', error);
    }
  }

  /**
   * Store message with real-time sync
   */
  async storeMessage(
    content: string,
    type: RealtimeMessage['type'],
    agent?: string,
    metadata?: Record<string, any>
  ): Promise<string> {
    try {
      const messageRef = doc(collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'messages'));
      const messageId = messageRef.id;

      const messageData: Omit<RealtimeMessage, 'id'> = {
        userId: this.userId,
        sessionId: this.sessionId,
        type,
        content,
        agent,
        timestamp: serverTimestamp() as Timestamp,
        metadata,
        read: false
      };

      await setDoc(messageRef, messageData);

      // Update session metrics
      await this.updateSessionMetrics('message', type);

      return messageId;
    } catch (error) {
      console.error('Error storing message:', error);
      throw error;
    }
  }

  /**
   * Create or update task with real-time sync
   */
  async storeTask(taskData: Omit<RealtimeTask, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    try {
      const taskRef = doc(collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'tasks'));
      const taskId = taskRef.id;

      const task: RealtimeTask = {
        ...taskData,
        id: taskId,
        createdAt: serverTimestamp() as Timestamp,
        updatedAt: serverTimestamp() as Timestamp
      };

      await setDoc(taskRef, task);

      // Update session metrics
      await this.updateSessionMetrics('task', task.status);

      return taskId;
    } catch (error) {
      console.error('Error storing task:', error);
      throw error;
    }
  }

  /**
   * Update task status
   */
  async updateTaskStatus(
    taskId: string,
    status: RealtimeTask['status'],
    result?: any,
    error?: string
  ): Promise<void> {
    try {
      const taskRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'tasks', taskId);

      const updateData: Partial<RealtimeTask> = {
        status,
        updatedAt: serverTimestamp() as Timestamp
      };

      if (status === 'completed') {
        updateData.completedAt = serverTimestamp() as Timestamp;
        updateData.result = result;
      }

      if (error) {
        updateData.error = error;
      }

      await updateDoc(taskRef, updateData);

      // Update session metrics
      await this.updateSessionMetrics('task', status);
    } catch (error) {
      console.error('Error updating task status:', error);
      throw error;
    }
  }

  /**
   * Listen to new messages in real-time
   */
  listenToMessages(callback: RealtimeEventListener<RealtimeMessage>): () => void {
    const messagesQuery = query(
      collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'messages'),
      orderBy('timestamp', 'desc'),
      limit(50)
    );

    const unsubscribe = onSnapshot(messagesQuery, (snapshot) => {
      snapshot.docChanges().forEach((change) => {
        if (change.type === 'added') {
          const message = {
            id: change.doc.id,
            ...change.doc.data()
          } as RealtimeMessage;

          callback(message);
        }
      });
    }, (error) => {
      console.error('Error listening to messages:', error);
    });

    this.listeners.set('messages', unsubscribe);
    return unsubscribe;
  }

  /**
   * Listen to task updates in real-time
   */
  listenToTasks(callback: RealtimeEventListener<RealtimeTask>): () => void {
    const tasksQuery = query(
      collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'tasks'),
      orderBy('updatedAt', 'desc')
    );

    const unsubscribe = onSnapshot(tasksQuery, (snapshot) => {
      snapshot.docChanges().forEach((change) => {
        const task = {
          id: change.doc.id,
          ...change.doc.data()
        } as RealtimeTask;

        callback(task);
      });
    }, (error) => {
      console.error('Error listening to tasks:', error);
    });

    this.listeners.set('tasks', unsubscribe);
    return unsubscribe;
  }

  /**
   * Listen to session updates
   */
  listenToSession(callback: RealtimeEventListener<RealtimeSession>): () => void {
    const sessionRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId);

    const unsubscribe = onSnapshot(sessionRef, (snapshot) => {
      if (snapshot.exists()) {
        const session = {
          id: snapshot.id,
          ...snapshot.data()
        } as RealtimeSession;

        callback(session);
      }
    }, (error) => {
      console.error('Error listening to session:', error);
    });

    this.listeners.set('session', unsubscribe);
    return unsubscribe;
  }

  /**
   * Send notification to user
   */
  async sendNotification(
    type: RealtimeNotification['type'],
    title: string,
    message: string,
    metadata?: Record<string, any>,
    actionUrl?: string
  ): Promise<string> {
    try {
      const notificationRef = doc(collection(this.getDb(), 'users', this.userId, 'notifications'));
      const notificationId = notificationRef.id;

      const notificationData: Omit<RealtimeNotification, 'id'> = {
        userId: this.userId,
        sessionId: this.sessionId,
        type,
        title,
        message,
        timestamp: serverTimestamp() as Timestamp,
        read: false,
        metadata,
        actionUrl,
        expiresAt: new Timestamp(Date.now() / 1000 + 7 * 24 * 60 * 60, 0) // 7 days from now
      };

      await setDoc(notificationRef, notificationData);

      return notificationId;
    } catch (error) {
      console.error('Error sending notification:', error);
      throw error;
    }
  }

  /**
   * Listen to notifications
   */
  listenToNotifications(callback: RealtimeEventListener<RealtimeNotification>): () => void {
    const notificationsQuery = query(
      collection(this.getDb(), 'users', this.userId, 'notifications'),
      where('read', '==', false),
      orderBy('timestamp', 'desc')
    );

    const unsubscribe = onSnapshot(notificationsQuery, (snapshot) => {
      snapshot.docChanges().forEach((change) => {
        if (change.type === 'added') {
          const notification = {
            id: change.doc.id,
            ...change.doc.data()
          } as RealtimeNotification;

          callback(notification);
        }
      });
    }, (error) => {
      console.error('Error listening to notifications:', error);
    });

    this.listeners.set('notifications', unsubscribe);
    return unsubscribe;
  }

  /**
   * Mark notification as read
   */
  async markNotificationRead(notificationId: string): Promise<void> {
    try {
      const notificationRef = doc(this.getDb(), 'users', this.userId, 'notifications', notificationId);
      await updateDoc(notificationRef, { read: true });
    } catch (error) {
      console.error('Error marking notification as read:', error);
      throw error;
    }
  }

  /**
   * Sync agent state
   */
  async syncAgentState(agentId: string, state: any): Promise<void> {
    try {
      const sessionRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId);
      await updateDoc(sessionRef, {
        [`agentStates.${agentId}`]: {
          ...state,
          lastSync: serverTimestamp()
        }
      });
    } catch (error) {
      console.error('Error syncing agent state:', error);
      throw error;
    }
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(limit: number = 50): Promise<RealtimeMessage[]> {
    try {
      const messagesQuery = query(
        collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'messages'),
        orderBy('timestamp', 'desc'),
        limit(limit)
      );

      const snapshot = await getDocs(messagesQuery);
      return snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as RealtimeMessage[];
    } catch (error) {
      console.error('Error getting conversation history:', error);
      throw error;
    }
  }

  /**
   * Get active tasks
   */
  async getActiveTasks(): Promise<RealtimeTask[]> {
    try {
      const tasksQuery = query(
        collection(this.getDb(), 'users', this.userId, 'sessions', this.sessionId, 'tasks'),
        where('status', 'in', ['pending', 'processing']),
        orderBy('createdAt', 'desc')
      );

      const snapshot = await getDocs(tasksQuery);
      return snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as RealtimeTask[];
    } catch (error) {
      console.error('Error getting active tasks:', error);
      throw error;
    }
  }

  /**
   * Complete session
   */
  async completeSession(): Promise<void> {
    try {
      const sessionRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId);
      await updateDoc(sessionRef, {
        status: 'completed',
        endTime: serverTimestamp()
      });

      // Remove all listeners
      this.removeAllListeners();

      await this.sendNotification(
        'success',
        'Session Completed',
        'Your AutoAdmin session has been completed and saved.',
        { sessionId: this.sessionId }
      );
    } catch (error) {
      console.error('Error completing session:', error);
      throw error;
    }
  }

  /**
   * Clean up old sessions
   */
  async cleanupOldSessions(olderThanDays: number = 30): Promise<number> {
    try {
      const cutoffDate = new Timestamp(Date.now() / 1000 - olderThanDays * 24 * 60 * 60, 0);

      const sessionsQuery = query(
        collection(this.getDb(), 'users', this.userId, 'sessions'),
        where('lastActivity', '<', cutoffDate)
      );

      const snapshot = await getDocs(sessionsQuery);
      let deletedCount = 0;

      for (const sessionDoc of snapshot.docs) {
        try {
          // Delete session
          await deleteDoc(doc(this.getDb(), 'users', this.userId, 'sessions', sessionDoc.id));

          // Delete all messages and tasks for this session
          const messagesQuery = query(collection(this.getDb(), 'users', this.userId, 'sessions', sessionDoc.id, 'messages'));
          const messagesSnapshot = await getDocs(messagesQuery);

          for (const messageDoc of messagesSnapshot.docs) {
            await deleteDoc(messageDoc.ref);
          }

          const tasksQuery = query(collection(this.getDb(), 'users', this.userId, 'sessions', sessionDoc.id, 'tasks'));
          const tasksSnapshot = await getDocs(tasksQuery);

          for (const taskDoc of tasksSnapshot.docs) {
            await deleteDoc(taskDoc.ref);
          }

          deletedCount++;
        } catch (error) {
          console.error(`Error cleaning up session ${sessionDoc.id}:`, error);
        }
      }

      return deletedCount;
    } catch (error) {
      console.error('Error cleaning up old sessions:', error);
      throw error;
    }
  }

  /**
   * Private helper methods
   */
  private getDb() {
    // This would be imported from the firebase config
    return this.getDb();
  }

  private async updateSessionMetrics(type: 'message' | 'task', value: string): Promise<void> {
    try {
      const sessionRef = doc(this.getDb(), 'users', this.userId, 'sessions', this.sessionId);

      if (type === 'message') {
        await updateDoc(sessionRef, {
          'metrics.totalMessages': serverTimestamp().increment(1),
          lastActivity: serverTimestamp()
        });
      } else if (type === 'task') {
        const increment = serverTimestamp().increment(1);
        const updates: any = {
          'metrics.totalTasks': increment,
          lastActivity: serverTimestamp()
        };

        if (value === 'completed') {
          updates['metrics.completedTasks'] = increment;
        } else if (value === 'failed') {
          updates['metrics.failedTasks'] = increment;
        }

        await updateDoc(sessionRef, updates);
      }
    } catch (error) {
      console.error('Error updating session metrics:', error);
    }
  }

  private removeAllListeners(): void {
    this.listeners.forEach((unsubscribe) => {
      unsubscribe();
    });
    this.listeners.clear();
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): 'connected' | 'disconnected' | 'connecting' {
    // This would be implemented based on Firebase's connection state
    return 'connected';
  }

  /**
   * Cleanup integration
   */
  cleanup(): void {
    this.removeAllListeners();
  }
}

export default FirebaseRealtimeIntegration;