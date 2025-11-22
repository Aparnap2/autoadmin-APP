import React from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Dimensions,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';

interface QuickAction {
  id: string;
  label: string;
  agent: 'ceo' | 'strategy' | 'devops';
  message: string;
  icon?: string;
}

interface QuickActionsProps {
  actions: QuickAction[];
  onActionPress: (action: QuickAction) => void;
  isDisabled?: boolean;
  style?: any;
  maxColumns?: number;
}

const { width: screenWidth } = Dimensions.get('window');

export function QuickActions({
  actions,
  onActionPress,
  isDisabled = false,
  style,
  maxColumns = 2,
}: QuickActionsProps) {
  const colorScheme = useColorScheme();

  const agentColors = {
    ceo: '#66FCF1',
    strategy: '#E91E63',
    devops: '#45A29E',
  };

  const getActionStyle = (agent: 'ceo' | 'strategy' | 'devops') => ({
    backgroundColor: '#1F2833',
    borderColor: agentColors[agent],
  });

  const getIconColor = (agent: 'ceo' | 'strategy' | 'devops') => {
    return agentColors[agent];
  };

  const getTextStyle = (agent: 'ceo' | 'strategy' | 'devops') => ({
    color: agentColors[agent],
  });

  return (
    <ThemedView style={[styles.container, style]}>
      <ThemedText style={styles.title}>Quick Actions</ThemedText>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {actions.map((action) => (
          <TouchableOpacity
            key={action.id}
            style={[
              styles.actionCard,
              getActionStyle(action.agent),
              isDisabled && styles.disabledCard,
            ]}
            onPress={() => !isDisabled && onActionPress(action)}
            disabled={isDisabled}
            activeOpacity={0.8}
          >
            {/* Action Icon */}
            <View style={[
              styles.iconContainer,
              { backgroundColor: agentColors[action.agent] + '20' }
            ]}>
              <IconSymbol
                name={(action.icon || 'star.fill') as any}
                size={20}
                color={getIconColor(action.agent)}
              />
            </View>

            {/* Action Content */}
            <View style={styles.actionContent}>
              <ThemedText
                style={[
                  styles.actionLabel,
                  getTextStyle(action.agent),
                  isDisabled && styles.disabledText,
                ]}
                numberOfLines={2}
              >
                {action.label}
              </ThemedText>

              {/* Agent Badge */}
              <View style={[
                styles.agentBadge,
                { backgroundColor: agentColors[action.agent] }
              ]}>
                <ThemedText style={styles.agentBadgeText}>
                  {action.agent.toUpperCase()}
                </ThemedText>
              </View>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 16,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  scrollContent: {
    flexDirection: 'row',
    gap: 12,
    paddingRight: 20,
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    minWidth: 160,
    maxWidth: 200,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  disabledCard: {
    opacity: 0.5,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  actionContent: {
    flex: 1,
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  actionLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 6,
    flex: 1,
    lineHeight: 18,
  },
  disabledText: {
    opacity: 0.6,
  },
  agentBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    alignSelf: 'flex-start',
  },
  agentBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#fff',
    letterSpacing: 0.5,
  },
});

export default QuickActions;