import 'react-native-worklets-core';

/**
 * Background Worklets for AutoAdmin
 *
 * These worklets run in a separate thread for heavy computations
 * like sorting, filtering, and data processing without blocking the UI
 */

// Worklet for sorting tasks by priority and status
export const sortTasksByPriority = worklet((tasks: any[]) => {
  'worklet';

  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const statusOrder = { processing: 0, pending: 1, review_ready: 2, done: 3, failed: 4 };

  return tasks.sort((a, b) => {
    // First sort by priority
    const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
    if (priorityDiff !== 0) return priorityDiff;

    // Then sort by status
    const statusDiff = statusOrder[a.status] - statusOrder[b.status];
    if (statusDiff !== 0) return statusDiff;

    // Finally sort by creation date
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
});

// Worklet for filtering tasks by multiple criteria
export const filterTasks = worklet((
  tasks: any[],
  filters: {
    agentType?: string[];
    status?: string[];
    priority?: string[];
    dateRange?: { start: number; end: number };
    searchText?: string;
  }
) => {
  'worklet';

  return tasks.filter(task => {
    // Filter by agent type
    if (filters.agentType && filters.agentType.length > 0) {
      if (!filters.agentType.includes(task.agent_type)) return false;
    }

    // Filter by status
    if (filters.status && filters.status.length > 0) {
      if (!filters.status.includes(task.status)) return false;
    }

    // Filter by priority
    if (filters.priority && filters.priority.length > 0) {
      if (!filters.priority.includes(task.priority)) return false;
    }

    // Filter by date range
    if (filters.dateRange) {
      const taskDate = new Date(task.created_at).getTime();
      if (taskDate < filters.dateRange.start || taskDate > filters.dateRange.end) {
        return false;
      }
    }

    // Filter by search text
    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      const taskText = `${task.input_prompt} ${task.output_result || ''} ${task.agent_type}`.toLowerCase();
      if (!taskText.includes(searchLower)) return false;
    }

    return true;
  });
});

// Worklet for calculating task statistics
export const calculateTaskStats = worklet((tasks: any[]) => {
  'worklet';

  const stats = {
    total: tasks.length,
    pending: 0,
    processing: 0,
    review_ready: 0,
    done: 0,
    failed: 0,
    byAgentType: {} as Record<string, number>,
    byPriority: { high: 0, medium: 0, low: 0 },
    avgCompletionTime: 0
  };

  let totalCompletionTime = 0;
  let completedTasks = 0;

  tasks.forEach(task => {
    // Count by status
    stats[task.status] = (stats[task.status] || 0) + 1;

    // Count by agent type
    stats.byAgentType[task.agent_type] = (stats.byAgentType[task.agent_type] || 0) + 1;

    // Count by priority
    stats.byPriority[task.priority] = (stats.byPriority[task.priority] || 0) + 1;

    // Calculate completion time for finished tasks
    if (task.status === 'done' && task.updated_at) {
      const created = new Date(task.created_at).getTime();
      const updated = new Date(task.updated_at).getTime();
      totalCompletionTime += (updated - created);
      completedTasks++;
    }
  });

  stats.avgCompletionTime = completedTasks > 0 ? totalCompletionTime / completedTasks : 0;

  return stats;
});

// Worklet for processing webhook events
export const processWebhookEvent = worklet((event: any) => {
  'worklet';

  const processed = {
    type: 'unknown',
    severity: 'info',
    actionRequired: false,
    summary: '',
    details: {},
    suggestedResponse: ''
  };

  try {
    switch (event.source) {
      case 'github':
        processed.type = 'github_webhook';
        processed.details = {
          repository: event.payload.repository?.full_name || 'Unknown',
          event: event.event,
          actor: event.payload.sender?.login || 'Unknown'
        };

        switch (event.event_type || event.action) {
          case 'push':
            processed.severity = event.payload.commits?.length > 5 ? 'warning' : 'info';
            processed.summary = `${event.payload.commits?.length || 0} commits pushed to ${event.payload.ref?.replace('refs/heads/', '') || 'unknown branch'}`;
            processed.actionRequired = event.payload.commits?.length > 10;
            processed.suggestedResponse = processed.actionRequired
              ? 'Review high volume of commits and consider agent coordination'
              : 'Monitor for potential issues';
            break;

          case 'opened':
            if (event.payload.pull_request) {
              processed.severity = 'high';
              processed.summary = `New PR: "${event.payload.pull_request.title}"`;
              processed.actionRequired = true;
              processed.suggestedResponse = 'Trigger DevOps agent for PR review';
            } else if (event.payload.issue) {
              processed.severity = 'medium';
              processed.summary = `New Issue: "${event.payload.issue.title}"`;
              processed.actionRequired = true;
              processed.suggestedResponse = 'Assess issue and assign appropriate agent';
            }
            break;

          case 'closed':
            if (event.payload.pull_request?.merged) {
              processed.severity = 'success';
              processed.summary = `PR #${event.payload.pull_request.number} merged`;
              processed.actionRequired = false;
              processed.suggestedResponse = 'Update project metrics and documentation';
            }
            break;
        }
        break;

      case 'hubspot':
        processed.type = 'hubspot_webhook';
        processed.details = {
          objectType: event.payload.objectType || 'unknown',
          objectId: event.payload.objectId || 'unknown'
        };

        switch (event.eventType) {
          case 'contact.creation':
            processed.severity = 'info';
            processed.summary = 'New contact created';
            processed.actionRequired = true;
            processed.suggestedResponse = 'Trigger marketing agent for lead qualification';
            break;

          case 'deal.creation':
            processed.severity = 'high';
            processed.summary = 'New deal created';
            processed.actionRequired = true;
            processed.suggestedResponse = 'Trigger finance agent for deal analysis';
            break;

          case 'deal.stage_change':
            processed.severity = 'high';
            processed.summary = `Deal stage changed to ${event.payload.propertyValue}`;
            processed.actionRequired = true;
            processed.suggestedResponse = 'Update sales strategy and next steps';
            break;
        }
        break;

      case 'monitoring':
        processed.type = 'monitoring_alert';
        processed.severity = event.payload.status === 'down' ? 'critical' : 'warning';
        processed.summary = `${event.payload.service}: ${event.payload.status}`;
        processed.actionRequired = true;
        processed.suggestedResponse = 'Trigger DevOps agent for immediate investigation';
        break;

      default:
        processed.type = 'generic_webhook';
        processed.summary = `Webhook from ${event.source}`;
        processed.actionRequired = false;
        processed.suggestedResponse = 'Log and monitor for patterns';
    }
  } catch (error) {
    processed.severity = 'error';
    processed.summary = `Error processing webhook: ${error.message}`;
    processed.actionRequired = true;
    processed.suggestedResponse = 'Review webhook processing logic';
  }

  return processed;
});

// Worklet for optimizing agent task allocation
export const optimizeTaskAllocation = worklet((
  tasks: any[],
  agentCapacity: Record<string, { maxConcurrent: number; currentLoad: number; avgProcessTime: number }>
) => {
  'worklet';

  const allocation = [];
  const agentLoad = { ...agentCapacity };

  // Sort tasks by priority and creation time
  const sortedTasks = tasks.sort((a, b) => {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
    if (priorityDiff !== 0) return priorityDiff;
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  sortedTasks.forEach(task => {
    // Find best available agent for this task type
    const agentType = task.agent_type;
    const capacity = agentLoad[agentType];

    if (capacity && capacity.currentLoad < capacity.maxConcurrent) {
      // Calculate estimated completion time
      const estimatedTime = capacity.avgProcessTime * (1 + capacity.currentLoad * 0.2); // Add load factor

      allocation.push({
        taskId: task.id,
        agentType,
        assignedAgent: findBestAgent(agentType, agentLoad),
        estimatedCompletionTime: Date.now() + estimatedTime,
        priority: task.priority
      });

      // Update agent load
      capacity.currentLoad += 1;
    }
  });

  function findBestAgent(type: string, loads: Record<string, any>) {
    // Simple logic: return agent type for now
    // In production, this would consider individual agent performance, specialization, etc.
    return `${type}_agent_${Math.floor(Math.random() * 3) + 1}`;
  }

  return {
    allocation,
    unassignedTasks: sortedTasks.length - allocation.length,
    totalEstimatedTime: Math.max(...allocation.map(a => a.estimatedCompletionTime)) - Date.now()
  };
});

// Worklet for generating daily brief summary
export const generateDailyBrief = worklet((
  tasks: any[],
  events: any[],
  metrics: Record<string, number>
) => {
  'worklet';

  const brief = {
    date: new Date().toISOString().split('T')[0],
    summary: '',
    highlights: [] as string[],
    concerns: [] as string[],
    recommendations: [] as string[],
    metrics: metrics
  };

  // Count tasks by status
  const taskStats = {
    completed: tasks.filter(t => t.status === 'done').length,
    failed: tasks.filter(t => t.status === 'failed').length,
    pending: tasks.filter(t => t.status === 'pending').length,
    processing: tasks.filter(t => t.status === 'processing').length
  };

  // Generate summary
  brief.summary = `Today: ${taskStats.completed} tasks completed, ${taskStats.processing} in progress`;

  // Generate highlights
  if (taskStats.completed > 0) {
    brief.highlights.push(`✅ ${taskStats.completed} tasks completed successfully`);
  }

  const recentEvents = events.filter(e => {
    const eventTime = new Date(e.created_at).getTime();
    const dayAgo = Date.now() - (24 * 60 * 60 * 1000);
    return eventTime > dayAgo;
  });

  if (recentEvents.length > 0) {
    brief.highlights.push(`📊 ${recentEvents.length} system events processed`);
  }

  // Generate concerns
  if (taskStats.failed > 0) {
    brief.concerns.push(`⚠️ ${taskStats.failed} tasks failed - requires investigation`);
  }

  if (taskStats.pending > 10) {
    brief.concerns.push(`⏰ ${taskStats.pending} tasks pending - possible bottleneck`);
  }

  // Generate recommendations
  if (taskStats.processing > 5) {
    brief.recommendations.push('Consider scaling agent capacity for processing queue');
  }

  if (metrics.avgResponseTime && metrics.avgResponseTime > 30000) {
    brief.recommendations.push('Investigate slow response times in agent processing');
  }

  return brief;
});

export default {
  sortTasksByPriority,
  filterTasks,
  calculateTaskStats,
  processWebhookEvent,
  optimizeTaskAllocation,
  generateDailyBrief
};