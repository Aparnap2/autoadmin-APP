/**
 * Simple Strategy Agent - Client-side stub
 * Delegates all processing to FastAPI backend
 */

import {
  getSimpleAgentService,
  AgentResponse
} from './simple-agent-service';

export interface SimpleStrategyConfig {
  id: string;
  name: string;
  capabilities: string[];
}

export class SimpleStrategyAgent {
  private config: SimpleStrategyConfig;
  private agentService: ReturnType<typeof getSimpleAgentService>;
  private isInitialized = false;

  constructor(config: SimpleStrategyConfig) {
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
      console.log('Simple Strategy Agent initialized successfully');
    } catch (error) {
      console.error('Error initializing Simple Strategy Agent:', error);
      throw error;
    }
  }

  async process(message: string, context?: any): Promise<AgentResponse> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      // Delegate to backend with strategy agent hint
      return await this.agentService.processUserMessage(message, 'strategy', context);
    } catch (error) {
      console.error('Error in Simple Strategy Agent processing:', error);
      throw error;
    }
  }

  getMetrics(): any {
    return {
      id: this.config.id,
      name: this.config.name,
      type: 'strategy',
      initialized: this.isInitialized,
      capabilities: this.config.capabilities
    };
  }
}

export default SimpleStrategyAgent;