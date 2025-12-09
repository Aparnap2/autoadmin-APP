/**
 * Graph Subgraph API Endpoint - Netlify Function
 * Replaces Firebase Cloud Functions getSubgraph
 */

import { collection, doc, getDoc, getDocs, query, where, or, and } from 'firebase/firestore';
import { getFirestoreInstance } from '../../../../lib/firebase-singleton';
import { runTask, createApiResponse, validateRequestBody } from '../../utils/expo-serverless';

// Get Firestore singleton instance
const db = getFirestoreInstance();

// Interface definitions
interface GraphSearchParams {
  nodeId: string;
  depth?: number;
  includeDirection?: 'both' | 'incoming' | 'outgoing';
}

interface GraphSearchResult {
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

/**
 * BFS traversal to collect subgraph nodes and edges
 */
async function collectSubgraph(
  startNodeId: string,
  maxDepth: number,
  direction: 'both' | 'incoming' | 'outgoing'
): Promise<GraphSearchResult> {
  const visitedNodes = new Set<string>();
  const nodes: GraphSearchResult['nodes'] = [];
  const edges: GraphSearchResult['edges'] = [];

  const queue: Array<{ nodeId: string; depth: number }> = [
    { nodeId: startNodeId, depth: 0 }
  ];

  while (queue.length > 0) {
    const { nodeId, depth } = queue.shift()!;

    if (visitedNodes.has(nodeId) || depth > maxDepth) {
      continue;
    }

    visitedNodes.add(nodeId);

    // Get node data
    const nodeDoc = await getDoc(doc(db, 'nodes', nodeId));
    if (nodeDoc.exists()) {
      const nodeData = nodeDoc.data();
      nodes.push({
        id: nodeDoc.id,
        type: nodeData?.type || '',
        content: nodeData?.content || '',
        metadata: nodeData?.metadata
      });
    }

    // Get connected edges
    let edgesQuery;
    if (direction === 'both') {
      edgesQuery = query(
        collection(db, 'edges'),
        or(
          where('source_id', '==', nodeId),
          where('target_id', '==', nodeId)
        )
      );
    } else if (direction === 'outgoing') {
      edgesQuery = query(
        collection(db, 'edges'),
        where('source_id', '==', nodeId)
      );
    } else {
      edgesQuery = query(
        collection(db, 'edges'),
        where('target_id', '==', nodeId)
      );
    }

    const edgesSnapshot = await getDocs(edgesQuery);

    for (const edgeDoc of edgesSnapshot) {
      const edgeData = edgeDoc.data();
      const sourceId = edgeData.source_id;
      const targetId = edgeData.target_id;

      edges.push({
        sourceId,
        targetId,
        relation: edgeData.relation
      });

      // Add connected nodes to queue if within depth limit
      if (depth < maxDepth) {
        const nextNodeId = sourceId === nodeId ? targetId : sourceId;
        if (!visitedNodes.has(nextNodeId)) {
          queue.push({ nodeId: nextNodeId, depth: depth + 1 });
        }
      }
    }
  }

  return { nodes, edges };
}

/**
 * POST /api/graph/subgraph
 * Get subgraph around a specific node
 */
export async function POST(request: Request) {
  try {
    // Parse and validate request body
    const body = validateRequestBody(await request.json(), (data: any) => {
      if (!data.nodeId || typeof data.nodeId !== 'string') {
        throw new Error('nodeId is required and must be a string');
      }
      const depth = Math.min(Math.max(data.depth ?? 2, 1), 5);
      return {
        nodeId: data.nodeId,
        depth,
        includeDirection: data.includeDirection ?? 'both'
      } as GraphSearchParams;
    });

    const { nodeId, depth, includeDirection } = body;

    // Check if start node exists
    const startNodeDoc = await getDoc(doc(db, 'nodes', nodeId));
    if (!startNodeDoc.exists()) {
      return createApiResponse(false, undefined, 'Start node not found', 404);
    }

    // Collect subgraph using background task
    let result: GraphSearchResult = { nodes: [], edges: [] };
    await runTask(async () => {
      result = await collectSubgraph(nodeId, depth, includeDirection);
    });

    return createApiResponse(true, {
      nodes: result.nodes,
      edges: result.edges,
      count: {
        nodes: result.nodes.length,
        edges: result.edges.length
      }
    });

  } catch (error) {
    console.error('Subgraph search error:', error);
    return createApiResponse(
      false,
      undefined,
      `Subgraph search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

/**
 * GET /api/graph/subgraph
 * Health check endpoint
 */
export async function GET() {
  return Response.json({
    status: 'healthy',
    service: 'graph-subgraph',
    timestamp: new Date().toISOString()
  });
}

/**
 * Default export for Expo/Next.js API route compatibility
 * This is needed for proper React component detection
 */
export default function handler() {
  // This is a placeholder export to satisfy Expo/Next.js requirements
  // The actual API functionality is handled by GET/POST methods
  return null;
}