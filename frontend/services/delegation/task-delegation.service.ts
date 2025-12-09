/**
 * Task Delegation Service - Core service for handling task delegation between frontend and backend
 * Manages task classification, routing, and communication with external systems
 */

import { z } from 'zod';
import { TaskStatus, TaskType, AgentResponse, UserContext } from '../agents/types';
import FirestoreService from '../firebase/firestore.service';
import GraphMemoryService from '../../utils/firebase/graph-memory';

// Task delegation schemas
export const TaskDelegationSchema = z.object({
  id: z.string(),
  type: z.enum([
    'light_task', // Handle by Expo agents
    'heavy_task', // Delegate to Python deep agents
    'hybrid_task' // Split between frontend and backend
  ]),
  category: z.enum([
    'market_research',
    'financial_analysis',
    'code_analysis',
    'ui_ux_review',
    'strategic_planning',
    'technical_decision',
    'data_processing',
    'computation_heavy'
  ]),
  priority: z.enum(['low', 'medium', 'high', 'urgent']),
  title: z.string(),
  description: z.string(),
  parameters: z.record(z.any()).optional(),
  expectedDuration: z.number(), // in seconds
  complexity: z.number().min(1).max(10),
  resourceRequirements: z.object({
    compute: z.enum(['low', 'medium', 'high']),
    memory: z.enum(['low', 'medium', 'high']),
    network: z.enum(['low', 'medium', 'high']).optional(),
    storage: z.enum(['low', 'medium', 'high']).optional()
  }),
  assignedTo: z.enum(['expo_agent', 'python_agent', 'github_actions', 'netlify_functions']),
  status: z.enum(['pending', 'processing', 'completed', 'failed', 'cancelled']),
  createdAt: z.date(),
  updatedAt: z.date(),
  scheduledAt: z.date().optional(),
  deadline: z.date().optional(),
  retryCount: z.number().default(0),
  maxRetries: z.number().default(3),
  metadata: z.record(z.any()).optional()
});

export type TaskDelegation = z.infer<typeof TaskDelegationSchema>;

export interface TaskClassificationResult {
  type: 'light_task' | 'heavy_task' | 'hybrid_task';
  category: TaskType;
  complexity: number;
  estimatedDuration: number;
  resourceRequirements: {
    compute: 'low' | 'medium' | 'high';
    memory: 'low' | 'medium' | 'high';
    network?: 'low' | 'medium' | 'high';
    storage?: 'low' | 'medium' | 'high';
  };
  confidence: number;
  reasoning: string;
}

export interface DelegationOptions {
  autoClassify?: boolean;
  enableRetry?: boolean;
  enableNotifications?: boolean;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  deadline?: Date;
  scheduledAt?: Date;
  metadata?: Record<string, any>;
}

export interface TaskResult {
  taskId: string;
  success: boolean;
  data?: any;
  error?: string;
  metrics?: {
    duration: number;
    resourcesUsed: Record<string, any>;
    quality?: number;
  };
  nextActions?: Array<{
    type: string;
    target: string;
    parameters: Record<string, any>;
  }>;
}

export interface DelegationConfig {
  userId: string;
  maxConcurrentTasks: number;
  enableSmartRouting: boolean;
  enableLoadBalancing: boolean;
  defaultTimeout: number; // seconds
  retryPolicy: {
    maxRetries: number;
    backoffMultiplier: number;
    maxDelay: number;
  };
  thresholds: {
    complexityForDelegation: number;
    durationForDelegation: number;
    resourceThresholds: {
      compute: number;
      memory: number;
    };
  };
}

export class TaskDelegationService {
  private config: DelegationConfig;
  private firestoreService: FirestoreService;
  private graphMemory: GraphMemoryService;
  private activeTasks: Map<string, TaskDelegation> = new Map();
  private taskQueue: TaskDelegation[] = [];
  private processingTasks = 0;

  constructor(config: DelegationConfig) {
    this.config = config;
    this.firestoreService = FirestoreService.getInstance();
    this.graphMemory = new GraphMemoryService();

    // Set user context for services
    this.firestoreService.setUserId(config.userId);
  }

