import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

interface QuickActionsProps {
  onAction: (action: string, params?: any) => void;
  isDisabled?: boolean;
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  agentType?: 'ceo' | 'strategy' | 'devops';
  requiresConfirmation?: boolean;
}

export function QuickActions({ onAction, isDisabled = false }: QuickActionsProps) {
  const quickActions: QuickAction[] = [
    {
      id: 'chat_with_ceo',
      title: 'CEO Status Update',
      description: 'Get current system status from CEO agent',
      icon: '👔',
      color: '#3b82f6',
      agentType: 'ceo',
    },
    {
      id: 'market_analysis',
      title: 'Market Analysis',
      description: 'Analyze market trends and competition',
      icon: '📊',
      color: '#8b5cf6',
      agentType: 'strategy',
    },
    {
      id: 'financial_planning',
      title: 'Financial Planning',
      description: 'Review financial metrics and projections',
      icon: '💰',
      color: '#10b981',
      agentType: 'strategy',
    },
    {
      id: 'code_review',
      title: 'Code Review',
      description: 'Analyze codebase for optimization',
      icon: '⚙️',
      color: '#f59e0b',
      agentType: 'devops',
    },
    {
      id: 'performance_audit',
      title: 'Performance Audit',
      description: 'Check system performance and bottlenecks',
      icon: '🚀',
      color: '#ef4444',
      agentType: 'devops',
    },
    {
      id: 'strategic_planning',
      title: 'Strategic Planning',
      description: 'Develop business growth strategies',
      icon: '🎯',
      color: '#6366f1',
      agentType: 'strategy',
    },
    {
      id: 'system_status',
      title: 'System Health Check',
      description: 'Comprehensive system diagnostics',
      icon: '🏥',
      color: '#14b8a6',
      agentType: 'ceo',
    },
    {
      id: 'open_chat',
      title: 'Open Chat',
      description: 'Full chat interface with all agents',
      icon: '💬',
      color: '#66FCF1',
    },
    {
      id: 'new_task',
      title: 'Create Task',
      description: 'Start a new custom task',
      icon: '➕',
      color: '#6b7280',
    },
  ];

  const handleActionPress = (action: QuickAction) => {
    if (isDisabled) return;

    if (action.requiresConfirmation) {
      // Handle confirmation logic here if needed
    }

    onAction(action.id, { agentType: action.agentType });
  };

  if (isDisabled) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.disabledContainer}>
          <ThemedText style={styles.disabledText}>
            Agent system is initializing...
          </ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.scrollContainer}
    >
      {quickActions.map((action) => (
        <TouchableOpacity
          key={action.id}
          style={[styles.actionCard, { borderLeftColor: action.color }]}
          onPress={() => handleActionPress(action)}
          activeOpacity={0.7}
          disabled={isDisabled}
        >
          <View style={styles.actionHeader}>
            <View style={[styles.iconContainer, { backgroundColor: `${action.color}20` }]}>
              <ThemedText style={styles.actionIcon}>{action.icon}</ThemedText>
            </View>
            <View style={styles.agentBadge}>
              <ThemedText style={styles.agentBadgeText}>
                {action.agentType ? action.agentType.toUpperCase() : 'AUTO'}
              </ThemedText>
            </View>
          </View>

          <View style={styles.actionContent}>
            <ThemedText style={styles.actionTitle} numberOfLines={1}>
              {action.title}
            </ThemedText>
            <ThemedText style={styles.actionDescription} numberOfLines={2}>
              {action.description}
            </ThemedText>
          </View>

          <View style={styles.actionFooter}>
            <View style={[styles.statusDot, { backgroundColor: action.color }]} />
            <ThemedText style={styles.statusText}>Available</ThemedText>
          </View>
        </TouchableOpacity>
      ))}

      {/* Advanced Actions Card */}
      <TouchableOpacity
        style={[styles.actionCard, styles.advancedCard]}
        onPress={() => onAction('advanced_options')}
        activeOpacity={0.7}
      >
        <View style={styles.actionHeader}>
          <View style={[styles.iconContainer, { backgroundColor: '#1f293720' }]}>
            <ThemedText style={styles.actionIcon}>⚡</ThemedText>
          </View>
        </View>

        <View style={styles.actionContent}>
          <ThemedText style={styles.actionTitle}>Advanced</ThemedText>
          <ThemedText style={styles.actionDescription}>
            System management and configuration
          </ThemedText>
        </View>

        <View style={styles.actionFooter}>
          <ThemedText style={styles.advancedText}>Settings →</ThemedText>
        </View>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 160,
  },
  scrollContainer: {
    paddingHorizontal: 4,
    gap: 12,
  },
  disabledContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    backgroundColor: '#1F2833',
    borderRadius: 12,
  },
  disabledText: {
    opacity: 0.6,
    textAlign: 'center',
  },
  actionCard: {
    width: 200,
    backgroundColor: '#1F2833',
    borderRadius: 12,
    padding: 16,
    marginRight: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  advancedCard: {
    borderLeftColor: '#1f2937',
    backgroundColor: '#0B0C10',
  },
  actionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionIcon: {
    fontSize: 20,
  },
  agentBadge: {
    backgroundColor: '#2C3E50',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  agentBadgeText: {
    color: '#C5C6C7',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  actionContent: {
    flex: 1,
    marginBottom: 12,
  },
  actionTitle: {
    color: '#66FCF1',
    fontWeight: '600',
    marginBottom: 4,
  },
  actionDescription: {
    color: '#C5C6C7',
    opacity: 0.7,
    lineHeight: 16,
  },
  actionFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    opacity: 0.6,
  },
  advancedText: {
    fontSize: 12,
    fontWeight: '500',
    opacity: 0.7,
  },
});