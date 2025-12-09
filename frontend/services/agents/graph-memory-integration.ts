/**
 * Enhanced Graph Memory Integration for AutoAdmin Agents
 * Provides intelligent memory management with semantic search and relationship tracking
 */

import { getFirebaseService } from '../../lib/firebase.ts';
import GraphMemoryService from '../../utils/firebase/graph-memory';
import {
  AgentState,
  TaskStatus,
  TaskType,
  GraphMemoryNode,
  GraphMemoryEdge,
  BusinessContext,
  LearnedPattern
} from './types';

export interface MemoryNode {
  id: string;
  type: 'conversation' | 'insight' | 'decision' | 'task_result' | 'user_preference' | 'business_rule' | 'trend' | 'metric' | 'file';
  content: string;
  agent?: string;
  userId: string;
  sessionId: string;
  timestamp: Date;
  embedding?: number[];
  metadata: Record<string, any>;
  relationships: Relationship[];
}

export interface Relationship {
  targetId: string;
  type: 'relates_to' | 'builds_on' | 'contradicts' | 'implements' | 'references' | 'depends_on';
  strength: number; // 0-1
  metadata?: Record<string, any>;
}

export interface MemorySearchOptions {
  query?: string;
  agent?: string;
  type?: MemoryNode['type'];
  sessionId?: string;
  timeframe?: {
    start: Date;
    end: Date;
  };
  includeRelated?: boolean;
  maxResults?: number;
  similarityThreshold?: number;
}

export interface MemoryAnalytics {
  totalNodes: number;
  nodesByType: Record<string, number>;
  nodesByAgent: Record<string, number>;
  averageConnections: number;
  strongestConnections: Array<{
    sourceId: string;
    targetId: string;
    strength: number;
    type: string;
  }>;
  temporalPatterns: Array<{
    date: string;
    nodeCount: number;
    primaryTypes: string[];
  }>;
}

export class GraphMemoryIntegration {
  private graphMemory: GraphMemoryService;
  private firebaseService = getFirebaseService();
  private userId: string;
  private sessionId: string;
  private embeddingCache: Map<string, number[]> = new Map();

  constructor(userId: string, sessionId: string) {
    this.userId = userId;
    this.sessionId = sessionId;
    this.graphMemory = new GraphMemoryService();
  }

  /**
   * Store conversation with automatic relationship creation
   */
  async storeConversation(
    userMessage: string,
    agentResponse: string,
    agent: string,
    agentState: AgentState
  ): Promise<string> {
    try {
      // Create user message node
      const userNodeId = await this.createMemoryNode({
        type: 'conversation',
        content: userMessage,
        agent: 'user',
        metadata: {
          role: 'user',
          messageIndex: agentState.messages.length - 1,
          context: this.extractContextFromState(agentState)
        }
      });

      // Create agent response node
      const agentNodeId = await this.createMemoryNode({
        type: 'conversation',
        content: agentResponse,
        agent,
        metadata: {
          role: 'agent',
          messageIndex: agentState.messages.length,
          taskType: agentState.taskStatus?.type,
          responseTime: agentState.executionContext?.performance?.responseTime
        }
      });

      // Create relationship between user message and agent response
      await this.createRelationship(userNodeId, agentNodeId, 'relates_to', 0.9);

      // Find related conversations and create relationships
      await this.linkToRelatedConversations(agentNodeId, agentResponse);

      return agentNodeId;
    } catch (error) {
      console.error('Error storing conversation:', error);
      throw error;
    }
  }

  /**
   * Store task result with learning
   */
  async storeTaskResult(
    task: TaskStatus,
    result: any,
    agent: string,
    insights?: string[]
  ): Promise<string> {
    try {
      const content = JSON.stringify({
        taskId: task.id,
        type: task.type,
        status: task.status,
        result,
        insights,
        duration: Date.now() - task.createdAt.getTime(),
        agent
      });

      const nodeId = await this.createMemoryNode({
        type: 'task_result',
        content,
        agent,
        metadata: {
          taskType: task.type,
          taskStatus: task.status,
          priority: task.priority,
          delegatedTo: task.delegatedTo,
          duration: Date.now() - task.createdAt.getTime()
        }
      });

      // Link to similar tasks
      await this.linkToSimilarTasks(nodeId, task);

      return nodeId;
    } catch (error) {
      console.error('Error storing task result:', error);
      throw error;
    }
  }

