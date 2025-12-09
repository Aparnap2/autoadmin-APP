/**
 * Simple CEO Agent - Client-side stub
 * Delegates all processing to FastAPI backend
 */

import {
  getSimpleAgentService,
  AgentResponse
} from './simple-agent-service';

export interface SimpleCEOConfig {
  id: string;
  name: string;
  delegationRules: any[];
}

export class SimpleCEOAgent {
  private config: SimpleCEOConfig;
  private agentService: ReturnType<typeof getSimpleAgentService>;
  private isInitialized = false;

  constructor(config: SimpleCEOConfig) {
    this.config = config;
    this.agentService = getSimpleAgentService();
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.agentService.initialize();
      this.isInitialized = true;
      console.log('Simple CEO Agent initialized successfully');
    } catch (error) {
      console.error('Error initializing Simple CEO Agent:', error);
      throw error;
    }
  }

  async process(message: string, context?: any): Promise<AgentResponse> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      // Delegate to backend with CEO agent hint
      return await this.agentService.processUserMessage(message, 'ceo', context);
    } catch (error) {
      console.error('Error in Simple CEO Agent processing:', error);
      throw error;
    }
  }

  getMetrics(): any {
    return {
      id: this.config.id,
      name: this.config.name,
      type: 'ceo',
      initialized: this.isInitialized,
      delegationRulesCount: this.config.delegationRules.length
    };
  }
}

export default SimpleCEOAgent;