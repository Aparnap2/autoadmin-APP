import { firebaseService } from '../../../lib/firebase';
import { runTask, createApiResponse, getEnvVar } from '../utils/expo-serverless';

interface TriggerRequest {
  agentType: 'marketing' | 'finance' | 'devops' | 'strategy';
  task: string;
  parameters?: Record<string, any>;
  priority?: 'low' | 'medium' | 'high';
}

interface TriggerResponse {
  success: boolean;
  taskId?: string;
  message?: string;
  error?: string;
}

/**
 * API Route: /api/agents/trigger
 *
 * Triggers GitHub Actions for agent tasks
 *
 * Usage:
 * POST /api/agents/trigger
 * {
 *   "agentType": "marketing",
 *   "task": "Create content about AI trends",
 *   "parameters": { "platform": "twitter", "length": "280" },
 *   "priority": "high"
 * }
 */
export async function POST(request: Request) {
  try {
    const { agentType, task, parameters = {}, priority = 'medium' } = await request.json() as TriggerRequest;

    // Validate required fields
    if (!agentType || !task) {
      return createApiResponse(
        false,
        undefined,
        'Missing required fields: agentType, task',
        400
      );
    }

    // Validate agent type
    const validAgentTypes = ['marketing', 'finance', 'devops', 'strategy'];
    if (!validAgentTypes.includes(agentType)) {
      return createApiResponse(
        false,
        undefined,
        `Invalid agentType. Must be one of: ${validAgentTypes.join(', ')}`,
        400
      );
    }

    // Validate priority
    const validPriorities = ['low', 'medium', 'high'];
    if (!validPriorities.includes(priority)) {
      return createApiResponse(
        false,
        undefined,
        `Invalid priority. Must be one of: ${validPriorities.join(', ')}`,
        400
      );
    }

    // Create task record in Firebase using background task
    let taskRecord: any = null;
    await runTask(async () => {
      taskRecord = await firebaseService.createTask({
        status: 'pending',
        input_prompt: task,
        agent_type: agentType,
        priority,
        parameters
      });
    });

    if (!taskRecord) {
      console.error('Error creating task record');
      return createApiResponse(
        false,
        undefined,
        'Failed to create task record',
        500
      );
    }

    // Trigger GitHub Action via repository dispatch using background task
    try {
      const githubToken = getEnvVar('GITHUB_TOKEN', true);
      const repoOwner = getEnvVar('GITHUB_REPO_OWNER', true);
      const repoName = getEnvVar('GITHUB_REPO_NAME', true);
    } catch (error) {
      return createApiResponse(
        false,
        undefined,
        'GitHub configuration missing',
        500
      );
    }

    const githubToken = getEnvVar('GITHUB_TOKEN', true)!;
    const repoOwner = getEnvVar('GITHUB_REPO_OWNER', true)!;
    const repoName = getEnvVar('GITHUB_REPO_NAME', true)!;

    let githubResponse: Response | null = null;
    await runTask(async () => {
      const dispatchPayload = {
        event_type: 'start_task',
        client_payload: {
          taskId: taskRecord.id,
          agentType,
          task,
          parameters,
          priority
        }
      };

      githubResponse = await fetch(
        `https://api.github.com/repos/${repoOwner}/${repoName}/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `token ${githubToken}`,
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(dispatchPayload)
        }
      );
    });

    if (!githubResponse || !githubResponse.ok) {
      console.error('Failed to trigger GitHub Action:', githubResponse ? await githubResponse.text() : 'No response');

      // Update task status to failed in background
      await runTask(async () => {
        await firebaseService.updateTaskStatus(taskRecord.id, 'failed');
      });

      return createApiResponse(
        false,
        undefined,
        'Failed to trigger GitHub Action',
        500
      );
    }

    // Update task status to processing in background
    await runTask(async () => {
      await firebaseService.updateTaskStatus(taskRecord.id, 'processing');
    });

    return createApiResponse(true, {
      taskId: taskRecord.id,
      message: `${agentType} agent task triggered successfully`
    });

  } catch (error) {
    console.error('Agent trigger error:', error);
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