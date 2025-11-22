import React, { forwardRef } from 'react';
import {
  FlatList,
  StyleSheet,
  View,
  ListRenderItem,
} from 'react-native';
import { MessageBubble, Message } from './MessageBubble';
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
  const renderMessage: ListRenderItem<Message> = ({ item, index }) => {
    return (
      <MessageBubble
        message={item}
        isStreaming={item.isStreaming}
        onPress={() => onMessagePress?.(item)}
        onLongPress={() => onMessageLongPress?.(item)}
        style={styles.messageBubble}
      />
    );
  };

  const renderFooter = () => {
    if (isTyping) {
      return <TypingIndicator style={styles.typingIndicator} />;
    }
    return null;
  };

  const getItemLayout = (data: any, index: number) => ({
    length: 80, // Approximate height, will be adjusted dynamically
    offset: 80 * index,
    index,
  });

  const keyExtractor = (item: Message) => item.id;

  return (
    <FlatList
      ref={ref}
      data={messages}
      renderItem={renderMessage}
      keyExtractor={keyExtractor}
      style={[styles.container, style]}
      contentContainerStyle={styles.contentContainer}
      ListFooterComponent={renderFooter}
      ListEmptyComponent={
        <View style={styles.emptyContainer}>
          <View style={styles.emptyContent} />
        </View>
      }
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
  },
  emptyContent: {
    height: 100, // Minimum height when empty
  },
});

MessageList.displayName = 'MessageList';