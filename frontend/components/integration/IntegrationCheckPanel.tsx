/**
 * Integration Check Panel Component
 * Shows auto-checks for Git, Deployments, PR checks, Tests, and CI/CD
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface IntegrationStatus {
  git: boolean;
  deployments: boolean;
  pr_checks: boolean;
  tests: boolean;
  cicd: boolean;
  github: boolean;
}

interface IntegrationCheckPanelProps {
  projectId: string;
  onStatusChange?: (status: IntegrationStatus) => void;
}

const IntegrationCheckPanel: React.FC<IntegrationCheckPanelProps> = ({
  projectId,
  onStatusChange,
}) => {
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load integration status
  useEffect(() => {
    loadIntegrationStatus();
  }, [projectId]);

  const loadIntegrationStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      // Mock data - in real app, this would call the API
      const mockStatus: IntegrationStatus = {
        git: Math.random() > 0.3, // 70% success rate
        deployments: Math.random() > 0.4, // 60% success rate
        pr_checks: Math.random() > 0.2, // 80% success rate
        tests: Math.random() > 0.25, // 75% success rate
        cicd: Math.random() > 0.35, // 65% success rate
        github: Math.random() > 0.15, // 85% success rate
      };

      setIntegrationStatus(mockStatus);
      onStatusChange?.(mockStatus);
    } catch (err) {
      setError('Failed to load integration status');
      console.error('Error loading integration status:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: boolean) => {
    if (status) {
      return <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />;
    }
    return <Ionicons name="close-circle" size={24} color="#F44336" />;
  };

  const getStatusText = (status: boolean) => {
    return status ? 'Active' : 'Inactive';
  };

  const getStatusColor = (status: boolean) => {
    return status ? '#E8F5E9' : '#FFEBEE';
  };

  const getStatusBorderColor = (status: boolean) => {
    return status ? '#4CAF50' : '#F44336';
  };

  const getIntegrationName = (key: keyof IntegrationStatus): string => {
    const names: Record<string, string> = {
      git: 'Git Repository',
      deployments: 'Deployments',
      pr_checks: 'PR Checks',
      tests: 'Tests',
      cicd: 'CI/CD Pipeline',
      github: 'GitHub Integration',
    };
    return names[key] || key;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Checking integrations...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="warning" size={24} color="#F44336" />
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadIntegrationStatus}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!integrationStatus) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>No integration data available</Text>
      </View>
    );
  }

  const integrationKeys = Object.keys(integrationStatus) as Array<keyof IntegrationStatus>;
  const activeIntegrations = integrationKeys.filter(key => integrationStatus[key]).length;
  const totalIntegrations = integrationKeys.length;
  const completionPercentage = Math.round((activeIntegrations / totalIntegrations) * 100);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🔌 Integration Check Panel</Text>
        <View style={styles.progressContainer}>
          <Text style={styles.progressText}>{activeIntegrations}/{totalIntegrations} Connected</Text>
          <Text style={styles.progressPercentage}>{completionPercentage}% Ready</Text>
        </View>
      </View>

      <View style={styles.progressBar}>
        <View 
          style={[
            styles.progressFill, 
            { width: `${completionPercentage}%` }
          ]} 
        />
      </View>

      <View style={styles.integrationList}>
        {integrationKeys.map((key) => (
          <TouchableOpacity
            key={key}
            style={[
              styles.integrationItem,
              { 
                backgroundColor: getStatusColor(integrationStatus[key]),
                borderColor: getStatusBorderColor(integrationStatus[key]),
              }
            ]}
            onPress={() => {
              if (!integrationStatus[key]) {
                Alert.alert(
                  'Integration Required',
                  `Connect to ${getIntegrationName(key)} to enable this feature.`,
                  [
                    { text: 'Cancel', style: 'cancel' },
                    { 
                      text: 'Connect', 
                      onPress: () => {
                        // In a real app, this would navigate to connection screen
                        Alert.alert('Connect', `To connect to ${getIntegrationName(key)}, please configure in settings.`);
                      }
                    }
                  ]
                );
              }
            }}
          >
            <View style={styles.integrationContent}>
              {getStatusIcon(integrationStatus[key])}
              <View style={styles.integrationDetails}>
                <Text style={styles.integrationName}>{getIntegrationName(key)}</Text>
                <Text style={styles.integrationStatus}>
                  Status: {getStatusText(integrationStatus[key])}
                </Text>
              </View>
              <Ionicons 
                name={integrationStatus[key] ? "checkmark" : "arrow-forward"} 
                size={20} 
                color={integrationStatus[key] ? "#4CAF50" : "#666"} 
              />
            </View>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity style={styles.configureButton} onPress={() => Alert.alert('Configure Integrations')}>
        <Text style={styles.configureButtonText}>Configure All Integrations</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    margin: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  progressContainer: {
    alignItems: 'flex-end',
  },
  progressText: {
    fontSize: 12,
    color: '#666',
  },
  progressPercentage: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  progressBar: {
    height: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
    marginBottom: 16,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 4,
  },
  integrationList: {
    marginBottom: 16,
  },
  integrationItem: {
    borderWidth: 1,
    borderRadius: 8,
    marginBottom: 8,
    overflow: 'hidden',
  },
  integrationContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
  },
  integrationDetails: {
    flex: 1,
    marginLeft: 12,
  },
  integrationName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  integrationStatus: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  loadingContainer: {
    padding: 20,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  errorContainer: {
    padding: 20,
    alignItems: 'center',
    backgroundColor: '#FFEBEE',
    borderRadius: 8,
    margin: 16,
  },
  errorText: {
    color: '#D32F2F',
    marginTop: 8,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: '#1976D2',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    marginTop: 12,
  },
  retryButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  emptyContainer: {
    padding: 20,
    alignItems: 'center',
  },
  emptyText: {
    color: '#666',
  },
  configureButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  configureButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default IntegrationCheckPanel;