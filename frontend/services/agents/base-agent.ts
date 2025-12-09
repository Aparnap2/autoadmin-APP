/**
 * Base Agent class for AutoAdmin system
 * Provides common functionality for all agents
 */

import { ChatOpenAI } from '@langchain/openai';
import { BaseMessage, HumanMessage, AIMessage } from '@langchain/core/messages';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { createChatOpenAIWithProviderSystem } from './llm-provider/langchain-adapter';
import {
  AgentState,
  AgentConfig,
  AgentTool,
  AgentResponse,
  AgentMetrics,
  VirtualFileSystem,
  ExecutionContext,
  TaskStatus,
  TaskType
} from './types';
import GraphMemoryService from '../../utils/firebase/graph-memory';
import FirestoreService from '../firebase/firestore.service';

export abstract class BaseAgent {
  protected config: AgentConfig;
  protected llm: ChatOpenAI;
  protected graphMemory: GraphMemoryService;
  protected firestoreService: FirestoreService;
  protected metrics: AgentMetrics;
  protected virtualFileSystem: VirtualFileSystem;

  constructor(config: AgentConfig, sessionId: string) {
    this.config = config;

    // Use the new flexible LLM provider system
    this.llm = createChatOpenAIWithProviderSystem({
      model: config.model,
      temperature: config.temperature,
      maxTokens: config.maxTokens,
      providerSystemConfig: {
        // Allow agent-specific provider configuration
        primary: {
          provider: (process.env.LLM_PROVIDER || 'openai') as any,
          apiKey: process.env.LLM_API_KEY || process.env.EXPO_PUBLIC_OPENAI_API_KEY || '',
          model: config.model,
          temperature: config.temperature,
          maxTokens: config.maxTokens,
          baseUrl: process.env.LLM_BASE_URL,
          timeout: parseInt(process.env.LLM_TIMEOUT || '60000'),
          retryAttempts: parseInt(process.env.LLM_MAX_RETRIES || '3')
        },
        fallback: {
          enabled: process.env.LLM_ENABLE_FALLBACK === 'true',
          providers: (process.env.LLM_FALLBACK_PROVIDERS || '').split(',').filter(Boolean),
          retryOnErrors: (process.env.LLM_RETRY_ERRORS || 'rate_limit,server_error,timeout').split(','),
          maxRetries: parseInt(process.env.LLM_MAX_RETRIES || '3')
        },
        caching: {
          enabled: process.env.LLM_ENABLE_CACHE !== 'false',
          ttl: parseInt(process.env.LLM_CACHE_TTL || '300'),
          maxSize: parseInt(process.env.LLM_CACHE_MAX_SIZE || '1000')
        },
        monitoring: {
          enabled: process.env.LLM_ENABLE_MONITORING !== 'false',
          trackMetrics: process.env.LLM_TRACK_METRICS !== 'false',
          trackCosts: process.env.LLM_TRACK_COSTS === 'true',
          alertOnFailures: process.env.LLM_ALERT_FAILURES === 'true'
        }
      }
    });

    this.graphMemory = new GraphMemoryService();
    this.firestoreService = FirestoreService.getInstance();
    this.firestoreService.setUserId(sessionId);

    this.metrics = {
      totalTasks: 0,
      completedTasks: 0,
      averageResponseTime: 0,
      successRate: 1.0,
      delegationRate: 0.0,
    };

    this.virtualFileSystem = {
      files: new Map(),
      directories: new Map(),
      currentPath: '/',
    };
  }

  /**
   * Initialize the agent with tools and setup
   */
  async initialize(): Promise<void> {
    try {
      // Load any saved state
      await this.loadAgentState();

      // Initialize virtual filesystem
      await this.initializeVirtualFileSystem();

      console.log(`Agent ${this.config.name} initialized successfully`);
    } catch (error) {
      console.error(`Error initializing agent ${this.config.name}:`, error);
      throw error;
    }
  }

  /**
   * Process a message/task - abstract method to be implemented by specific agents
   */
  abstract process(state: AgentState): Promise<AgentResponse>;

