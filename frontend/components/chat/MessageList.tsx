import React, { forwardRef, useCallback, useMemo } from 'react';
import {
  FlatList,
  StyleSheet,
  View,
  ListRenderItem,
  Text,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
// Import MessageBubble and Message from index barrel export
import { MessageBubble, Message } from './index';
import { TypingIndicator } from './TypingIndicator';

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  isTyping?: boolean;
  style?: any;
  onMessagePress?: (message: Message) => void;
  onMessageLongPress?: (message: Message) => void;
}

export const MessageList = forwardRef<any, MessageListProps>(({
  messages,
  isStreaming = false,
  streamingContent = '',
  isTyping = false,
  style,
  onMessagePress,
  onMessageLongPress,
}, ref) => {
  const renderMessage: ListRenderItem<Message> = useCallback(({ item, index }) => {
    // Defensive check to prevent rendering undefined components
    if (!MessageBubble) {
      console.error('MessageBubble component is not properly imported');
      return null;
    }

    return (
      <MessageBubble
        message={item}
        isStreaming={item.isStreaming}
        onPress={() => onMessagePress?.(item)}
        onLongPress={() => onMessageLongPress?.(item)}
        style={styles.messageBubble}
      />
    );
  }, [onMessagePress, onMessageLongPress]);

  const renderFooter = useCallback(() => {
    if (isTyping) {
      return <TypingIndicator style={styles.typingIndicator} />;
    }
    return null;
  }, [isTyping]);

  const getItemLayout = useCallback((data: any, index: number) => ({
    length: 80, // Approximate height, will be adjusted dynamically
    offset: 80 * index,
    index,
  }), []);

  const keyExtractor = useCallback((item: Message) => item.id, []);

  const memoizedData = useMemo(() => messages, [messages]);

  const EmptyComponent = useMemo(() => (
    <View style={styles.emptyContainer}>
      <View style={styles.emptyContent}>
        <View style={styles.emptyIcon}>
          <Ionicons name="chatbubble-ellipses-outline" size={48} color="#9CA3AF" />
        </View>
        <Text style={styles.emptyTitle}>Welcome to your chat!</Text>
        <Text style={styles.emptySubtitle}>Send a message to start the conversation</Text>
      </View>
    </View>
  ), []);

  return (
    <FlatList
      ref={ref}
      data={memoizedData}
      renderItem={renderMessage}
      keyExtractor={keyExtractor}
      style={[styles.container, style]}
      contentContainerStyle={styles.contentContainer}
      ListFooterComponent={renderFooter}
      ListEmptyComponent={EmptyComponent}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      removeClippedSubviews={false}
      maxToRenderPerBatch={10}
      updateCellsBatchingPeriod={50}
      initialNumToRender={10}
      windowSize={10}
      getItemLayout={getItemLayout}
      maintainVisibleContentPosition={{
        minIndexForVisible: 0,
        autoscrollToTopThreshold: 100,
      }}
    />
  );
});

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  contentContainer: {
    paddingVertical: 8,
    flexGrow: 1,
  },
  messageBubble: {
    marginVertical: 4,
  },
  typingIndicator: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyContent: {
    alignItems: 'center',
  },
  emptyIcon: {
    marginBottom: 16,
    padding: 16,
    backgroundColor: '#F3F4F6',
    borderRadius: 24,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 20,
  },
});

MessageList.displayName = 'MessageList';