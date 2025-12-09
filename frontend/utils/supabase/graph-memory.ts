import { createClientSupabaseClient, Database, SupabaseService } from '../../lib/supabase';

/**
 * Graph Memory Service for Shared Knowledge Management
 *
 * This service implements the "Brain" of the AutoAdmin system using
 * Supabase as a graph database with vector similarity search.
 */
export class GraphMemoryService extends SupabaseService {
  private openaiEmbeddings: any;

  constructor() {
    super(createClientSupabaseClient());
  }

  /**
   * Initialize embeddings service (OpenAI or compatible)
   */
  private async getEmbeddings() {
    if (!this.openaiEmbeddings) {
      // This would be initialized with your preferred embedding service
      // For now, we'll use a placeholder
      this.openaiEmbeddings = {
        embed: async (text: string): Promise<number[]> => {
          // In production, this would call OpenAI's embedding API
          // or a self-hosted alternative like sentence-transformers
          // For now, return a dummy embedding
          return new Array(1536).fill(0).map(() => Math.random());
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
    type: Database['public']['Tables']['nodes']['Row']['type'],
    relatedNodeIds: string[] = [],
    metadata: Record<string, any> = {}
  ) {
    try {
      const embeddings = await this.getEmbeddings();
      const embedding = await embeddings.embed(content);

      // Create the node
      const node = await this.addNode({
        type,
        content,
        embedding,
        ...metadata
      });

      // Create relationships (edges) to related nodes
      if (relatedNodeIds.length > 0) {
        const edges = relatedNodeIds.map(targetId => ({
          source_id: node.id,
          target_id: targetId,
          relation: 'related_to'
        }));

        await this.client
          .from('edges')
          .insert(edges);
      }

      return node;
    } catch (error) {
      console.error('Error adding memory:', error);
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
  ) {
    try {
      const embeddings = await this.getEmbeddings();
      const queryEmbedding = await embeddings.embed(question);

      // Find relevant nodes using vector similarity
      const nodes = await this.queryGraph(queryEmbedding, matchThreshold);

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

        // Get outgoing edges
        const { data: outgoingEdges } = await this.client
          .from('edges')
          .select(`
            target_id,
            relation,
            nodes!edges_target_id_fkey (
              id,
              type,
              content
            )
          `)
          .eq('source_id', node.id);

        // Get incoming edges
        const { data: incomingEdges } = await this.client
          .from('edges')
          .select(`
            source_id,
            relation,
            nodes!edges_source_id_fkey (
              id,
              type,
              content
            )
          `)
          .eq('target_id', node.id);

        // Process outgoing edges
        if (outgoingEdges) {
          for (const edge of outgoingEdges) {
            const targetNode = edge.nodes;
            if (targetNode) {
              context.push(`  --[${edge.relation}]--> ${targetNode.content} (${targetNode.type})`);
              graph.push({
                from: node.id,
                to: targetNode.id,
                relation: edge.relation
              });
            }
          }
        }

        // Process incoming edges
        if (incomingEdges) {
          for (const edge of incomingEdges) {
            const sourceNode = edge.nodes;
            if (sourceNode) {
              context.push(`  <--[${edge.relation}]-- ${sourceNode.content} (${sourceNode.type})`);
              graph.push({
                from: sourceNode.id,
                to: node.id,
                relation: edge.relation
              });
            }
          }
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
  async getNodesByType(type: Database['public']['Tables']['nodes']['Row']['type']) {
    try {
      const { data, error } = await this.client
        .from('nodes')
        .select('*')
        .eq('type', type)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
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
    relation: Database['public']['Tables']['edges']['Row']['relation']
  ) {
    try {
      const { data, error } = await this.client
        .from('edges')
        .insert({
          source_id: sourceId,
          target_id: targetId,
          relation
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error creating relationship:', error);
      throw error;
    }
  }

  /**
   * Get a subgraph around a specific node
   */
  async getSubgraph(nodeId: string, depth: number = 2) {
    try {
      // This is a simplified version - in production you'd want
      // a recursive CTE or a more efficient graph traversal
      const { data: edges } = await this.client
        .from('edges')
        .select(`
          *,
          source_node:source_id!edges_source_id_fkey (
            id,
            type,
            content
          ),
          target_node:target_id!edges_target_id_fkey (
            id,
            type,
            content
          )
        `)
        .or(`source_id.eq.${nodeId},target_id.eq.${nodeId}`);

      if (!edges) return { nodes: [], edges: [] };

      // Collect all unique node IDs
      const nodeIds = new Set<string>();
      nodeIds.add(nodeId);

      edges.forEach(edge => {
        nodeIds.add(edge.source_id);
        nodeIds.add(edge.target_id);
      });

      // Get all nodes in the subgraph
      const { data: nodes } = await this.client
        .from('nodes')
        .select('*')
        .in('id', Array.from(nodeIds));

      return {
        nodes: nodes || [],
        edges: edges || []
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
  ) {
    return this.addMemory(
      description || rule,
      'business_rule',
      appliesTo,
      { rule }
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
  ) {
    return this.addMemory(
      trend,
      'trend',
      relatedTopics,
      { confidence, source }
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
  ) {
    const content = `${name}: ${value}${unit}${target ? ` (target: ${target}${unit})` : ''}`;

    return this.addMemory(
      content,
      'metric',
      [],
      { value, unit, target, timeframe, name }
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
  ) {
    const relatedNodes = dependencies;
    if (implementsFeature) {
      // Would need to find the feature node first
      relatedNodes.push(implementsFeature);
    }

    return this.addMemory(
      description,
      'file',
      relatedNodes,
      { filePath, type: 'code' }
    );
  }

  /**
   * Get graph statistics
   */
  async getGraphStats() {
    try {
      const { count: nodeCount } = await this.client
        .from('nodes')
        .select('*', { count: 'exact', head: true });

      const { count: edgeCount } = await this.client
        .from('edges')
        .select('*', { count: 'exact', head: true });

      const { data: nodeTypes } = await this.client
        .from('nodes')
        .select('type')
        .then(({ data }) => {
          const counts: Record<string, number> = {};
          data?.forEach(node => {
            counts[node.type] = (counts[node.type] || 0) + 1;
          });
          return counts;
        });

      return {
        totalNodes: nodeCount || 0,
        totalEdges: edgeCount || 0,
        nodeTypes: nodeTypes || {},
        density: nodeCount > 1 ? (edgeCount || 0) / (nodeCount * (nodeCount - 1) / 2) : 0
      };
    } catch (error) {
      console.error('Error getting graph stats:', error);
      throw error;
    }
  }
}

export default GraphMemoryService;