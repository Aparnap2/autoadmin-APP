import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { createReactAgent, AgentExecutor } from '@langchain/langgraph/prebuilt';
import { HumanMessage, AIMessage } from '@langchain/core/messages';
import FirestoreService from '../firebase/firestore.service';
import { createChatOpenAIWithProviderSystem } from './llm-provider/langchain-adapter';

export interface AgentMessage {
  id: string;
  content: string;
  type: 'human' | 'ai';
  timestamp: Date;
}

export interface AgentConfig {
  model: string;
  temperature: number;
  maxTokens?: number;
}

export interface AgentTool {
  name: string;
  description: string;
  schema: z.ZodSchema;
  handler: (input: any) => Promise<string>;
}

export class LangGraphService {
  private static instance: LangGraphService;
  private agent: AgentExecutor | null = null;
  private firestoreService: FirestoreService;
  private userId: string | null = null;
  private agentId: string = 'ceo-agent';

  private constructor() {
    this.firestoreService = FirestoreService.getInstance();
  }

  static getInstance(): LangGraphService {
    if (!LangGraphService.instance) {
      LangGraphService.instance = new LangGraphService();
    }
    return LangGraphService.instance;
  }

  setUserId(userId: string): void {
    this.userId = userId;
  }

  private createLLM(config: AgentConfig) {
    return createChatOpenAIWithProviderSystem({
      model: config.model,
      temperature: config.temperature,
      maxTokens: config.maxTokens,
      providerSystemConfig: {
        primary: {
          provider: (process.env.LLM_PROVIDER || 'openai') as any,
          apiKey: process.env.LLM_API_KEY || process.env.EXPO_PUBLIC_OPENAI_API_KEY || '',
          model: config.model,
          temperature: config.temperature,
          maxTokens: config.maxTokens,
          baseUrl: process.env.LLM_BASE_URL,
          timeout: parseInt(process.env.LLM_TIMEOUT || '60000'),
          retryAttempts: parseInt(process.env.LLM_MAX_RETRIES || '3')
        },
        fallback: {
          enabled: process.env.LLM_ENABLE_FALLBACK === 'true',
          providers: (process.env.LLM_FALLBACK_PROVIDERS || '').split(',').filter(Boolean),
          retryOnErrors: (process.env.LLM_RETRY_ERRORS || 'rate_limit,server_error,timeout').split(','),
          maxRetries: parseInt(process.env.LLM_MAX_RETRIES || '3')
        },
        caching: {
          enabled: process.env.LLM_ENABLE_CACHE !== 'false',
          ttl: parseInt(process.env.LLM_CACHE_TTL || '300'),
          maxSize: parseInt(process.env.LLM_CACHE_MAX_SIZE || '1000')
        },
        monitoring: {
          enabled: process.env.LLM_ENABLE_MONITORING !== 'false',
          trackMetrics: process.env.LLM_TRACK_METRICS !== 'false',
          trackCosts: process.env.LLM_TRACK_COSTS === 'true',
          alertOnFailures: process.env.LLM_ALERT_FAILURES === 'true'
        }
      }
    });
  }

