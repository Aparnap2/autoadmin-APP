/**
 * Graph Traversal API Endpoint - Netlify Function
 * Advanced graph traversal and path finding operations
 */

import { collection, doc, getDoc, getDocs, query, where } from 'firebase/firestore';
import { getFirestoreInstance } from '../../../../lib/firebase-singleton';
import { runTask, createApiResponse } from '../../utils/expo-serverless';

// Get Firestore singleton instance
const db = getFirestoreInstance();

// Interface definitions
interface PathFindingParams {
  sourceId: string;
  targetId: string;
  maxDepth?: number;
  relationTypes?: string[];
}

interface PathFindingResult {
  paths: Array<{
    nodes: string[];
    edges: Array<{
      sourceId: string;
      targetId: string;
      relation: string;
    }>;
    length: number;
  }>;
}

interface NeighborParams {
  nodeId: string;
  direction?: 'both' | 'incoming' | 'outgoing';
  relationTypes?: string[];
}

interface NeighborResult {
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
 * Find all paths between two nodes using BFS
 */
async function findPaths(
  sourceId: string,
  targetId: string,
  maxDepth: number,
  relationTypes?: string[]
): Promise<PathFindingResult['paths']> {
  const paths: PathFindingResult['paths'] = [];
  const queue: Array<{
    currentId: string;
    path: string[];
    edges: Array<{ sourceId: string; targetId: string; relation: string }>;
  }> = [
    {
      currentId: sourceId,
      path: [sourceId],
      edges: []
    }
  ];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const { currentId, path, edges } = queue.shift()!;

    if (path.length - 1 > maxDepth) {
      continue;
    }

    if (currentId === targetId) {
      paths.push({
        nodes: path,
        edges,
        length: path.length - 1
      });
      continue;
    }

    const visitKey = `${currentId}-${path.length}`;
    if (visited.has(visitKey)) {
      continue;
    }
    visited.add(visitKey);

    // Get outgoing edges
    let edgesQuery = query(
      collection(db, 'edges'),
      where('source_id', '==', currentId)
    );

    if (relationTypes && relationTypes.length > 0) {
      edgesQuery = query(
        collection(db, 'edges'),
        where('source_id', '==', currentId),
        where('relation', 'in', relationTypes)
      );
    }

    const edgesSnapshot = await getDocs(edgesQuery);

    for (const edgeDoc of edgesSnapshot) {
      const edgeData = edgeDoc.data();
      const nextId = edgeData.target_id;

      if (!path.includes(nextId)) {
        queue.push({
          currentId: nextId,
          path: [...path, nextId],
          edges: [
            ...edges,
            {
              sourceId: currentId,
              targetId: nextId,
              relation: edgeData.relation
            }
          ]
        });
      }
    }
  }

  return paths;
}

/**
 * Get neighbors of a node
 */
async function getNeighbors(
  nodeId: string,
  direction: 'both' | 'incoming' | 'outgoing',
  relationTypes?: string[]
): Promise<NeighborResult> {
  const nodes: NeighborResult['nodes'] = [];
  const edges: NeighborResult['edges'] = [];

  // Get edges based on direction
  let edgesQueries = [];

  if (direction === 'both' || direction === 'outgoing') {
    let outgoingQuery = query(
      collection(db, 'edges'),
      where('source_id', '==', nodeId)
    );

    if (relationTypes && relationTypes.length > 0) {
      outgoingQuery = query(
        collection(db, 'edges'),
        where('source_id', '==', nodeId),
        where('relation', 'in', relationTypes)
      );
    }
    edgesQueries.push(outgoingQuery);
  }

  if (direction === 'both' || direction === 'incoming') {
    let incomingQuery = query(
      collection(db, 'edges'),
      where('target_id', '==', nodeId)
    );

    if (relationTypes && relationTypes.length > 0) {
      incomingQuery = query(
        collection(db, 'edges'),
        where('target_id', '==', nodeId),
        where('relation', 'in', relationTypes)
      );
    }
    edgesQueries.push(incomingQuery);
  }

  // Execute queries and collect edges
  for (const edgesQuery of edgesQueries) {
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

      // Get connected node
      const connectedNodeId = sourceId === nodeId ? targetId : sourceId;
      const nodeDoc = await getDoc(doc(db, 'nodes', connectedNodeId));

      if (nodeDoc.exists() && !nodes.find(n => n.id === connectedNodeId)) {
        const nodeData = nodeDoc.data();
        nodes.push({
          id: nodeDoc.id,
          type: nodeData?.type || '',
          content: nodeData?.content || '',
          metadata: nodeData?.metadata
        });
      }
    }
  }

  return { nodes, edges };
}

/**
 * POST /api/graph/traversal/paths
 * Find all paths between two nodes
 */
export async function POST(request: Request) {
  try {
    const url = new URL(request.url);
    const action = url.searchParams.get('action');

    if (action === 'paths') {
      const body: PathFindingParams = await request.json();
      const { sourceId, targetId, maxDepth = 5, relationTypes } = body;

      // Validate required parameters
      if (!sourceId || !targetId) {
        return createApiResponse(
          false,
          undefined,
          'sourceId and targetId are required',
          400
        );
      }

      // Validate maxDepth
      if (maxDepth < 1 || maxDepth > 10) {
        return createApiResponse(
          false,
          undefined,
          'maxDepth must be between 1 and 10',
          400
        );
      }

      // Check if nodes exist
      const sourceDoc = await getDoc(doc(db, 'nodes', sourceId));
      const targetDoc = await getDoc(doc(db, 'nodes', targetId));

      if (!sourceDoc.exists()) {
        return createApiResponse(
          false,
          undefined,
          'Source node not found',
          404
        );
      }

      if (!targetDoc.exists()) {
        return createApiResponse(
          false,
          undefined,
          'Target node not found',
          404
        );
      }

      // Find paths using background task
      let paths: PathFindingResult['paths'] = [];
      await runTask(async () => {
        paths = await findPaths(sourceId, targetId, maxDepth, relationTypes);
      });

      return createApiResponse(true, {
        paths,
        count: paths.length,
        sourceId,
        targetId
      });

    } else if (action === 'neighbors') {
      const body: NeighborParams = await request.json();
      const { nodeId, direction = 'both', relationTypes } = body;

      // Validate required parameters
      if (!nodeId) {
        return createApiResponse(
          false,
          undefined,
          'nodeId is required',
          400
        );
      }

      // Check if node exists
      const nodeDoc = await getDoc(doc(db, 'nodes', nodeId));
      if (!nodeDoc.exists()) {
        return createApiResponse(
          false,
          undefined,
          'Node not found',
          404
        );
      }

      // Get neighbors using background task
      let result: NeighborResult = { nodes: [], edges: [] };
      await runTask(async () => {
        result = await getNeighbors(nodeId, direction, relationTypes);
      });

      return createApiResponse(true, {
        nodes: result.nodes,
        edges: result.edges,
        count: {
          nodes: result.nodes.length,
          edges: result.edges.length
        }
      });
    } else {
      return createApiResponse(
        false,
        undefined,
        'Invalid action. Use ?action=paths or ?action=neighbors',
        400
      );
    }

  } catch (error) {
    console.error('Graph traversal error:', error);
    return createApiResponse(
      false,
      undefined,
      `Graph traversal failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

/**
 * GET /api/graph/traversal
 * Health check endpoint
 */
export async function GET() {
  return Response.json({
    status: 'healthy',
    service: 'graph-traversal',
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