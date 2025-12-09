import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  Modal,
  StyleSheet,
  Animated,
  Dimensions,
  Keyboard,
  Platform,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Colors } from '@/constants/theme';
import * as Haptics from 'expo-haptics';
import { getMonoFontFamily } from '@/utils/fonts';

interface Command {
  id: string;
  title: string;
  description: string;
  icon: string;
  keywords?: string[];
  action: () => void;
  shortcut?: string;
  category: 'agent' | 'navigation' | 'system' | 'task';
}

interface CommandPaletteProps {
  isVisible: boolean;
  onClose: () => void;
  commands: Command[];
}

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export function CommandPalette({ isVisible, onClose, commands }: CommandPaletteProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredCommands, setFilteredCommands] = useState<Command[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [animatedValue] = useState(new Animated.Value(0));
  const inputRef = useRef<TextInput>(null);

  // Filter commands based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredCommands(commands);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = commands.filter(
        (cmd) =>
          cmd.title.toLowerCase().includes(query) ||
          cmd.description.toLowerCase().includes(query) ||
          cmd.keywords?.some((keyword) => keyword.toLowerCase().includes(query))
      );
      setFilteredCommands(filtered);
    }
    setSelectedIndex(0);
  }, [searchQuery, commands]);

  // Handle modal animation
  useEffect(() => {
    if (isVisible) {
      Animated.timing(animatedValue, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
      
      // Focus input when modal opens
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    } else {
      Animated.timing(animatedValue, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }).start();
    }
  }, [isVisible, animatedValue]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: any) => {
      if (!isVisible) return;

      // Handle arrow keys for navigation
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(
          (prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length
        );
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          filteredCommands[selectedIndex].action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    },
    [isVisible, filteredCommands, selectedIndex, onClose]
  );

  // Add keyboard event listeners
  useEffect(() => {
    if (Platform.OS === 'web' && isVisible) {
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [handleKeyDown, isVisible]);

  const handleCommandSelect = (command: Command, index: number) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    command.action();
    onClose();
  };

  const getCategoryColor = (category: Command['category']) => {
    switch (category) {
      case 'agent':
        return '#3b82f6';
      case 'navigation':
        return '#10b981';
      case 'system':
        return '#f59e0b';
      case 'task':
        return '#8b5cf6';
      default:
        return '#66FCF1';
    }
  };

  const backdropOpacity = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 0.5],
  });

  const modalTranslateY = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [SCREEN_HEIGHT, 0],
  });

  if (!isVisible) return null;

  return (
    <Modal
      transparent
      visible={isVisible}
      animationType="none"
      onRequestClose={onClose}
    >
      {/* Backdrop */}
      <Animated.View
        style={[
          styles.backdrop,
          {
            opacity: backdropOpacity,
          },
        ]}
        onTouchStart={onClose}
      />
      
      {/* Modal Content */}
      <Animated.View
        style={[
          styles.modalContainer,
          {
            transform: [{ translateY: modalTranslateY }],
          },
        ]}
      >
        <ThemedView style={styles.commandPalette}>
          {/* Search Input */}
          <View style={styles.searchContainer}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              ref={inputRef}
              style={styles.searchInput}
              placeholder="Type a command or search..."
              placeholderTextColor="#666"
              value={searchQuery}
              onChangeText={setSearchQuery}
              autoCorrect={false}
              autoCapitalize="none"
              clearButtonMode="while-editing"
            />
          </View>

          {/* Commands List */}
          <FlatList
            data={filteredCommands}
            keyExtractor={(item) => item.id}
            style={styles.commandsList}
            keyboardShouldPersistTaps="handled"
            renderItem={({ item, index }) => (
              <TouchableOpacity
                style={[
                  styles.commandItem,
                  index === selectedIndex && styles.selectedCommandItem,
                  { borderLeftColor: getCategoryColor(item.category) }
                ]}
                onPress={() => handleCommandSelect(item, index)}
              >
                <View style={styles.commandIcon}>
                  <Text style={styles.commandIconText}>{item.icon}</Text>
                </View>
                
                <View style={styles.commandContent}>
                  <ThemedText style={styles.commandTitle}>
                    {item.title}
                  </ThemedText>
                  <ThemedText style={styles.commandDescription}>
                    {item.description}
                  </ThemedText>
                </View>

                <View style={styles.commandMeta}>
                  {item.shortcut && (
                    <View style={styles.shortcutBadge}>
                      <Text style={styles.shortcutText}>{item.shortcut}</Text>
                    </View>
                  )}
                  <View style={[
                    styles.categoryDot,
                    { backgroundColor: getCategoryColor(item.category) }
                  ]} />
                </View>
              </TouchableOpacity>
            )}
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyIcon}>🔍</Text>
                <ThemedText style={styles.emptyText}>
                  No commands found for "{searchQuery}"
                </ThemedText>
              </View>
            }
          />

          {/* Footer */}
          <View style={styles.footer}>
            <ThemedText style={styles.footerText}>
              ↑↓ Navigate • Enter Select • Esc Close
            </ThemedText>
          </View>
        </ThemedView>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: '#000',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'center',
    paddingTop: 100,
  },
  commandPalette: {
    width: '90%',
    maxWidth: 600,
    height: '70%',
    maxHeight: 500,
    backgroundColor: Colors.dark.background,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.dark.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 20,
    overflow: 'hidden',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.dark.border,
  },
  searchIcon: {
    fontSize: 20,
    marginRight: 12,
    opacity: 0.7,
  },
  searchInput: {
    flex: 1,
    fontSize: 18,
    color: Colors.dark.text,
    fontFamily: getMonoFontFamily(),
  },
  commandsList: {
    flex: 1,
  },
  commandItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
  },
  selectedCommandItem: {
    backgroundColor: '#1F2833',
  },
  commandIcon: {
    width: 40,
    height: 40,
    borderRadius: 8,
    backgroundColor: '#1F2833',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  commandIconText: {
    fontSize: 18,
  },
  commandContent: {
    flex: 1,
  },
  commandTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.dark.tint,
    marginBottom: 2,
  },
  commandDescription: {
    fontSize: 14,
    opacity: 0.7,
    lineHeight: 18,
  },
  commandMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  shortcutBadge: {
    backgroundColor: '#1F2833',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  shortcutText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.dark.tint,
    fontFamily: getMonoFontFamily(),
  },
  categoryDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
    opacity: 0.5,
  },
  emptyText: {
    fontSize: 16,
    opacity: 0.7,
    textAlign: 'center',
  },
  footer: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.dark.border,
    backgroundColor: '#0B0C10',
  },
  footerText: {
    fontSize: 12,
    opacity: 0.6,
    textAlign: 'center',
    fontFamily: getMonoFontFamily(),
  },
});
