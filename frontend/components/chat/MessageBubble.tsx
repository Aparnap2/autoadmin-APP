import React, { useState, useMemo, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Share,
  Dimensions,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  agent?: 'ceo' | 'strategy' | 'devops';
  timestamp: Date;
  isStreaming?: boolean;
  metadata?: any;
}

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  onPress?: () => void;
  onLongPress?: () => void;
  style?: any;
  showTimestamp?: boolean;
  showAgent?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = React.memo(function MessageBubble({
  message,
  isStreaming = false,
  onPress,
  onLongPress,
  style,
  showTimestamp,
  showAgent,
}: MessageBubbleProps) {
  const { colorScheme } = useColorScheme();
  const { width: screenWidth } = Dimensions.get('window');

  const isUser = message.role === 'user';

  const styles = useMemo(() => StyleSheet.create({
    messageContainer: {
      marginVertical: 4,
      marginHorizontal: 16,
      maxWidth: screenWidth * 0.8,
      padding: 12,
      borderRadius: 16,
      backgroundColor: isUser ? '#007AFF' : (colorScheme === 'dark' ? '#2C2C2E' : '#F2F2F7'),
    },
    userContainer: {
      alignSelf: 'flex-end',
    },
    assistantContainer: {
      alignSelf: 'flex-start',
    },
    messageText: {
      fontSize: 16,
      lineHeight: 22,
      color: isUser ? '#FFFFFF' : (colorScheme === 'dark' ? '#FFFFFF' : '#000000'),
    },
    timestamp: {
      fontSize: 12,
      marginTop: 4,
      color: isUser ? '#FFFFFF80' : (colorScheme === 'dark' ? '#FFFFFF60' : '#00000060'),
    },
    userTimestamp: {
      alignSelf: 'flex-end',
      textAlign: 'right',
    },
    assistantTimestamp: {
      alignSelf: 'flex-start',
      textAlign: 'left',
    },
    agentName: {
      fontSize: 12,
      marginTop: 4,
      color: isUser ? '#FFFFFF80' : (colorScheme === 'dark' ? '#FFFFFF60' : '#00000060'),
      fontStyle: 'italic',
    },
  }), [colorScheme, screenWidth, isUser]);

  const formatTimestamp = useCallback((timestamp: Date) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  }, []);

  const handlePress = useCallback(() => {
    if (onPress) {
      onPress();
    }
  }, [onPress]);

  const handleLongPress = useCallback(() => {
    Alert.alert(
      'Message Options',
      'What would you like to do with this message?',
      [
        { text: 'Copy', onPress: () => Share.share(message.content) },
        { text: 'Reply', onPress: () => handlePress() },
        { text: 'Delete', onPress: () => console.log('Delete message') },
      ]
    );
  }, []);

  return (
    <TouchableOpacity onPress={handlePress} onLongPress={handleLongPress} style={[styles.userContainer, style]}>
      <ThemedView style={[styles.messageContainer, isUser ? styles.userContainer : styles.assistantContainer]}>
        <ThemedText style={[styles.timestamp, isUser ? styles.userTimestamp : styles.assistantTimestamp]}>
          {showTimestamp && formatTimestamp(message.timestamp)}
        </ThemedText>

        <ThemedText style={[styles.messageText]}>
          {message.content}
        </ThemedText>

        {showTimestamp && (
          <ThemedText style={[styles.timestamp, isUser ? styles.userTimestamp : styles.assistantTimestamp]}>
            {formatTimestamp(message.timestamp)}
          </ThemedText>
        )}

        {showAgent && message.agent && (
          <ThemedText style={[styles.agentName]}>
            <IconSymbol
              name={message.agent}
              size={12}
            />
          </ThemedText>
        )}
      </ThemedView>
    </TouchableOpacity>
  );
});

MessageBubble.displayName = 'MessageBubble';

export default MessageBubble;
export { Message };