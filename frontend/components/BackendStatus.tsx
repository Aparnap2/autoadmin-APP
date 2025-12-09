/**
 * Backend Status Component
 * Shows backend connection status and handles offline mode gracefully
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useThemeColor } from '@/hooks/use-theme-color';

interface BackendStatusProps {
  status: 'online' | 'offline' | 'error';
  isOnline: boolean;
  onRetry?: () => void;
  message?: string;
}

export const BackendStatus: React.FC<BackendStatusProps> = ({
  status,
  isOnline,
  onRetry,
  message
}) => {
  const borderColor = useThemeColor({}, 'border');
  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');

  const getStatusConfig = () => {
    switch (status) {
      case 'online':
        return {
          icon: 'wifi' as const,
          color: '#4CAF50',
          title: 'Backend Connected',
          message: message || 'All features are available'
        };
      case 'offline':
        return {
          icon: 'remove-outline' as const,
          color: '#FF9800',
          title: 'Backend Offline',
          message: message || 'Working in offline mode. Limited features available.'
        };
      case 'error':
        return {
          icon: 'alert-circle' as const,
          color: '#F44336',
          title: 'Connection Error',
          message: message || 'Unable to connect to backend. Some features may be unavailable.'
        };
      default:
        return {
          icon: 'help-circle' as const,
          color: '#9E9E9E',
          title: 'Status Unknown',
          message: message || 'Checking backend connection...'
        };
    }
  };

  const config = getStatusConfig();

  return (
    <View style={[
      styles.container,
      {
        borderColor: config.color + '30',
        backgroundColor: backgroundColor
      }
    ]}>
      <View style={styles.statusRow}>
        <Ionicons
          name={config.icon}
          size={20}
          color={config.color}
        />
        <View style={styles.textContainer}>
          <Text style={[
            styles.title,
            { color: textColor }
          ]}>
            {config.title}
          </Text>
          <Text style={[
            styles.message,
            { color: textColor + '80' }
          ]}>
            {config.message}
          </Text>
        </View>
        {(status === 'offline' || status === 'error') && onRetry && (
          <TouchableOpacity
            style={[styles.retryButton, { backgroundColor: config.color }]}
            onPress={onRetry}
          >
            <Ionicons name="refresh" size={16} color="white" />
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 16,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.02)',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 2,
  },
  message: {
    fontSize: 12,
    lineHeight: 16,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  retryText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '500',
  },
});

export default BackendStatus;