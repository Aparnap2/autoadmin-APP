/**
 * Vector Embeddings API Endpoint - Netlify Function
 * Generate embeddings using FastAPI backend
 */

import { runTask, createApiResponse, validateRequestBody, getEnvVar } from '../../utils/expo-serverless';
import { getFastAPIClient } from '../../../../services/api/fastapi-client';

// Interface definitions
interface EmbeddingParams {
  text: string;
  model?: string;
}

interface EmbeddingResult {
  embedding: number[];
  dimensions: number;
  model: string;
}

/**
 * POST /api/vector/embeddings
 * Generate embeddings for the given text using FastAPI backend
 */
export async function POST(request: Request) {
  try {
    // Parse and validate request body
    const body = validateRequestBody(await request.json(), (data: any) => {
      if (!data.text || typeof data.text !== 'string') {
        throw new Error('text is required and must be a string');
      }
      return {
        text: data.text,
        model: data.model ?? 'text-embedding-ada-002'
      } as EmbeddingParams;
    });

    const { text, model: modelName } = body;

    // Get FastAPI client instance
    const fastapiClient = getFastAPIClient({
      baseURL: getEnvVar('FASTAPI_BASE_URL') || 'http://localhost:8000'
    });

    // Generate embedding using FastAPI backend in background task
    let embedding: number[] = [];
    let model: string = '';
    let usage: any = null;
    let dimensions: number = 0;

    await runTask(async () => {
      const response = await fastapiClient.aiEmbeddings(text, {
        model: modelName
      });

      if (response.success && response.data) {
        // Parse the embedding response from backend
        const embeddingData = response.data;
        embedding = embeddingData.embedding;
        model = embeddingData.model ?? modelName;
        dimensions = embeddingData.dimensions || embedding.length;
        usage = embeddingData.usage || null;
      } else {
        throw new Error(response.error || 'Failed to generate embedding via backend');
      }
    });

    return createApiResponse(true, {
      embedding,
      dimensions,
      model,
      usage
    });

  } catch (error) {
    console.error('Embedding generation error:', error);
    return createApiResponse(
      false,
      undefined,
      `Embedding generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

/**
 * GET /api/vector/embeddings
 * Health check endpoint
 */
export async function GET() {
  return Response.json({
    status: 'healthy',
    service: 'vector-embeddings',
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