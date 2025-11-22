import React, { useState } from 'react';
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

export interface Message {
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

const { width: screenWidth } = Dimensions.get('window');

export function MessageBubble({
  message,
  isStreaming = false,
  onPress,
  onLongPress,
  style,
  showTimestamp = true,
  showAgent = true,
}: MessageBubbleProps) {
  const colorScheme = useColorScheme();
  const [showActions, setShowActions] = useState(false);

  const isUser = message.role === 'user';
  const agentColors = {
    ceo: '#66FCF1', // Neon Cyan
    strategy: '#E91E63', // Keep pink but maybe brighter? Or use purple #9D00FF? Let's keep pink for contrast
    devops: '#45A29E', // Muted Cyan/Green
  };

  const agentNames = {
    ceo: 'CEO Agent',
    strategy: 'Strategy Agent',
    devops: 'DevOps Agent',
  };

  const agentIcons = {
    ceo: 'person.crop.circle',
    strategy: 'chart.bar',
    devops: 'gear',
  };

  const bubbleStyle = isUser
    ? [styles.bubble, styles.userBubble, { backgroundColor: '#66FCF1' }]
    : [
      styles.bubble,
      styles.assistantBubble,
      {
        backgroundColor: '#1F2833',
        borderLeftColor: message.agent ? agentColors[message.agent] : '#ccc',
      },
    ];

  const textStyle = isUser
    ? [styles.text, styles.userText, { color: '#0B0C10' }]
    : [styles.text, styles.assistantText, { color: '#C5C6C7' }];

  const containerStyle = isUser
    ? [styles.messageContainer, styles.userContainer]
    : [styles.messageContainer, styles.assistantContainer];

  const handleCopy = async () => {
    try {
      await Share.share({
        message: message.content,
      });
    } catch (error) {
      console.error('Error sharing message:', error);
    }
    setShowActions(false);
  };

  const handleDelete = () => {
    Alert.alert(
      'Delete Message',
      'Are you sure you want to delete this message?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            // Handle message deletion through parent
            onLongPress?.();
          },
        },
      ]
    );
    setShowActions(false);
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <TouchableOpacity
      style={[containerStyle, style]}
      onPress={() => {
        onPress?.();
        setShowActions(!showActions);
      }}
      onLongPress={() => {
        onLongPress?.();
        setShowActions(true);
      }}
      activeOpacity={0.8}
    >
      {/* Agent Indicator for Assistant Messages */}
      {!isUser && message.agent && showAgent && (
        <View style={styles.agentIndicator}>
          <View style={[styles.agentIcon, { backgroundColor: agentColors[message.agent] }]}>
            <IconSymbol
              name={agentIcons[message.agent] as any}
              size={14}
              color="#fff"
            />
          </View>
          <Text style={[styles.agentName, { color: agentColors[message.agent] }]}>
            {agentNames[message.agent]}
          </Text>
        </View>
      )}

      <ThemedView style={bubbleStyle}>
        <Text style={textStyle}>
          {message.content}
          {isStreaming && <Text style={styles.cursor}>|</Text>}
        </Text>

        {/* Message Actions */}
        {showActions && !isStreaming && (
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={handleCopy}
            >
              <IconSymbol
                name={"doc.on.doc" as any}
                size={16}
                color={isUser ? '#fff' : (colorScheme === 'dark' ? '#fff' : '#333')}
              />
            </TouchableOpacity>
            {!isUser && (
              <TouchableOpacity
                style={styles.actionButton}
                onPress={handleDelete}
              >
                <IconSymbol
                  name={"trash" as any}
                  size={16}
                  color={isUser ? '#fff' : (colorScheme === 'dark' ? '#fff' : '#333')}
                />
              </TouchableOpacity>
            )}
          </View>
        )}
      </ThemedView>

      {/* Timestamp */}
      {showTimestamp && (
        <Text style={[
          styles.timestamp,
          isUser ? styles.userTimestamp : styles.assistantTimestamp,
          { color: colorScheme === 'dark' ? '#888' : '#666' }
        ]}>
          {formatTimestamp(message.timestamp)}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  messageContainer: {
    marginVertical: 4,
    marginHorizontal: 16,
    maxWidth: screenWidth * 0.8,
  },
  userContainer: {
    alignSelf: 'flex-end',
  },
  assistantContainer: {
    alignSelf: 'flex-start',
  },
  agentIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    marginLeft: 8,
  },
  agentIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 6,
  },
  agentName: {
    fontSize: 12,
    fontWeight: '600',
  },
  bubble: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 20,
    position: 'relative',
    minHeight: 44,
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  userBubble: {
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    borderBottomLeftRadius: 4,
    borderLeftWidth: 3,
  },
  text: {
    fontSize: 16,
    lineHeight: 22,
    flex: 1,
  },
  userText: {
    color: '#fff',
  },
  assistantText: {
    color: '#333',
  },
  cursor: {
    color: '#66FCF1',
  },
  actionsContainer: {
    position: 'absolute',
    top: -30,
    right: 8,
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: 8,
    padding: 4,
  },
  actionButton: {
    padding: 4,
    marginHorizontal: 2,
  },
  timestamp: {
    fontSize: 11,
    marginTop: 4,
    alignSelf: 'flex-end',
    opacity: 0.7,
  },
  userTimestamp: {
    alignSelf: 'flex-end',
  },
  assistantTimestamp: {
    alignSelf: 'flex-start',
  },
});

export default MessageBubble;