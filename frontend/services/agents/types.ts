/**
 * Core types and interfaces for the AutoAdmin Agent System
 */

import { BaseMessage } from '@langchain/core/messages';

export interface AgentState {
  messages: BaseMessage[];
  currentAgent?: string;
  taskStatus: TaskStatus;
  virtualFileSystem?: VirtualFileSystem;
  userContext?: UserContext;
  executionContext?: ExecutionContext;
}

export interface TaskStatus {
  id: string;
  type: TaskType;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'delegated';
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
  assignedTo?: string;
  delegatedTo?: string;
  metadata?: Record<string, any>;
}

export type TaskType =
  | 'market_research'
  | 'financial_analysis'
  | 'code_analysis'
  | 'ui_ux_review'
  | 'strategic_planning'
  | 'technical_decision'
  | 'github_actions_delegation'
  | 'virtual_file_operation';

export interface VirtualFileSystem {
  files: Map<string, VirtualFile>;
  directories: Map<string, VirtualDirectory>;
  currentPath: string;
}

export interface VirtualFile {
  path: string;
  content: string;
  type: 'code' | 'data' | 'config' | 'document';
  lastModified: Date;
  size: number;
  metadata?: Record<string, any>;
}

export interface VirtualDirectory {
  path: string;
  files: string[];
  subdirectories: string[];
  createdAt: Date;
  lastModified: Date;
}

export interface UserContext {
  id: string;
  preferences: UserPreferences;
  businessProfile?: BusinessProfile;
  subscription: SubscriptionInfo;
  sessionContext: SessionContext;
}

export interface UserPreferences {
  industry: string;
  businessSize: 'startup' | 'small' | 'medium' | 'enterprise';
  timezone: string;
  language: string;
  notifications: NotificationPreferences;
}

export interface BusinessProfile {
  industry: string;
  segment: string;
  revenue?: number;
  employees?: number;
  targetMarket?: string;
  competitors?: string[];
}

export interface SubscriptionInfo {
  tier: 'free' | 'pro' | 'enterprise';
  limits: SubscriptionLimits;
  features: string[];
}

export interface SubscriptionLimits {
  maxAgents: number;
  maxTasksPerDay: number;
  maxStorageSize: number;
  maxAPICallsPerDay: number;
}

export interface SessionContext {
  startTime: Date;
  lastActivity: Date;
  activeAgents: string[];
  currentTasks: string[];
  sessionGoals?: string[];
}

export interface ExecutionContext {
  sessionId: string;
  requestId: string;
  timestamp: Date;
  environment: 'development' | 'staging' | 'production';
  performance: PerformanceMetrics;
}

export interface PerformanceMetrics {
  startTime: Date;
  responseTime?: number;
  tokensUsed?: number;
  operationsCompleted?: number;
  errorsCount?: number;
}

export interface AgentTool {
  name: string;
  description: string;
  schema: any;
  handler: (input: any) => Promise<string | any>;
}

export interface AgentConfig {
  id: string;
  name: string;
  type: AgentType;
  model: string;
  temperature: number;
  maxTokens?: number;
  tools: AgentTool[];
  systemPrompt: string;
  capabilities: AgentCapability[];
  delegationRules: DelegationRule[];
}

export type AgentType = 'ceo' | 'strategy' | 'devops';

export interface AgentCapability {
  name: string;
  description: string;
  tools: string[];
  supportedTasks: TaskType[];
  maxComplexity: 'low' | 'medium' | 'high';
}

export interface DelegationRule {
  condition: string;
  targetAgent?: AgentType;
  targetBackend?: 'github_actions' | 'netlify_functions';
  threshold: {
    complexity?: number;
    timeLimit?: number; // seconds
    resourceUsage?: number;
  };
  requireApproval: boolean;
}

export interface AgentResponse {
  success: boolean;
  data?: any;
  message?: string;
  nextAction?: NextAction;
  requiresUserInput?: boolean;
  userInputPrompt?: string;
}

export interface NextAction {
  type: 'continue' | 'delegate' | 'complete' | 'error';
  target?: string;
  payload?: any;
  expectedDuration?: number; // seconds
}

