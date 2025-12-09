/**
 * Communication Protocol Service - Manages bidirectional communication between agent systems
 * Handles message routing, real-time sync, and event-driven communication
 */

import { z } from 'zod';
import { TaskDelegation } from './task-delegation.service';
import FirestoreService from '../firebase/firestore.service';
import GraphMemoryService from '../../utils/firebase/graph-memory';

// Communication protocol schemas
export const MessageSchema = z.object({
  id: z.string(),
  type: z.enum([
    'task_request',
    'task_response',
    'status_update',
    'progress_update',
    'error_notification',
    'cancellation',
    'heartbeat',
    'handoff_request',
    'context_sharing'
  ]),
  source: z.enum(['expo_agent', 'python_agent', 'github_actions', 'netlify_functions', 'orchestrator']),
  target: z.enum(['expo_agent', 'python_agent', 'github_actions', 'netlify_functions', 'orchestrator', 'all']),
  payload: z.record(z.any()),
  timestamp: z.date(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  requiresAck: z.boolean().default(false),
  correlationId: z.string().optional(),
  routing: z.object({
    direct: z.boolean().default(true),
    broadcast: z.boolean().default(false),
    topic: z.string().optional()
  }).optional()
});

export type Message = z.infer<typeof MessageSchema>;

export interface CommunicationConfig {
  userId: string;
  sessionId: string;
  enableRealtime: boolean;
  enableEncryption: boolean;
  heartbeatInterval: number; // seconds
  messageRetention: number; // days
  maxMessageSize: number; // bytes
  compressionThreshold: number; // bytes
}

export interface HandoffRequest {
  taskId: string;
  fromAgent: string;
  toAgent: string;
  reason: string;
  context: Record<string, any>;
  metadata: Record<string, any>;
}

export interface ContextSharing {
  sessionId: string;
  agentId: string;
  contextType: 'task_context' | 'user_context' | 'system_context' | 'learning_context';
  context: Record<string, any>;
  timestamp: Date;
  expiresAt?: Date;
}

export interface EventSubscription {
  id: string;
  eventType: string;
  sourceFilter?: string;
  targetFilter?: string;
  condition?: string;
  callback: (message: Message) => Promise<void>;
  active: boolean;
}

export class CommunicationProtocolService {
  private config: CommunicationConfig;
  private firestoreService: FirestoreService;
  private graphMemory: GraphMemoryService;
  private messageQueue: Message[] = [];
  private subscriptions: Map<string, EventSubscription> = new Map();
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectionStatus: 'connected' | 'disconnected' | 'connecting' = 'disconnected';

  constructor(config: CommunicationConfig) {
    this.config = config;
    this.firestoreService = FirestoreService.getInstance();
    this.graphMemory = new GraphMemoryService();

    // Set user context for services
    this.firestoreService.setUserId(config.userId);
  }

  /**
   * Initialize the communication service
   */
  async initialize(): Promise<void> {
    try {
      // Start heartbeat mechanism
      this.startHeartbeat();

      // Set up real-time listeners
      if (this.config.enableRealtime) {
        await this.setupRealtimeListeners();
      }

      // Process any queued messages
      await this.processMessageQueue();

      this.connectionStatus = 'connected';
      console.log('Communication Protocol Service initialized successfully');
    } catch (error) {
      console.error('Error initializing Communication Protocol Service:', error);
      this.connectionStatus = 'disconnected';
      throw error;
    }
  }

  /**
   * Send a message to another agent or system
   */
  async sendMessage(
    type: Message['type'],
    payload: Record<string, any>,
    target: Message['target'],
    options: {
      priority?: Message['priority'];
      requiresAck?: boolean;
      correlationId?: string;
      routing?: {
        direct?: boolean;
        broadcast?: boolean;
        topic?: string;
      };
    } = {}
  ): Promise<string> {
    try {
      const message: Message = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type,
        source: 'expo_agent', // This service runs in Expo
        target,
        payload,
        timestamp: new Date(),
        priority: options.priority || 'medium',
        requiresAck: options.requiresAck || false,
        correlationId: options.correlationId,
        routing: {
          direct: true,
          broadcast: false,
          ...options.routing
        }
      };

      // Validate message
      MessageSchema.parse(message);

      // Check message size
      const messageSize = JSON.stringify(message).length;
      if (messageSize > this.config.maxMessageSize) {
        throw new Error(`Message size (${messageSize}) exceeds maximum allowed size (${this.config.maxMessageSize})`);
      }

      // Compress if needed
      let finalMessage = message;
      if (messageSize > this.config.compressionThreshold) {
        finalMessage = await this.compressMessage(message);
      }

      // Store message for persistence
      await this.storeMessage(finalMessage);

      // Route message
      await this.routeMessage(finalMessage);

      // Check for local subscriptions
      this.checkSubscriptions(finalMessage);

      return message.id;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * Send task request to backend agents
   */
  async sendTaskRequest(
    task: TaskDelegation,
    target: 'python_agent' | 'github_actions' | 'netlify_functions'
  ): Promise<string> {
    return this.sendMessage('task_request', {
      taskId: task.id,
      type: task.type,
      category: task.category,
      title: task.title,
      description: task.description,
      parameters: task.parameters,
      priority: task.priority,
      expectedDuration: task.expectedDuration,
      complexity: task.complexity,
      resourceRequirements: task.resourceRequirements,
      deadline: task.deadline
    }, target, {
      priority: task.priority === 'urgent' ? 'critical' : task.priority,
      requiresAck: true,
      correlationId: task.id
    });
  }

  /**
   * Send handoff request between agents
   */
  async sendHandoffRequest(handoff: HandoffRequest): Promise<string> {
    return this.sendMessage('handoff_request', handoff, handoff.toAgent, {
      priority: 'high',
      requiresAck: true,
      correlationId: handoff.taskId
    });
  }

  /**
   * Share context between agents
   */
  async shareContext(context: ContextSharing): Promise<string> {
    return this.sendMessage('context_sharing', context, 'all', {
      priority: 'medium',
      routing: {
        direct: false,
        broadcast: true,
        topic: 'context_sharing'
      }
    });
  }

  /**
   * Subscribe to specific message types
   */
  subscribe(
    eventType: string,
    callback: (message: Message) => Promise<void>,
    options: {
      sourceFilter?: string;
      targetFilter?: string;
      condition?: string;
    } = {}
  ): string {
    const subscription: EventSubscription = {
      id: `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      eventType,
      sourceFilter: options.sourceFilter,
      targetFilter: options.targetFilter,
      condition: options.condition,
      callback,
      active: true
    };

    this.subscriptions.set(subscription.id, subscription);
    return subscription.id;
  }

  /**
   * Unsubscribe from events
   */
  unsubscribe(subscriptionId: string): boolean {
    return this.subscriptions.delete(subscriptionId);
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): 'connected' | 'disconnected' | 'connecting' {
    return this.connectionStatus;
  }

  /**
   * Get message history
   */
  async getMessageHistory(
    limit: number = 50,
    typeFilter?: string,
    sourceFilter?: string
  ): Promise<Message[]> {
    try {
      const messages = await this.firestoreService.getMessages(this.config.userId, 'communication', limit);

      const filteredMessages: Message[] = [];
      for (const messageRecord of messages) {
        try {
          const message = JSON.parse(messageRecord.content);

          // Apply filters
          if (typeFilter && message.type !== typeFilter) continue;
          if (sourceFilter && message.source !== sourceFilter) continue;

          filteredMessages.push(message);
        } catch (parseError) {
          console.warn('Could not parse message from record:', parseError);
        }
      }

      return filteredMessages;
    } catch (error) {
      console.error('Error getting message history:', error);
      return [];
    }
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    try {
      // Stop heartbeat
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        this.heartbeatInterval = null;
      }

      // Clear subscriptions
      this.subscriptions.clear();

      // Process remaining messages
      await this.processMessageQueue();

      this.connectionStatus = 'disconnected';
      console.log('Communication Protocol Service cleaned up successfully');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  /**
   * Private methods
   */

  private async storeMessage(message: Message): Promise<void> {
    try {
      await this.firestoreService.saveMessage({
        userId: this.config.userId,
        agentId: 'communication_service',
        content: JSON.stringify(message),
        type: 'agent',
        metadata: {
          type: 'message_stored',
          messageId: message.id,
          messageType: message.type,
          source: message.source,
          target: message.target,
          priority: message.priority
        }
      });

      // Also store in Firebase for backend access
      await this.graphMemory.addMemory(
        JSON.stringify(message),
        'message',
        [],
        {
          messageId: message.id,
          type: message.type,
          source: message.source,
          target: message.target,
          timestamp: message.timestamp.toISOString(),
          sessionId: this.config.sessionId
        }
      );
    } catch (error) {
      console.error('Error storing message:', error);
      throw error;
    }
  }

  private async routeMessage(message: Message): Promise<void> {
    try {
      if (message.routing?.broadcast) {
        // Broadcast message to all targets
        await this.broadcastMessage(message);
      } else if (message.routing?.topic) {
        // Route by topic
        await this.routeByTopic(message);
      } else {
        // Direct routing
        await this.routeDirect(message);
      }
    } catch (error) {
      console.error('Error routing message:', error);
      throw error;
    }
  }

  private async routeDirect(message: Message): Promise<void> {
    // Implement direct routing logic based on target
    switch (message.target) {
      case 'python_agent':
        await this.sendToPythonAgent(message);
        break;
      case 'github_actions':
        await this.sendToGitHubActions(message);
        break;
      case 'netlify_functions':
        await this.sendToNetlifyFunctions(message);
        break;
      case 'orchestrator':
        await this.sendToOrchestrator(message);
        break;
      case 'expo_agent':
        // Local handling - check subscriptions
        break;
      default:
        console.warn(`Unknown target for message routing: ${message.target}`);
    }
  }

  private async broadcastMessage(message: Message): Promise<void> {
    const targets = ['python_agent', 'github_actions', 'netlify_functions', 'orchestrator'];

    for (const target of targets) {
      try {
        await this.sendToTarget(message, target);
      } catch (error) {
        console.error(`Error broadcasting to ${target}:`, error);
      }
    }
  }

  private async routeByTopic(message: Message): Promise<void> {
    // Implement topic-based routing
    // This could be enhanced with a more sophisticated topic system
    console.log(`Routing message by topic: ${message.routing?.topic}`);
  }

  private async sendToPythonAgent(message: Message): Promise<void> {
    // Implementation for sending to Python backend
    // This could involve API calls, webhook triggers, etc.
    console.log(`Sending message to Python agent: ${message.id}`);
  }

  private async sendToGitHubActions(message: Message): Promise<void> {
    // Implementation for sending to GitHub Actions
    // This would involve triggering workflows via GitHub API
    console.log(`Sending message to GitHub Actions: ${message.id}`);
  }

  private async sendToNetlifyFunctions(message: Message): Promise<void> {
    // Implementation for sending to Netlify Functions
    // This would involve calling specific functions
    console.log(`Sending message to Netlify Functions: ${message.id}`);
  }

  private async sendToOrchestrator(message: Message): Promise<void> {
    // Implementation for sending to orchestrator
    console.log(`Sending message to orchestrator: ${message.id}`);
  }

  private async sendToTarget(message: Message, target: string): Promise<void> {
    // Generic target sending method
    const targetMessage = {
      ...message,
      target: target as Message['target']
    };

    await this.storeMessage(targetMessage);

    // Implementation would vary by target
    switch (target) {
      case 'python_agent':
        await this.sendToPythonAgent(targetMessage);
        break;
      case 'github_actions':
        await this.sendToGitHubActions(targetMessage);
        break;
      case 'netlify_functions':
        await this.sendToNetlifyFunctions(targetMessage);
        break;
      default:
        console.warn(`Unknown target: ${target}`);
    }
  }

  private checkSubscriptions(message: Message): void {
    for (const [id, subscription] of this.subscriptions) {
      if (!subscription.active) continue;

      // Check event type match
      if (subscription.eventType !== message.type && subscription.eventType !== '*') continue;

      // Check source filter
      if (subscription.sourceFilter && subscription.sourceFilter !== message.source) continue;

      // Check target filter
      if (subscription.targetFilter && subscription.targetFilter !== message.target) continue;

      // Check condition (simple implementation)
      if (subscription.condition && !this.evaluateCondition(subscription.condition, message)) continue;

      // Execute callback asynchronously
      subscription.callback(message).catch(error => {
        console.error(`Error in subscription callback ${id}:`, error);
      });
    }
  }

  private evaluateCondition(condition: string, message: Message): boolean {
    // Simple condition evaluation - could be enhanced
    try {
      // Basic key-value checks
      if (condition.includes('priority')) {
        const priorityMatch = condition.match(/priority[=<>!]+(\w+)/);
        if (priorityMatch) {
          const operator = priorityMatch[0].replace('priority', '').trim();
          const value = priorityMatch[1];
          return this.compareValues(message.priority, value, operator);
        }
      }

      return true;
    } catch (error) {
      console.warn('Error evaluating condition:', error);
      return false;
    }
  }

  private compareValues(actual: string, expected: string, operator: string): boolean {
    switch (operator) {
      case '==':
      case '=':
        return actual === expected;
      case '!=':
        return actual !== expected;
      default:
        return false;
    }
  }

  private async compressMessage(message: Message): Promise<Message> {
    // Simple compression implementation
    // In a production system, you'd use a proper compression library
    const compressed = {
      ...message,
      payload: this.compressObject(message.payload)
    };

    return compressed;
  }

  private compressObject(obj: any): any {
    // Simple compression - remove undefined and null values
    if (typeof obj !== 'object' || obj === null) return obj;

    if (Array.isArray(obj)) {
      return obj.filter(item => item !== undefined && item !== null);
    }

    const compressed: any = {};
    for (const [key, value] of Object.entries(obj)) {
      if (value !== undefined && value !== null) {
        compressed[key] = typeof value === 'object' ? this.compressObject(value) : value;
      }
    }

    return compressed;
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(async () => {
      try {
        await this.sendMessage('heartbeat', {
          timestamp: new Date(),
          sessionId: this.config.sessionId,
          status: this.connectionStatus
        }, 'all', {
          priority: 'low',
          routing: { broadcast: true }
        });
      } catch (error) {
        console.error('Error sending heartbeat:', error);
      }
    }, this.config.heartbeatInterval * 1000);
  }

  private async setupRealtimeListeners(): Promise<void> {
    // Set up Firebase real-time listeners for messages
    // Implementation would depend on the specific Firebase setup
    console.log('Setting up real-time listeners for communication');
  }

  private async processMessageQueue(): Promise<void> {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        try {
          await this.routeMessage(message);
        } catch (error) {
          console.error('Error processing queued message:', error);
        }
      }
    }
  }
}

export default CommunicationProtocolService;