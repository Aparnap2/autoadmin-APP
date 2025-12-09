import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Text,
} from 'react-native';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';
import { useAutoAdminAgents } from '@/hooks/useAutoAdminAgents';
import { AgentSelector } from './AgentSelector';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { QuickActions } from './QuickActions';
import { StreamingIndicator } from './StreamingIndicator';
// Import MessageBubble and Message from index barrel export
import { MessageBubble, Message } from './index';

interface AgentChatInterfaceProps {
  userId: string;
  initialAgent?: 'ceo' | 'strategy' | 'devops';
  style?: any;
  onMessageSent?: (message: string, agentType: string) => void;
  onAgentSwitch?: (agentType: 'ceo' | 'strategy' | 'devops') => void;
}

interface QuickAction {
  id: string;
  label: string;
  agent: 'ceo' | 'strategy' | 'devops';
  message: string;
  icon?: string;
}

export function AgentChatInterface({
  userId,
  initialAgent = 'ceo',
  style,
  onMessageSent,
  onAgentSwitch,
}: AgentChatInterfaceProps) {
  const colorScheme = useColorScheme() ?? 'dark';
  const [selectedAgent, setSelectedAgent] = useState<'ceo' | 'strategy' | 'devops'>(initialAgent);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const flatListRef = useRef<any>(null);

  const {
    isInitialized,
    isLoading,
    error,
    state,
    conversationHistory,
    sendMessage,
    sendMessageStream,
  } = useAutoAdminAgents({
    userId,
    autoInitialize: true,
    enableStreaming: true,
    enableRealtimeSync: true,
    onMessageProcessed: (response) => {
      // Handle processed messages
      setStreamingContent('');
      setIsStreaming(false);
      setIsTyping(false);
    },
    onError: (err) => {
      console.error('Agent Chat Error:', err);
      Alert.alert('Error', 'Failed to send message');
      setIsStreaming(false);
      setIsTyping(false);
    },
  });

  const quickActions: QuickAction[] = useMemo(() => [
    {
      id: 'status_update',
      label: 'Status Update',
      agent: 'ceo',
      message: 'Please provide a comprehensive status update on current operations',
      icon: 'chart.bar',
    },
    {
      id: 'market_analysis',
      label: 'Market Analysis',
      agent: 'strategy',
      message: 'Can you analyze current market trends and provide strategic insights?',
      icon: 'trending.up',
    },
    {
      id: 'system_health',
      label: 'System Health',
      agent: 'devops',
      message: 'Please check system health and identify any optimization opportunities',
      icon: 'gear',
    },
    {
      id: 'performance_metrics',
      label: 'Performance Metrics',
      agent: 'ceo',
      message: 'Show me current performance metrics and KPIs',
      icon: 'speedometer',
    },
  ], []);

  // Convert conversation history to message format
  useEffect(() => {
    const convertedMessages: Message[] = conversationHistory.map((msg, index) => ({
      id: `msg-${index}`,
      content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
      role: msg.getType() === 'human' ? 'user' : 'assistant',
      agent: selectedAgent,
      timestamp: new Date(),
      isStreaming: false,
    }));
    setMessages(convertedMessages);
  }, [conversationHistory, selectedAgent]);

  const handleSendMessage = useCallback(async () => {
    if (!inputMessage.trim() || isStreaming || !isInitialized) return;

    const messageContent = inputMessage.trim();
    setInputMessage('');
    setIsStreaming(true);
    setIsTyping(true);

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: messageContent,
      role: 'user',
      agent: selectedAgent,
      timestamp: new Date(),
      isStreaming: false,
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      // Use streaming for better UX
      const stream = sendMessageStream(messageContent);

      let assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        content: '',
        role: 'assistant',
        agent: selectedAgent,
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages(prev => [...prev, assistantMessage]);

      for await (const chunk of stream) {
        assistantMessage.content += chunk.content || '';
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = assistantMessage;
          return updated;
        });
        setStreamingContent(assistantMessage.content);
      }

      // Finalize the message
      assistantMessage.isStreaming = false;
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = assistantMessage;
        return updated;
      });

      onMessageSent?.(messageContent, selectedAgent);

    } catch (error) {
      console.error('Error sending message:', error);
      Alert.alert('Error', 'Failed to send message. Please try again.');

      // Remove the assistant message if it failed
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsStreaming(false);
      setIsTyping(false);
      setStreamingContent('');
    }
  }, [inputMessage, isStreaming, isInitialized, selectedAgent, sendMessageStream, onMessageSent]);

  const handleQuickAction = useCallback((action: QuickAction) => {
    setSelectedAgent(action.agent);
    onAgentSwitch?.(action.agent);
    setInputMessage(action.message);
  }, [onAgentSwitch]);

  const handleAgentSwitch = useCallback((agentType: 'ceo' | 'strategy' | 'devops') => {
    setSelectedAgent(agentType);
    onAgentSwitch?.(agentType);
  }, [onAgentSwitch]);

  const handleClearConversation = useCallback(() => {
    Alert.alert(
      'Clear Conversation',
      'Are you sure you want to clear all messages in this conversation?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => setMessages([]),
        },
      ]
    );
  }, []);

  const scrollToBottom = useCallback(() => {
    if (flatListRef.current) {
      flatListRef.current.scrollToEnd({ animated: true });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  if (isLoading) {
    return (
      <View style={[styles.container, { backgroundColor: Colors[colorScheme].background }, style]}>
        <View style={styles.centerContainer}>
          <Text style={[styles.titleText, { color: Colors[colorScheme].text }]}>Initializing Agent Chat...</Text>
          <Text style={[styles.loadingText, { color: Colors[colorScheme].text }]}>
            Setting up your AI business partners
          </Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.container, { backgroundColor: Colors[colorScheme].background }, style]}>
        <View style={styles.centerContainer}>
          <Text style={[styles.titleText, { color: Colors[colorScheme].text }]}>Connection Error</Text>
          <Text style={[styles.errorText, { color: Colors[colorScheme].text }]}>
            Failed to connect to agent system. Please check your connection.
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: Colors[colorScheme].background }, style]} testID="agent-chat-interface">
      {/* Agent Selector */}
      <AgentSelector
        testID="agent-selector"
        selectedAgent={selectedAgent}
        onAgentChange={handleAgentSwitch}
        isDisabled={isStreaming}
        agentStatus={state?.agentStates}
      />

      {/* Message List */}
      <MessageList
        testID="message-list"
        ref={flatListRef}
        messages={messages}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        isTyping={isTyping}
        style={styles.messageList}
      />

      {/* Streaming Indicator */}
      {isStreaming && (
        <StreamingIndicator
          agent={selectedAgent}
          content={streamingContent}
          style={styles.streamingIndicator}
        />
      )}

      {/* Quick Actions */}
      {messages.length === 0 && (
        <QuickActions
          actions={quickActions}
          onActionPress={handleQuickAction}
          style={styles.quickActions}
        />
      )}

      {/* Chat Input */}
      <KeyboardAvoidingView
        testID="chat-input-container"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
        style={styles.inputContainer}
      >
        <ChatInput
          testID="chat-input"
          value={inputMessage}
          onChangeText={setInputMessage}
          onSend={handleSendMessage}
          onClearConversation={handleClearConversation}
          isDisabled={isStreaming || !isInitialized}
          placeholder={`Message ${selectedAgent.toUpperCase()} Agent...`}
        />
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'column',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  titleText: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    textAlign: 'center',
  },
  loadingText: {
    fontSize: 16,
    marginTop: 10,
    textAlign: 'center',
    opacity: 0.7,
  },
  errorText: {
    marginTop: 10,
    textAlign: 'center',
    opacity: 0.7,
  },
  messageList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  streamingIndicator: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  quickActions: {
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  inputContainer: {
    backgroundColor: 'transparent',
  },
});

export default AgentChatInterface;