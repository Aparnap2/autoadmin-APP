import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Alert,
  Share,
  Dimensions,
} from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { ThemedText } from '@/components/themed-text.stylex';
import { ThemedView } from '@/components/themed-view.stylex';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';

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
  style?: stylex.StyleXStyles;
  showTimestamp?: boolean;
  showAgent?: boolean;
}

const { width: screenWidth } = Dimensions.get('window');

const messageStyles = stylex.create({
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
    ...tokens.shadow.sm,
  },
  userBubble: {
    backgroundColor: tokens.colors.tint,
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: '#1F2833', // Secondary background
    borderBottomLeftRadius: 4,
    borderLeftWidth: 3,
    borderLeftColor: tokens.colors.border,
  },
  text: {
    fontSize: 16,
    lineHeight: 22,
    flex: 1,
  },
  userText: {
    color: tokens.colors.background,
  },
  assistantText: {
    color: tokens.colors.text,
  },
  cursor: {
    color: tokens.colors.tint,
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
    opacity: 0.7,
  },
  userTimestamp: {
    alignSelf: 'flex-end',
  },
  assistantTimestamp: {
    alignSelf: 'flex-start',
  },
});

const agentColors = {
  ceo: '#66FCF1', // Neon Cyan
  strategy: '#E91E63', // Pink
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
} as const;

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

  const bubbleStyle = isUser
    ? [messageStyles.bubble, messageStyles.userBubble]
    : [
        messageStyles.bubble,
        messageStyles.assistantBubble,
        {
          borderLeftColor: message.agent
            ? agentColors[message.agent]
            : tokens.colors.border,
        },
      ];

  const textStyle = isUser
    ? [messageStyles.text, messageStyles.userText]
    : [messageStyles.text, messageStyles.assistantText];

  const containerStyle = isUser
    ? [messageStyles.messageContainer, messageStyles.userContainer]
    : [messageStyles.messageContainer, messageStyles.assistantContainer];

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
      {...stylex.props(containerStyle, style)}
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
        <View {...stylex.props(messageStyles.agentIndicator)}>
          <View
            {...stylex.props(messageStyles.agentIcon)}
            style={{
              backgroundColor: agentColors[message.agent],
            }}
          >
            <IconSymbol
              name={agentIcons[message.agent]}
              size={14}
              color="#fff"
            />
          </View>
          <Text
            {...stylex.props(messageStyles.agentName)}
            style={{
              color: agentColors[message.agent],
            }}
          >
            {agentNames[message.agent]}
          </Text>
        </View>
      )}

      <ThemedView {...stylex.props(bubbleStyle)}>
        <Text {...stylex.props(textStyle)}>
          {message.content}
          {isStreaming && <Text {...stylex.props(messageStyles.cursor)}>|</Text>}
        </Text>

        {/* Message Actions */}
        {showActions && !isStreaming && (
          <View {...stylex.props(messageStyles.actionsContainer)}>
            <TouchableOpacity
              {...stylex.props(messageStyles.actionButton)}
              onPress={handleCopy}
            >
              <IconSymbol
                name="doc.on.doc"
                size={16}
                color={
                  isUser
                    ? tokens.colors.background
                    : colorScheme === 'dark'
                    ? '#fff'
                    : '#333'
                }
              />
            </TouchableOpacity>
            {!isUser && (
              <TouchableOpacity
                {...stylex.props(messageStyles.actionButton)}
                onPress={handleDelete}
              >
                <IconSymbol
                  name="trash"
                  size={16}
                  color={
                    isUser
                      ? tokens.colors.background
                      : colorScheme === 'dark'
                      ? '#fff'
                      : '#333'
                  }
                />
              </TouchableOpacity>
            )}
          </View>
        )}
      </ThemedView>

      {/* Timestamp */}
      {showTimestamp && (
        <Text
          {...stylex.props(
            messageStyles.timestamp,
            isUser
              ? messageStyles.userTimestamp
              : messageStyles.assistantTimestamp
          )}
          style={{
            color: colorScheme === 'dark' ? '#888' : '#666',
          }}
        >
          {formatTimestamp(message.timestamp)}
        </Text>
      )}
    </TouchableOpacity>
  );
}

export default MessageBubble;