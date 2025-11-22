import React from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BaseMessage } from '@langchain/core/messages';

interface ConversationPreviewProps {
  conversations: BaseMessage[];
  isLoading?: boolean;
}

interface ConversationItem {
  id: string;
  type: 'human' | 'ai' | 'system';
  content: string;
  agent?: string;
  timestamp: Date;
  isPartial?: boolean;
}

export function ConversationPreview({ conversations, isLoading }: ConversationPreviewProps) {
  const formatConversations = (messages: BaseMessage[]): ConversationItem[] => {
    return messages.map((message, index) => ({
      id: `${message.getType()}-${index}`,
      type: message.getType() as 'human' | 'ai' | 'system',
      content: message.content as string,
      agent: (message as any).agentType || getAgentFromContent(message.content as string),
      timestamp: new Date(), // LangChain messages might not have timestamp
      isPartial: (message as any).isPartial || false,
    }));
  };

  const getAgentFromContent = (content: string): string | undefined => {
    // Simple heuristic to identify agent type from content
    const lowerContent = content.toLowerCase();
    if (lowerContent.includes('market') || lowerContent.includes('financial') || lowerContent.includes('strategy')) {
      return 'strategy';
    }
    if (lowerContent.includes('code') || lowerContent.includes('technical') || lowerContent.includes('performance')) {
      return 'devops';
    }
    if (lowerContent.includes('coordination') || lowerContent.includes('orchestration')) {
      return 'ceo';
    }
    return undefined;
  };

  const getAgentInfo = (agentType?: string) => {
    const agentMap = {
      ceo: { icon: '👔', name: 'CEO Agent', color: '#3b82f6' },
      strategy: { icon: '📊', name: 'Strategy Agent', color: '#8b5cf6' },
      devops: { icon: '⚙️', name: 'DevOps Agent', color: '#f59e0b' },
    };
    return agentMap[agentType as keyof typeof agentMap] || { icon: '🤖', name: 'Agent', color: '#6b7280' };
  };

  const formatTimeAgo = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  const truncateContent = (content: string, maxLength: number = 80): string => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  const formattedConversations = formatConversations(conversations);

  if (isLoading) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ThemedText style={styles.loadingText}>Loading conversations...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (formattedConversations.length === 0) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.emptyContainer}>
          <ThemedText style={styles.emptyIcon}>💬</ThemedText>
          <ThemedText style={styles.emptyTitle}>No conversations yet</ThemedText>
          <ThemedText style={styles.emptyText}>
            Start interacting with your AI agents to see conversation history
          </ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {formattedConversations.map((conversation) => {
          const agentInfo = getAgentInfo(conversation.agent);
          const isUserMessage = conversation.type === 'human';

          return (
            <TouchableOpacity
              key={conversation.id}
              style={[styles.conversationItem, isUserMessage && styles.userMessage]}
              activeOpacity={0.7}
            >
              {/* Message Header */}
              <View style={styles.messageHeader}>
                <View style={styles.messageInfo}>
                  <View style={styles.avatarContainer}>
                    <ThemedText style={styles.avatar}>
                      {isUserMessage ? '👤' : agentInfo.icon}
                    </ThemedText>
                  </View>
                  <View style={styles.messageMeta}>
                    <ThemedText style={styles.senderName}>
                      {isUserMessage ? 'You' : agentInfo.name}
                    </ThemedText>
                    <ThemedText style={styles.timestamp}>
                      {formatTimeAgo(conversation.timestamp)}
                    </ThemedText>
                  </View>
                </View>

                {conversation.isPartial && (
                  <View style={styles.partialIndicator}>
                    <View style={styles.typingDot} />
                    <View style={[styles.typingDot, { animationDelay: '0.2s' }]} />
                    <View style={[styles.typingDot, { animationDelay: '0.4s' }]} />
                  </View>
                )}
              </View>

              {/* Message Content */}
              <View style={styles.messageContent}>
                <ThemedText
                  style={[
                    styles.messageText,
                    isUserMessage && styles.userMessageText
                  ]}
                >
                  {truncateContent(conversation.content)}
                </ThemedText>
              </View>

              {/* Message Footer */}
              {!isUserMessage && conversation.agent && (
                <View style={styles.messageFooter}>
                  <View style={[styles.agentBadge, { backgroundColor: `${agentInfo.color}20` }]}>
                    <ThemedText style={[styles.agentBadgeText, { color: agentInfo.color }]}>
                      {conversation.agent.toUpperCase()}
                    </ThemedText>
                  </View>
                </View>
              )}
            </TouchableOpacity>
          );
        })}

        {/* View More Link */}
        {formattedConversations.length >= 5 && (
          <TouchableOpacity style={styles.viewMoreButton} activeOpacity={0.7}>
            <ThemedText style={styles.viewMoreText}>View All Conversations</ThemedText>
            <ThemedText style={styles.viewMoreArrow}>→</ThemedText>
          </TouchableOpacity>
        )}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    minHeight: 200,
    maxHeight: 400,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 12,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  loadingText: {
    opacity: 0.6,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
    opacity: 0.5,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyText: {
    fontSize: 14,
    opacity: 0.6,
    textAlign: 'center',
    lineHeight: 20,
  },
  conversationItem: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  userMessage: {
    backgroundColor: '#eff6ff',
    borderLeftWidth: 3,
    borderLeftColor: '#3b82f6',
  },
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  messageInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatarContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  avatar: {
    fontSize: 16,
  },
  messageMeta: {
    flex: 1,
  },
  senderName: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 2,
  },
  timestamp: {
    fontSize: 11,
    opacity: 0.6,
  },
  partialIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  typingDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#9ca3af',
    marginHorizontal: 2,
  },
  messageContent: {
    marginBottom: 8,
  },
  messageText: {
    fontSize: 14,
    lineHeight: 20,
  },
  userMessageText: {
    color: '#1e40af',
  },
  messageFooter: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  agentBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  agentBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  viewMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: '#f1f5f9',
    borderRadius: 8,
    marginTop: 8,
  },
  viewMoreText: {
    fontSize: 14,
    fontWeight: '500',
    marginRight: 8,
  },
  viewMoreArrow: {
    fontSize: 16,
    fontWeight: '600',
  },
});