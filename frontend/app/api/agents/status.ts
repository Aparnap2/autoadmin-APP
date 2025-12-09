import { getFirebaseService } from '../../../lib/firebase.ts';
import { runTask, getPaginationParams, createApiResponse } from '../utils/expo-serverless';

interface StatusRequest {
  taskId?: string;
  agentType?: 'marketing' | 'finance' | 'devops' | 'strategy';
  limit?: number;
  offset?: number;
}

interface StatusResponse {
  success: boolean;
  data?: any;
  error?: string;
  count?: number;
}

/**
 * API Route: /api/agents/status
 *
 * Get status of agent tasks
 *
 * Usage:
 * GET /api/agents/status?taskId=uuid
 * GET /api/agents/status?agentType=marketing&limit=10
 */
export async function GET(request: Request) {
  try {
    // Get query parameters using helper
    const { searchParams } = new URL(request.url);
    const taskId = searchParams.get('taskId');
    const agentType = searchParams.get('agentType') as 'marketing' | 'finance' | 'devops' | 'strategy' | null;
    const { limit, offset } = getPaginationParams(request.url, 10, 100);

    // Initialize Firebase service and run data fetching in background task
    const firebaseService = getFirebaseService();
    let tasks: any[] = [];

    // Use runTask for background operations
    await runTask(async () => {
      if (taskId) {
        // Get specific task
        const task = await firebaseService.getTask(taskId);
        tasks = task ? [task] : [];
      } else if (agentType) {
        // Get tasks by agent type
        const validAgentTypes = ['marketing', 'finance', 'devops', 'strategy'];
        if (!validAgentTypes.includes(agentType)) {
          throw new Error(`Invalid agentType. Must be one of: ${validAgentTypes.join(', ')}`);
        }
        tasks = await firebaseService.getTasksByAgentType(agentType);
      } else {
        // Get all tasks
        tasks = await firebaseService.getTasksByAgentType('strategy'); // Default or implement getAllTasks
      }
    });

    // Validate agentType after background task
    if (agentType) {
      const validAgentTypes = ['marketing', 'finance', 'devops', 'strategy'];
      if (!validAgentTypes.includes(agentType)) {
        return createApiResponse(
          false,
          undefined,
          `Invalid agentType. Must be one of: ${validAgentTypes.join(', ')}`,
          400
        );
      }
    }

    // Apply pagination
    const paginatedTasks = tasks.slice(offset, offset + limit);
    const count = tasks.length;

    // Enrich tasks with additional information
    const enrichedData = paginatedTasks.map(task => ({
      ...task,
      status_description: {
        pending: 'Task is queued and waiting to be processed',
        processing: 'Agent is currently working on this task',
        review_ready: 'Task is complete and ready for review',
        done: 'Task has been completed successfully',
        failed: 'Task failed during processing'
      }[task.status] || 'Unknown status',
      time_elapsed: getTimeElapsed(task.created_at),
      priority_badge: getPriorityBadge(task.priority || 'medium')
    }));

    return createApiResponse(true, {
      data: enrichedData,
      count
    });

  } catch (error) {
    console.error('Agent status error:', error);
    return createApiResponse(false, undefined, 'Internal server error', 500);
  }
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

/**
 * Calculate time elapsed since task creation
 */
function getTimeElapsed(createdAt: string | { toDate: () => Date }): string {
  let created: Date;
  if (typeof createdAt === 'string') {
    created = new Date(createdAt);
  } else if (typeof createdAt === 'object' && createdAt.toDate) {
    created = createdAt.toDate();
  } else {
    created = new Date();
  }

  const now = new Date();
  const diffMs = now.getTime() - created.getTime();

  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

/**
 * Get priority badge styling info
 */
function getPriorityBadge(priority: string): { label: string; color: string } {
  switch (priority) {
    case 'high':
      return { label: 'High', color: '#ef4444' };
    case 'medium':
      return { label: 'Medium', color: '#f59e0b' };
    case 'low':
      return { label: 'Low', color: '#10b981' };
    default:
      return { label: 'Unknown', color: '#6b7280' };
  }
}