  /**
   * Get agent-specific tools
   */
  protected getTools(): AgentTool[] {
    const commonTools = [
      this.createMemoryTool(),
      this.createVirtualFileSystemTool(),
      this.createDelegateTool(),
      this.createMetricsTool(),
    ];

    return [...commonTools, ...this.config.tools];
  }

  /**
   * Tool for interacting with graph memory
   */
  protected createMemoryTool(): AgentTool {
    return {
      name: 'memory_query',
      description: 'Query the shared graph memory for relevant information',
      schema: z.object({
        query: z.string().describe('The search query'),
        expandContext: z.boolean().optional().describe('Whether to expand context with related nodes'),
        matchThreshold: z.number().optional().describe('Similarity threshold for matching'),
      }),
      handler: async (input) => {
        try {
          const result = await this.graphMemory.queryGraph(
            input.query,
            input.matchThreshold || 0.7,
            input.expandContext !== false
          );

          return JSON.stringify({
            nodes: result.nodes,
            context: result.context,
            graph: result.graph
          }, null, 2);
        } catch (error) {
          console.error('Memory query error:', error);
          return `Error querying memory: ${error}`;
        }
      }
    };
  }

  /**
   * Tool for virtual file system operations
   */
  protected createVirtualFileSystemTool(): AgentTool {
    return {
      name: 'file_system',
      description: 'Manage the virtual file system',
      schema: z.object({
        operation: z.enum(['read', 'write', 'list', 'create_dir', 'delete']),
        path: z.string().describe('File or directory path'),
        content: z.string().optional().describe('Content for write operations'),
      }),
      handler: async (input) => {
        try {
          switch (input.operation) {
            case 'read':
              return await this.readFile(input.path);
            case 'write':
              return await this.writeFile(input.path, input.content || '');
            case 'list':
              return await this.listFiles(input.path);
            case 'create_dir':
              return await this.createDirectory(input.path);
            case 'delete':
              return await this.deleteFile(input.path);
            default:
              return `Unknown operation: ${input.operation}`;
          }
        } catch (error) {
          console.error('File system error:', error);
          return `Error in file system operation: ${error}`;
        }
      }
    };
  }

  /**
   * Tool for delegating tasks to other agents or backends
   */
  protected createDelegateTool(): AgentTool {
    return {
      name: 'delegate_task',
      description: 'Delegate a task to another agent or backend service',
      schema: z.object({
        target: z.enum(['strategy_agent', 'devops_agent', 'github_actions', 'netlify_functions']),
        task: z.string().describe('Task description'),
        parameters: z.record(z.any()).optional().describe('Task parameters'),
        priority: z.enum(['low', 'medium', 'high']).default('medium'),
      }),
      handler: async (input) => {
        try {
          // Create task record
          const task: TaskStatus = {
            id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type: this.mapTaskType(input.task),
            status: 'delegated',
            priority: input.priority,
            createdAt: new Date(),
            updatedAt: new Date(),
            assignedTo: this.config.id,
            delegatedTo: input.target,
            metadata: {
              task: input.task,
              parameters: input.parameters,
            }
          };

          // Save task to firestore
          await this.firestoreService.saveMessage({
            userId: this.config.id,
            agentId: this.config.id,
            content: JSON.stringify(task),
            type: 'agent',
            metadata: { type: 'task_delegation' }
          });

          return JSON.stringify({
            success: true,
            taskId: task.id,
            delegatedTo: input.target,
            status: 'delegated'
          }, null, 2);
        } catch (error) {
          console.error('Delegation error:', error);
          return `Error delegating task: ${error}`;
        }
      }
    };
  }

  /**
   * Tool for performance metrics and monitoring
   */
  protected createMetricsTool(): AgentTool {
    return {
      name: 'update_metrics',
      description: 'Update agent performance metrics',
      schema: z.object({
        operation: z.enum(['task_complete', 'task_start', 'error']),
        responseTime: z.number().optional(),
        tokensUsed: z.number().optional(),
        success: z.boolean().optional(),
      }),
      handler: async (input) => {
        try {
          switch (input.operation) {
            case 'task_start':
              this.metrics.totalTasks++;
              break;
            case 'task_complete':
              if (input.success !== false) {
                this.metrics.completedTasks++;
              }
              if (input.responseTime) {
                this.metrics.averageResponseTime =
                  (this.metrics.averageResponseTime + input.responseTime) / 2;
              }
              break;
            case 'error':
              // Handle error metrics
              break;
          }

          // Save metrics
          await this.saveAgentState();

          return JSON.stringify(this.metrics, null, 2);
        } catch (error) {
          console.error('Metrics update error:', error);
          return `Error updating metrics: ${error}`;
        }
      }
    };
  }

