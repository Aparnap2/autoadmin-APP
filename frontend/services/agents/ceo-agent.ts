/**
 * CEO Agent - Main orchestrator for the AutoAdmin system
 * Coordinates between Strategy and DevOps agents
 */

import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { createSupervisor } from '@langchain/langgraph';
import { StateGraph, MessagesAnnotation, Command } from '@langchain/langgraph';
import { BaseMessage, HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';

import BaseAgent from './base-agent';
import {
  AgentState,
  AgentConfig,
  AgentResponse,
  AgentTool,
  NextAction,
  TaskStatus,
  TaskType,
  UserContext,
  ExecutionContext
} from './types';
import StrategyAgent from './strategy-agent';
import DevOpsAgent from './devops-agent';
import GraphMemoryService from '../../utils/supabase/graph-memory';

export interface SupervisorResponse {
  next: string;
  reasoning: string;
  instructions: string;
  requiresApproval: boolean;
}

export interface CEOAgentConfig extends AgentConfig {
  maxDelegationDepth: number;
  approvalThreshold: number;
  autoApproveTasks: string[];
}

export class CEOAgent extends BaseAgent {
  private strategyAgent: StrategyAgent;
  private devOpsAgent: DevOpsAgent;
  private supervisorChain: any;
  private currentDelegationDepth: number = 0;
  private ceoConfig: CEOAgentConfig;

  constructor(config: CEOAgentConfig, userId: string) {
    super(config, userId);
    this.ceoConfig = config;

    // Initialize sub-agents
    this.strategyAgent = new StrategyAgent(this.createStrategyAgentConfig(), userId);
    this.devOpsAgent = new DevOpsAgent(this.createDevOpsAgentConfig(), userId);
  }

  /**
   * Initialize CEO agent and sub-agents
   */
  async initialize(): Promise<void> {
    await super.initialize();
    await this.strategyAgent.initialize();
    await this.devOpsAgent.initialize();

    // Create the supervisor chain
    this.supervisorChain = await this.createSupervisorChain();

    console.log('CEO Agent and sub-agents initialized successfully');
  }

  /**
   * Process incoming tasks and orchestrate between sub-agents
   */
  async process(state: AgentState): Promise<AgentResponse> {
    const startTime = Date.now();

    try {
      await this.updateMetrics('start');

      // Analyze the request and determine best approach
      const analysis = await this.analyzeRequest(state);

      // Make delegation decision
      const delegationDecision = await this.makeDelegationDecision(analysis, state);

      if (delegationDecision.delegateToAgent) {
        return await this.delegateToAgent(delegationDecision.delegateToAgent, state);
      }

      if (delegationDecision.delegateToBackend) {
        return await this.delegateToBackend(delegationDecision.delegateToBackend, state);
      }

      // Handle directly or create coordinated workflow
      return await this.handleDirectly(state);

    } catch (error) {
      console.error('CEO Agent processing error:', error);
      await this.updateMetrics('error');

      return {
        success: false,
        message: `Error processing request: ${error}`,
        requiresUserInput: true,
        userInputPrompt: 'The system encountered an error. Would you like to try again or provide more details?'
      };
    } finally {
      const responseTime = Date.now() - startTime;
      await this.updateMetrics('complete', responseTime, true);
    }
  }

  /**
   * Analyze the incoming request to understand requirements
   */
  private async analyzeRequest(state: AgentState): Promise<{
    complexity: number;
    type: TaskType;
    requiresResearch: boolean;
    requiresTechnicalAnalysis: boolean;
    requiresFinancialAnalysis: boolean;
    estimatedDuration: number;
    risks: string[];
  }> {
    const latestMessage = state.messages[state.messages.length - 1];
    const content = latestMessage.content as string;

    // Use LLM to analyze the request
    const analysisPrompt = `Analyze this user request and provide structured analysis:

    Request: "${content}"

    Provide analysis in JSON format with:
    - complexity (1-10 scale)
    - type (market_research, financial_analysis, code_analysis, ui_ux_review, strategic_planning, technical_decision)
    - requiresResearch (boolean)
    - requiresTechnicalAnalysis (boolean)
    - requiresFinancialAnalysis (boolean)
    - estimatedDuration (in minutes)
    - risks (array of potential risks)

    Consider factors like:
    - Amount of research needed
    - Technical complexity
    - Financial implications
    - Strategic importance
    - Resource requirements`;

    const response = await this.llm.invoke(analysisPrompt);
    const analysisText = response.content as string;

    try {
      // Extract JSON from response
      const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
    } catch (error) {
      console.warn('Could not parse analysis JSON, using defaults');
    }

    // Fallback analysis
    return {
      complexity: 5,
      type: 'strategic_planning',
      requiresResearch: content.toLowerCase().includes('research'),
      requiresTechnicalAnalysis: content.toLowerCase().includes('code') || content.toLowerCase().includes('technical'),
      requiresFinancialAnalysis: content.toLowerCase().includes('financial') || content.toLowerCase().includes('budget'),
      estimatedDuration: 10,
      risks: []
    };
  }

  /**
   * Make intelligent delegation decisions
   */
  private async makeDelegationDecision(
    analysis: any,
    state: AgentState
  ): Promise<{
    delegateToAgent?: 'strategy' | 'devops';
    delegateToBackend?: 'github_actions' | 'netlify_functions';
    handleDirectly: boolean;
  }> {
    // Check delegation rules
    for (const rule of this.ceoConfig.delegationRules) {
      if (this.evaluateRule(rule, analysis, state)) {
        if (rule.targetAgent) {
          return {
            delegateToAgent: rule.targetAgent,
            handleDirectly: false
          };
        }
        if (rule.targetBackend) {
          return {
            delegateToBackend: rule.targetBackend,
            handleDirectly: false
          };
        }
      }
    }

    // Intelligent delegation based on analysis
    if (analysis.requiresResearch || analysis.requiresFinancialAnalysis) {
      return {
        delegateToAgent: 'strategy',
        handleDirectly: false
      };
    }

    if (analysis.requiresTechnicalAnalysis || analysis.type === 'code_analysis' || analysis.type === 'ui_ux_review') {
      return {
        delegateToAgent: 'devops',
        handleDirectly: false
      };
    }

    // High complexity tasks might need backend processing
    if (analysis.complexity >= 8 && analysis.estimatedDuration > 30) {
      return {
        delegateToBackend: 'github_actions',
        handleDirectly: false
      };
    }

    // Simple tasks can be handled directly
    return { handleDirectly: true };
  }

  /**
   * Evaluate delegation rule conditions
   */
  private evaluateRule(rule: any, analysis: any, state: AgentState): boolean {
    // Simple rule evaluation - can be enhanced with more complex logic
    if (rule.threshold.complexity && analysis.complexity >= rule.threshold.complexity) {
      return true;
    }

    if (rule.threshold.timeLimit && analysis.estimatedDuration >= rule.threshold.timeLimit) {
      return true;
    }

    // Check condition string (simple keyword matching)
    if (rule.condition) {
      const content = state.messages[state.messages.length - 1].content as string;
      const conditionLower = rule.condition.toLowerCase();
      const contentLower = content.toLowerCase();

      return conditionLower.split(' ').some((word: string) => contentLower.includes(word));
    }

    return false;
  }

  /**
   * Delegate task to a sub-agent
   */
  private async delegateToAgent(
    agentType: 'strategy' | 'devops',
    state: AgentState
  ): Promise<AgentResponse> {
    const agent = agentType === 'strategy' ? this.strategyAgent : this.devOpsAgent;

    try {
      // Create task for delegation
      const task: TaskStatus = {
        id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: this.determineTaskType(state),
        status: 'processing',
        priority: 'medium',
        createdAt: new Date(),
        updatedAt: new Date(),
        assignedTo: this.ceoConfig.id,
        delegatedTo: agentType,
        metadata: {
          originalRequest: state.messages[state.messages.length - 1].content,
          delegationReason: 'auto_delegation'
        }
      };

      // Add task to state
      state.taskStatus = task;

      // Process with sub-agent
      const response = await agent.process(state);

      // Update task status
      task.status = response.success ? 'completed' : 'failed';
      task.updatedAt = new Date();
      state.taskStatus = task;

      return response;
    } catch (error) {
      console.error(`Error delegating to ${agentType} agent:`, error);
      return {
        success: false,
        message: `Error processing with ${agentType} agent: ${error}`,
        nextAction: {
          type: 'continue',
          payload: { fallback: true }
        }
      };
    }
  }

  /**
   * Delegate task to backend services
   */
  private async delegateToBackend(
    backend: 'github_actions' | 'netlify_functions',
    state: AgentState
  ): Promise<AgentResponse> {
    try {
      // Create backend task
      const taskData = {
        task: state.messages[state.messages.length - 1].content,
        parameters: {
          userContext: state.userContext,
          currentPath: state.virtualFileSystem?.currentPath,
          timestamp: new Date().toISOString()
        },
        priority: 'medium',
        backend
      };

      // Store task in Supabase for backend processing
      await this.graphMemory.addMemory(
        JSON.stringify(taskData),
        'task',
        [],
        { backend, status: 'queued' }
      );

      return {
        success: true,
        message: `Task delegated to ${backend} for processing. You will receive a notification when it's complete.`,
        requiresUserInput: false,
        nextAction: {
          type: 'complete',
          expectedDuration: 300 // 5 minutes estimate
        }
      };
    } catch (error) {
      console.error('Error delegating to backend:', error);
      return {
        success: false,
        message: `Error delegating to backend: ${error}`,
        requiresUserInput: true
      };
    }
  }

  /**
   * Handle task directly with CEO agent
   */
  private async handleDirectly(state: AgentState): Promise<AgentResponse> {
    try {
      // Use tools and LLM to handle the task
      const tools = this.getTools().map(t =>
        tool(t.handler, {
          name: t.name,
          description: t.description,
          schema: t.schema,
        })
      );

      const agent = createReactAgent({
        llm: this.llm,
        tools,
        stateModifier: this.ceoConfig.systemPrompt,
      });

      const result = await agent.invoke({
        messages: state.messages
      });

      const agentResponse = result.messages[result.messages.length - 1]?.content || 'No response generated';

      // Store interaction in graph memory
      await this.graphMemory.addMemory(
        state.messages[state.messages.length - 1].content as string,
        'feature',
        [],
        { agent: 'ceo', response: agentResponse }
      );

      return {
        success: true,
        data: agentResponse,
        message: 'Task completed successfully'
      };
    } catch (error) {
      console.error('Error handling task directly:', error);
      return {
        success: false,
        message: `Error processing task: ${error}`
      };
    }
  }

  /**
   * Create supervisor chain for multi-agent coordination
   */
  private async createSupervisorChain(): Promise<any> {
    const members = ['strategy', 'devops', 'ceo'];

    const systemPrompt = `You are the CEO supervisor of AutoAdmin, managing specialized agents:

    - strategy_agent: Handles market research, financial analysis, and strategic planning
    - devops_agent: Handles code analysis, UI/UX review, and technical decisions
    - ceo: Handles high-level coordination and direct responses for simple tasks

    Your responsibilities:
    1. Analyze user requests and determine the best agent to handle them
    2. Coordinate between agents when tasks require multiple perspectives
    3. Make decisions about when to delegate to backend services vs handle client-side
    4. Ensure all responses are aligned with user goals and business objectives
    5. Manage task priority and resource allocation

    Routing rules:
    - Market research, competitive analysis, financial planning → strategy_agent
    - Code review, technical architecture, UI/UX analysis → devops_agent
    - Simple coordination, status updates, quick decisions → ceo
    - Complex, long-running tasks → GitHub Actions or Netlify Functions

    Always provide reasoning for your routing decisions.`;

    const workflow = createSupervisor({
      agents: [this.strategyAgent, this.devOpsAgent],
      llm: this.llm,
      prompt: systemPrompt,
      outputMode: 'full_history'
    });

    return workflow.compile();
  }

  /**
   * Create strategy agent configuration
   */
  private createStrategyAgentConfig(): AgentConfig {
    return {
      id: 'strategy-agent',
      name: 'Strategy Agent (CMO/CFO)',
      type: 'strategy',
      model: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 2000,
      tools: [],
      systemPrompt: `You are a Strategy Agent for AutoAdmin, combining CMO (Chief Marketing Officer) and CFO (Chief Financial Officer) capabilities.

Your expertise includes:
- Market research and competitive analysis
- Financial planning and budget analysis
- Business strategy and growth planning
- Customer acquisition and retention strategies
- Revenue optimization and cost analysis
- Market trend identification
- Business intelligence and insights

Always provide data-driven recommendations and consider both marketing and financial implications in your advice.`,
      capabilities: [],
      delegationRules: []
    };
  }

  /**
   * Create DevOps agent configuration
   */
  private createDevOpsAgentConfig(): AgentConfig {
    return {
      id: 'devops-agent',
      name: 'DevOps Agent (CTO)',
      type: 'devops',
      model: 'gpt-4o-mini',
      temperature: 0.3,
      maxTokens: 2000,
      tools: [],
      systemPrompt: `You are a DevOps Agent for AutoAdmin, serving as the CTO (Chief Technology Officer).

Your expertise includes:
- Code analysis and technical architecture review
- UI/UX consistency and accessibility analysis
- Performance optimization and security auditing
- Technical decision making and best practices
- System architecture and scalability planning
- Development workflows and CI/CD optimization
- Technical debt assessment and refactoring recommendations

Always focus on code quality, performance, security, and maintainability in your recommendations.`,
      capabilities: [],
      delegationRules: []
    };
  }

  /**
   * Determine task type from message
   */
  private determineTaskType(state: AgentState): TaskType {
    const content = state.messages[state.messages.length - 1].content as string;
    const contentLower = content.toLowerCase();

    if (contentLower.includes('research') || contentLower.includes('market') || contentLower.includes('competition')) {
      return 'market_research';
    }
    if (contentLower.includes('financial') || contentLower.includes('budget') || contentLower.includes('revenue')) {
      return 'financial_analysis';
    }
    if (contentLower.includes('code') || contentLower.includes('technical') || contentLower.includes('development')) {
      return 'code_analysis';
    }
    if (contentLower.includes('ui') || contentLower.includes('ux') || contentLower.includes('design')) {
      return 'ui_ux_review';
    }
    if (contentLower.includes('architecture') || contentLower.includes('system') || contentLower.includes('scalability')) {
      return 'technical_decision';
    }

    return 'strategic_planning';
  }

  /**
   * Get system status and health
   */
  async getSystemStatus(): Promise<{
    ceoAgent: any;
    strategyAgent: any;
    devOpsAgent: any;
    totalTasks: number;
    successRate: number;
  }> {
    return {
      ceoAgent: this.getMetrics(),
      strategyAgent: this.strategyAgent.getMetrics(),
      devOpsAgent: this.devOpsAgent.getMetrics(),
      totalTasks: this.metrics.totalTasks + this.strategyAgent.getMetrics().totalTasks + this.devOpsAgent.getMetrics().totalTasks,
      successRate: this.calculateOverallSuccessRate()
    };
  }

  private calculateOverallSuccessRate(): number {
    const totalTasks = this.metrics.totalTasks + this.strategyAgent.getMetrics().totalTasks + this.devOpsAgent.getMetrics().totalTasks;
    const completedTasks = this.metrics.completedTasks + this.strategyAgent.getMetrics().completedTasks + this.devOpsAgent.getMetrics().completedTasks;

    return totalTasks > 0 ? completedTasks / totalTasks : 1.0;
  }
}

export default CEOAgent;