  /**
   * Store business insight or trend
   */
  async storeInsight(
    insight: string,
    category: 'business' | 'technical' | 'market' | 'financial',
    agent: string,
    confidence: number = 0.8,
    relatedTopics: string[] = []
  ): Promise<string> {
    try {
      const nodeId = await this.createMemoryNode({
        type: 'insight',
        content: insight,
        agent,
        metadata: {
          category,
          confidence,
          relatedTopics,
          verified: false
        }
      });

      // Link to related topics and existing insights
      await this.linkInsightToTopics(nodeId, relatedTopics);

      return nodeId;
    } catch (error) {
      console.error('Error storing insight:', error);
      throw error;
    }
  }

  /**
   * Store learned pattern
   */
  async storeLearnedPattern(
    pattern: string,
    context: string,
    agent: string,
    successRate: number,
    frequency: number = 1
  ): Promise<string> {
    try {
      // Check if pattern already exists
      const existingPattern = await this.findExistingPattern(pattern);

      if (existingPattern) {
        // Update existing pattern
        await this.updatePattern(existingPattern.id, {
          frequency: existingPattern.metadata.frequency + frequency,
          successRate: (existingPattern.metadata.successRate + successRate) / 2,
          lastUsed: new Date()
        });
        return existingPattern.id;
      }

      const nodeId = await this.createMemoryNode({
        type: 'insight',
        content: pattern,
        agent,
        metadata: {
          patternType: 'learned',
          context,
          successRate,
          frequency,
          lastUsed: new Date()
        }
      });

      return nodeId;
    } catch (error) {
      console.error('Error storing learned pattern:', error);
      throw error;
    }
  }

  /**
   * Search memory with advanced options
   */
  async searchMemory(options: MemorySearchOptions): Promise<MemoryNode[]> {
    try {
      // Use Firebase service for memory search
      const searchResults = await this.graphMemory.searchNodes({
        query: options.query,
        userId: this.userId,
        sessionId: options.sessionId,
        agent: options.agent,
        type: options.type,
        timeframe: options.timeframe,
        maxResults: options.maxResults || 50,
        similarityThreshold: options.similarityThreshold || 0.7,
        includeRelated: options.includeRelated || false
      });

      // Convert to MemoryNode format
      const memoryNodes: MemoryNode[] = searchResults.map(node => ({
        id: node.id,
        type: node.type,
        content: node.content,
        agent: node.metadata?.agent,
        userId: node.metadata?.userId || this.userId,
        sessionId: node.metadata?.sessionId || this.sessionId,
        timestamp: node.timestamp,
        embedding: node.embedding,
        metadata: node.metadata || {},
        relationships: node.relationships || []
      }));

      return memoryNodes;
    } catch (error) {
      console.error('Error searching memory:', error);
      throw error;
    }
  }

  /**
   * Get memory analytics
   */
  async getAnalytics(): Promise<MemoryAnalytics> {
    try {
      // Use Firebase service for analytics
      const analytics = await this.graphMemory.getAnalytics(this.userId);

      return analytics;
    } catch (error) {
      console.error('Error getting analytics:', error);
      throw error;
    }
  }

  /**
   * Private helper methods
   */
  private async createMemoryNode(nodeData: Omit<MemoryNode, 'id' | 'userId' | 'sessionId' | 'timestamp' | 'relationships'>): Promise<string> {
    try {
      const embedding = await this.getEmbedding(nodeData.content);

      const { data, error } = await this.client
        .from('nodes')
        .insert({
          type: nodeData.type,
          content: nodeData.content,
          embedding,
          metadata: {
            ...nodeData.metadata,
            agent: nodeData.agent,
            userId: this.userId,
            sessionId: this.sessionId
          }
        })
        .select()
        .single();

      if (error) throw error;
      return data.id;
    } catch (error) {
      console.error('Error creating memory node:', error);
      throw error;
    }
  }