  /**
   * Virtual file system operations
   */
  private async readFile(path: string): Promise<string> {
    const file = this.virtualFileSystem.files.get(path);
    if (!file) {
      throw new Error(`File not found: ${path}`);
    }
    return file.content;
  }

  private async writeFile(path: string, content: string): Promise<string> {
    const file = {
      path,
      content,
      type: 'document' as const,
      lastModified: new Date(),
      size: content.length,
    };

    this.virtualFileSystem.files.set(path, file);

    // Persist to Firebase
    await this.graphMemory.addMemory(
      `File: ${path}`,
      'file',
      [],
      { path, type: 'document' }
    );

    return `File written successfully: ${path}`;
  }

  private async listFiles(path: string): Promise<string> {
    const files = Array.from(this.virtualFileSystem.files.entries())
      .filter(([filePath]) => filePath.startsWith(path));

    return JSON.stringify(files.map(([path, file]) => ({
      path,
      type: file.type,
      size: file.size,
      lastModified: file.lastModified
    })), null, 2);
  }

  private async createDirectory(path: string): Promise<string> {
    const dir = {
      path,
      files: [],
      subdirectories: [],
      createdAt: new Date(),
      lastModified: new Date(),
    };

    this.virtualFileSystem.directories.set(path, dir);
    return `Directory created: ${path}`;
  }

  private async deleteFile(path: string): Promise<string> {
    this.virtualFileSystem.files.delete(path);
    return `File deleted: ${path}`;
  }

  /**
   * Map task description to TaskType
   */
  private mapTaskType(task: string): TaskType {
    const taskLower = task.toLowerCase();

    if (taskLower.includes('research') || taskLower.includes('market') || taskLower.includes('competition')) {
      return 'market_research';
    }
    if (taskLower.includes('financial') || taskLower.includes('budget') || taskLower.includes('revenue')) {
      return 'financial_analysis';
    }
    if (taskLower.includes('code') || taskLower.includes('technical') || taskLower.includes('development')) {
      return 'code_analysis';
    }
    if (taskLower.includes('ui') || taskLower.includes('ux') || taskLower.includes('design')) {
      return 'ui_ux_review';
    }

    return 'strategic_planning';
  }

  /**
   * Initialize virtual file system
   */
  private async initializeVirtualFileSystem(): Promise<void> {
    // Create basic directory structure
    await this.createDirectory('/workspace');
    await this.createDirectory('/workspace/code');
    await this.createDirectory('/workspace/data');
    await this.createDirectory('/workspace/config');
    await this.createDirectory('/workspace/docs');

    // Load existing files from Firebase if available
    try {
      const storedFiles = await this.graphMemory.getNodesByType('file');
      for (const fileNode of storedFiles) {
        const filePath = fileNode.metadata?.filePath;
        if (filePath) {
          this.virtualFileSystem.files.set(filePath, {
            path: filePath,
            content: fileNode.content,
            type: fileNode.metadata?.type || 'document',
            lastModified: fileNode.timestamp,
            size: fileNode.content.length,
            metadata: fileNode.metadata,
          });
        }
      }
    } catch (error) {
      console.warn('Could not load existing files:', error);
    }
  }

  /**
   * Save agent state to Firestore
   */
  private async saveAgentState(): Promise<void> {
    try {
      const state = {
        config: this.config,
        metrics: this.metrics,
        virtualFileSystem: this.virtualFileSystem,
        lastUpdated: new Date().toISOString(),
      };

      await this.firestoreService.saveAgentState({
        userId: this.config.id,
        agentId: this.config.id,
        state,
      });
    } catch (error) {
      console.error('Error saving agent state:', error);
    }
  }

