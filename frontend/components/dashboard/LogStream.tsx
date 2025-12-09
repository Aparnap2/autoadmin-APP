import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  PanGestureHandler,
  State,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Colors } from '@/constants/theme';
import * as Haptics from 'expo-haptics';

interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warning' | 'error' | 'success' | 'debug';
  source: string;
  message: string;
  agent?: string;
  metadata?: any;
}

interface LogStreamProps {
  isVisible: boolean;
  onClose: () => void;
  logs?: LogEntry[];
  maxHeight?: number;
}

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export function LogStream({ isVisible, onClose, logs = [], maxHeight = SCREEN_HEIGHT * 0.4 }: LogStreamProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>(logs);
  const [selectedLogLevel, setSelectedLogLevel] = useState<string>('all');
  const [animatedHeight] = useState(new Animated.Value(0));
  const [dragPosition] = useState(new Animated.Value(0));
  const flatListRef = useRef<FlatList>(null);

  // Update filtered logs when logs or filter changes
  useEffect(() => {
    if (selectedLogLevel === 'all') {
      setFilteredLogs(logs);
    } else {
      setFilteredLogs(logs.filter(log => log.level === selectedLogLevel));
    }
  }, [logs, selectedLogLevel]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (filteredLogs.length > 0 && flatListRef.current) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [filteredLogs]);

  // Handle panel animation
  useEffect(() => {
    if (isVisible) {
      Animated.timing(animatedHeight, {
        toValue: isExpanded ? maxHeight : maxHeight * 0.6,
        duration: 300,
        useNativeDriver: false,
      }).start();
    } else {
      Animated.timing(animatedHeight, {
        toValue: 0,
        duration: 200,
        useNativeDriver: false,
      }).start();
    }
  }, [isVisible, isExpanded, animatedHeight, maxHeight]);

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return '#ef4444';
      case 'warning':
        return '#f59e0b';
      case 'success':
        return '#10b981';
      case 'info':
        return '#3b82f6';
      case 'debug':
        return '#8b5cf6';
      default:
        return '#66FCF1';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      case 'info':
        return 'ℹ️';
      case 'debug':
        return '🔍';
      default:
        return '📝';
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const handleToggleExpand = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setIsExpanded(!isExpanded);
  };

  const handleClearLogs = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setFilteredLogs([]);
  };

  const renderLogEntry = ({ item, index }: { item: LogEntry; index: number }) => (
    <View style={[
      styles.logEntry,
      index % 2 === 0 && styles.logEntryEven,
    ]}>
      <View style={styles.logHeader}>
        <Text style={[styles.logIcon, { color: getLevelColor(item.level) }]}>
          {getLevelIcon(item.level)}
        </Text>
        <Text style={styles.logTimestamp}>
          {formatTimestamp(item.timestamp)}
        </Text>
        <Text style={[styles.logLevel, { color: getLevelColor(item.level) }]}>
          {item.level.toUpperCase()}
        </Text>
        <Text style={styles.logSource}>
          {item.source}
        </Text>
        {item.agent && (
          <View style={styles.agentBadge}>
            <Text style={styles.agentText}>{item.agent}</Text>
          </View>
        )}
      </View>
      <ThemedText style={styles.logMessage}>
        {item.message}
      </ThemedText>
      {item.metadata && (
        <View style={styles.metadataContainer}>
          <Text style={styles.metadataText}>
            {JSON.stringify(item.metadata, null, 2)}
          </Text>
        </View>
      )}
    </View>
  );

  const logLevels = [
    { key: 'all', label: 'All', count: logs.length },
    { key: 'error', label: 'Errors', count: logs.filter(l => l.level === 'error').length },
    { key: 'warning', label: 'Warnings', count: logs.filter(l => l.level === 'warning').length },
    { key: 'success', label: 'Success', count: logs.filter(l => l.level === 'success').length },
    { key: 'info', label: 'Info', count: logs.filter(l => l.level === 'info').length },
    { key: 'debug', label: 'Debug', count: logs.filter(l => l.level === 'debug').length },
  ];

  if (!isVisible) return null;

  return (
    <Animated.View style={[styles.container, { height: animatedHeight }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.dragHandle}
          onPressIn={() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)}
          onPress={handleToggleExpand}
        >
          <View style={styles.dragHandleBar} />
        </TouchableOpacity>
        
        <View style={styles.headerContent}>
          <View style={styles.titleContainer}>
            <Text style={styles.titleIcon}>📡</Text>
            <ThemedText style={styles.title}>The Matrix</ThemedText>
            <View style={styles.logCount}>
              <Text style={styles.logCountText}>{filteredLogs.length}</Text>
            </View>
          </View>
          
          <View style={styles.headerActions}>
            {/* Log Level Filter */}
            <View style={styles.filterContainer}>
              {logLevels.map((level) => (
                <TouchableOpacity
                  key={level.key}
                  style={[
                    styles.filterButton,
                    selectedLogLevel === level.key && styles.filterButtonActive,
                    { borderColor: getLevelColor(level.key as LogEntry['level']) }
                  ]}
                  onPress={() => {
                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                    setSelectedLogLevel(level.key);
                  }}
                >
                  <Text style={[
                    styles.filterButtonText,
                    selectedLogLevel === level.key && styles.filterButtonTextActive,
                    { color: getLevelColor(level.key as LogEntry['level']) }
                  ]}>
                    {level.label}
                  </Text>
                  {level.count > 0 && (
                    <Text style={styles.filterCount}>{level.count}</Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
            
            {/* Actions */}
            <TouchableOpacity
              style={styles.actionButton}
              onPress={handleClearLogs}
            >
              <Text style={styles.actionButtonText}>Clear</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.closeButton}
              onPress={onClose}
            >
              <Text style={styles.closeButtonText}>✕</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* Logs List */}
      <FlatList
        ref={flatListRef}
        data={filteredLogs}
        keyExtractor={(item) => item.id}
        renderItem={renderLogEntry}
        style={styles.logsList}
        showsVerticalScrollIndicator={true}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>📭</Text>
            <ThemedText style={styles.emptyText}>
              No logs to display
            </ThemedText>
            <ThemedText style={styles.emptySubtext}>
              Agent activity will appear here in real-time
            </ThemedText>
          </View>
        }
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: Colors.dark.background,
    borderTopWidth: 1,
    borderTopColor: Colors.dark.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -5 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 10,
  },
  header: {
    backgroundColor: '#0B0C10',
    borderTopWidth: 1,
    borderTopColor: Colors.dark.border,
  },
  dragHandle: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  dragHandleBar: {
    width: 40,
    height: 4,
    backgroundColor: Colors.dark.border,
    borderRadius: 2,
  },
  headerContent: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  titleIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: Colors.dark.tint,
    flex: 1,
  },
  logCount: {
    backgroundColor: '#1F2833',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  logCountText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.dark.tint,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  filterContainer: {
    flexDirection: 'row',
    flex: 1,
    flexWrap: 'wrap',
    gap: 4,
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
    borderRadius: 6,
    backgroundColor: '#1F2833',
  },
  filterButtonActive: {
    backgroundColor: '#1F2833',
  },
  filterButtonText: {
    fontSize: 11,
    fontWeight: '500',
    marginRight: 4,
  },
  filterButtonTextActive: {
    fontWeight: '600',
  },
  filterCount: {
    fontSize: 10,
    opacity: 0.7,
  },
  actionButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#1F2833',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.dark.border,
  },
  actionButtonText: {
    fontSize: 12,
    fontWeight: '500',
    color: Colors.dark.text,
  },
  closeButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#1F2833',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.dark.border,
  },
  closeButtonText: {
    fontSize: 14,
    color: Colors.dark.text,
  },
  logsList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  logEntry: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1F2833',
  },
  logEntryEven: {
    backgroundColor: '#0B0C10',
  },
  logHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  logIcon: {
    fontSize: 12,
    marginRight: 6,
  },
  logTimestamp: {
    fontSize: 11,
    color: Colors.dark.text,
    opacity: 0.7,
    fontFamily: 'monospace',
    marginRight: 8,
    minWidth: 80,
  },
  logLevel: {
    fontSize: 10,
    fontWeight: '600',
    marginRight: 8,
    minWidth: 50,
  },
  logSource: {
    fontSize: 11,
    color: Colors.dark.text,
    opacity: 0.8,
    marginRight: 8,
    flex: 1,
  },
  agentBadge: {
    backgroundColor: '#1F2833',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  agentText: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.dark.tint,
  },
  logMessage: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 4,
    color: Colors.dark.text,
  },
  metadataContainer: {
    backgroundColor: '#1F2833',
    padding: 8,
    borderRadius: 6,
    marginTop: 4,
  },
  metadataText: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: Colors.dark.text,
    opacity: 0.8,
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
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    opacity: 0.5,
    textAlign: 'center',
  },
});