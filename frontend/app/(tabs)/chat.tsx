import React, { useState } from 'react';
import { StyleSheet, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';
// Import AgentChatInterface from chat components
import { AgentChatInterface } from '@/components/chat';

// Mock user ID - in a real app, this would come from authentication
const MOCK_USER_ID = 'demo-user-123';

export default function ChatScreen() {
  const colorScheme = useColorScheme();
  const [selectedAgent, setSelectedAgent] = useState<'ceo' | 'strategy' | 'devops'>('ceo');

  const handleAgentSwitch = (agentType: 'ceo' | 'strategy' | 'devops') => {
    setSelectedAgent(agentType);
  };

  const handleMessageSent = (message: string, agentType: string) => {
    console.log(`Message sent to ${agentType} agent:`, message);
  };

  return (
    <SafeAreaView
      style={[
        styles.container,
        { backgroundColor: Colors[colorScheme ?? 'dark'].background }
      ]}
      edges={['top', 'left', 'right']}
    >
      <StatusBar
        barStyle="light-content"
        backgroundColor={Colors[colorScheme ?? 'dark'].background}
      />

      <AgentChatInterface
        userId={MOCK_USER_ID}
        initialAgent={selectedAgent}
        onAgentSwitch={handleAgentSwitch}
        onMessageSent={handleMessageSent}
        style={styles.chatInterface}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  chatInterface: {
    flex: 1,
  },
});