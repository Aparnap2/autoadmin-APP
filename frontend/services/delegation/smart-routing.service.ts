/**
 * Smart Routing Service - Intelligent task routing based on complexity, resources, and system load
 * Implements load balancing, priority management, and optimal resource allocation
 */

import { z } from 'zod';
import { TaskDelegation, TaskClassificationResult } from './task-delegation.service';
import { AgentMetrics } from '../agents/types';

// Routing schemas
export const RoutingRuleSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  priority: z.number().min(1).max(10),
  conditions: z.array(z.object({
    field: z.string(),
    operator: z.enum(['equals', 'not_equals', 'greater_than', 'less_than', 'contains', 'matches']),
    value: z.any(),
    caseSensitive: z.boolean().default(false)
  })),
  actions: z.array(z.object({
    type: z.enum(['assign_to', 'set_priority', 'add_metadata', 'transform']),
    parameters: z.record(z.any())
  })),
  enabled: z.boolean().default(true),
  createdAt: z.date(),
  updatedAt: z.date(),
  usageCount: z.number().default(0),
  successRate: z.number().default(0)
});

export type RoutingRule = z.infer<typeof RoutingRuleSchema>;

export const AgentCapabilitySchema = z.object({
  agentId: z.string(),
  agentType: z.enum(['expo_agent', 'python_agent', 'github_actions', 'netlify_functions']),
  capabilities: z.array(z.string()),
  maxConcurrentTasks: z.number(),
  currentLoad: z.number(),
  averageProcessingTime: z.number(), // milliseconds
  successRate: z.number(), // 0-1
  resourceLimits: z.object({
    compute: z.number(),
    memory: z.number(),
    network: z.number(),
    storage: z.number()
  }),
  currentResourceUsage: z.object({
    compute: z.number(),
    memory: z.number(),
    network: z.number(),
    storage: z.number()
  }),
  supportedTaskTypes: z.array(z.string()),
  specialties: z.array(z.string()),
  availability: z.object({
    online: z.boolean(),
    lastSeen: z.date(),
    scheduledMaintenance: z.array(z.object({
      start: z.date(),
      end: z.date(),
      reason: z.string()
    }))
  }),
  performance: z.object({
    throughput: z.number(), // tasks per hour
    latency: z.number(), // average response time
    errorRate: z.number() // percentage
  })
});

export type AgentCapability = z.infer<typeof AgentCapabilitySchema>;

export interface RoutingDecision {
  taskId: string;
  selectedAgent: string;
  reasoning: string;
  confidence: number; // 0-1
  alternatives: Array<{
    agent: string;
    score: number;
    reasoning: string;
  }>;
  estimatedCompletionTime: number; // seconds
  cost: {
    compute: number;
    monetary?: number;
    time: number;
  };
  risks: Array<{
    type: string;
    probability: number;
    impact: string;
    mitigation: string;
  }>;
}

export interface RoutingConfig {
  enableLoadBalancing: boolean;
  enablePredictiveRouting: boolean;
  enableCostOptimization: boolean;
  defaultStrategy: 'fastest' | 'cheapest' | 'reliable' | 'balanced';
  maxConcurrentTasksPerAgent: number;
  thresholdForDelegation: number;
  priorityWeights: {
    complexity: number;
    urgency: number;
    cost: number;
    reliability: number;
    speed: number;
  };
  fallbackStrategy: 'retry' | 'reassign' | 'fail';
}

export interface LoadBalancingMetrics {
  totalAgents: number;
  activeAgents: number;
  averageLoad: number; // 0-1
  maxLoad: number;
  loadDistribution: Record<string, number>;
  throughput: number; // tasks per minute
  averageResponseTime: number; // milliseconds
  queueSize: number;
  failedRoutings: number;
  successfulRoutings: number;
}

export class SmartRoutingService {
  private config: RoutingConfig;
  private routingRules: Map<string, RoutingRule> = new Map();
  private agentCapabilities: Map<string, AgentCapability> = new Map();
  private routingHistory: RoutingDecision[] = [];
  private performanceMetrics: Map<string, AgentMetrics> = new Map();

  constructor(config: RoutingConfig) {
    this.config = config;
    this.initializeDefaultRules();
  }