  /**
   * Classify a task to determine delegation requirements
   */
  async classifyTask(
    description: string,
    context?: UserContext
  ): Promise<TaskClassificationResult> {
    try {
      // Analyze task complexity using multiple factors
      const complexityAnalysis = await this.analyzeComplexity(description, context);

      // Estimate resource requirements
      const resourceAnalysis = await this.estimateResourceRequirements(description, complexityAnalysis);

      // Determine task type based on analysis
      const taskType = this.determineTaskType(complexityAnalysis, resourceAnalysis);

      // Estimate duration
      const estimatedDuration = await this.estimateDuration(description, taskType, complexityAnalysis);

      return {
        type: taskType,
        category: this.categorizeTask(description),
        complexity: complexityAnalysis.score,
        estimatedDuration,
        resourceRequirements: resourceAnalysis,
        confidence: complexityAnalysis.confidence,
        reasoning: complexityAnalysis.reasoning
      };
    } catch (error) {
      console.error('Error classifying task:', error);

      // Fallback classification
      return {
        type: 'light_task',
        category: 'strategic_planning',
        complexity: 5,
        estimatedDuration: 60,
        resourceRequirements: {
          compute: 'low',
          memory: 'low'
        },
        confidence: 0.5,
        reasoning: 'Fallback classification due to error'
      };
    }
  }

  /**
   * Submit a task for delegation
   */
  async submitTask(
    title: string,
    description: string,
    options: DelegationOptions = {}
  ): Promise<TaskDelegation> {
    try {
      // Check if we can accept more tasks
      if (this.processingTasks >= this.config.maxConcurrentTasks) {
        throw new Error('Maximum concurrent tasks reached. Please try again later.');
      }

      // Classify the task if auto-classification is enabled
      let classification: TaskClassificationResult;
      if (options.autoClassify !== false) {
        classification = await this.classifyTask(description);
      } else {
        classification = {
          type: 'light_task',
          category: 'strategic_planning',
          complexity: 5,
          estimatedDuration: 60,
          resourceRequirements: { compute: 'low', memory: 'low' },
          confidence: 0.7,
          reasoning: 'User-provided classification'
        };
      }

      // Determine where to assign the task
      const assignedTo = await this.determineTaskAssignment(classification, options);

      // Create task delegation object
      const task: TaskDelegation = {
        id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: classification.type,
        category: classification.category,
        priority: options.priority || 'medium',
        title,
        description,
        expectedDuration: classification.estimatedDuration,
        complexity: classification.complexity,
        resourceRequirements: classification.resourceRequirements,
        assignedTo,
        status: 'pending',
        createdAt: new Date(),
        updatedAt: new Date(),
        scheduledAt: options.scheduledAt,
        deadline: options.deadline,
        metadata: {
          ...options.metadata,
          classification,
          autoClassify: options.autoClassify !== false
        }
      };

      // Validate task
      TaskDelegationSchema.parse(task);

      // Save task to Firestore
      await this.firestoreService.saveMessage({
        userId: this.config.userId,
        agentId: 'delegation_service',
        content: JSON.stringify(task),
        type: 'agent',
        metadata: { type: 'task_created' }
      });

      // Store task in Firebase for backend processing
      await this.storeTaskInBackend(task);

      // Add to active tasks
      this.activeTasks.set(task.id, task);

      // Process task if it's time
      if (!task.scheduledAt || task.scheduledAt <= new Date()) {
        await this.processTask(task);
      } else {
        // Schedule the task
        this.scheduleTask(task);
      }

      return task;
    } catch (error) {
      console.error('Error submitting task:', error);
      throw error;
    }
  }

  /**
   * Get task status and updates
   */
  async getTaskStatus(taskId: string): Promise<TaskDelegation | null> {
    try {
      // Check active tasks first
      const activeTask = this.activeTasks.get(taskId);
      if (activeTask) {
        return activeTask;
      }

      // Query from Firestore
      const messages = await this.firestoreService.getMessages(this.config.userId);
      const taskMessage = messages.find(msg =>
        msg.metadata?.type === 'task_created' &&
        msg.content.includes(`"id":"${taskId}"`)
      );

      if (taskMessage) {
        const task = JSON.parse(taskMessage.content);
        return task;
      }

      return null;
    } catch (error) {
      console.error('Error getting task status:', error);
      return null;
    }
  }

