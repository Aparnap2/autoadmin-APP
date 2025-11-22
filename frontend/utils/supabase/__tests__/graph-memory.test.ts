import GraphMemoryService from '../graph-memory';
import { Database } from '../../../lib/supabase';

// Mock the Supabase client
const mockSupabase = {
  from: jest.fn(),
  auth: {
    setSession: jest.fn(),
    getUser: jest.fn()
  }
};

jest.mock('../../../lib/supabase', () => ({
  createClientSupabaseClient: jest.fn(() => mockSupabase)
}));

describe('GraphMemoryService', () => {
  let graphMemory;

  beforeEach(() => {
    graphMemory = new GraphMemoryService();
    jest.clearAllMocks();
  });

  describe('addMemory', () => {
    it('should add a memory with embedding', async () => {
      // Mock embedding service
      const mockEmbedding = new Array(1536).fill(0.5);

      // Mock node creation
      const mockNode = {
        id: 'node-123',
        type: 'feature',
        content: 'Test feature',
        embedding: mockEmbedding
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
          })
        })
      });

      const result = await graphMemory.addMemory(
        'Test feature',
        'feature',
        [],
        { description: 'Test description' }
      );

      expect(result).toEqual(mockNode);
      expect(mockSupabase.from).toHaveBeenCalledWith('nodes');
    });

    it('should create relationships when relatedNodeIds are provided', async () => {
      const mockNode = {
        id: 'node-123',
        type: 'feature',
        content: 'Test feature',
        embedding: []
      };

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'nodes') {
          return {
            insert: jest.fn().mockReturnValue({
              select: jest.fn().mockReturnValue({
                single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
              })
            })
          };
        }
        if (table === 'edges') {
          return {
            insert: jest.fn().mockResolvedValue({ data: [], error: null })
          };
        }
        return mockSupabase.from(table);
      });

      await graphMemory.addMemory(
        'Test feature',
        'feature',
        ['related-node-1', 'related-node-2']
      );

      expect(mockSupabase.from).toHaveBeenCalledWith('edges');
      expect(mockSupabase.from().insert).toHaveBeenCalledWith([
        {
          source_id: 'node-123',
          target_id: 'related-node-1',
          relation: 'related_to'
        },
        {
          source_id: 'node-123',
          target_id: 'related-node-2',
          relation: 'related_to'
        }
      ]);
    });
  });

  describe('queryGraph', () => {
    it('should query graph and return context', async () => {
      const mockNodes = [
        { id: 'node-1', type: 'feature', content: 'Feature 1', similarity: 0.9 },
        { id: 'node-2', type: 'rule', content: 'Rule 1', similarity: 0.8 }
      ];

      const mockOutgoingEdges = [
        {
          target_id: 'target-1',
          relation: 'implements',
          nodes: {
            id: 'target-1',
            type: 'file',
            content: 'File 1'
          }
        }
      ];

      const mockIncomingEdges = [
        {
          source_id: 'source-1',
          relation: 'depends_on',
          nodes: {
            id: 'source-1',
            type: 'feature',
            content: 'Source Feature'
          }
        }
      ];

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'rpc') {
          return {
            mockReturnValue: jest.fn().mockResolvedValue({ data: mockNodes, error: null })
          };
        }
        if (table === 'edges') {
          return {
            select: jest.fn().mockReturnValue({
              eq: jest.fn().mockReturnValue({
                data: mockOutgoingEdges
              })
            }),
            select: jest.fn().mockReturnValue({
              eq: jest.fn().mockReturnValue({
                data: mockIncomingEdges
              })
            })
          };
        }
        return mockSupabase.from(table);
      });

      const result = await graphMemory.queryGraph('test question', 0.7, true);

      expect(result.nodes).toEqual(mockNodes);
      expect(result.context).toContain('Feature 1 (feature)');
      expect(result.graph).toHaveLength(2); // One outgoing, one incoming edge
    });

    it('should return basic results when expandContext is false', async () => {
      const mockNodes = [
        { id: 'node-1', type: 'feature', content: 'Feature 1', similarity: 0.9 }
      ];

      mockSupabase.rpc = jest.fn().mockResolvedValue({ data: mockNodes, error: null });

      const result = await graphMemory.queryGraph('test question', 0.7, false);

      expect(result.nodes).toEqual(mockNodes);
      expect(result.context).toBe('Feature 1 (feature)');
      expect(result.graph).toEqual([]);
    });
  });

  describe('getNodesByType', () => {
    it('should get nodes by type', async () => {
      const mockNodes = [
        { id: 'node-1', type: 'feature', content: 'Feature 1' },
        { id: 'node-2', type: 'feature', content: 'Feature 2' }
      ];

      mockSupabase.from.mockReturnValue({
        select: jest.fn().mockReturnValue({
          eq: jest.fn().mockReturnValue({
            order: jest.fn().mockResolvedValue({ data: mockNodes, error: null })
          })
        })
      });

      const result = await graphMemory.getNodesByType('feature');

      expect(result).toEqual(mockNodes);
      expect(mockSupabase.from).toHaveBeenCalledWith('nodes');
      expect(mockSupabase.from().select().eq).toHaveBeenCalledWith('type', 'feature');
    });
  });

  describe('createRelationship', () => {
    it('should create a relationship between nodes', async () => {
      const mockEdge = {
        source_id: 'source-1',
        target_id: 'target-1',
        relation: 'implements'
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockEdge, error: null })
          })
        })
      });

      const result = await graphMemory.createRelationship('source-1', 'target-1', 'implements');

      expect(result).toEqual(mockEdge);
      expect(mockSupabase.from).toHaveBeenCalledWith('edges');
    });
  });

  describe('getSubgraph', () => {
    it('should get subgraph around a node', async () => {
      const mockEdges = [
        {
          source_id: 'node-1',
          target_id: 'node-2',
          relation: 'implements',
          nodes: { id: 'node-2', type: 'file', content: 'File 2' }
        }
      ];

      const mockNodes = [
        { id: 'node-1', type: 'feature', content: 'Feature 1' },
        { id: 'node-2', type: 'file', content: 'File 2' }
      ];

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'edges') {
          return {
            select: jest.fn().mockReturnValue({
              or: jest.fn().mockResolvedValue({ data: mockEdges, error: null })
            })
          };
        }
        if (table === 'nodes') {
          return {
            select: jest.fn().mockReturnValue({
              in: jest.fn().mockResolvedValue({ data: mockNodes, error: null })
            })
          };
        }
        return mockSupabase.from(table);
      });

      const result = await graphMemory.getSubgraph('node-1', 2);

      expect(result.nodes).toEqual(mockNodes);
      expect(result.edges).toEqual(mockEdges);
    });
  });

  describe('Specialized Memory Methods', () => {
    it('should add business rules', async () => {
      const mockNode = {
        id: 'rule-123',
        type: 'business_rule',
        content: 'Test rule'
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
          })
        })
      });

      const result = await graphMemory.addBusinessRule(
        'All features must have tests',
        ['feature-1', 'feature-2'],
        'Testing requirement'
      );

      expect(result).toEqual(mockNode);
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'business_rule',
          rule: 'All features must have tests'
        })
      );
    });

    it('should add trends', async () => {
      const mockNode = {
        id: 'trend-123',
        type: 'trend',
        content: 'AI is trending'
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
          })
        })
      });

      const result = await graphMemory.addTrend(
        'AI is trending',
        0.9,
        'Twitter',
        ['machine-learning', 'automation']
      );

      expect(result).toEqual(mockNode);
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'trend',
          confidence: 0.9,
          source: 'Twitter'
        })
      );
    });

    it('should add metrics', async () => {
      const mockNode = {
        id: 'metric-123',
        type: 'metric',
        content: 'User Count: 1000 (target: 1500)'
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
          })
        })
      });

      const result = await graphMemory.addMetric(
        'User Count',
        1000,
        'users',
        1500,
        'monthly'
      );

      expect(result).toEqual(mockNode);
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'metric',
          value: 1000,
          unit: 'users',
          target: 1500,
          timeframe: 'monthly',
          name: 'User Count'
        })
      );
    });

    it('should add file references', async () => {
      const mockNode = {
        id: 'file-123',
        type: 'file',
        content: 'Implementation of auth system'
      };

      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: mockNode, error: null })
          })
        })
      });

      const result = await graphMemory.addFileReference(
        'src/auth/index.ts',
        'Implementation of auth system',
        'auth-feature',
        ['dependency-1', 'dependency-2']
      );

      expect(result).toEqual(mockNode);
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'file',
          filePath: 'src/auth/index.ts',
          type: 'code'
        })
      );
    });
  });

  describe('getGraphStats', () => {
    it('should return graph statistics', async () => {
      mockSupabase.from.mockImplementation((table) => {
        if (table === 'nodes') {
          return {
            select: jest.fn().mockReturnValue({
              count: 'exact',
              head: jest.fn().mockResolvedValue({ count: 100, error: null })
            }),
            select: jest.fn().mockReturnValue({
              data: [
                { type: 'feature' },
                { type: 'feature' },
                { type: 'rule' },
                { type: 'trend' }
              ],
              then: jest.fn().mockImplementation((callback) => {
                const data = [
                  { type: 'feature' },
                  { type: 'feature' },
                  { type: 'rule' },
                  { type: 'trend' }
                ];
                const counts = { feature: 2, rule: 1, trend: 1 };
                return callback({ data });
              })
            })
          };
        }
        if (table === 'edges') {
          return {
            select: jest.fn().mockReturnValue({
              count: 'exact',
              head: jest.fn().mockResolvedValue({ count: 50, error: null })
            })
          };
        }
        return mockSupabase.from(table);
      });

      const result = await graphMemory.getGraphStats();

      expect(result).toEqual({
        totalNodes: 100,
        totalEdges: 50,
        nodeTypes: { feature: 2, rule: 1, trend: 1 },
        density: 50 / (100 * 99 / 2) // Expected density calculation
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle errors in addMemory', async () => {
      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: null, error: new Error('Database error') })
          })
        })
      });

      await expect(graphMemory.addMemory('test', 'feature')).rejects.toThrow('Database error');
    });

    it('should handle errors in queryGraph', async () => {
      mockSupabase.rpc = jest.fn().mockResolvedValue({ data: null, error: new Error('Query error') });

      await expect(graphMemory.queryGraph('test')).rejects.toThrow('Query error');
    });

    it('should handle errors in createRelationship', async () => {
      mockSupabase.from.mockReturnValue({
        insert: jest.fn().mockReturnValue({
          select: jest.fn().mockReturnValue({
            single: jest.fn().mockResolvedValue({ data: null, error: new Error('Edge error') })
          })
        })
      });

      await expect(
        graphMemory.createRelationship('source', 'target', 'implements')
      ).rejects.toThrow('Edge error');
    });
  });
});