/**
 * Netlify Functions Service
 * Replaces Firebase Functions Service with Netlify API calls
 */

// Type definitions for API calls
export interface VectorSearchParams {
  queryEmbedding: number[];
  matchThreshold?: number;
  limit?: number;
  collection?: string;
}

export interface VectorSearchResult {
  id: string;
  content: string;
  type: string;
  similarity: number;
  metadata?: Record<string, any>;
}

export interface GraphSearchParams {
  nodeId: string;
  depth?: number;
  includeDirection?: 'both' | 'incoming' | 'outgoing';
}

export interface GraphSearchResult {
  nodes: Array<{
    id: string;
    type: string;
    content: string;
    metadata?: Record<string, any>;
  }>;
  edges: Array<{
    sourceId: string;
    targetId: string;
    relation: string;
  }>;
}

export interface EmbeddingParams {
  text: string;
  model?: string;
}

export interface EmbeddingResult {
  embedding: number[];
  dimensions: number;
  model: string;
}

export interface PathFindingParams {
  sourceId: string;
  targetId: string;
  maxDepth?: number;
  relationTypes?: string[];
}

export interface NeighborParams {
  nodeId: string;
  direction?: 'both' | 'incoming' | 'outgoing';
  relationTypes?: string[];
}

export class NetlifyApiService {
  private static instance: NetlifyApiService;
  private baseUrl: string;

  private constructor() {
    // Use relative URLs for same-origin requests, or configure base URL
    this.baseUrl = process.env.NETLIFY_API_URL || '';
  }

  static getInstance(): NetlifyApiService {
    if (!NetlifyApiService.instance) {
      NetlifyApiService.instance = new NetlifyApiService();
    }
    return NetlifyApiService.instance;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...defaultHeaders,
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `API request failed: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error(`API request to ${endpoint} failed:`, error);
      throw error;
    }
  }

  // Vector Search Methods
  async vectorSearch(params: VectorSearchParams): Promise<VectorSearchResult[]> {
    const response = await this.makeRequest<{ success: boolean; results: VectorSearchResult[] }>(
      '/api/vector/search',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );

    return response.results;
  }

  // Embedding Generation Methods
  async generateEmbedding(params: EmbeddingParams): Promise<EmbeddingResult> {
    return await this.makeRequest<EmbeddingResult>(
      '/api/vector/embeddings',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  }

  // Graph Operations Methods
  async getSubgraph(params: GraphSearchParams): Promise<GraphSearchResult> {
    const response = await this.makeRequest<
      { success: boolean; nodes: GraphSearchResult['nodes']; edges: GraphSearchResult['edges'] }
    >('/api/graph/subgraph', {
      method: 'POST',
      body: JSON.stringify(params),
    });

    return {
      nodes: response.nodes,
      edges: response.edges,
    };
  }

  async findPaths(params: PathFindingParams): Promise<{
    paths: Array<{
      nodes: string[];
      edges: Array<{
        sourceId: string;
        targetId: string;
        relation: string;
      }>;
      length: number;
    }>;
  }> {
    const response = await this.makeRequest<{ success: boolean; paths: any[] }>(
      `/api/graph/traversal?action=paths`,
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );

    return {
      paths: response.paths,
    };
  }

  async getNeighbors(params: NeighborParams): Promise<{
    nodes: GraphSearchResult['nodes'];
    edges: GraphSearchResult['edges'];
  }> {
    const response = await this.makeRequest<
      { success: boolean; nodes: GraphSearchResult['nodes']; edges: GraphSearchResult['edges'] }
    >(`/api/graph/traversal?action=neighbors`, {
      method: 'POST',
      body: JSON.stringify(params),
    });

    return {
      nodes: response.nodes,
      edges: response.edges,
    };
  }

  // Health Check Methods
  async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    services: Record<string, boolean>;
    timestamp: string;
  }> {
    const services = {
      'vector-search': false,
      'vector-embeddings': false,
      'graph-subgraph': false,
      'graph-traversal': false,
    };

    const results = await Promise.allSettled([
      this.makeRequest('/api/vector/search', { method: 'GET' }),
      this.makeRequest('/api/vector/embeddings', { method: 'GET' }),
      this.makeRequest('/api/graph/subgraph', { method: 'GET' }),
      this.makeRequest('/api/graph/traversal', { method: 'GET' }),
    ]);

    results.forEach((result, index) => {
      const serviceNames = Object.keys(services);
      if (result.status === 'fulfilled') {
        services[serviceNames[index] as keyof typeof services] = true;
      }
    });

    const healthyCount = Object.values(services).filter(Boolean).length;
    const totalCount = Object.keys(services).length;

    return {
      status: healthyCount === totalCount ? 'healthy' :
              healthyCount > 0 ? 'degraded' : 'unhealthy',
      services,
      timestamp: new Date().toISOString(),
    };
  }
}

// Export singleton instance
export default NetlifyApiService.getInstance();