  /**
   * Load agent state from Firestore
   */
  private async loadAgentState(): Promise<void> {
    try {
      const savedState = await this.firestoreService.getAgentState(this.config.id, this.config.id);

      if (savedState?.state) {
        const state = savedState.state;

        if (state.metrics) {
          this.metrics = { ...this.metrics, ...state.metrics };
        }

        if (state.virtualFileSystem) {
          this.virtualFileSystem = state.virtualFileSystem;
        }
      }
    } catch (error) {
      console.warn('Could not load agent state:', error);
    }
  }

  /**
   * Update agent metrics after task completion
   */
  protected async updateMetrics(
    operation: 'start' | 'complete' | 'error',
    responseTime?: number,
    success?: boolean
  ): Promise<void> {
    switch (operation) {
      case 'start':
        this.metrics.totalTasks++;
        break;
      case 'complete':
        if (success !== false) {
          this.metrics.completedTasks++;
        }
        if (responseTime) {
          this.metrics.averageResponseTime =
            (this.metrics.averageResponseTime + responseTime) / 2;
        }
        break;
    }

    this.metrics.successRate = this.metrics.totalTasks > 0
      ? this.metrics.completedTasks / this.metrics.totalTasks
      : 1.0;

    await this.saveAgentState();
  }

  /**
   * Get current agent metrics
   */
  getMetrics(): AgentMetrics {
    return { ...this.metrics };
  }

  /**
   * Get agent configuration
   */
  getConfig(): AgentConfig {
    return { ...this.config };
  }

  /**
   * Switch LLM provider at runtime
   */
  async switchLLMProvider(providerConfig: {
    provider?: string;
    apiKey?: string;
    baseUrl?: string;
    model?: string;
    temperature?: number;
    maxTokens?: number;
  }): Promise<void> {
    try {
      // Cast to access provider system methods
      const adapter = this.llm as any;

      if (adapter.switchProvider) {
        await adapter.switchProvider({
          provider: providerConfig.provider || (process.env.LLM_PROVIDER || 'openai') as any,
          apiKey: providerConfig.apiKey || process.env.LLM_API_KEY || process.env.EXPO_PUBLIC_OPENAI_API_KEY || '',
          model: providerConfig.model || this.config.model,
          temperature: providerConfig.temperature ?? this.config.temperature,
          maxTokens: providerConfig.maxTokens ?? this.config.maxTokens,
          baseUrl: providerConfig.baseUrl || process.env.LLM_BASE_URL,
          timeout: parseInt(process.env.LLM_TIMEOUT || '60000'),
          retryAttempts: parseInt(process.env.LLM_MAX_RETRIES || '3')
        });

        // Update agent config if model changed
        if (providerConfig.model) {
          this.config.model = providerConfig.model;
        }
        if (providerConfig.temperature !== undefined) {
          this.config.temperature = providerConfig.temperature;
        }
        if (providerConfig.maxTokens) {
          this.config.maxTokens = providerConfig.maxTokens;
        }

        console.log(`Switched LLM provider to: ${providerConfig.provider || 'default'}`);
      } else {
        throw new Error('LLM adapter does not support provider switching');
      }
    } catch (error) {
      console.error('Failed to switch LLM provider:', error);
      throw error;
    }
  }

  /**
   * Get current LLM provider information
   */
  getLLMProviderInfo() {
    try {
      const adapter = this.llm as any;
      if (adapter.getProviderInfo) {
        return adapter.getProviderInfo();
      }
    } catch (error) {
      console.error('Failed to get LLM provider info:', error);
    }
    return null;
  }

  /**
   * Get LLM provider metrics
   */
  getLLMMetrics() {
    try {
      const adapter = this.llm as any;
      if (adapter.getMetrics) {
        return adapter.getMetrics();
      }
    } catch (error) {
      console.error('Failed to get LLM metrics:', error);
    }
    return null;
  }

  /**
   * Estimate cost for a request
   */
  estimateLLMCost(messages: BaseMessage[]) {
    try {
      const adapter = this.llm as any;
      if (adapter.estimateCost) {
        return adapter.estimateCost(messages);
      }
    } catch (error) {
      console.error('Failed to estimate LLM cost:', error);
    }
    return 0;
  }
}

export default BaseAgent;