  private createTools(): AgentTool[] {
    return [
      {
        name: 'save_to_firestore',
        description: 'Save data to Firestore database for persistence',
        schema: z.object({
          collection: z.string().describe('The collection name to save to'),
          data: z.record(z.any()).describe('The data to save'),
        }),
        handler: async (input) => {
          try {
            if (!this.userId) {
              return 'Error: User not authenticated';
            }

            const dataToSave = {
              ...input.data,
              userId: this.userId,
              createdAt: new Date(),
            };

            const docId = await this.firestoreService.saveMessage({
              userId: this.userId,
              agentId: this.agentId,
              content: JSON.stringify(dataToSave),
              type: 'agent',
              metadata: { collection: input.collection }
            });

            return `Successfully saved data to ${input.collection} with ID: ${docId}`;
          } catch (error) {
            console.error('Firestore save error:', error);
            return `Error saving to Firestore: ${error}`;
          }
        }
      },
      {
        name: 'get_firestore_data',
        description: 'Retrieve data from Firestore database',
        schema: z.object({
          collection: z.string().describe('The collection name to retrieve from'),
          limit: z.number().optional().describe('Maximum number of documents to retrieve'),
        }),
        handler: async (input) => {
          try {
            if (!this.userId) {
              return 'Error: User not authenticated';
            }

            // This is a simplified example - you'd implement actual collection-specific queries
            const messages = await this.firestoreService.getMessages(
              this.userId,
              this.agentId,
              input.limit || 10
            );

            return JSON.stringify(messages, null, 2);
          } catch (error) {
            console.error('Firestore retrieve error:', error);
            return `Error retrieving from Firestore: ${error}`;
          }
        }
      },
      {
        name: 'netlify_function_call',
        description: 'Call backend Netlify Functions for complex operations',
        schema: z.object({
          functionName: z.string().describe('The name of the Netlify function to call'),
          data: z.record(z.any()).describe('The data to send to the function'),
        }),
        handler: async (input) => {
          try {
            const functionsUrl = process.env.EXPO_PUBLIC_NETLIFY_FUNCTIONS_URL;
            if (!functionsUrl) {
              return 'Error: Netlify Functions URL not configured';
            }

            const response = await fetch(`${functionsUrl}/${input.functionName}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(input.data),
            });

            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return JSON.stringify(result, null, 2);
          } catch (error) {
            console.error('Netlify function error:', error);
            return `Error calling Netlify function: ${error}`;
          }
        }
      }
    ];
  }

  async initializeAgent(config: AgentConfig): Promise<void> {
    try {
      const llm = this.createLLM(config);
      const tools = this.createTools();

      // Convert AgentTool[] to LangGraph tools
      const langGraphTools = tools.map(agentTool =>
        tool(agentTool.handler, {
          name: agentTool.name,
          description: agentTool.description,
          schema: agentTool.schema,
        })
      );

      // Create the CEO agent with system prompt
      const systemPrompt = `You are the CEO Agent for AutoAdmin, an intelligent automation system.

Your responsibilities:
1. Coordinate and delegate tasks to specialized agents
2. Make strategic decisions about task execution
3. Store important information in the database for persistence
4. Call backend services when complex processing is needed
5. Provide clear, actionable responses to user requests

You have access to tools for:
- Saving and retrieving data from Firestore
- Calling backend Netlify Functions
- Executing various operational tasks

Always respond professionally and focus on providing actionable solutions to user requests.`;

      this.agent = createReactAgent({
        llm,
        tools: langGraphTools,
        stateModifier: systemPrompt,
      });

      console.log('LangGraph agent initialized successfully');
    } catch (error) {
      console.error('Error initializing agent:', error);
      throw error;
    }
  }

  async processMessage(message: string): Promise<string> {
    if (!this.agent) {
      throw new Error('Agent not initialized. Call initializeAgent() first.');
    }

    if (!this.userId) {
      throw new Error('User ID not set. Call setUserId() first.');
    }

    try {
      // Save user message to Firestore
      await this.firestoreService.saveMessage({
        userId: this.userId,
        agentId: this.agentId,
        content: message,
        type: 'user',
      });

      // Process message with agent
      const result = await this.agent.invoke({
        messages: [new HumanMessage(message)]
      });

      const agentResponse = result.messages[result.messages.length - 1]?.content || 'No response generated';

      // Save agent response to Firestore
      await this.firestoreService.saveMessage({
        userId: this.userId,
        agentId: this.agentId,
        content: agentResponse as string,
        type: 'agent',
      });

      return agentResponse as string;
    } catch (error) {
      console.error('Error processing message:', error);
      throw error;
    }
  }

  async getConversationHistory(limit: number = 20): Promise<AgentMessage[]> {
    if (!this.userId) {
      throw new Error('User ID not set. Call setUserId() first.');
    }

    try {
      const messages = await this.firestoreService.getMessages(this.userId, this.agentId, limit);

      return messages.map(msg => ({
        id: msg.id || '',
        content: msg.content,
        type: msg.type === 'user' ? 'human' : 'ai',
        timestamp: msg.timestamp.toDate(),
      }));
    } catch (error) {
      console.error('Error getting conversation history:', error);
      throw error;
    }
  }

  async saveAgentState(state: Record<string, any>): Promise<void> {
    if (!this.userId) {
      throw new Error('User ID not set. Call setUserId() first.');
    }

    try {
      await this.firestoreService.saveAgentState({
        userId: this.userId,
        agentId: this.agentId,
        state,
      });
    } catch (error) {
      console.error('Error saving agent state:', error);
      throw error;
    }
  }

  async loadAgentState(): Promise<Record<string, any> | null> {
    if (!this.userId) {
      throw new Error('User ID not set. Call setUserId() first.');
    }

    try {
      const agentState = await this.firestoreService.getAgentState(this.userId, this.agentId);
      return agentState?.state || null;
    } catch (error) {
      console.error('Error loading agent state:', error);
      throw error;
    }
  }

  getAgentStatus(): { initialized: boolean; userId: string | null; agentId: string } {
    return {
      initialized: this.agent !== null,
      userId: this.userId,
      agentId: this.agentId,
    };
  }
}

export default LangGraphService;