  /**
   * Initialize the routing service with default rules
   */
  private initializeDefaultRules(): void {
    const defaultRules: RoutingRule[] = [
      {
        id: 'complex_tasks_to_python',
        name: 'Complex Tasks to Python Backend',
        description: 'Route high complexity tasks to Python backend agents',
        priority: 9,
        conditions: [
          { field: 'complexity', operator: 'greater_than', value: 7 },
          { field: 'type', operator: 'equals', value: 'heavy_task' }
        ],
        actions: [
          { type: 'assign_to', parameters: { agent: 'python_agent' } }
        ],
        enabled: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        usageCount: 0,
        successRate: 0
      },
      {
        id: 'code_analysis_to_github',
        name: 'Code Analysis to GitHub Actions',
        description: 'Route code analysis tasks to GitHub Actions for CI/CD integration',
        priority: 8,
        conditions: [
          { field: 'category', operator: 'contains', value: 'code_analysis' },
          { field: 'resourceRequirements.compute', operator: 'greater_than', value: 'medium' }
        ],
        actions: [
          { type: 'assign_to', parameters: { agent: 'github_actions' } }
        ],
        enabled: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        usageCount: 0,
        successRate: 0
      },
      {
        id: 'quick_tasks_to_expo',
        name: 'Quick Tasks to Expo Agents',
        description: 'Route simple tasks to Expo agents for immediate processing',
        priority: 7,
        conditions: [
          { field: 'expectedDuration', operator: 'less_than', value: 60 },
          { field: 'complexity', operator: 'less_than', value: 4 }
        ],
        actions: [
          { type: 'assign_to', parameters: { agent: 'expo_agent' } }
        ],
        enabled: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        usageCount: 0,
        successRate: 0
      },
      {
        id: 'urgent_tasks_priority',
        name: 'Urgent Tasks Fast Track',
        description: 'Prioritize urgent tasks and route to fastest available agent',
        priority: 10,
        conditions: [
          { field: 'priority', operator: 'equals', value: 'urgent' }
        ],
        actions: [
          { type: 'set_priority', parameters: { priority: 'critical' } }
        ],
        enabled: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        usageCount: 0,
        successRate: 0
      },
      {
        id: 'market_research_to_python',
        name: 'Market Research to Python Backend',
        description: 'Route market research tasks to Python agents with web scraping capabilities',
        priority: 8,
        conditions: [
          { field: 'category', operator: 'equals', value: 'market_research' },
          { field: 'resourceRequirements.network', operator: 'greater_than', value: 'low' }
        ],
        actions: [
          { type: 'assign_to', parameters: { agent: 'python_agent' } }
        ],
        enabled: true,
        createdAt: new Date(),
        updatedAt: new Date(),
        usageCount: 0,
        successRate: 0
      }
    ];

    defaultRules.forEach(rule => this.routingRules.set(rule.id, rule));
  }

  /**
   * Make intelligent routing decision for a task
   */
  async makeRoutingDecision(task: TaskDelegation, classification?: TaskClassificationResult): Promise<RoutingDecision> {
    try {
      // Apply routing rules
      const ruleBasedAssignment = await this.applyRoutingRules(task);

      if (ruleBasedAssignment) {
        return ruleBasedAssignment;
      }

      // Fallback to intelligent analysis
      return await this.makeIntelligentDecision(task, classification);
    } catch (error) {
      console.error('Error making routing decision:', error);

      // Return fallback decision
      return {
        taskId: task.id,
        selectedAgent: 'expo_agent',
        reasoning: 'Fallback routing due to error',
        confidence: 0.3,
        alternatives: [],
        estimatedCompletionTime: task.expectedDuration,
        cost: { compute: 1, time: task.expectedDuration },
        risks: [{
          type: 'routing_error',
          probability: 1.0,
          impact: 'high',
          mitigation: 'Manual review required'
        }]
      };
    }
  }

  /**
   * Apply configured routing rules to determine assignment
   */
  private async applyRoutingRules(task: TaskDelegation): Promise<RoutingDecision | null> {
    // Sort rules by priority (highest first)
    const sortedRules = Array.from(this.routingRules.values())
      .filter(rule => rule.enabled)
      .sort((a, b) => b.priority - a.priority);

    for (const rule of sortedRules) {
      if (await this.evaluateRule(rule, task)) {
        // Rule matched - execute actions
        const assignment = await this.executeRuleActions(rule, task);

        if (assignment) {
          // Update rule usage statistics
          rule.usageCount++;
          rule.updatedAt = new Date();

          return assignment;
        }
      }
    }

    return null;
  }

