/**
 * Comprehensive test suite for AutoAdmin Agent System
 * Tests all agents, orchestrator, and integrations
 */

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import AgentOrchestrator from '../agent-orchestrator';
import CEOAgent from '../ceo-agent';
import StrategyAgent from '../strategy-agent';
import DevOpsAgent from '../devops-agent';
import VirtualFileSystemManager from '../virtual-filesystem';
import GraphMemoryIntegration from '../graph-memory-integration';
import FirebaseRealtimeIntegration from '../firebase-realtime-integration';
import {
  AgentState,
  TaskStatus,
  UserContext,
  VirtualFileSystem
} from '../types';

// Mock dependencies
jest.mock('../../utils/supabase/graph-memory');
jest.mock('../firebase/firestore.service');
jest.mock('../../lib/supabase');

describe('AutoAdmin Agent System', () => {
  let orchestrator: AgentOrchestrator;
  let mockUserId: string;
  let mockSessionId: string;
  let mockUserContext: UserContext;

  beforeEach(() => {
    mockUserId = 'test-user-123';
    mockSessionId = 'test-session-456';

    mockUserContext = {
      id: mockUserId,
      preferences: {
        industry: 'Technology',
        businessSize: 'small',
        timezone: 'UTC',
        language: 'en',
        notifications: {
          email: true,
          push: true,
          sms: false,
          frequency: 'daily',
          types: ['task_completed']
        }
      },
      businessProfile: {
        industry: 'Technology',
        segment: 'SaaS',
        revenue: 1000000,
        employees: 25
      },
      subscription: {
        tier: 'pro',
        limits: {
          maxAgents: 3,
          maxTasksPerDay: 100,
          maxStorageSize: 1000000000,
          maxAPICallsPerDay: 10000
        },
        features: ['multi_agent', 'realtime_sync']
      },
      sessionContext: {
        startTime: new Date(),
        lastActivity: new Date(),
        activeAgents: ['ceo', 'strategy', 'devops'],
        currentTasks: []
      }
    };

    // Mock environment variables
    process.env.EXPO_PUBLIC_OPENAI_API_KEY = 'test-api-key';
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('AgentOrchestrator', () => {
    beforeEach(() => {
      orchestrator = new AgentOrchestrator({
        userId: mockUserId,
        sessionConfig: {
          maxSessionDuration: 120,
          maxConcurrentTasks: 5,
          enableRealtimeSync: false, // Disable for tests
          persistenceStrategy: 'immediate'
        },
        agentConfigs: {
          ceo: {
            id: 'ceo-agent',
            name: 'CEO Agent',
            type: 'ceo',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test CEO prompt',
            capabilities: [],
            delegationRules: [],
            maxDelegationDepth: 2,
            approvalThreshold: 0.8,
            autoApproveTasks: []
          },
          strategy: {
            id: 'strategy-agent',
            name: 'Strategy Agent',
            type: 'strategy',
            model: 'gpt-4o-mini',
            temperature: 0.7,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test Strategy prompt',
            capabilities: [],
            delegationRules: []
          },
          devops: {
            id: 'devops-agent',
            name: 'DevOps Agent',
            type: 'devops',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test DevOps prompt',
            capabilities: [],
            delegationRules: []
          }
        },
        performanceConfig: {
          enableWorklets: false,
          maxWorkletConcurrency: 1,
          enableStreaming: false,
          chunkSize: 500
        }
      });
    });

    test('should initialize orchestrator successfully', async () => {
      await expect(orchestrator.initialize()).resolves.not.toThrow();

      const state = orchestrator.getState();
      expect(state).toBeDefined();
      expect(state.userId).toBe(mockUserId);
      expect(state.sessionId).toBeDefined();
      expect(state.activeTasks).toHaveLength(0);
    });

    test('should process simple user message', async () => {
      await orchestrator.initialize();

      const response = await orchestrator.processUserMessage('Hello, I need help with my business');

      expect(response).toBeDefined();
      expect(response.success).toBe(true);
      expect(response.message).toBeDefined();
    });

    test('should handle market research request', async () => {
      await orchestrator.initialize();

      const response = await orchestrator.processUserMessage('Can you research the SaaS market trends?');

      expect(response).toBeDefined();
      expect(response.success).toBe(true);
      // Should delegate to strategy agent
      expect(response.nextAction?.target).toBe('strategy');
    });

    test('should handle code analysis request', async () => {
      await orchestrator.initialize();

      const response = await orchestrator.processUserMessage('Please analyze this React component code');

      expect(response).toBeDefined();
      expect(response.success).toBe(true);
      // Should delegate to DevOps agent
      expect(response.nextAction?.target).toBe('devops');
    });

    test('should maintain conversation history', async () => {
      await orchestrator.initialize();

      await orchestrator.processUserMessage('First message');
      await orchestrator.processUserMessage('Second message');

      const history = orchestrator.getConversationHistory();
      expect(history.length).toBeGreaterThanOrEqual(4); // 2 user + 2 agent messages
    });

    test('should get agent metrics', async () => {
      await orchestrator.initialize();

      const metrics = await orchestrator.getAgentMetrics();

      expect(metrics).toBeDefined();
      expect(metrics.ceo).toBeDefined();
      expect(metrics.strategy).toBeDefined();
      expect(metrics.devops).toBeDefined();
      expect(metrics.orchestrator).toBeDefined();
    });

    test('should clear conversation history', async () => {
      await orchestrator.initialize();

      await orchestrator.processUserMessage('Test message');
      expect(orchestrator.getConversationHistory().length).toBeGreaterThan(0);

      orchestrator.clearConversationHistory();
      expect(orchestrator.getConversationHistory()).toHaveLength(0);
    });

    test('should reset session', async () => {
      await orchestrator.initialize();

      await orchestrator.processUserMessage('Test message');
      await orchestrator.resetSession();

      const state = orchestrator.getState();
      expect(state.completedTasks).toHaveLength(0);
      expect(state.failedTasks).toHaveLength(0);
      expect(state.activeTasks).toHaveLength(0);
    });
  });

  describe('VirtualFileSystemManager', () => {
    let vfs: VirtualFileSystemManager;

    beforeEach(() => {
      vfs = VirtualFileSystemManager.getInstance(mockUserId);
    });

    test('should create default directories', async () => {
      await vfs.initialize();

      const directories = await vfs.listDirectories();
      expect(directories.some(dir => dir.path === '/workspace')).toBe(true);
      expect(directories.some(dir => dir.path === '/workspace/code')).toBe(true);
    });

    test('should create and read files', async () => {
      const testPath = '/workspace/test.txt';
      const testContent = 'Hello, World!';

      await vfs.createFile(testPath, testContent);

      const content = await vfs.readFile(testPath);
      expect(content).toBe(testContent);
    });

    test('should update existing files', async () => {
      const testPath = '/workspace/test.txt';
      const initialContent = 'Initial content';
      const updatedContent = 'Updated content';

      await vfs.createFile(testPath, initialContent);
      await vfs.writeFile(testPath, updatedContent);

      const content = await vfs.readFile(testPath);
      expect(content).toBe(updatedContent);
    });

    test('should list files in directory', async () => {
      await vfs.createFile('/workspace/file1.txt', 'Content 1');
      await vfs.createFile('/workspace/file2.txt', 'Content 2');

      const files = await vfs.listFiles('/workspace');
      expect(files.length).toBeGreaterThanOrEqual(2);
    });

    test('should search files', async () => {
      await vfs.createFile('/workspace/search-test.txt', 'Searchable content here');

      const results = await vfs.searchFiles('searchable');
      expect(results.length).toBeGreaterThanOrEqual(1);
      expect(results[0].content).toContain('Searchable');
    });

    test('should provide file system statistics', async () => {
      await vfs.createFile('/workspace/stats.txt', 'File for stats');

      const stats = await vfs.getStats();
      expect(stats.totalFiles).toBeGreaterThan(0);
      expect(stats.totalDirectories).toBeGreaterThan(0);
    });

    test('should handle file operations errors gracefully', async () => {
      await expect(vfs.readFile('/nonexistent/file.txt')).rejects.toThrow();
      await expect(vfs.deleteFile('/nonexistent/file.txt')).rejects.toThrow();
    });
  });

  describe('GraphMemoryIntegration', () => {
    let memoryIntegration: GraphMemoryIntegration;

    beforeEach(() => {
      memoryIntegration = new GraphMemoryIntegration(mockUserId, mockSessionId);
    });

    test('should store conversation', async () => {
      const userMessage = 'Hello, I need help';
      const agentResponse = 'I can help you with that';
      const agentState: AgentState = {
        messages: [],
        currentAgent: 'ceo',
        taskStatus: {
          id: 'task-1',
          type: 'strategic_planning',
          status: 'processing',
          priority: 'medium',
          createdAt: new Date(),
          updatedAt: new Date()
        }
      };

      const nodeId = await memoryIntegration.storeConversation(
        userMessage,
        agentResponse,
        'ceo',
        agentState
      );

      expect(nodeId).toBeDefined();
      expect(typeof nodeId).toBe('string');
    });

    test('should store task result', async () => {
      const task: TaskStatus = {
        id: 'task-1',
        type: 'market_research',
        status: 'completed',
        priority: 'high',
        createdAt: new Date(),
        updatedAt: new Date()
      };

      const result = { insights: ['Market is growing', 'Competition is high'] };

      const nodeId = await memoryIntegration.storeTaskResult(task, result, 'strategy');

      expect(nodeId).toBeDefined();
      expect(typeof nodeId).toBe('string');
    });

    test('should store insights', async () => {
      const insight = 'Users prefer mobile-first design';
      const nodeId = await memoryIntegration.storeInsight(
        insight,
        'technical',
        'devops',
        0.9,
        ['design', 'mobile']
      );

      expect(nodeId).toBeDefined();
      expect(typeof nodeId).toBe('string');
    });

    test('should search memory', async () => {
      // First store some data
      await memoryIntegration.storeInsight(
        'Market analysis shows growth',
        'business',
        'strategy'
      );

      const results = await memoryIntegration.searchMemory({
        query: 'market growth',
        maxResults: 10
      });

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);
    });

    test('should provide analytics', async () => {
      // Store some test data
      await memoryIntegration.storeInsight('Test insight 1', 'business', 'strategy');
      await memoryIntegration.storeInsight('Test insight 2', 'technical', 'devops');

      const analytics = await memoryIntegration.getAnalytics();

      expect(analytics).toBeDefined();
      expect(analytics.totalNodes).toBeGreaterThan(0);
      expect(analytics.nodesByType).toBeDefined();
      expect(analytics.nodesByAgent).toBeDefined();
    });
  });

  describe('FirebaseRealtimeIntegration', () => {
    let realtimeIntegration: FirebaseRealtimeIntegration;

    beforeEach(() => {
      realtimeIntegration = new FirebaseRealtimeIntegration(
        mockUserId,
        mockSessionId,
        {
          enabled: false, // Disable for tests
          channels: ['test'],
          syncStrategy: 'optimistic',
          conflictResolution: 'last_write_wins'
        }
      );
    });

    test('should initialize session', async () => {
      await expect(realtimeIntegration.initializeSession(mockUserContext)).resolves.not.toThrow();
    });

    test('should store messages', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      const messageId = await realtimeIntegration.storeMessage(
        'Test message',
        'user'
      );

      expect(messageId).toBeDefined();
      expect(typeof messageId).toBe('string');
    });

    test('should store tasks', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      const taskId = await realtimeIntegration.storeTask({
        userId: mockUserId,
        sessionId: mockSessionId,
        type: 'market_research',
        status: 'pending',
        priority: 'medium',
        title: 'Test Task',
        description: 'Test task description'
      });

      expect(taskId).toBeDefined();
      expect(typeof taskId).toBe('string');
    });

    test('should update task status', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      const taskId = await realtimeIntegration.storeTask({
        userId: mockUserId,
        sessionId: mockSessionId,
        type: 'market_research',
        status: 'pending',
        priority: 'medium',
        title: 'Test Task',
        description: 'Test task description'
      });

      await expect(realtimeIntegration.updateTaskStatus(taskId, 'completed')).resolves.not.toThrow();
    });

    test('should send notifications', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      const notificationId = await realtimeIntegration.sendNotification(
        'info',
        'Test Notification',
        'This is a test notification'
      );

      expect(notificationId).toBeDefined();
      expect(typeof notificationId).toBe('string');
    });

    test('should get conversation history', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      // Store some messages
      await realtimeIntegration.storeMessage('Message 1', 'user');
      await realtimeIntegration.storeMessage('Message 2', 'agent', 'ceo');

      const history = await realtimeIntegration.getConversationHistory();

      expect(history).toBeDefined();
      expect(Array.isArray(history)).toBe(true);
      expect(history.length).toBeGreaterThanOrEqual(2);
    });

    test('should get active tasks', async () => {
      await realtimeIntegration.initializeSession(mockUserContext);

      // Store some tasks
      await realtimeIntegration.storeTask({
        userId: mockUserId,
        sessionId: mockSessionId,
        type: 'task1',
        status: 'pending',
        priority: 'medium',
        title: 'Task 1',
        description: 'Description 1'
      });

      await realtimeIntegration.storeTask({
        userId: mockUserId,
        sessionId: mockSessionId,
        type: 'task2',
        status: 'processing',
        priority: 'high',
        title: 'Task 2',
        description: 'Description 2'
      });

      const activeTasks = await realtimeIntegration.getActiveTasks();

      expect(activeTasks).toBeDefined();
      expect(Array.isArray(activeTasks)).toBe(true);
      expect(activeTasks.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Integration Tests', () => {
    test('should orchestrate complete workflow', async () => {
      const testOrchestrator = new AgentOrchestrator({
        userId: mockUserId,
        sessionConfig: {
          maxSessionDuration: 120,
          maxConcurrentTasks: 5,
          enableRealtimeSync: false,
          persistenceStrategy: 'immediate'
        },
        agentConfigs: {
          ceo: {
            id: 'ceo-agent',
            name: 'CEO Agent',
            type: 'ceo',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test CEO prompt',
            capabilities: [],
            delegationRules: [],
            maxDelegationDepth: 2,
            approvalThreshold: 0.8,
            autoApproveTasks: []
          },
          strategy: {
            id: 'strategy-agent',
            name: 'Strategy Agent',
            type: 'strategy',
            model: 'gpt-4o-mini',
            temperature: 0.7,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test Strategy prompt',
            capabilities: [],
            delegationRules: []
          },
          devops: {
            id: 'devops-agent',
            name: 'DevOps Agent',
            type: 'devops',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test DevOps prompt',
            capabilities: [],
            delegationRules: []
          }
        },
        performanceConfig: {
          enableWorklets: false,
          maxWorkletConcurrency: 1,
          enableStreaming: false,
          chunkSize: 500
        }
      });

      await testOrchestrator.initialize();

      // Test a complete user journey
      const marketResearchResponse = await testOrchestrator.processUserMessage(
        'Research the SaaS market for small businesses'
      );

      expect(marketResearchResponse.success).toBe(true);

      const codeAnalysisResponse = await testOrchestrator.processUserMessage(
        'Review this React component for best practices'
      );

      expect(codeAnalysisResponse.success).toBe(true);

      const metrics = await testOrchestrator.getAgentMetrics();
      expect(metrics.orchestrator.totalTasks).toBeGreaterThan(0);
      expect(metrics.orchestrator.completedTasks).toBeGreaterThan(0);

      await testOrchestrator.cleanup();
    });

    test('should handle errors gracefully', async () => {
      const testOrchestrator = new AgentOrchestrator({
        userId: mockUserId,
        sessionConfig: {
          maxSessionDuration: 120,
          maxConcurrentTasks: 5,
          enableRealtimeSync: false,
          persistenceStrategy: 'immediate'
        },
        agentConfigs: {
          ceo: {
            id: 'ceo-agent',
            name: 'CEO Agent',
            type: 'ceo',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test CEO prompt',
            capabilities: [],
            delegationRules: [],
            maxDelegationDepth: 2,
            approvalThreshold: 0.8,
            autoApproveTasks: []
          },
          strategy: {
            id: 'strategy-agent',
            name: 'Strategy Agent',
            type: 'strategy',
            model: 'gpt-4o-mini',
            temperature: 0.7,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test Strategy prompt',
            capabilities: [],
            delegationRules: []
          },
          devops: {
            id: 'devops-agent',
            name: 'DevOps Agent',
            type: 'devops',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            maxTokens: 1000,
            tools: [],
            systemPrompt: 'Test DevOps prompt',
            capabilities: [],
            delegationRules: []
          }
        },
        performanceConfig: {
          enableWorklets: false,
          maxWorkletConcurrency: 1,
          enableStreaming: false,
          chunkSize: 500
        }
      });

      await testOrchestrator.initialize();

      // Test with malformed input
      const response = await testOrchestrator.processUserMessage('');

      expect(response).toBeDefined();
      expect(response.success).toBeDefined(); // May be true or false, but should not crash

      await testOrchestrator.cleanup();
    });
  });
});