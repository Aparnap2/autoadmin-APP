/**
 * Vector Search API Endpoint - Netlify Function
 * Replaces Firebase Cloud Functions vectorSearch - now delegates to FastAPI backend
 */

import { collection, query, where, limit, getDocs } from 'firebase/firestore';
import { getFirestoreInstance } from '../../../../lib/firebase-singleton';
import { runTask, createApiResponse, validateRequestBody, getEnvVar } from '../../utils/expo-serverless';
import { getFastAPIClient } from '../../../../services/api/fastapi-client';

// Get Firestore singleton instance
const db = getFirestoreInstance();

// Interface definitions
interface VectorSearchParams {
  queryEmbedding: number[];
  matchThreshold?: number;
  limit?: number;
  collection?: string;
}

interface VectorSearchResult {
  id: string;
  content: string;
  type: string;
  similarity: number;
  metadata?: Record<string, any>;
}

/**
 * Calculate cosine similarity between two vectors
 */
function cosineSimilarity(vecA: number[], vecB: number[]): number {
  if (vecA.length !== vecB.length) {
    throw new Error('Vectors must be of same length');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);

  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dotProduct / (normA * normB);
}

/**
 * POST /api/vector/search
 * Perform vector similarity search using FastAPI backend
 */
export async function POST(request: Request) {
  try {
    // Parse and validate request body
    const body = validateRequestBody(await request.json(), (data: any) => {
      if (!data.queryEmbedding || !Array.isArray(data.queryEmbedding)) {
        throw new Error('queryEmbedding is required and must be an array');
      }
      return {
        queryEmbedding: data.queryEmbedding,
        matchThreshold: data.matchThreshold ?? 0.7,
        limit: Math.min(Math.max(data.limit ?? 10, 1), 100),
        collection: data.collection ?? 'nodes'
      } as VectorSearchParams;
    });

    const { queryEmbedding, matchThreshold, limit, collection } = body;

    // Get FastAPI client instance
    const fastapiClient = getFastAPIClient({
      baseURL: getEnvVar('FASTAPI_BASE_URL') || 'http://localhost:8000'
    });

    // Perform vector search using FastAPI backend in background task
    let finalResults: VectorSearchResult[] = [];
    let resultCount: number = 0;

    await runTask(async () => {
      const response = await fastapiClient.vectorSearch(queryEmbedding, {
        matchThreshold,
        limit,
        collection
      });

      if (response.success && response.data) {
        finalResults = response.data.results.map((result: any) => ({
          id: result.id,
          content: result.content,
          type: result.type,
          similarity: result.similarity,
          metadata: result.metadata
        }));
        resultCount = response.data.count;
      } else {
        // Fallback to local Firebase search if backend fails
        console.warn('Backend vector search failed, falling back to local Firebase search:', response.error);

        const q = query(
          collection(db, collection),
          where('embedding', '!=', null),
          limit(limit * 2) // Get more to account for threshold filtering
        );
        const snapshot = await getDocs(q);

        const results: VectorSearchResult[] = [];

        for (const doc of snapshot.docs) {
          const docData = doc.data() as any;
          const embedding = docData.embedding as number[];

          if (embedding && embedding.length === queryEmbedding.length) {
            // Calculate cosine similarity
            const similarity = cosineSimilarity(queryEmbedding, embedding);

            if (similarity >= (matchThreshold ?? 0.7)) {
              results.push({
                id: doc.id,
                content: docData.content || '',
                type: docData.type || '',
                similarity,
                metadata: docData.metadata
              });
            }
          }
        }

        // Sort by similarity and limit results
        results.sort((a, b) => b.similarity - a.similarity);
        finalResults = results.slice(0, limit);
        resultCount = finalResults.length;
      }
    });

    return createApiResponse(true, {
      results: finalResults,
      count: resultCount
    });

  } catch (error) {
    console.error('Vector search error:', error);
    return createApiResponse(
      false,
      undefined,
      `Vector search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

/**
 * GET /api/vector/search
 * Health check endpoint
 */
export async function GET() {
  return Response.json({
    status: 'healthy',
    service: 'vector-search',
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