  /**
   * Evaluate if a routing rule matches the task
   */
  private async evaluateRule(rule: RoutingRule, task: TaskDelegation): Promise<boolean> {
    for (const condition of rule.conditions) {
      if (!this.evaluateCondition(condition, task)) {
        return false;
      }
    }
    return true;
  }

  /**
   * Evaluate individual condition
   */
  private evaluateCondition(
    condition: RoutingRule['conditions'][0],
    task: TaskDelegation
  ): boolean {
    // Get the value from the task
    const fieldValue = this.getFieldValue(task, condition.field);
    let conditionValue = condition.value;

    // Case insensitive comparison for strings
    if (typeof fieldValue === 'string' && typeof conditionValue === 'string' && !condition.caseSensitive) {
      conditionValue = conditionValue.toLowerCase();
    }

    switch (condition.operator) {
      case 'equals':
        return fieldValue === conditionValue;
      case 'not_equals':
        return fieldValue !== conditionValue;
      case 'greater_than':
        return Number(fieldValue) > Number(conditionValue);
      case 'less_than':
        return Number(fieldValue) < Number(conditionValue);
      case 'contains':
        return String(fieldValue).toLowerCase().includes(String(conditionValue).toLowerCase());
      case 'matches':
        const regex = new RegExp(String(conditionValue), 'i');
        return regex.test(String(fieldValue));
      default:
        return false;
    }
  }

  /**
   * Get nested field value from task object
   */
  private getFieldValue(task: TaskDelegation, field: string): any {
    const parts = field.split('.');
    let value: any = task;

    for (const part of parts) {
      if (value && typeof value === 'object' && part in value) {
        value = value[part];
      } else {
        return undefined;
      }
    }

    return value;
  }

  /**
   * Execute routing rule actions
   */
  private async executeRuleActions(rule: RoutingRule, task: TaskDelegation): Promise<RoutingDecision | null> {
    let selectedAgent: string | null = null;
    let reasoning = `Applied routing rule: ${rule.name}`;
    const alternatives: Array<{ agent: string; score: number; reasoning: string }> = [];

    for (const action of rule.actions) {
      switch (action.type) {
        case 'assign_to':
          selectedAgent = action.parameters.agent;
          break;
        case 'set_priority':
          // Priority would be updated on the task
          break;
        case 'add_metadata':
          // Metadata would be added to the task
          break;
        case 'transform':
          // Task transformation would be applied
          break;
      }
    }

    if (selectedAgent) {
      return {
        taskId: task.id,
        selectedAgent,
        reasoning,
        confidence: 0.9,
        alternatives,
        estimatedCompletionTime: task.expectedDuration,
        cost: { compute: 1, time: task.expectedDuration },
        risks: []
      };
    }

    return null;
  }

  /**
   * Make intelligent routing decision based on analysis
   */
  private async makeIntelligentDecision(
    task: TaskDelegation,
    classification?: TaskClassificationResult
  ): Promise<RoutingDecision> {
    const candidates = await this.getCandidateAgents(task);
    const scored = await this.scoreCandidates(candidates, task, classification);

    // Sort by score (highest first)
    scored.sort((a, b) => b.score - a.score);

    const best = scored[0];
    const alternatives = scored.slice(1, 3); // Top 3 alternatives

    return {
      taskId: task.id,
      selectedAgent: best.agent,
      reasoning: best.reasoning,
      confidence: best.score,
      alternatives: alternatives.map(alt => ({
        agent: alt.agent,
        score: alt.score,
        reasoning: alt.reasoning
      })),
      estimatedCompletionTime: best.estimatedTime,
      cost: best.cost,
      risks: best.risks || []
    };
  }

  /**
   * Get candidate agents that can handle the task
   */
  private async getCandidateAgents(task: TaskDelegation): Promise<string[]> {
    const candidates: string[] = [];

    // Check all known agents
    for (const [agentId, capabilities] of this.agentCapabilities) {
      if (await this.canAgentHandleTask(capabilities, task)) {
        candidates.push(agentId);
      }
    }

    // If no specific agents, add defaults
    if (candidates.length === 0) {
      candidates.push('expo_agent', 'python_agent', 'github_actions', 'netlify_functions');
    }

    return candidates;
  }

