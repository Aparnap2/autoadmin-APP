/**
 * Basic functionality tests for AutoAdmin Agent System
 */

// Mock dependencies before importing
jest.mock('../../../utils/supabase/graph-memory', () => ({
  __esModule: true,
  default: class MockGraphMemoryService {
    async addMemory() { return { id: 'mock-id' }; }
    async queryGraph() { return { nodes: [], context: '', graph: [] }; }
    async getNodesByType() { return []; }
  }
}));

jest.mock('../../firebase/firestore.service', () => ({
  __esModule: true,
  default: class MockFirestoreService {
    static getInstance() { return new MockFirestoreService(); }
    setUserId() {}
    async saveMessage() { return 'mock-id'; }
    async getMessages() { return []; }
    async saveAgentState() {}
    async getAgentState() { return null; }
  }
}));

jest.mock('../../../lib/supabase', () => ({
  __esModule: true,
  createClientSupabaseClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({ insert: () => Promise.resolve({ data: { id: 'mock-id' } }) }),
        insert: () => Promise.resolve({ data: { id: 'mock-id' } })
      })
    })
  })
}));

describe('AutoAdmin Agent System - Basic Functionality', () => {
  // Test that modules can be imported
  test('should be able to import main agent classes', async () => {
    const { AgentOrchestrator } = await import('../index');
    expect(AgentOrchestrator).toBeDefined();
    expect(typeof AgentOrchestrator).toBe('function');
  });

  test('should be able to import agent types', async () => {
    const types = await import('../types');
    expect(types).toBeDefined();
    expect(types.TaskStatus).toBeDefined();
    expect(types.AgentResponse).toBeDefined();
    expect(types.AgentState).toBeDefined();
  });

  test('should create orchestrator with default config', async () => {
    const { createAgentSystem } = await import('../index');

    const orchestrator = createAgentSystem('test-user-123');

    expect(orchestrator).toBeDefined();
    expect(typeof orchestrator.initialize).toBe('function');
    expect(typeof orchestrator.processUserMessage).toBe('function');
  });

  test('should validate task status objects', async () => {
    const { validateTaskStatus, TASK_STATUS } = await import('../index');

    const validTask = {
      id: 'task-1',
      type: 'market_research',
      status: TASK_STATUS.PENDING,
      priority: 'medium',
      createdAt: new Date()
    };

    expect(validateTaskStatus(validTask)).toBe(true);

    const invalidTask = {
      id: 'task-1',
      // Missing required fields
    };

    expect(validateTaskStatus(invalidTask)).toBe(false);
  });

  test('should format processing time correctly', async () => {
    const { formatProcessingTime } = await import('../index');

    expect(formatProcessingTime(1000)).toBe('1s');
    expect(formatProcessingTime(65000)).toBe('1m 5s');
    expect(formatProcessingTime(3665000)).toBe('1h 1m 5s');
  });

  test('should calculate success rate correctly', async () => {
    const { calculateSuccessRate } = await import('../index');

    expect(calculateSuccessRate(10, 8)).toBe(80);
    expect(calculateSuccessRate(5, 5)).toBe(100);
    expect(calculateSuccessRate(0, 0)).toBe(0);
  });

  test('should estimate task complexity', async () => {
    const { estimateTaskComplexity, TASK_TYPES } = await import('../index');

    const marketResearchComplexity = estimateTaskComplexity(
      TASK_TYPES.MARKET_RESEARCH,
      'strategy'
    );

    expect(marketResearchComplexity.complexity).toBeGreaterThan(0);
    expect(marketResearchComplexity.estimatedTime).toBeGreaterThan(0);
    expect(typeof marketResearchComplexity.requiresBackend).toBe('boolean');
  });

  test('should validate agent configuration', async () => {
    const { validateAgentConfig } = await import('../index');

    const validConfig = {
      id: 'test-agent',
      name: 'Test Agent',
      type: 'strategy',
      model: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 2000,
      tools: [],
      systemPrompt: 'Test prompt',
      capabilities: [],
      delegationRules: []
    };

    expect(validateAgentConfig(validConfig)).toBe(true);

    const invalidConfig = {
      id: 'test-agent',
      // Missing required fields
    };

    expect(validateAgentConfig(invalidConfig)).toBe(false);
  });

  test('should export all expected constants', async () => {
    const exported = await import('../index');

    expect(exported.AGENT_TYPES).toBeDefined();
    expect(exported.TASK_TYPES).toBeDefined();
    expect(exported.TASK_STATUS).toBeDefined();
    expect(exported.PRIORITY_LEVELS).toBeDefined();

    expect(exported.AGENT_TYPES.CEO).toBe('ceo');
    expect(exported.AGENT_TYPES.STRATEGY).toBe('strategy');
    expect(exported.AGENT_TYPES.DEVOPS).toBe('devops');
  });

  test('should create quick setup instance', async () => {
    const { quickSetup } = await import('../index');

    const orchestrator = quickSetup('test-user-123');

    expect(orchestrator).toBeDefined();
    expect(typeof orchestrator.initialize).toBe('function');
  });

  test('should handle worklet utilities', async () => {
    const { WorkletUtils } = await import('../index');

    expect(WorkletUtils).toBeDefined();
    expect(typeof WorkletUtils.validateWorkletData).toBe('function');
    expect(typeof WorkletUtils.createOptimizedTask).toBe('function');
    expect(typeof WorkletUtils.sanitizeData).toBe('function');
  });
});