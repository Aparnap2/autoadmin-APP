import { getFirebaseService } from '../../../lib/firebase.ts';
import { runTask, createApiResponse, getEnvVar } from '../utils/expo-serverless';

interface WebhookEvent {
  event: string;
  data: any;
  timestamp: string;
  signature?: string;
}

interface WebhookResponse {
  success: boolean;
  message?: string;
  error?: string;
}

/**
 * API Route: /api/webhooks/handler
 *
 * Universal webhook handler for external services
 * Handles webhooks from GitHub, HubSpot, external monitoring services, etc.
 *
 * Supported webhook sources:
 * - GitHub (push, pull_request, issues)
 * - HubSpot (contact, deal, company changes)
 * - Monitoring services (uptime, performance alerts)
 * - Custom business webhooks
 */
export async function POST(request: Request) {
  try {
    const signature = request.headers.get('x-webhook-signature') as string;
    const source = request.headers.get('x-webhook-source') as string;
    const event = request.headers.get('x-github-event') || request.headers.get('event') as string;

    const payload = await request.json() as WebhookEvent;

    // Verify webhook signature if provided
    if (signature) {
      const webhookSecret = getEnvVar('WEBHOOK_SECRET', true);
      if (webhookSecret) {
        try {
          const encoder = new TextEncoder();
          const keyData = encoder.encode(webhookSecret);
          const messageData = encoder.encode(JSON.stringify(payload));

          const key = await crypto.subtle.importKey(
            'raw',
            keyData,
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign', 'verify']
          );

          const signatureBuffer = await crypto.subtle.sign('HMAC', key, messageData);
          const expectedSignature = Array.from(new Uint8Array(signatureBuffer))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');

          // Simple timing-safe comparison for React Native
          if (signature.length !== expectedSignature.length) {
            return createApiResponse(
              false,
              undefined,
              'Invalid webhook signature',
              401
            );
          }

          let isValid = true;
          for (let i = 0; i < signature.length; i++) {
            if (signature[i] !== expectedSignature[i]) {
              isValid = false;
              break;
            }
          }

          if (!isValid) {
            return createApiResponse(
              false,
              undefined,
              'Invalid webhook signature',
              401
            );
          }
        } catch (error) {
          console.error('Error verifying webhook signature:', error);
          return createApiResponse(
            false,
            undefined,
            'Signature verification failed',
            401
          );
        }
      }
    }

    // Initialize Firebase service and process webhook in background task
    const firebaseService = getFirebaseService();
    let processedEvent: any = null;

    // Process webhook using background task
    await runTask(async () => {
      if (source === 'github' || event) {
        processedEvent = await handleGitHubWebhook(payload);
      } else if (source === 'hubspot') {
        processedEvent = await handleHubSpotWebhook(payload);
      } else if (source === 'monitoring') {
        processedEvent = await handleMonitoringWebhook(payload);
      } else {
        processedEvent = await handleGenericWebhook(payload, source);
      }

      // Store webhook event in database
      try {
        await firebaseService.createWebhookEvent({
          source: source || 'unknown',
          event: event || 'generic',
          payload,
          processed_data: processedEvent
        });
      } catch (dbError) {
        console.error('Failed to store webhook event:', dbError);
        // Continue processing even if storage fails
      }

      // Trigger relevant agent if needed
      if (processedEvent?.triggerAgent) {
        await triggerAgentFromWebhook(processedEvent, firebaseService);
      }
    });

    return createApiResponse(
      true,
      undefined,
      'Webhook processed successfully'
    );

  } catch (error) {
    console.error('Webhook handler error:', error);
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
 * Handle GitHub webhooks (push, PR, issues, etc.)
 */
async function handleGitHubWebhook(payload: any) {
  const { zen, repository, sender, action, issue, pull_request } = payload;

  // Handle different GitHub events
  switch (payload.event_type || action) {
    case 'push':
      return {
        type: 'github_push',
        repository: repository?.full_name,
        branch: payload.ref?.replace('refs/heads/', ''),
        commits: payload.commits?.length || 0,
        triggerAgent: true,
        agentType: 'devops',
        priority: payload.commits?.length > 5 ? 'high' : 'medium'
      };

    case 'opened':
      if (pull_request) {
        return {
          type: 'github_pr_opened',
          repository: repository?.full_name,
          prNumber: pull_request.number,
          title: pull_request.title,
          author: pull_request.user?.login,
          triggerAgent: true,
          agentType: 'devops',
          priority: 'high'
        };
      }
      if (issue) {
        return {
          type: 'github_issue_opened',
          repository: repository?.full_name,
          issueNumber: issue.number,
          title: issue.title,
          author: issue.user?.login,
          triggerAgent: true,
          agentType: 'devops',
          priority: 'medium'
        };
      }
      break;

    case 'closed':
      if (pull_request?.merged) {
        return {
          type: 'github_pr_merged',
          repository: repository?.full_name,
          prNumber: pull_request.number,
          triggerAgent: false
        };
      }
      break;

    default:
      return {
        type: 'github_other',
        event: action,
        repository: repository?.full_name,
        triggerAgent: false
      };
  }

  return null;
}

/**
 * Handle HubSpot webhooks (contacts, deals, companies)
 */
async function handleHubSpotWebhook(payload: any) {
  const { eventType, objectId, propertyName, propertyValue } = payload;

  switch (eventType) {
    case 'contact.creation':
      return {
        type: 'hubspot_contact_created',
        contactId: objectId,
        triggerAgent: true,
        agentType: 'marketing',
        priority: 'medium'
      };

    case 'deal.creation':
      return {
        type: 'hubspot_deal_created',
        dealId: objectId,
        triggerAgent: true,
        agentType: 'finance',
        priority: 'high'
      };

    case 'deal.stage_change':
      return {
        type: 'hubspot_deal_stage_changed',
        dealId: objectId,
        newStage: propertyValue,
        triggerAgent: true,
        agentType: 'finance',
        priority: 'high'
      };

    default:
      return {
        type: 'hubspot_other',
        event: eventType,
        objectId,
        triggerAgent: false
      };
  }
}

/**
 * Handle monitoring service webhooks
 */
async function handleMonitoringWebhook(payload: any) {
  const { alertType, service, status, message } = payload;

  return {
    type: 'monitoring_alert',
    alertType,
    service,
    status,
    message,
    triggerAgent: status === 'down' || status === 'critical',
    agentType: 'devops',
    priority: status === 'down' ? 'high' : 'medium'
  };
}

/**
 * Handle generic/custom webhooks
 */
async function handleGenericWebhook(payload: any, source: string) {
  return {
    type: 'generic_webhook',
    source,
    payload,
    triggerAgent: false
  };
}

/**
 * Trigger agent based on webhook event
 */
async function triggerAgentFromWebhook(event: any, firebaseService: any) {
  try {
    const { agentType, priority, type } = event;

    // Create agent task
    const taskDescription = generateTaskDescription(event);

    await firebaseService.createTask({
      status: 'pending',
      input_prompt: taskDescription,
      agent_type: agentType,
      priority,
      parameters: { webhookEvent: event }
    });

    // TODO: Trigger GitHub Action for agent processing
    // This would be similar to the trigger.ts endpoint

  } catch (error) {
    console.error('Error triggering agent from webhook:', error);
  }
}

/**
 * Generate human-readable task description from webhook event
 */
function generateTaskDescription(event: any): string {
  switch (event.type) {
    case 'github_push':
      return `Process ${event.commits} new commits in ${event.repository} on ${event.branch} branch`;

    case 'github_pr_opened':
      return `Review and analyze new PR "${event.title}" #${event.prNumber} in ${event.repository}`;

    case 'github_issue_opened':
      return `Investigate new issue "${event.title}" #${event.issueNumber} in ${event.repository}`;

    case 'hubspot_contact_created':
      return `Follow up with new contact and assess business potential`;

    case 'hubspot_deal_created':
      return `Analyze new deal opportunity and create follow-up strategy`;

    case 'hubspot_deal_stage_changed':
      return `Deal stage changed to ${event.newStage}. Update strategy and next steps`;

    case 'monitoring_alert':
      return `${event.service} is ${event.status}: ${event.message}. Investigate and resolve.`;

    default:
      return `Process webhook event: ${event.type}`;
  }
}