  /**
   * Check if an agent can handle a specific task
   */
  private async canAgentHandleTask(capabilities: AgentCapability, task: TaskDelegation): Promise<boolean> {
    // Check if agent is online
    if (!capabilities.availability.online) {
      return false;
    }

    // Check if agent supports the task type
    if (!capabilities.supportedTaskTypes.includes(task.category)) {
      return false;
    }

    // Check if agent has capacity
    if (capabilities.currentLoad >= capabilities.maxConcurrentTasks) {
      return false;
    }

    // Check resource requirements
    const taskResources = task.resourceRequirements;
    const agentLimits = capabilities.resourceLimits;
    const currentUsage = capabilities.currentResourceUsage;

    if (taskResources.compute === 'high' && currentUsage.compute >= agentLimits.compute * 0.8) {
      return false;
    }

    if (taskResources.memory === 'high' && currentUsage.memory >= agentLimits.memory * 0.8) {
      return false;
    }

    // Check for special capabilities
    if (task.category === 'code_analysis' && !capabilities.capabilities.includes('code_analysis')) {
      return false;
    }

    if (task.category === 'market_research' && !capabilities.capabilities.includes('web_scraping')) {
      return false;
    }

    return true;
  }

  /**
   * Score candidate agents for the task
   */
  private async scoreCandidates(
    candidates: string[],
    task: TaskDelegation,
    classification?: TaskClassificationResult
  ): Promise<Array<{
    agent: string;
    score: number;
    reasoning: string;
    estimatedTime: number;
    cost: { compute: number; monetary?: number; time: number };
    risks?: Array<{ type: string; probability: number; impact: string; mitigation: string }>;
  }>> {
    const scored = [];

    for (const agentId of candidates) {
      const capabilities = this.agentCapabilities.get(agentId);
      if (!capabilities) {
        // Default scoring for unknown agents
        scored.push({
          agent: agentId,
          score: 0.5,
          reasoning: 'Default agent with unknown capabilities',
          estimatedTime: task.expectedDuration,
          cost: { compute: 1, time: task.expectedDuration }
        });
        continue;
      }

      const score = await this.calculateAgentScore(capabilities, task, classification);
      const estimatedTime = await this.estimateCompletionTime(capabilities, task);
      const cost = await this.calculateCost(capabilities, task, estimatedTime);
      const reasoning = await this.generateReasoning(capabilities, task, score);
      const risks = await this.assessRisks(capabilities, task);

      scored.push({
        agent: agentId,
        score,
        reasoning,
        estimatedTime,
        cost,
        risks
      });
    }

    return scored;
  }

  /**
   * Calculate score for an agent based on multiple factors
   */
  private async calculateAgentScore(
    capabilities: AgentCapability,
    task: TaskDelegation,
    classification?: TaskClassificationResult
  ): Promise<number> {
    let score = 0.5; // Base score

    // Load factor (lower load = higher score)
    const loadFactor = 1 - (capabilities.currentLoad / capabilities.maxConcurrentTasks);
    score += loadFactor * this.config.priorityWeights.reliability * 0.3;

    // Performance factor
    const performanceFactor = capabilities.successRate;
    score += performanceFactor * this.config.priorityWeights.reliability * 0.2;

    // Speed factor
    const avgTime = capabilities.performance.latency;
    const speedFactor = Math.max(0, 1 - (avgTime / 300000)); // Normalize to 5 minutes
    score += speedFactor * this.config.priorityWeights.speed * 0.2;

    // Specialization factor
    const specialties = capabilities.specialties;
    if (specialties.includes(task.category)) {
      score += 0.2;
    }

    // Resource availability
    const resourceAvailability = this.calculateResourceAvailability(capabilities, task);
    score += resourceAvailability * 0.1;

    // Cost factor (if optimization is enabled)
    if (this.config.enableCostOptimization) {
      const costFactor = await this.calculateCostScore(capabilities, task);
      score += costFactor * this.config.priorityWeights.cost * 0.1;
    }

    // Urgency factor for high priority tasks
    if (task.priority === 'urgent' || task.priority === 'high') {
      score += 0.1;
    }

    return Math.max(0, Math.min(1, score));
  }

  /**
   * Calculate resource availability for the task
   */
  private calculateResourceAvailability(capabilities: AgentCapability, task: TaskDelegation): number {
    const taskResources = task.resourceRequirements;
    const limits = capabilities.resourceLimits;
    const usage = capabilities.currentResourceUsage;

    let availability = 1;

    // Compute availability
    const computeUsage = taskResources.compute === 'high' ? 0.8 : taskResources.compute === 'medium' ? 0.5 : 0.2;
    const computeAvailability = Math.max(0, 1 - (usage.compute + computeUsage) / limits.compute);
    availability = Math.min(availability, computeAvailability);

    // Memory availability
    const memoryUsage = taskResources.memory === 'high' ? 0.8 : taskResources.memory === 'medium' ? 0.5 : 0.2;
    const memoryAvailability = Math.max(0, 1 - (usage.memory + memoryUsage) / limits.memory);
    availability = Math.min(availability, memoryAvailability);

    return availability;
  }

