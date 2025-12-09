import React from 'react';
import {
  View,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { ThemedText } from '@/components/themed-text.stylex';
import { ThemedView } from '@/components/themed-view.stylex';

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

const quickActionsStyles = stylex.create({
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
    backgroundColor: '#1F2833', // Secondary background
    borderRadius: 12,
  },
  disabledText: {
    opacity: 0.6,
    textAlign: 'center',
  },
  actionCard: {
    width: 200,
    backgroundColor: '#1F2833', // Secondary background
    borderRadius: 12,
    padding: 16,
    marginRight: 12,
    ...tokens.shadow.md,
    borderLeftWidth: 4,
    borderLeftColor: tokens.colors.tint,
  },
  advancedCard: {
    borderLeftColor: tokens.colors.icon,
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
    backgroundColor: 'rgba(102, 252, 241, 0.2)', // Tint color with opacity
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
    color: tokens.colors.text,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontSize: 10,
  },
  actionContent: {
    flex: 1,
    marginBottom: 12,
  },
  actionTitle: {
    color: tokens.colors.tint,
    fontWeight: '600',
    marginBottom: 4,
  },
  actionDescription: {
    color: tokens.colors.text,
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

export function QuickActions({ onAction, isDisabled = false }: QuickActionsProps) {
  const quickActions: QuickAction[] = [
    {
      id: 'chat_with_ceo',
      title: 'CEO Status Update',
      description: 'Get current system status from CEO agent',
      icon: '👔',
      color: tokens.colors.tint,
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
      color: tokens.colors.tint,
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
      <ThemedView {...stylex.props(quickActionsStyles.container)}>
        <View {...stylex.props(quickActionsStyles.disabledContainer)}>
          <ThemedText {...stylex.props(quickActionsStyles.disabledText)}>
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
      contentContainerStyle={{ ...stylex.props(quickActionsStyles.scrollContainer).style }}
    >
      {quickActions.map((action) => (
        <TouchableOpacity
          key={action.id}
          {...stylex.props(
            quickActionsStyles.actionCard,
            { borderLeftColor: action.color as any }
          )}
          onPress={() => handleActionPress(action)}
          activeOpacity={0.7}
          disabled={isDisabled}
        >
          <View {...stylex.props(quickActionsStyles.actionHeader)}>
            <View
              {...stylex.props(
                quickActionsStyles.iconContainer,
                { backgroundColor: `${action.color}20` as any }
              )}
            >
              <ThemedText {...stylex.props(quickActionsStyles.actionIcon)}>
                {action.icon}
              </ThemedText>
            </View>
            <View {...stylex.props(quickActionsStyles.agentBadge)}>
              <ThemedText {...stylex.props(quickActionsStyles.agentBadgeText)}>
                {action.agentType ? action.agentType.toUpperCase() : 'AUTO'}
              </ThemedText>
            </View>
          </View>

          <View {...stylex.props(quickActionsStyles.actionContent)}>
            <ThemedText
              {...stylex.props(quickActionsStyles.actionTitle)}
              numberOfLines={1}
            >
              {action.title}
            </ThemedText>
            <ThemedText
              {...stylex.props(quickActionsStyles.actionDescription)}
              numberOfLines={2}
            >
              {action.description}
            </ThemedText>
          </View>

          <View {...stylex.props(quickActionsStyles.actionFooter)}>
            <View
              {...stylex.props(
                quickActionsStyles.statusDot,
                { backgroundColor: action.color as any }
              )}
            />
            <ThemedText {...stylex.props(quickActionsStyles.statusText)}>
              Available
            </ThemedText>
          </View>
        </TouchableOpacity>
      ))}

      {/* Advanced Actions Card */}
      <TouchableOpacity
        {...stylex.props(
          quickActionsStyles.actionCard,
          quickActionsStyles.advancedCard
        )}
        onPress={() => onAction('advanced_options')}
        activeOpacity={0.7}
      >
        <View {...stylex.props(quickActionsStyles.actionHeader)}>
          <View
            {...stylex.props(
              quickActionsStyles.iconContainer,
              { backgroundColor: 'rgba(31, 41, 55, 0.8)' } // Secondary background with opacity
            )}
          >
            <ThemedText {...stylex.props(quickActionsStyles.actionIcon)}>⚡</ThemedText>
          </View>
        </View>

        <View {...stylex.props(quickActionsStyles.actionContent)}>
          <ThemedText {...stylex.props(quickActionsStyles.actionTitle)}>
            Advanced
          </ThemedText>
          <ThemedText {...stylex.props(quickActionsStyles.actionDescription)}>
            System management and configuration
          </ThemedText>
        </View>

        <View {...stylex.props(quickActionsStyles.actionFooter)}>
          <ThemedText {...stylex.props(quickActionsStyles.advancedText)}>
            Settings →
          </ThemedText>
        </View>
      </TouchableOpacity>
    </ScrollView>
  );
}