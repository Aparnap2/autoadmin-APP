/**
 * Simple DevOps Agent - Client-side stub
 * Delegates all processing to FastAPI backend
 */

import {
  getSimpleAgentService,
  AgentResponse
} from './simple-agent-service';

export interface SimpleDevOpsConfig {
  id: string;
  name: string;
  capabilities: string[];
}

export class SimpleDevOpsAgent {
  private config: SimpleDevOpsConfig;
  private agentService: ReturnType<typeof getSimpleAgentService>;
  private isInitialized = false;

  constructor(config: SimpleDevOpsConfig) {
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
      console.log('Simple DevOps Agent initialized successfully');
    } catch (error) {
      console.error('Error initializing Simple DevOps Agent:', error);
      throw error;
    }
  }

  async process(message: string, context?: any): Promise<AgentResponse> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    try {
      // Delegate to backend with devops agent hint
      return await this.agentService.processUserMessage(message, 'devops', context);
    } catch (error) {
      console.error('Error in Simple DevOps Agent processing:', error);
      throw error;
    }
  }

  getMetrics(): any {
    return {
      id: this.config.id,
      name: this.config.name,
      type: 'devops',
      initialized: this.isInitialized,
      capabilities: this.config.capabilities
    };
  }
}

export default SimpleDevOpsAgent;