  /**
   * Estimate completion time for the task
   */
  private async estimateCompletionTime(capabilities: AgentCapability, task: TaskDelegation): Promise<number> {
    const baseTime = task.expectedDuration;

    // Adjust based on agent performance
    const performanceMultiplier = capabilities.performance.latency / 60000; // Convert to minutes
    const adjustedTime = baseTime * performanceMultiplier;

    // Adjust based on current load
    const loadMultiplier = 1 + (capabilities.currentLoad / capabilities.maxConcurrentTasks);
    const finalTime = adjustedTime * loadMultiplier;

    // Add buffer for uncertainty
    return Math.round(finalTime * 1.2);
  }

  /**
   * Calculate cost for the task
   */
  private async calculateCost(
    capabilities: AgentCapability,
    task: TaskDelegation,
    estimatedTime: number
  ): Promise<{ compute: number; monetary?: number; time: number }> {
    const computeCost = this.calculateComputeCost(capabilities, task);
    const timeCost = estimatedTime;

    // Monetary cost would depend on specific pricing model
    const monetaryCost = capabilities.agentType === 'github_actions' ?
      Math.ceil(estimatedTime / 60) * 0.008 : // $0.008 per minute for GitHub Actions
      capabilities.agentType === 'netlify_functions' ?
      Math.ceil(estimatedTime / 100) * 0.0000001 : // Function invocation cost
      undefined;

    return {
      compute: computeCost,
      monetary: monetaryCost,
      time: timeCost
    };
  }

  /**
   * Calculate compute cost for the task
   */
  private calculateComputeCost(capabilities: AgentCapability, task: TaskDelegation): number {
    const taskResources = task.resourceRequirements;
    const complexity = task.complexity;

    let cost = 1;

    // Resource-based cost
    if (taskResources.compute === 'high') cost *= 3;
    else if (taskResources.compute === 'medium') cost *= 2;

    if (taskResources.memory === 'high') cost *= 2;

    // Complexity-based cost
    cost *= (complexity / 5); // Normalize around complexity 5

    // Agent-specific multipliers
    switch (capabilities.agentType) {
      case 'github_actions':
        cost *= 0.5; // Usually cheaper for compute-heavy tasks
        break;
      case 'netlify_functions':
        cost *= 1.5; // Premium for serverless convenience
        break;
      case 'python_agent':
        cost *= 1.2; // Slightly more expensive for advanced AI capabilities
        break;
      default:
        break;
    }

    return Math.max(0.1, cost);
  }

  /**
   * Generate reasoning for the routing decision
   */
  private async generateReasoning(
    capabilities: AgentCapability,
    task: TaskDelegation,
    score: number
  ): Promise<string> {
    const reasons = [];

    if (capabilities.specialties.includes(task.category)) {
      reasons.push('specialized in task type');
    }

    if (capabilities.successRate > 0.9) {
      reasons.push('high success rate');
    }

    if (capabilities.currentLoad < capabilities.maxConcurrentTasks * 0.5) {
      reasons.push('low current load');
    }

    if (capabilities.performance.latency < 60000) {
      reasons.push('fast response time');
    }

    if (score > 0.8) {
      reasons.push('overall high score');
    }

    return `Selected based on: ${reasons.join(', ')}`;
  }

  /**
   * Assess potential risks for the routing decision
   */
  private async assessRisks(
    capabilities: AgentCapability,
    task: TaskDelegation
  ): Promise<Array<{ type: string; probability: number; impact: string; mitigation: string }>> {
    const risks = [];

    // High load risk
    if (capabilities.currentLoad > capabilities.maxConcurrentTasks * 0.8) {
      risks.push({
        type: 'high_load',
        probability: 0.7,
        impact: 'medium',
        mitigation: 'Monitor performance and consider reassignment if delays occur'
      });
    }

    // Resource constraint risk
    const resourceAvailability = this.calculateResourceAvailability(capabilities, task);
    if (resourceAvailability < 0.3) {
      risks.push({
        type: 'resource_constraint',
        probability: 0.8,
        impact: 'high',
        mitigation: 'Consider alternative agent with more resources'
      });
    }

    // Low success rate risk
    if (capabilities.successRate < 0.7) {
      risks.push({
        type: 'low_success_rate',
        probability: 0.6,
        impact: 'high',
        mitigation: 'Have backup agent ready for reassignment'
      });
    }

    // Agent availability risk
    if (!capabilities.availability.online) {
      risks.push({
        type: 'agent_offline',
        probability: 1.0,
        impact: 'high',
        mitigation: 'Route to alternative agent immediately'
      });
    }

    return risks;
  }