export interface AgentMetrics {
  totalTasks: number;
  completedTasks: number;
  averageResponseTime: number;
  successRate: number;
  delegationRate: number;
  userSatisfaction?: number;
}

export interface AgentMemory {
  userId: string;
  agentId: string;
  conversations: ConversationEntry[];
  learnedPatterns: LearnedPattern[];
  businessContext: BusinessContext;
  userPreferences: UserPreferences;
}

export interface ConversationEntry {
  id: string;
  timestamp: Date;
  userMessage: string;
  agentResponse: string;
  context: Record<string, any>;
  feedback?: {
    rating: number;
    comments?: string;
  };
}

export interface LearnedPattern {
  id: string;
  pattern: string;
  context: string;
  frequency: number;
  successRate: number;
  lastUsed: Date;
}

export interface BusinessContext {
  industry: string;
  businessModel: string;
  targetAudience: string;
  competitiveLandscape: string;
  recentTrends: string[];
  keyMetrics: Record<string, number>;
}

export interface NotificationPreferences {
  email: boolean;
  push: boolean;
  sms: boolean;
  frequency: 'immediate' | 'hourly' | 'daily' | 'weekly';
  types: string[];
}

/**
 * Agent-specific tool configurations
 */
export interface StrategyAgentTools {
  marketResearch: MarketResearchTool;
  financialAnalysis: FinancialAnalysisTool;
  competitiveIntelligence: CompetitiveIntelligenceTool;
}

export interface MarketResearchTool {
  webSearch: boolean;
  socialMediaAnalysis: boolean;
  trendIdentification: boolean;
  audienceSegmentation: boolean;
}

export interface FinancialAnalysisTool {
  budgetAnalysis: boolean;
  revenueProjection: boolean;
  costOptimization: boolean;
  riskAssessment: boolean;
}

export interface CompetitiveIntelligenceTool {
  competitorTracking: boolean;
  marketPositioning: boolean;
  swotAnalysis: boolean;
  opportunityIdentification: boolean;
}

export interface DevOpsAgentTools {
  codeAnalysis: CodeAnalysisTool;
  uiUxReview: UiUxReviewTool;
  performanceOptimization: PerformanceOptimizationTool;
  securityAudit: SecurityAuditTool;
}

export interface CodeAnalysisTool {
  staticAnalysis: boolean;
  dependencyCheck: boolean;
  codeQuality: boolean;
  bestPractices: boolean;
}

export interface UiUxReviewTool {
  accessibilityCheck: boolean;
  responsiveDesign: boolean;
  usabilityAnalysis: boolean;
  designConsistency: boolean;
}

export interface PerformanceOptimizationTool {
  bundleAnalysis: boolean;
  renderOptimization: boolean;
  cachingStrategy: boolean;
  resourceOptimization: boolean;
}

export interface SecurityAuditTool {
  vulnerabilityScan: boolean;
  dependencyAudit: boolean;
  codeReview: boolean;
  complianceCheck: boolean;
}

/**
 * Graph Memory integration types
 */
export interface GraphMemoryNode {
  id: string;
  type: 'feature' | 'file' | 'trend' | 'metric' | 'rule' | 'business_rule';
  content: string;
  embedding?: number[];
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface GraphMemoryEdge {
  id: string;
  sourceId: string;
  targetId: string;
  relation: 'impacts' | 'depends_on' | 'implements' | 'blocks' | 'related_to';
  createdAt: Date;
}

/**
 * Worklets integration for performance
 */
export interface WorkletAgentConfig {
  useWorklets: boolean;
  maxWorkletConcurrency: number;
  workletTimeout: number;
  enableStreaming: boolean;
  chunkSize: number;
}

/**
 * Real-time synchronization types
 */
export interface SyncEvent {
  type: 'agent_update' | 'task_complete' | 'user_input' | 'system_notification';
  payload: any;
  timestamp: Date;
  userId: string;
  sessionId: string;
}

export interface RealtimeConfig {
  enabled: boolean;
  channels: string[];
  syncStrategy: 'optimistic' | 'pessimistic';
  conflictResolution: 'last_write_wins' | 'merge' | 'prompt_user';
}

// No default export to avoid hoisting issues - use named exports only