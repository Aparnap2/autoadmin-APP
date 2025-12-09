/**
 * Alert Center Component
 * Comprehensive alert management system with real-time monitoring,
  * intelligent detection, and escalation workflows
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Modal,
  TextInput,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { AlertData } from '@/services/business-intelligence/api';
import { getBusinessIntelligenceService } from '@/services/business-intelligence/api';

interface AlertCenterProps {
  data?: AlertData;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function AlertCenter({
  data: initialData,
  autoRefresh = false,
  refreshInterval = 60000, // 1 minute for alerts
}: AlertCenterProps) {
  const [alertData, setAlertData] = useState<AlertData | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'active' | 'history' | 'rules' | 'escalation'>('active');
  const [selectedAlert, setSelectedAlert] = useState<any>(null);
  const [createRuleModalVisible, setCreateRuleModalVisible] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    kpi_id: '',
    operator: 'greater_than' as const,
    threshold: 0,
    actions: [] as any[],
  });
  const [acknowledging, setAcknowledging] = useState(false);
  const [creatingRule, setCreatingRule] = useState(false);

  const biService = getBusinessIntelligenceService();

  useEffect(() => {
    if (!initialData) {
      loadAlertData();
    }
  }, [initialData]);

  useEffect(() => {
    setAlertData(initialData || null);
  }, [initialData]);

  useEffect(() => {
    if (autoRefresh) {
      const refreshTimer = setInterval(loadAlertData, refreshInterval);
      return () => clearInterval(refreshTimer);
    }
  }, [autoRefresh, refreshInterval]);

  useEffect(() => {
    // Subscribe to alert updates
    biService.addListener('alert_update', (data) => {
      setAlertData(data);
    });
  }, [biService]);

  const loadAlertData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await biService.getAlerts();

      if (response.success && response.data) {
        setAlertData(response.data);
      } else {
        throw new Error(response.error || 'Failed to load alert data');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      setAcknowledging(true);

      const response = await biService.acknowledgeAlert(alertId);

      if (response.success) {
        Alert.alert('Success', 'Alert acknowledged');
        await loadAlertData();
      } else {
        throw new Error(response.error || 'Failed to acknowledge alert');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to acknowledge alert');
    } finally {
      setAcknowledging(false);
    }
  };

  const createAlertRule = async () => {
    if (!newRule.name || !newRule.kpi_id || !newRule.threshold) {
      Alert.alert('Validation Error', 'Please fill in all required fields');
      return;
    }

    try {
      setCreatingRule(true);

      const response = await biService.createAlertRule(newRule);

      if (response.success) {
        Alert.alert('Success', 'Alert rule created');
        setCreateRuleModalVisible(false);
        resetNewRule();
        await loadAlertData();
      } else {
        throw new Error(response.error || 'Failed to create alert rule');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to create alert rule');
    } finally {
      setCreatingRule(false);
    }
  };

  const deleteAlertRule = async (ruleId: string) => {
    try {
      const response = await biService.deleteAlertRule(ruleId);

      if (response.success) {
        Alert.alert('Success', 'Alert rule deleted');
        await loadAlertData();
      } else {
        throw new Error(response.error || 'Failed to delete alert rule');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to delete alert rule');
    }
  };

  const resetNewRule = () => {
    setNewRule({
      name: '',
      description: '',
      kpi_id: '',
      operator: 'greater_than',
      threshold: 0,
      actions: [],
    });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#F44336';
      case 'error': return '#FF5722';
      case 'warning': return '#FF9800';
      case 'info': return '#2196F3';
      default: return '#C5C6C7';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved': return '#4CAF50';
      case 'acknowledged': return '#FF9800';
      case 'escalated': return '#9C27B0';
      default: return '#C5C6C7';
    }
  };

  const renderActiveAlerts = () => {
    const activeAlerts = alertData?.active_alerts || [];

    return (
      <View style={styles.alertsList}>
        {activeAlerts.length === 0 ? (
          <View style={styles.emptyState}>
            <ThemedText style={styles.emptyText}>No active alerts</ThemedText>
            <ThemedText style={styles.emptySubtext}>
              All systems are operating normally
            </ThemedText>
          </View>
        ) : (
          activeAlerts.map((alert) => (
            <View key={alert.id} style={[
              styles.alertCard,
              { borderLeftColor: getSeverityColor(alert.severity) }
            ]}>
              <View style={styles.alertHeader}>
                <View style={styles.alertInfo}>
                  <ThemedText style={styles.alertTitle}>{alert.title}</ThemedText>
                  <View style={styles.alertMeta}>
                    <View style={[
                      styles.severityBadge,
                      { backgroundColor: getSeverityColor(alert.severity) }
                    ]}>
                      <ThemedText style={styles.severityText}>
                        {alert.severity.toUpperCase()}
                      </ThemedText>
                    </View>
                    <ThemedText style={styles.alertSource}>{alert.source}</ThemedText>
                    <ThemedText style={styles.alertTime}>
                      {new Date(alert.timestamp).toLocaleString()}
                    </ThemedText>
                  </View>
                </View>
                <View style={styles.alertActions}>
                  {!alert.acknowledged && (
                    <TouchableOpacity
                      style={[styles.actionButton, styles.acknowledgeButton]}
                      onPress={() => acknowledgeAlert(alert.id)}
                      disabled={acknowledging}
                    >
                      <ThemedText style={styles.actionButtonText}>Acknowledge</ThemedText>
                    </TouchableOpacity>
                  )}
                </View>
              </View>

              <ThemedText style={styles.alertDescription}>{alert.description}</ThemedText>

              {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                <View style={styles.alertMetadata}>
                  <ThemedText style={styles.metadataTitle}>Details:</ThemedText>
                  {Object.entries(alert.metadata).map(([key, value]) => (
                    <View key={key} style={styles.metadataItem}>
                      <ThemedText style={styles.metadataKey}>{key}:</ThemedText>
                      <ThemedText style={styles.metadataValue}>
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </ThemedText>
                    </View>
                  ))}
                </View>
              )}
            </View>
          ))
        )}
      </View>
    );
  };

  const renderAlertHistory = () => {
    const alertHistory = alertData?.alert_history || [];

    return (
      <View style={styles.alertsList}>
        {alertHistory.length === 0 ? (
          <View style={styles.emptyState}>
            <ThemedText style={styles.emptyText}>No alert history</ThemedText>
          </View>
        ) : (
          alertHistory.map((alert) => (
            <View key={alert.id} style={[
              styles.alertCard,
              styles.historyCard,
              { borderLeftColor: getSeverityColor(alert.severity) }
            ]}>
              <View style={styles.alertHeader}>
                <View style={styles.alertInfo}>
                  <ThemedText style={styles.alertTitle}>{alert.title}</ThemedText>
                  <View style={styles.alertMeta}>
                    <View style={[
                      styles.statusBadge,
                      { backgroundColor: getStatusColor(alert.status) }
                    ]}>
                      <ThemedText style={styles.statusText}>
                        {alert.status.toUpperCase()}
                      </ThemedText>
                    </View>
                    <View style={[
                      styles.severityBadge,
                      { backgroundColor: getSeverityColor(alert.severity) }
                    ]}>
                      <ThemedText style={styles.severityText}>
                        {alert.severity.toUpperCase()}
                      </ThemedText>
                    </View>
                  </View>
                </View>
                <View style={styles.historyTimes}>
                  <ThemedText style={styles.historyTime}>
                    Created: {new Date(alert.created_at).toLocaleDateString()}
                  </ThemedText>
                  {alert.resolved_at && (
                    <ThemedText style={styles.historyTime}>
                      Resolved: {new Date(alert.resolved_at).toLocaleDateString()}
                    </ThemedText>
                  )}
                  {alert.resolution_time && (
                    <ThemedText style={styles.resolutionTime}>
                      Resolution: {alert.resolution_time}min
                    </ThemedText>
                  )}
                </View>
              </View>
            </View>
          ))
        )}
      </View>
    );
  };

  const renderAlertRules = () => {
    const alertRules = alertData?.alert_rules || [];

    return (
      <View style={styles.rulesSection}>
        <View style={styles.rulesHeader}>
          <ThemedText style={styles.sectionTitle}>Alert Rules</ThemedText>
          <TouchableOpacity
            style={styles.createRuleButton}
            onPress={() => setCreateRuleModalVisible(true)}
          >
            <ThemedText style={styles.createRuleButtonText}>+ Create Rule</ThemedText>
          </TouchableOpacity>
        </View>

        {alertRules.length === 0 ? (
          <View style={styles.emptyState}>
            <ThemedText style={styles.emptyText}>No alert rules configured</ThemedText>
            <ThemedText style={styles.emptySubtext}>
              Create rules to automatically monitor your KPIs
            </ThemedText>
          </View>
        ) : (
          alertRules.map((rule) => (
            <View key={rule.id} style={[
              styles.ruleCard,
              { opacity: rule.is_active ? 1 : 0.5 }
            ]}>
              <View style={styles.ruleHeader}>
                <View style={styles.ruleInfo}>
                  <ThemedText style={styles.ruleName}>{rule.name}</ThemedText>
                  <ThemedText style={styles.ruleDescription}>{rule.description}</ThemedText>
                </View>
                <TouchableOpacity
                  style={styles.deleteRuleButton}
                  onPress={() => {
                    Alert.alert(
                      'Delete Rule',
                      `Are you sure you want to delete "${rule.name}"?`,
                      [
                        { text: 'Cancel', style: 'cancel' },
                        {
                          text: 'Delete',
                          style: 'destructive',
                          onPress: () => deleteAlertRule(rule.id)
                        }
                      ]
                    );
                  }}
                >
                  <ThemedText style={styles.deleteRuleText}>Delete</ThemedText>
                </TouchableOpacity>
              </View>

              <View style={styles.ruleCondition}>
                <ThemedText style={styles.ruleConditionText}>
                  When {rule.condition.kpi_id} is {rule.condition.operator.replace('_', ' ')} {rule.condition.threshold}
                  {rule.condition.duration_minutes ? ` for ${rule.condition.duration_minutes} minutes` : ''}
                </ThemedText>
              </View>

              <View style={styles.ruleActions}>
                <ThemedText style={styles.ruleActionsTitle}>Actions:</ThemedText>
                {rule.actions.map((action, index) => (
                  <ThemedText key={index} style={styles.ruleActionText}>
                    • {action.type}: {action.message}
                  </ThemedText>
                ))}
              </View>

              {rule.last_triggered && (
                <ThemedText style={styles.lastTriggered}>
                  Last triggered: {new Date(rule.last_triggered).toLocaleString()}
                </ThemedText>
              )}
            </View>
          ))
        )}
      </View>
    );
  };

  const renderEscalationPolicies = () => {
    const escalationPolicies = alertData?.escalation_policies || [];

    return (
      <View style={styles.policiesSection}>
        <ThemedText style={styles.sectionTitle}>Escalation Policies</ThemedText>

        {escalationPolicies.length === 0 ? (
          <View style={styles.emptyState}>
            <ThemedText style={styles.emptyText}>No escalation policies configured</ThemedText>
          </View>
        ) : (
          escalationPolicies.map((policy) => (
            <View key={policy.id} style={[
              styles.policyCard,
              { opacity: policy.is_active ? 1 : 0.5 }
            ]}>
              <View style={styles.policyHeader}>
                <ThemedText style={styles.policyName}>{policy.name}</ThemedText>
                <ThemedText style={styles.policyStatus}>
                  {policy.is_active ? 'Active' : 'Inactive'}
                </ThemedText>
              </View>

              <View style={styles.escalationLevels}>
                {policy.levels.map((level, index) => (
                  <View key={index} style={styles.escalationLevel}>
                    <ThemedText style={styles.levelTitle}>
                      Level {level.level} - {level.delay_minutes}min
                    </ThemedText>
                    <View style={styles.levelDetails}>
                      <ThemedText style={styles.levelTargets}>
                        Targets: {level.targets.join(', ')}
                      </ThemedText>
                      <ThemedText style={styles.levelActions}>
                        Actions: {level.actions.join(', ')}
                      </ThemedText>
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ))
        )}
      </View>
    );
  };

  if (loading && !alertData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#66FCF1" />
          <ThemedText style={styles.loadingText}>Loading alert center...</ThemedText>
        </View>
      </ThemedView>
    );
  }

  if (error && !alertData) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.errorContainer}>
          <ThemedText style={styles.errorText}>Error loading alert center</ThemedText>
          <ThemedText style={styles.errorSubtext}>{error}</ThemedText>
          <TouchableOpacity style={styles.retryButton} onPress={() => loadAlertData()}>
            <ThemedText style={styles.retryButtonText}>Retry</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        {[
          { key: 'active', label: 'Active', count: alertData?.active_alerts?.length || 0 },
          { key: 'history', label: 'History' },
          { key: 'rules', label: 'Rules' },
          { key: 'escalation', label: 'Escalation' },
        ].map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              activeTab === tab.key && styles.activeTab
            ]}
            onPress={() => setActiveTab(tab.key as any)}
          >
            <ThemedText style={[
              styles.tabText,
              activeTab === tab.key && styles.activeTabText
            ]}>
              {tab.label}
            </ThemedText>
            {tab.count && tab.count > 0 && (
              <View style={styles.tabBadge}>
                <ThemedText style={styles.tabBadgeText}>{tab.count}</ThemedText>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {activeTab === 'active' && renderActiveAlerts()}
        {activeTab === 'history' && renderAlertHistory()}
        {activeTab === 'rules' && renderAlertRules()}
        {activeTab === 'escalation' && renderEscalationPolicies()}
      </ScrollView>

      {/* Create Rule Modal */}
      <Modal
        visible={createRuleModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setCreateRuleModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ThemedText style={styles.modalTitle}>Create Alert Rule</ThemedText>

            <View style={styles.formGroup}>
              <ThemedText style={styles.formLabel}>Rule Name *</ThemedText>
              <TextInput
                style={styles.formInput}
                value={newRule.name}
                onChangeText={(value) => setNewRule(prev => ({ ...prev, name: value }))}
                placeholder="Enter rule name"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.formLabel}>Description</ThemedText>
              <TextInput
                style={[styles.formInput, styles.textArea]}
                value={newRule.description}
                onChangeText={(value) => setNewRule(prev => ({ ...prev, description: value }))}
                placeholder="Describe when this alert should trigger"
                placeholderTextColor="#666"
                multiline
                numberOfLines={3}
              />
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.formLabel}>KPI ID *</ThemedText>
              <TextInput
                style={styles.formInput}
                value={newRule.kpi_id}
                onChangeText={(value) => setNewRule(prev => ({ ...prev, kpi_id: value }))}
                placeholder="Enter KPI identifier"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.formGroup}>
              <ThemedText style={styles.formLabel}>Condition</ThemedText>
              <View style={styles.conditionRow}>
                <TextInput
                  style={[styles.formInput, styles.thresholdInput]}
                  value={newRule.threshold.toString()}
                  onChangeText={(value) => setNewRule(prev => ({ ...prev, threshold: Number(value) || 0 }))}
                  placeholder="Threshold"
                  placeholderTextColor="#666"
                  keyboardType="numeric"
                />
              </View>
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => {
                  setCreateRuleModalVisible(false);
                  resetNewRule();
                }}
              >
                <ThemedText style={styles.modalCancelText}>Cancel</ThemedText>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalCreateButton, creating && styles.disabledButton]}
                onPress={createAlertRule}
                disabled={creating}
              >
                <ThemedText style={styles.modalCreateText}>
                  {creating ? 'Creating...' : 'Create Rule'}
                </ThemedText>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0C10',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 15,
    color: '#C5C6C7',
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: '#F44336',
    fontSize: 16,
    marginBottom: 8,
  },
  errorSubtext: {
    color: '#C5C6C7',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#45A29E',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#1F2833',
    paddingHorizontal: 10,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
  },
  activeTab: {
    borderBottomColor: '#66FCF1',
    backgroundColor: '#0B0C10',
  },
  tabText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#C5C6C7',
  },
  activeTabText: {
    color: '#66FCF1',
    fontWeight: '600',
  },
  tabBadge: {
    backgroundColor: '#F44336',
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 5,
  },
  tabBadgeText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '700',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  alertsList: {
    flex: 1,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    color: '#C5C6C7',
    fontSize: 16,
    marginBottom: 8,
  },
  emptySubtext: {
    color: '#C5C6C7',
    fontSize: 14,
    opacity: 0.7,
    textAlign: 'center',
  },
  alertCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    borderLeftWidth: 4,
    padding: 20,
    marginBottom: 15,
  },
  historyCard: {
    opacity: 0.8,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  alertInfo: {
    flex: 1,
  },
  alertTitle: {
    color: '#C5C6C7',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  alertMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  severityText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statusText: {
    color: '#0B0C10',
    fontSize: 10,
    fontWeight: '600',
  },
  alertSource: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  alertTime: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.6,
  },
  alertActions: {
    gap: 8,
  },
  actionButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  acknowledgeButton: {
    backgroundColor: '#4CAF50',
  },
  actionButtonText: {
    color: '#0B0C10',
    fontSize: 12,
    fontWeight: '600',
  },
  alertDescription: {
    color: '#C5C6C7',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  alertMetadata: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    padding: 12,
  },
  metadataTitle: {
    color: '#66FCF1',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
  },
  metadataItem: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  metadataKey: {
    color: '#C5C6C7',
    fontSize: 12,
    fontWeight: '600',
    marginRight: 8,
  },
  metadataValue: {
    color: '#C5C6C7',
    fontSize: 12,
    flex: 1,
  },
  historyTimes: {
    alignItems: 'flex-end',
    gap: 4,
  },
  historyTime: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.7,
  },
  resolutionTime: {
    color: '#4CAF50',
    fontSize: 11,
    fontWeight: '600',
  },
  rulesSection: {
    flex: 1,
  },
  rulesHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
  },
  createRuleButton: {
    backgroundColor: '#66FCF1',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 6,
  },
  createRuleButtonText: {
    color: '#0B0C10',
    fontWeight: '600',
    fontSize: 14,
  },
  ruleCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 15,
  },
  ruleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  ruleInfo: {
    flex: 1,
  },
  ruleName: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  ruleDescription: {
    color: '#C5C6C7',
    fontSize: 13,
    opacity: 0.8,
  },
  deleteRuleButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#F44336',
    borderRadius: 6,
  },
  deleteRuleText: {
    color: '#0B0C10',
    fontSize: 12,
    fontWeight: '600',
  },
  ruleCondition: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  ruleConditionText: {
    color: '#C5C6C7',
    fontSize: 14,
  },
  ruleActions: {
    marginBottom: 8,
  },
  ruleActionsTitle: {
    color: '#66FCF1',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
  },
  ruleActionText: {
    color: '#C5C6C7',
    fontSize: 12,
    marginLeft: 8,
  },
  lastTriggered: {
    color: '#C5C6C7',
    fontSize: 11,
    opacity: 0.6,
  },
  policiesSection: {
    flex: 1,
  },
  policyCard: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#45A29E',
    padding: 20,
    marginBottom: 15,
  },
  policyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  policyName: {
    color: '#66FCF1',
    fontSize: 16,
    fontWeight: '600',
  },
  policyStatus: {
    color: '#C5C6C7',
    fontSize: 12,
    opacity: 0.7,
  },
  escalationLevels: {
    gap: 12,
  },
  escalationLevel: {
    backgroundColor: '#0B0C10',
    borderRadius: 8,
    padding: 12,
  },
  levelTitle: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 6,
  },
  levelDetails: {
    gap: 4,
  },
  levelTargets: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  levelActions: {
    color: '#C5C6C7',
    fontSize: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1F2833',
    borderRadius: 12,
    padding: 25,
    width: '100%',
    maxWidth: 500,
    borderWidth: 1,
    borderColor: '#45A29E',
  },
  modalTitle: {
    color: '#66FCF1',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 20,
    textAlign: 'center',
  },
  formGroup: {
    marginBottom: 20,
  },
  formLabel: {
    color: '#66FCF1',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  formInput: {
    backgroundColor: '#0B0C10',
    borderWidth: 1,
    borderColor: '#45A29E',
    borderRadius: 8,
    color: '#C5C6C7',
    fontSize: 16,
    padding: 15,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  conditionRow: {
    flexDirection: 'row',
    gap: 10,
  },
  thresholdInput: {
    flex: 1,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 10,
  },
  modalCancelButton: {
    flex: 1,
    backgroundColor: '#45A29E',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalCancelText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
  modalCreateButton: {
    flex: 1,
    backgroundColor: '#66FCF1',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.5,
  },
  modalCreateText: {
    color: '#0B0C10',
    fontSize: 16,
    fontWeight: '600',
  },
});