  private async createRelationship(
    sourceId: string,
    targetId: string,
    type: Relationship['type'],
    strength: number = 0.5
  ): Promise<void> {
    try {
      await this.client
        .from('edges')
        .insert({
          source_id: sourceId,
          target_id: targetId,
          relation: type,
          metadata: { strength }
        });
    } catch (error) {
      console.error('Error creating relationship:', error);
    }
  }

  private async getEmbedding(text: string): Promise<number[]> {
    const cacheKey = text.toLowerCase().trim();

    if (this.embeddingCache.has(cacheKey)) {
      return this.embeddingCache.get(cacheKey)!;
    }

    try {
      // In production, this would call an actual embedding service
      // For now, we'll use a placeholder embedding
      const embedding = await this.graphMemory['getEmbeddings']().then((e: any) => e.embed(text));

      // Cache the embedding
      this.embeddingCache.set(cacheKey, embedding);

      return embedding;
    } catch (error) {
      console.error('Error getting embedding:', error);
      // Return a dummy embedding as fallback
      return new Array(1536).fill(0).map(() => Math.random());
    }
  }

  private extractContextFromState(agentState: AgentState): Record<string, any> {
    return {
      currentAgent: agentState.currentAgent,
      taskType: agentState.taskStatus?.type,
      taskStatus: agentState.taskStatus?.status,
      hasVirtualFileSystem: !!agentState.virtualFileSystem,
      messageCount: agentState.messages.length
    };
  }

  private async linkToRelatedConversations(nodeId: string, content: string): Promise<void> {
    try {
      // Find related conversations using semantic search
      const relatedNodes = await this.searchMemory({
        query: content,
        type: 'conversation',
        maxResults: 3,
        similarityThreshold: 0.6
      });

      for (const relatedNode of relatedNodes) {
        await this.createRelationship(nodeId, relatedNode.id, 'relates_to', 0.6);
      }
    } catch (error) {
      console.error('Error linking to related conversations:', error);
    }
  }

  private async linkToSimilarTasks(nodeId: string, task: TaskStatus): Promise<void> {
    try {
      const similarTasks = await this.searchMemory({
        type: 'task_result',
        maxResults: 5
      });

      for (const similarTask of similarTasks) {
        if (similarTask.metadata?.taskType === task.type) {
          await this.createRelationship(nodeId, similarTask.id, 'relates_to', 0.7);
        }
      }
    } catch (error) {
      console.error('Error linking to similar tasks:', error);
    }
  }

  private async linkInsightToTopics(nodeId: string, topics: string[]): Promise<void> {
    try {
      for (const topic of topics) {
        const relatedNodes = await this.searchMemory({
          query: topic,
          maxResults: 2,
          similarityThreshold: 0.5
        });

        for (const relatedNode of relatedNodes) {
          await this.createRelationship(nodeId, relatedNode.id, 'references', 0.5);
        }
      }
    } catch (error) {
      console.error('Error linking insight to topics:', error);
    }
  }

  private async findExistingPattern(pattern: string): Promise<MemoryNode | null> {
    try {
      const results = await this.searchMemory({
        query: pattern,
        type: 'insight',
        maxResults: 1,
        similarityThreshold: 0.9
      });

      return results[0] || null;
    } catch (error) {
      console.error('Error finding existing pattern:', error);
      return null;
    }
  }

  private async updatePattern(nodeId: string, updates: Partial<any>): Promise<void> {
    try {
      await this.client
        .from('nodes')
        .update({
          metadata: updates
        })
        .eq('id', nodeId);
    } catch (error) {
      console.error('Error updating pattern:', error);
    }
  }

  /**
   * Clean up old memory nodes based on retention policy
   */
  async cleanup(olderThanDays: number = 90): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

      const { data, error } = await this.client
        .from('nodes')
        .delete()
        .lt('created_at', cutoffDate.toISOString())
        .eq('user_id', this.userId);

      if (error) throw error;

      // Clear embedding cache for old entries
      this.embeddingCache.clear();

      return data?.length || 0;
    } catch (error) {
      console.error('Error cleaning up memory:', error);
      throw error;
    }
  }
}

export default GraphMemoryIntegration;