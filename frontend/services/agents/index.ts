/**
 * AutoAdmin Simple Agent System - Main Export File
 * Client-side simple agent system that delegates to FastAPI backend
 */

// Core Types and Interfaces
import type { SimpleOrchestratorConfig } from './agent-orchestrator';
import {
  AgentState,
  TaskStatus,
  TaskType,
  UserContext,
  ExecutionContext,
  VirtualFileSystem,
  AgentConfig,
  AgentResponse,
  AgentMetrics,
  AgentMemory,
  SyncEvent
} from './types';

// Export all types
export {
  AgentState,
  TaskStatus,
  TaskType,
  UserContext,
  ExecutionContext,
  VirtualFileSystem,
  AgentConfig,
  AgentResponse,
  AgentMetrics,
  AgentMemory,
  SyncEvent
};

// Simple Agent Classes
export { default as SimpleAgentService, getSimpleAgentService } from './simple-agent-service';
export { default as SimpleCEOAgent } from './simple-ceo-agent';
export { default as SimpleStrategyAgent } from './simple-strategy-agent';
export { default as SimpleDevOpsAgent } from './simple-devops-agent';

// Orchestrator
export { default as AgentOrchestrator } from './agent-orchestrator';

// API Client Services
export { default as SimpleAPIClient, getAPIClient } from '../api/client-service';
export { default as FastAPIClient, getFastAPIClient } from '../api/fastapi-client';

// Factory Functions
export function createSimpleAgentSystem(userId: string, options?: Partial<SimpleOrchestratorConfig>) {
  const defaultConfig: SimpleOrchestratorConfig = {
    userId,
    backendURL: options?.backendURL,
    enableRealtimeSync: options?.enableRealtimeSync ?? true,
    offlineMode: options?.offlineMode ?? false
  };

  const config = { ...defaultConfig, ...options };
  return new AgentOrchestrator(config);
}

// Quick Setup Function
export function quickSetup(userId: string, backendURL?: string) {
  return createSimpleAgentSystem(userId, {
    backendURL,
    enableRealtimeSync: true,
    offlineMode: false
  });
}

// Constants
export const AGENT_TYPES = {
  CEO: 'ceo',
  STRATEGY: 'strategy',
  DEVOPS: 'devops'
} as const;

export const TASK_TYPES = {
  MARKET_RESEARCH: 'market_research',
  FINANCIAL_ANALYSIS: 'financial_analysis',
  CODE_ANALYSIS: 'code_analysis',
  UI_UX_REVIEW: 'ui_ux_review',
  STRATEGIC_PLANNING: 'strategic_planning',
  TECHNICAL_DECISION: 'technical_decision'
} as const;

export const TASK_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
} as const;

export const PRIORITY_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high'
} as const;

export const BACKEND_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  ERROR: 'error'
} as const;

// Utility Functions
export function validateSimpleAgentConfig(config: any): boolean {
  return !!(
    config.id &&
    config.name &&
    config.type &&
    Object.values(AGENT_TYPES).includes(config.type)
  );
}

export function validateTaskStatus(task: TaskStatus): boolean {
  return !!(
    task.id &&
    task.type &&
    Object.values(TASK_STATUS).includes(task.status) &&
    Object.values(PRIORITY_LEVELS).includes(task.priority) &&
    task.createdAt
  );
}

export function formatProcessingTime(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

export function calculateSuccessRate(totalTasks: number, completedTasks: number): number {
  return totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
}

export function estimateTaskComplexity(taskType: TaskType, agentType: string): {
  complexity: number;
  estimatedTime: number;
  requiresBackend: boolean;
} {
  const complexityMap: Record<string, { complexity: number; time: number; backend: boolean }> = {
    market_research: { complexity: 8, time: 15000, backend: true },
    financial_analysis: { complexity: 7, time: 12000, backend: true },
    code_analysis: { complexity: 6, time: 10000, backend: true },
    ui_ux_review: { complexity: 5, time: 8000, backend: true },
    strategic_planning: { complexity: 9, time: 18000, backend: true },
    technical_decision: { complexity: 7, time: 10000, backend: true }
  };

  const base = complexityMap[taskType] || { complexity: 5, time: 10000, backend: true };
  const agentMultiplier = agentType === 'strategy' ? 1.2 : agentType === 'devops' ? 0.8 : 1;

  return {
    complexity: Math.min(10, base.complexity),
    estimatedTime: base.time * agentMultiplier,
    requiresBackend: true // All tasks now require backend processing
  };
}

// Backend Connection Helper
export function determineBackendURL(platform?: string): string {
  // Use environment variable if available, otherwise use localhost for web and IP for native
  if (process.env.EXPO_PUBLIC_FASTAPI_URL) {
    return process.env.EXPO_PUBLIC_FASTAPI_URL;
  }

  // For web development (browser), use localhost
  if (platform === 'web') {
    return 'http://localhost:8000';
  } else {
    // For React Native apps, we need to handle platform-specific URLs
    // Note: This will be properly set by the Platform module in the actual implementation
    // For now, default to localhost which works for iOS simulator
    return 'http://10.0.2.2:8000'; // Use for Android emulator by default
  }
}