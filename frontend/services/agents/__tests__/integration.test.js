/**
 * Integration tests for AutoAdmin Agent System
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

// Mock OpenAI
jest.mock('@langchain/openai', () => ({
  ChatOpenAI: class MockChatOpenAI {
    constructor() {}
    async invoke() {
      return { content: 'Mock response from LLM' };
    }
  }
}));

// Mock LangChain core
jest.mock('@langchain/core/tools', () => ({
  tool: (fn, options) => fn
}));

jest.mock('@langchain/core/messages', () => ({
  BaseMessage: class MockBaseMessage {
    constructor(content) {
      this.content = content;
    }
    getType() { return 'human'; }
  },
  HumanMessage: class MockHumanMessage {
    constructor(content) {
      this.content = content;
    }
  },
  AIMessage: class MockAIMessage {
    constructor(content) {
      this.content = content;
    }
  }
}));

jest.mock('@langchain/langgraph/prebuilt', () => ({
  createReactAgent: () => ({
    invoke: () => ({
      messages: [{ content: 'Mock agent response' }]
    })
  })
}));

jest.mock('@langchain/langgraph', () => ({
  createSupervisor: () => ({
    compile: () => ({
      invoke: () => ({ messages: [] })
    })
  })
}));

// Mock environment variables
process.env.EXPO_PUBLIC_OPENAI_API_KEY = 'test-api-key';

describe('AutoAdmin Agent System - Integration Tests', () => {
  // Import after mocking
  let {
    AGENT_TYPES,
    TASK_TYPES,
    TASK_STATUS,
    PRIORITY_LEVELS,
    validateAgentConfig,
    validateTaskStatus,
    formatProcessingTime,
    calculateSuccessRate,
    estimateTaskComplexity
  } = require('../index');

  test('should have correct constant values', () => {
    expect(AGENT_TYPES.CEO).toBe('ceo');
    expect(AGENT_TYPES.STRATEGY).toBe('strategy');
    expect(AGENT_TYPES.DEVOPS).toBe('devops');

    expect(TASK_TYPES.MARKET_RESEARCH).toBe('market_research');
    expect(TASK_TYPES.FINANCIAL_ANALYSIS).toBe('financial_analysis');
    expect(TASK_TYPES.CODE_ANALYSIS).toBe('code_analysis');

    expect(TASK_STATUS.PENDING).toBe('pending');
    expect(TASK_STATUS.PROCESSING).toBe('processing');
    expect(TASK_STATUS.COMPLETED).toBe('completed');

    expect(PRIORITY_LEVELS.LOW).toBe('low');
    expect(PRIORITY_LEVELS.MEDIUM).toBe('medium');
    expect(PRIORITY_LEVELS.HIGH).toBe('high');
  });

  test('should validate task status objects correctly', () => {
    const validTask = {
      id: 'task-1',
      type: TASK_TYPES.MARKET_RESEARCH,
      status: TASK_STATUS.PENDING,
      priority: PRIORITY_LEVELS.MEDIUM,
      createdAt: new Date()
    };

    expect(validateTaskStatus(validTask)).toBe(true);

    const invalidTask = {
      id: 'task-1',
      type: 'invalid_type',
      status: 'invalid_status',
      priority: 'invalid_priority',
      createdAt: new Date()
    };

    expect(validateTaskStatus(invalidTask)).toBe(false);
  });

  test('should validate agent configuration correctly', () => {
    const validConfig = {
      id: 'test-agent',
      name: 'Test Agent',
      type: AGENT_TYPES.STRATEGY,
      model: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 2000,
      tools: [],
      systemPrompt: 'Test prompt with sufficient length',
      capabilities: [],
      delegationRules: []
    };

    expect(validateAgentConfig(validConfig)).toBe(true);

    const invalidConfig = {
      id: 'test-agent',
      name: 'Test Agent',
      // Missing required fields
    };

    expect(validateAgentConfig(invalidConfig)).toBe(false);
  });

  test('should format processing time correctly', () => {
    expect(formatProcessingTime(1000)).toBe('1s');
    expect(formatProcessingTime(65000)).toBe('1m 5s');
    expect(formatProcessingTime(3665000)).toBe('1h 1m 5s');
    expect(formatProcessingTime(0)).toBe('0s');
  });

  test('should calculate success rate correctly', () => {
    expect(calculateSuccessRate(10, 8)).toBe(80);
    expect(calculateSuccessRate(5, 5)).toBe(100);
    expect(calculateSuccessRate(10, 3)).toBe(30);
    expect(calculateSuccessRate(0, 0)).toBe(0);
  });

  test('should estimate task complexity correctly', () => {
    const marketResearchComplexity = estimateTaskComplexity(
      TASK_TYPES.MARKET_RESEARCH,
      'strategy'
    );

    expect(marketResearchComplexity.complexity).toBeGreaterThan(0);
    expect(marketResearchComplexity.complexity).toBeLessThanOrEqual(10);
    expect(marketResearchComplexity.estimatedTime).toBeGreaterThan(0);
    expect(typeof marketResearchComplexity.requiresBackend).toBe('boolean');

    const codeAnalysisComplexity = estimateTaskComplexity(
      TASK_TYPES.CODE_ANALYSIS,
      'devops'
    );

    expect(codeAnalysisComplexity.complexity).toBeGreaterThan(0);
    expect(codeAnalysisComplexity.estimatedTime).toBeGreaterThan(0);
  });

  test('should handle different task types with appropriate complexity', () => {
    const strategicPlanning = estimateTaskComplexity(TASK_TYPES.STRATEGIC_PLANNING, 'strategy');
    const technicalDecision = estimateTaskComplexity(TASK_TYPES.TECHNICAL_DECISION, 'devops');

    // Strategic planning should generally be more complex than technical decisions
    expect(strategicPlanning.complexity).toBeGreaterThanOrEqual(technicalDecision.complexity);
  });

  test('should handle agent type multipliers correctly', () => {
    const strategyTask = estimateTaskComplexity(TASK_TYPES.MARKET_RESEARCH, 'strategy');
    const devopsTask = estimateTaskComplexity(TASK_TYPES.CODE_ANALYSIS, 'devops');
    const ceoTask = estimateTaskComplexity(TASK_TYPES.STRATEGIC_PLANNING, 'ceo');

    // Strategy agent should take longer than DevOps for similar complexity tasks
    expect(strategyTask.estimatedTime).toBeGreaterThan(devopsTask.estimatedTime);
  });

  test('should determine backend delegation correctly', () => {
    const simpleTask = estimateTaskComplexity(TASK_TYPES.CODE_ANALYSIS, 'devops');
    const complexTask = estimateTaskComplexity(TASK_TYPES.STRATEGIC_PLANNING, 'strategy');

    // Very complex tasks might require backend processing
    expect(typeof simpleTask.requiresBackend).toBe('boolean');
    expect(typeof complexTask.requiresBackend).toBe('boolean');
  });

  test('should handle edge cases correctly', () => {
    expect(calculateSuccessRate(-1, 0)).toBe(0);
    expect(calculateSuccessRate(10, 15)).toBe(150); // More completed than total
    expect(formatProcessingTime(-1000)).toBe('-1s');
    expect(validateTaskStatus(null)).toBe(false);
    expect(validateAgentConfig(null)).toBe(false);
  });
});