  /**
   * Cancel a task
   */
  async cancelTask(taskId: string, reason?: string): Promise<boolean> {
    try {
      const task = await this.getTaskStatus(taskId);
      if (!task) {
        return false;
      }

      // Only cancel pending or processing tasks
      if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
        return false;
      }

      // Update task status
      task.status = 'cancelled';
      task.updatedAt = new Date();
      task.metadata = {
        ...task.metadata,
        cancellationReason: reason
      };

      // Update in Firestore
      await this.firestoreService.saveMessage({
        userId: this.config.userId,
        agentId: 'delegation_service',
        content: JSON.stringify(task),
        type: 'agent',
        metadata: { type: 'task_cancelled', reason }
      });

      // Remove from active tasks
      this.activeTasks.delete(taskId);

      return true;
    } catch (error) {
      console.error('Error cancelling task:', error);
      return false;
    }
  }

  /**
   * Get active tasks for the user
   */
  async getActiveTasks(): Promise<TaskDelegation[]> {
    try {
      // Get all task messages from Firestore
      const messages = await this.firestoreService.getMessages(this.config.userId);
      const taskMessages = messages.filter(msg =>
        msg.metadata?.type === 'task_created' ||
        msg.metadata?.type === 'task_updated'
      );

      const tasks: TaskDelegation[] = [];
      for (const message of taskMessages) {
        try {
          const task = JSON.parse(message.content);
          if (task.status !== 'completed' && task.status !== 'failed' && task.status !== 'cancelled') {
            tasks.push(task);
          }
        } catch (parseError) {
          console.warn('Could not parse task from message:', parseError);
        }
      }

      return tasks;
    } catch (error) {
      console.error('Error getting active tasks:', error);
      return [];
    }
  }

  /**
   * Get task results
   */
  async getTaskResults(taskId: string): Promise<TaskResult | null> {
    try {
      // Look for result messages in Firestore
      const messages = await this.firestoreService.getMessages(this.config.userId);
      const resultMessage = messages.find(msg =>
        msg.metadata?.type === 'task_result' &&
        msg.content.includes(`"taskId":"${taskId}"`)
      );

      if (resultMessage) {
        return JSON.parse(resultMessage.content);
      }

      return null;
    } catch (error) {
      console.error('Error getting task results:', error);
      return null;
    }
  }

  /**
   * Private methods
   */

  private async analyzeComplexity(
    description: string,
    context?: UserContext
  ): Promise<{ score: number; confidence: number; reasoning: string }> {
    // Complexity analysis based on multiple factors
    const factors = {
      length: description.length,
      keywords: this.countComplexityKeywords(description),
      questions: this.countQuestions(description),
      entities: this.countEntities(description),
      structure: this.analyzeStructure(description)
    };

    // Calculate complexity score
    let score = 5; // Base score
    let reasoning = 'Base complexity: 5';

    // Length factor
    if (factors.length > 500) {
      score += 2;
      reasoning += ' (+2 for long description)';
    } else if (factors.length > 200) {
      score += 1;
      reasoning += ' (+1 for medium description)';
    }

    // Keywords factor
    if (factors.keywords >= 5) {
      score += 2;
      reasoning += ' (+2 for many complex keywords)';
    } else if (factors.keywords >= 3) {
      score += 1;
      reasoning += ' (+1 for some complex keywords)';
    }

    // Questions factor
    if (factors.questions >= 3) {
      score += 1;
      reasoning += ' (+1 for multiple questions)';
    }

    // Structure factor
    if (factors.structure.complexity === 'high') {
      score += 2;
      reasoning += ' (+2 for complex structure)';
    } else if (factors.structure.complexity === 'medium') {
      score += 1;
      reasoning += ' (+1 for medium structure)';
    }

    // Clamp score between 1-10
    score = Math.max(1, Math.min(10, score));

    // Calculate confidence based on factors clarity
    const confidence = Math.min(0.9, 0.5 + (factors.keywords * 0.1) + (factors.entities * 0.05));

    return { score, confidence, reasoning };
  }

  private countComplexityKeywords(description: string): number {
    const complexKeywords = [
      'analyze', 'research', 'implement', 'optimize', 'architecture', 'strategy',
      'comprehensive', 'detailed', 'thorough', 'complex', 'advanced', 'integrate',
      'multiple', 'various', 'several', 'extensive', 'deep', 'investigate'
    ];

    return complexKeywords.reduce((count, keyword) => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      const matches = description.match(regex);
      return count + (matches ? matches.length : 0);
    }, 0);
  }

  private countQuestions(description: string): number {
    const questionMarks = (description.match(/\?/g) || []).length;
    const questionWords = description.match(/\b(what|how|why|when|where|which|who)\b/gi) || [];
    return questionMarks + questionWords.length;
  }

  private countEntities(description: string): number {
    // Simple entity counting (could be enhanced with NLP)
    const sentences = description.split(/[.!?]+/);
    let entityCount = 0;

    for (const sentence of sentences) {
      if (sentence.trim().length > 10) {
        entityCount += 1;
      }
    }

    return entityCount;
  }

  private analyzeStructure(description: string): { complexity: 'low' | 'medium' | 'high' } {
    const sentences = description.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const avgSentenceLength = description.length / sentences.length;
    const listItems = description.match(/[-*+]\s/g) || [];
    const numbers = description.match(/\d+/g) || [];

    if (sentences.length > 10 || avgSentenceLength > 50 || listItems.length > 5) {
      return { complexity: 'high' };
    } else if (sentences.length > 5 || avgSentenceLength > 30 || listItems.length > 0) {
      return { complexity: 'medium' };
    } else {
      return { complexity: 'low' };
    }
  }

  private async estimateResourceRequirements(
    description: string,
    complexity: { score: number; confidence: number }
  ): Promise<{
    compute: 'low' | 'medium' | 'high';
    memory: 'low' | 'medium' | 'high';
    network?: 'low' | 'medium' | 'high';
    storage?: 'low' | 'medium' | 'high';
  }> {
    const baseCompute = complexity.score >= 7 ? 'high' : complexity.score >= 5 ? 'medium' : 'low';
    const baseMemory = complexity.score >= 6 ? 'medium' : 'low';

    // Check for specific resource requirements
    const needsNetwork = /api|web|scrape|fetch|download|upload/gi.test(description);
    const needsStorage = /file|database|save|store|export/gi.test(description);
    const needsHighCompute = /process|analyze|compute|calculate|algorithm/gi.test(description);

    return {
      compute: needsHighCompute ? 'high' : baseCompute,
      memory: baseMemory,
      network: needsNetwork ? 'medium' : 'low',
      storage: needsStorage ? 'medium' : 'low'
    };
  }

  private determineTaskType(
    complexity: { score: number },
    resources: { compute: 'low' | 'medium' | 'high' }
  ): 'light_task' | 'heavy_task' | 'hybrid_task' {
    if (complexity.score >= 8 || resources.compute === 'high') {
      return 'heavy_task';
    } else if (complexity.score >= 5 || resources.compute === 'medium') {
      return 'hybrid_task';
    } else {
      return 'light_task';
    }
  }

  private categorizeTask(description: string): TaskType {
    const desc = description.toLowerCase();

    if (desc.includes('research') || desc.includes('market') || desc.includes('competition')) {
      return 'market_research';
    }
    if (desc.includes('financial') || desc.includes('budget') || desc.includes('revenue')) {
      return 'financial_analysis';
    }
    if (desc.includes('code') || desc.includes('technical') || desc.includes('development')) {
      return 'code_analysis';
    }
    if (desc.includes('ui') || desc.includes('ux') || desc.includes('design')) {
      return 'ui_ux_review';
    }
    if (desc.includes('architecture') || desc.includes('system') || desc.includes('technical')) {
      return 'technical_decision';
    }

    return 'strategic_planning';
  }

  private async estimateDuration(
    description: string,
    taskType: 'light_task' | 'heavy_task' | 'hybrid_task',
    complexity: { score: number }
  ): Promise<number> {
    // Base durations in seconds
    const baseDurations = {
      light_task: 30,      // 30 seconds
      hybrid_task: 180,    // 3 minutes
      heavy_task: 600      // 10 minutes
    };

    let duration = baseDurations[taskType];

    // Adjust based on complexity
    duration *= (complexity.score / 5);

    // Adjust based on description length
    const lengthMultiplier = Math.min(3, description.length / 100);
    duration *= lengthMultiplier;

    return Math.round(duration);
  }

  private async determineTaskAssignment(
    classification: TaskClassificationResult,
    options: DelegationOptions
  ): Promise<'expo_agent' | 'python_agent' | 'github_actions' | 'netlify_functions'> {
    // Check for manual assignment
    if (options.metadata?.assignedTo) {
      return options.metadata.assignedTo;
    }

    // Smart assignment based on classification
    if (classification.type === 'light_task') {
      return 'expo_agent';
    } else if (classification.type === 'heavy_task') {
      // Determine based on category and resources
      if (classification.category === 'code_analysis' || classification.resourceRequirements.compute === 'high') {
        return 'github_actions';
      } else {
        return 'python_agent';
      }
    } else { // hybrid_task
      // Split workload based on complexity
      return classification.complexity >= 7 ? 'github_actions' : 'python_agent';
    }
  }

  private async storeTaskInBackend(task: TaskDelegation): Promise<void> {
    try {
      // Store in Firebase for backend processing
      await this.graphMemory.addMemory(
        JSON.stringify(task),
        'task',
        [],
        {
          taskId: task.id,
          status: task.status,
          assignedTo: task.assignedTo,
          type: task.type
        }
      );
    } catch (error) {
      console.error('Error storing task in backend:', error);
      throw error;
    }
  }

  private async processTask(task: TaskDelegation): Promise<void> {
    try {
      // Update status to processing
      task.status = 'processing';
      task.updatedAt = new Date();
      this.processingTasks++;

      // Save status update
      await this.firestoreService.saveMessage({
        userId: this.config.userId,
        agentId: 'delegation_service',
        content: JSON.stringify(task),
        type: 'agent',
        metadata: { type: 'task_updated', status: 'processing' }
      });

      // Process task based on assignment
      switch (task.assignedTo) {
        case 'expo_agent':
          await this.processWithExpoAgent(task);
          break;
        case 'python_agent':
          await this.processWithPythonAgent(task);
          break;
        case 'github_actions':
          await this.processWithGitHubActions(task);
          break;
        case 'netlify_functions':
          await this.processWithNetlifyFunctions(task);
          break;
      }
    } catch (error) {
      console.error('Error processing task:', error);

      // Update status to failed
      task.status = 'failed';
      task.updatedAt = new Date();
      this.processingTasks--;

      // Save failure
      await this.firestoreService.saveMessage({
        userId: this.config.userId,
        agentId: 'delegation_service',
        content: JSON.stringify(task),
        type: 'agent',
        metadata: { type: 'task_updated', status: 'failed', error: error.message }
      });
    } finally {
      this.activeTasks.delete(task.id);
      this.processingTasks--;
    }
  }

  private scheduleTask(task: TaskDelegation): void {
    if (task.scheduledAt && task.scheduledAt > new Date()) {
      const delay = task.scheduledAt.getTime() - Date.now();
      setTimeout(() => {
        this.processTask(task);
      }, delay);
    }
  }

  private async processWithExpoAgent(task: TaskDelegation): Promise<void> {
    // Implementation for processing with Expo agents
    // This would integrate with the existing agent orchestrator
    console.log(`Processing task ${task.id} with Expo agent`);
  }

  private async processWithPythonAgent(task: TaskDelegation): Promise<void> {
    // Implementation for processing with Python backend agents
    console.log(`Processing task ${task.id} with Python agent`);
  }

  private async processWithGitHubActions(task: TaskDelegation): Promise<void> {
    // Implementation for processing with GitHub Actions
    console.log(`Processing task ${task.id} with GitHub Actions`);
  }

  private async processWithNetlifyFunctions(task: TaskDelegation): Promise<void> {
    // Implementation for processing with Netlify Functions
    console.log(`Processing task ${task.id} with Netlify Functions`);
  }
}

export default TaskDelegationService;