  /**
   * Calculate cost score for optimization
   */
  private async calculateCostScore(capabilities: AgentCapability, task: TaskDelegation): Promise<number> {
    // Simple cost scoring - lower cost = higher score
    const baseCost = this.calculateComputeCost(capabilities, task);
    const maxCost = 10; // Assume maximum cost is 10 units
    return Math.max(0, 1 - (baseCost / maxCost));
  }

  /**
   * Update agent capabilities
   */
  async updateAgentCapabilities(agentId: string, capabilities: Partial<AgentCapability>): Promise<void> {
    const existing = this.agentCapabilities.get(agentId) || {
      agentId,
      agentType: 'expo_agent',
      capabilities: [],
      maxConcurrentTasks: 5,
      currentLoad: 0,
      averageProcessingTime: 0,
      successRate: 1.0,
      resourceLimits: { compute: 100, memory: 100, network: 100, storage: 100 },
      currentResourceUsage: { compute: 0, memory: 0, network: 0, storage: 0 },
      supportedTaskTypes: [],
      specialties: [],
      availability: { online: true, lastSeen: new Date(), scheduledMaintenance: [] },
      performance: { throughput: 0, latency: 0, errorRate: 0 }
    };

    const updated = { ...existing, ...capabilities };
    this.agentCapabilities.set(agentId, updated);
  }

  /**
   * Add or update routing rule
   */
  async updateRoutingRule(rule: RoutingRule): Promise<void> {
    RoutingRuleSchema.parse(rule);
    this.routingRules.set(rule.id, { ...rule, updatedAt: new Date() });
  }

  /**
   * Delete routing rule
   */
  deleteRoutingRule(ruleId: string): boolean {
    return this.routingRules.delete(ruleId);
  }

  /**
   * Get all routing rules
   */
  getRoutingRules(): RoutingRule[] {
    return Array.from(this.routingRules.values());
  }

  /**
   * Get load balancing metrics
   */
  getLoadBalancingMetrics(): LoadBalancingMetrics {
    const agents = Array.from(this.agentCapabilities.values());
    const activeAgents = agents.filter(a => a.availability.online);
    const loads = agents.map(a => a.currentLoad / a.maxConcurrentTasks);
    const averageLoad = loads.length > 0 ? loads.reduce((a, b) => a + b, 0) / loads.length : 0;
    const maxLoad = loads.length > 0 ? Math.max(...loads) : 0;

    const loadDistribution: Record<string, number> = {};
    agents.forEach(agent => {
      loadDistribution[agent.agentId] = agent.currentLoad;
    });

    const totalRoutings = this.routingHistory.length;
    const failedRoutings = this.routingHistory.filter(r => r.confidence < 0.5).length;
    const successfulRoutings = totalRoutings - failedRoutings;

    return {
      totalAgents: agents.length,
      activeAgents: activeAgents.length,
      averageLoad,
      maxLoad,
      loadDistribution,
      throughput: this.calculateThroughput(),
      averageResponseTime: this.calculateAverageResponseTime(),
      queueSize: this.calculateQueueSize(),
      failedRoutings,
      successfulRoutings
    };
  }

  private calculateThroughput(): number {
    // Calculate tasks per minute from recent history
    const recentRoutings = this.routingHistory.slice(-100); // Last 100 routings
    if (recentRoutings.length < 2) return 0;

    const timeSpan = (new Date().getTime() - recentRoutings[0].estimatedCompletionTime * 1000) / 60000;
    return timeSpan > 0 ? recentRoutings.length / timeSpan : 0;
  }

  private calculateAverageResponseTime(): number {
    if (this.routingHistory.length === 0) return 0;

    const totalTime = this.routingHistory.reduce((sum, r) => sum + r.estimatedCompletionTime * 1000, 0);
    return totalTime / this.routingHistory.length;
  }

  private calculateQueueSize(): number {
    return Array.from(this.agentCapabilities.values())
      .reduce((total, agent) => total + agent.currentLoad, 0);
  }
}

export default SmartRoutingService;