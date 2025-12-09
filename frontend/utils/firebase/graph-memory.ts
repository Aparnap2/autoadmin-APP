import { firebaseService, GraphNode, GraphEdge } from '../../lib/firebase';
import { NetlifyApiService } from '../../services/netlify/api.service';

/**
 * Firebase-based Graph Memory Service for Shared Knowledge Management
 *
 * This service implements the "Brain" of the AutoAdmin system using
 * Firebase Firestore as a graph database with vector similarity search
 * via Netlify Functions.
 */
export class GraphMemoryService {
  private apiService: NetlifyApiService;
  private embeddingCache: Map<string, number[]> = new Map();
  private openaiEmbeddings: any;

  constructor() {
    this.apiService = NetlifyApiService.getInstance();
  }

  /**
   * Initialize embeddings service (OpenAI or compatible)
   */
  private async getEmbeddings() {
    if (!this.openaiEmbeddings) {
      // This would be initialized with your preferred embedding service
      // For now, we'll use Netlify API to generate embeddings
      this.openaiEmbeddings = {
        embed: async (text: string): Promise<number[]> => {
          try {
            const result = await this.apiService.generateEmbedding({
              text,
              model: 'text-embedding-ada-002'
            });
            return result.embedding;
          } catch (error) {
            console.error('Error generating embedding:', error);
            // Fallback to dummy embedding
            return new Array(1536).fill(0).map(() => Math.random());
          }
        }
      };
    }
    return this.openaiEmbeddings;
  }

  /**
   * Add a new node to the graph memory
   */
  async addMemory(
    content: string,
    type: GraphNode['type'],
    relatedNodeIds: string[] = [],
    metadata: Record<string, any> = {}
  ): Promise<GraphNode> {
    try {
      // Check cache first
      let embedding: number[];
      const cacheKey = `${content.substring(0, 100)}`; // Use first 100 chars as cache key

      if (this.embeddingCache.has(cacheKey)) {
        embedding = this.embeddingCache.get(cacheKey)!;
      } else {
        const embeddings = await this.getEmbeddings();
        embedding = await embeddings.embed(content);
        this.embeddingCache.set(cacheKey, embedding);
      }

      // Create the node
      const node = await firebaseService.addNode({
        type,
        content,
        embedding,
        ...metadata
      });

      // Create relationships (edges) to related nodes
      if (relatedNodeIds.length > 0) {
        await this.createMultipleRelationships(node.id, relatedNodeIds, 'related_to');
      }

      return node;
    } catch (error) {
      console.error('Error adding memory:', error);
      throw error;
    }
  }

  /**
   * Create multiple relationships at once
   */
  private async createMultipleRelationships(
    sourceId: string,
    targetIds: string[],
    relation: GraphEdge['relation']
  ): Promise<void> {
    try {
      const edges = targetIds.map(targetId => ({
        source_id: sourceId,
        target_id: targetId,
        relation
      }));

      // Batch create edges using Firebase Firestore
      const edgePromises = edges.map(edge =>
        firebaseService.addEdge({
          source_id: edge.source_id,
          target_id: edge.target_id,
          relation: edge.relation
        })
      );
      await Promise.all(edgePromises);
    } catch (error) {
      console.error('Error creating multiple relationships:', error);
      throw error;
    }
  }

  /**
   * Query the graph memory using semantic search
   */
  async queryGraph(
    question: string,
    matchThreshold: number = 0.7,
    expandContext: boolean = true
  ): Promise<{
    nodes: any[];
    context: string;
    graph: Array<{
      from: string;
      to: string;
      relation: string;
    }>;
  }> {
    try {
      const embeddings = await this.getEmbeddings();
      const queryEmbedding = await embeddings.embed(question);

      // Find relevant nodes using vector similarity via Firebase Functions
      const nodes = await firebaseService.queryGraph(queryEmbedding, matchThreshold);

      if (!expandContext || nodes.length === 0) {
        return {
          nodes,
          context: nodes.map(n => `${n.type}: ${n.content}`).join('\n'),
          graph: []
        };
      }

      // Expand context by getting neighboring nodes in the graph
      const context = [];
      const graph = [];

      for (const node of nodes) {
        context.push(`Node: ${node.content} (${node.type})`);

        // Use Netlify API to get subgraph around this node
        try {
          const subgraph = await this.apiService.getSubgraph({
            nodeId: node.id,
            depth: 1,
            includeDirection: 'both'
          });

          // Process the subgraph
          subgraph.nodes.forEach((relatedNode: any) => {
            if (relatedNode.id !== node.id) {
              context.push(`  Related: ${relatedNode.content} (${relatedNode.type})`);
            }
          });

          subgraph.edges.forEach((edge: any) => {
            graph.push({
              from: edge.sourceId,
              to: edge.targetId,
              relation: edge.relation
            });
          });
        } catch (subgraphError) {
          console.warn('Failed to get subgraph for node:', node.id, subgraphError);
        }
      }

      return {
        nodes,
        context: context.join('\n'),
        graph
      };
    } catch (error) {
      console.error('Error querying graph:', error);
      throw error;
    }
  }

  /**
   * Get all nodes of a specific type
   */
  async getNodesByType(type: GraphNode['type']): Promise<GraphNode[]> {
    try {
      // Use Firebase service search method
      return await firebaseService.searchNodes('', type);
    } catch (error) {
      console.error('Error getting nodes by type:', error);
      throw error;
    }
  }

  /**
   * Create a relationship between two nodes
   */
  async createRelationship(
    sourceId: string,
    targetId: string,
    relation: GraphEdge['relation']
  ): Promise<void> {
    try {
      await firebaseService.addEdge({
        source_id: sourceId,
        target_id: targetId,
        relation
      });
    } catch (error) {
      console.error('Error creating relationship:', error);
      throw error;
    }
  }

