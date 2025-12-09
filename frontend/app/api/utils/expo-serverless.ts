/**
 * Expo Serverless Function Utilities
 * Shared utilities for Expo API routes and serverless functions
 */

/**
 * Run a background task in a serverless environment
 * This utility helps with async operations that should run in the background
 * while maintaining proper error handling and logging
 */
export async function runTask(task: () => Promise<void>): Promise<void> {
  try {
    await task();
  } catch (error) {
    console.error('Background task error:', error);
    // Don't rethrow to prevent hanging requests
    // Errors are logged for debugging purposes
  }
}

/**
 * Validate query parameters from request URL
 */
export function validateQueryParams(url: string, requiredParams: string[]): Record<string, string> {
  const { searchParams } = new URL(url);
  const params: Record<string, string> = {};

  for (const param of requiredParams) {
    const value = searchParams.get(param);
    if (!value) {
      throw new Error(`Missing required query parameter: ${param}`);
    }
    params[param] = value;
  }

  return params;
}

/**
 * Common response helper for consistent API responses
 */
export function createApiResponse(
  success: boolean,
  data?: any,
  error?: string,
  status: number = 200
): Response {
  const body: any = { success };

  if (data !== undefined) {
    body.data = data;
  }

  if (error) {
    body.error = error;
  }

  return Response.json(body, { status });
}

/**
 * Validate request body against expected structure
 */
export function validateRequestBody<T>(body: unknown, validator: (data: any) => T): T {
  if (!body || typeof body !== 'object') {
    throw new Error('Invalid request body: must be an object');
  }

  return validator(body);
}

/**
 * Get pagination parameters from query string
 */
export function getPaginationParams(url: string, defaultLimit: number = 10, maxLimit: number = 100) {
  const { searchParams } = new URL(url);
  const limit = Math.min(
    Math.max(parseInt(searchParams.get('limit') || defaultLimit.toString()), 1),
    maxLimit
  );
  const offset = Math.max(parseInt(searchParams.get('offset') || '0'), 0);

  return { limit, offset };
}

export default {
  runTask,
  createApiResponse,
  validateQueryParams,
  validateRequestBody,
  getPaginationParams,
  getEnvVar
};

/**
 * Type-safe environment variable getter
 */
export function getEnvVar(name: string, required: boolean = false): string | undefined {
  const value = process.env[name];

  if (required && !value) {
    throw new Error(`Required environment variable ${name} is not set`);
  }

  return value;
}