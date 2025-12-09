import React from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';

interface AgentSelectorProps {
  selectedAgent: 'ceo' | 'strategy' | 'devops';
  onAgentChange: (agent: 'ceo' | 'strategy' | 'devops') => void;
  isDisabled?: boolean;
  agentStatus?: any; // Agent state from the hook
  style?: any;
}

interface Agent {
  id: 'ceo' | 'strategy' | 'devops';
  name: string;
  description: string;
  icon: string;
  color: string;
  status?: 'online' | 'busy' | 'offline';
}

const agents: Agent[] = [
  {
    id: 'ceo',
    name: 'CEO',
    description: 'Strategic oversight',
    icon: 'person.crop.circle',
    color: '#66FCF1',
  },
  {
    id: 'strategy',
    name: 'Strategy',
    description: 'Marketing & Finance',
    icon: 'chart.bar',
    color: '#E91E63',
  },
  {
    id: 'devops',
    name: 'DevOps',
    description: 'Technical operations',
    icon: 'gear',
    color: '#45A29E',
  },
];

export function AgentSelector({
  selectedAgent,
  onAgentChange,
  isDisabled = false,
  agentStatus,
  style,
}: AgentSelectorProps) {
  const colorScheme = useColorScheme();

  const getAgentStatus = (agentId: 'ceo' | 'strategy' | 'devops') => {
    if (agentStatus?.[agentId]) {
      const state = agentStatus[agentId];
      if (state.status === 'processing' || state.status === 'thinking') {
        return 'busy';
      }
      if (state.status === 'idle' || state.status === 'ready') {
        return 'online';
      }
    }
    return 'online'; // Default to online
  };

  return (
    <ThemedView style={[
      styles.container,
      {
        backgroundColor: '#0B0C10',
        borderBottomColor: '#333',
      },
      style,
    ]}>
      <ThemedText style={styles.title}>Select Agent</ThemedText>
      <View style={styles.agentsContainer}>
        {agents.map((agent) => {
          const isSelected = selectedAgent === agent.id;
          const status = getAgentStatus(agent.id);

          return (
            <TouchableOpacity
              key={agent.id}
              style={[
                styles.agentCard,
                {
                  backgroundColor: isSelected
                    ? agent.color
                    : '#1F2833',
                  borderColor: isSelected
                    ? agent.color
                    : '#45A29E',
                },
                isDisabled && styles.disabledCard,
              ]}
              onPress={() => !isDisabled && onAgentChange(agent.id)}
              disabled={isDisabled}
              activeOpacity={0.8}
            >
              {/* Agent Icon */}
              <View style={[
                styles.iconContainer,
                {
                  backgroundColor: isSelected
                    ? 'rgba(255, 255, 255, 0.2)'
                    : agent.color,
                }
              ]}>
                <IconSymbol
                  name={agent.icon as any}
                  size={24}
                  color={isSelected ? '#fff' : '#fff'}
                />
              </View>

              {/* Status Indicator */}
              <View style={[
                styles.statusIndicator,
                {
                  backgroundColor: status === 'online' ? '#4caf50' :
                    status === 'busy' ? '#ff9800' : '#f44336'
                }
              ]} />

              {/* Agent Info */}
              <View style={styles.agentInfo}>
                <ThemedText style={[
                  styles.agentName,
                  {
                    color: isSelected ? '#0B0C10' : '#C5C6C7',
                  }
                ]}>
                  {agent.name}
                </ThemedText>
                <ThemedText style={[
                  styles.agentDescription,
                  {
                    color: isSelected
                      ? 'rgba(255, 255, 255, 0.8)'
                      : '#9BA1A6',
                  }
                ]}>
                  {agent.description}
                </ThemedText>
              </View>

              {/* Selection Indicator */}
              {isSelected && (
                <View style={styles.selectionIndicator}>
                  <IconSymbol
                    name="checkmark.circle.fill"
                    size={20}
                    color="#fff"
                  />
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Agent Status Legend */}
      <View style={styles.legendContainer}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#4caf50' }]} />
          <ThemedText style={styles.legendText}>Online</ThemedText>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#ff9800' }]} />
          <ThemedText style={styles.legendText}>Busy</ThemedText>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#f44336' }]} />
          <ThemedText style={styles.legendText}>Offline</ThemedText>
        </View>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  agentsContainer: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  agentCard: {
    flex: 1,
    flexDirection: 'column',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 2,
    position: 'relative',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  disabledCard: {
    opacity: 0.5,
    shadowOpacity: 0,
    elevation: 0,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusIndicator: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#fff',
  },
  agentInfo: {
    alignItems: 'center',
    flex: 1,
  },
  agentName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  agentDescription: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 16,
  },
  selectionIndicator: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#fff',
    borderRadius: 10,
  },
  legendContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 12,
    gap: 16,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 12,
    opacity: 0.7,
  },
});

export default AgentSelector;