  /**
   * Get a subgraph around a specific node
   */
  async getSubgraph(nodeId: string, depth: number = 2): Promise<{
    nodes: GraphNode[];
    edges: GraphEdge[];
  }> {
    try {
      // Use Netlify API for efficient subgraph traversal
      const result = await this.apiService.getSubgraph({
        nodeId,
        depth,
        includeDirection: 'both'
      });

      return {
        nodes: result.nodes.map(node => ({
          id: node.id,
          type: node.type,
          content: node.content,
          embedding: null, // We don't return embeddings for subgraph queries
          created_at: new Date(), // Placeholder
          updated_at: null,
          metadata: node.metadata
        })),
        edges: result.edges.map(edge => ({
          source_id: edge.sourceId,
          target_id: edge.targetId,
          relation: edge.relation,
          created_at: new Date() // Placeholder
        }))
      };
    } catch (error) {
      console.error('Error getting subgraph:', error);
      throw error;
    }
  }

  /**
   * Add a business rule or constraint to the graph
   */
  async addBusinessRule(
    rule: string,
    appliesTo: string[],
    description?: string
  ): Promise<GraphNode> {
    return this.addMemory(
      description || rule,
      'business_rule',
      appliesTo,
      { rule, type: 'constraint' }
    );
  }

  /**
   * Add a trend or market insight
   */
  async addTrend(
    trend: string,
    confidence: number = 0.8,
    source?: string,
    relatedTopics: string[] = []
  ): Promise<GraphNode> {
    return this.addMemory(
      trend,
      'trend',
      relatedTopics,
      { confidence, source, type: 'market_insight' }
    );
  }

  /**
   * Add a metric or KPI
   */
  async addMetric(
    name: string,
    value: number,
    unit: string,
    target?: number,
    timeframe?: string
  ): Promise<GraphNode> {
    const content = `${name}: ${value}${unit}${target ? ` (target: ${target}${unit})` : ''}`;

    return this.addMemory(
      content,
      'metric',
      [],
      { value, unit, target, timeframe, name, type: 'kpi' }
    );
  }

  /**
   * Link a file or code to the graph
   */
  async addFileReference(
    filePath: string,
    description: string,
    implementsFeature?: string,
    dependencies: string[] = []
  ): Promise<GraphNode> {
    const relatedNodes = [...dependencies];
    if (implementsFeature) {
      relatedNodes.push(implementsFeature);
    }

    return this.addMemory(
      description,
      'file',
      relatedNodes,
      { filePath, type: 'code', fileType: filePath.split('.').pop() }
    );
  }

  /**
   * Get graph statistics
   */
  async getGraphStats(): Promise<{
    totalNodes: number;
    totalEdges: number;
    nodeTypes: Record<string, number>;
    density: number;
  }> {
    try {
      const [nodesCount, edgesCount] = await Promise.all([
        firebaseService.getCollectionStats('nodes'),
        firebaseService.getCollectionStats('edges')
      ]);

      // Get node type distribution using Firebase query
      const nodeTypesDistribution = await firebaseService.searchNodes('');
      const nodeTypes: Record<string, number> = {};
      nodeTypesDistribution.forEach((node: GraphNode) => {
        nodeTypes[node.type] = (nodeTypes[node.type] || 0) + 1;
      });

      const totalNodes = nodesCount.count;
      const totalEdges = edgesCount.count;

      return {
        totalNodes,
        totalEdges,
        nodeTypes,
        density: totalNodes > 1 ? totalEdges / (totalNodes * (totalNodes - 1) / 2) : 0
      };
    } catch (error) {
      console.error('Error getting graph stats:', error);
      throw error;
    }
  }

  /**
   * Find shortest path between two nodes
   */
  async findShortestPath(sourceId: string, targetId: string): Promise<{
    path: string[];
    edges: Array<{ from: string; to: string; relation: string }>;
    distance: number;
  } | null> {
    try {
      // Use Netlify API for path finding
      const result = await this.apiService.findPaths({
        sourceId,
        targetId,
        maxDepth: 10
      });

      if (result.paths.length === 0) {
        return null;
      }

      const shortestPath = result.paths[0];
      return {
        path: shortestPath.nodes,
        edges: shortestPath.edges.map((edge: any) => ({
          from: edge.sourceId,
          to: edge.targetId,
          relation: edge.relation
        })),
        distance: shortestPath.length
      };
    } catch (error) {
      console.error('Error finding shortest path:', error);
      // Fallback to null if API fails
      return null;
    }
  }

  /**
   * Get memory for a specific context or session
   */
  async getContextualMemory(
    context: string,
    limit: number = 10
  ): Promise<GraphNode[]> {
    try {
      const embeddings = await this.getEmbeddings();
      const contextEmbedding = await embeddings.embed(context);

      const results = await this.apiService.vectorSearch({
        queryEmbedding: contextEmbedding,
        matchThreshold: 0.6,
        limit,
        collection: 'nodes'
      });

      return results.map(result => ({
        id: result.id,
        type: result.type,
        content: result.content,
        embedding: null,
        created_at: new Date(),
        updated_at: null,
        metadata: result.metadata
      }));
    } catch (error) {
      console.error('Error getting contextual memory:', error);
      throw error;
    }
  }

  /**
   * Clear embedding cache
   */
  clearCache(): void {
    this.embeddingCache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; keys: string[] } {
    return {
      size: this.embeddingCache.size,
      keys: Array.from(this.embeddingCache.keys())
    };
  }
}

export default GraphMemoryService;