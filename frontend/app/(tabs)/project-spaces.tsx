/**
 * Project Spaces Component
 * Manages projects, goal trees, and Kanban boards
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
  TextInput,
  Modal,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

// Import new components
import IntegrationCheckPanel from '@/components/integration/IntegrationCheckPanel';
import DailyCycleComponent from '@/components/daily/DailyCycleComponent';
import PortfolioViewComponent from '@/components/portfolio/PortfolioViewComponent';

// Types
interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  priority: string;
  progress_percentage: number;
  team_members: string[];
}

interface GoalNode {
  id: string;
  title: string;
  type: string;
  status: string;
  priority: number;
  progress_percentage: number;
  children: GoalNode[];
}

interface KanbanCard {
  id: string;
  goal_id: string;
  column: string;
  position: number;
}

interface ProjectDashboard {
  project: Project;
  goal_tree: { roots: GoalNode[] };
  kanban_board?: { columns: string[] };
  kanban_cards: KanbanCard[];
}

export default function ProjectSpaces({ navigation }: any) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectDashboard, setProjectDashboard] = useState<ProjectDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [activeTab, setActiveTab] = useState<'projects' | 'portfolio' | 'daily' | 'integrations'>('projects');

  // Load projects
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);

      const response = await fetch('http://localhost:8000/api/projects', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setProjects(result.data);
        }
      }
    } catch (error) {
      console.error('Error loading projects:', error);
      Alert.alert('Error', 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load project dashboard
  const loadProjectDashboard = useCallback(async (projectId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/dashboard`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setProjectDashboard(result.dashboard);
        }
      }
    } catch (error) {
      console.error('Error loading project dashboard:', error);
      Alert.alert('Error', 'Failed to load project dashboard');
    }
  }, []);

  // Create new project
  const createProject = useCallback(async () => {
    if (!newProjectName.trim()) {
      Alert.alert('Error', 'Project name is required');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newProjectName.trim(),
          description: newProjectDescription.trim(),
          priority: 'medium',
          team_members: [],
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          Alert.alert('Success', 'Project created successfully!');
          setShowCreateModal(false);
          setNewProjectName('');
          setNewProjectDescription('');
          await loadProjects();
        }
      }
    } catch (error) {
      console.error('Error creating project:', error);
      Alert.alert('Error', 'Failed to create project');
    }
  }, [newProjectName, newProjectDescription, loadProjects]);

  // Create new goal
  const createGoal = useCallback(async (projectId: string, title: string, type: string = 'task') => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/goals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          type: type,
          title: title,
          priority: 5,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          Alert.alert('Success', 'Goal created successfully!');
          if (selectedProject) {
            await loadProjectDashboard(selectedProject.id);
          }
        }
      }
    } catch (error) {
      console.error('Error creating goal:', error);
      Alert.alert('Error', 'Failed to create goal');
    }
  }, [selectedProject, loadProjectDashboard]);

  // Refresh data
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadProjects();
    if (selectedProject) {
      await loadProjectDashboard(selectedProject.id);
    }
    setRefreshing(false);
  }, [loadProjects, selectedProject, loadProjectDashboard]);

  // Load data on focus
  useFocusEffect(
    useCallback(() => {
      loadProjects();
    }, [loadProjects])
  );

  // Render project card
  const renderProjectCard = (project: Project) => (
    <TouchableOpacity
      key={project.id}
      style={[
        styles.projectCard,
        selectedProject?.id === project.id && styles.selectedProjectCard
      ]}
      onPress={() => {
        setSelectedProject(project);
        loadProjectDashboard(project.id);
      }}
    >
      <View style={styles.projectHeader}>
        <Text style={styles.projectName}>{project.name}</Text>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(project.status) }]}>
          <Text style={styles.statusText}>{project.status.toUpperCase()}</Text>
        </View>
      </View>

      {project.description && (
        <Text style={styles.projectDescription} numberOfLines={2}>
          {project.description}
        </Text>
      )}

      <View style={styles.projectStats}>
        <Text style={styles.progressText}>
          Progress: {project.progress_percentage || 0}%
        </Text>
        <Text style={styles.teamText}>
          Team: {project.team_members.length} members
        </Text>
      </View>
    </TouchableOpacity>
  );

  // Render goal tree
  const renderGoalTree = (goals: GoalNode[], level: number = 0) => (
    goals.map((goal) => (
      <View key={goal.id} style={[styles.goalItem, { marginLeft: level * 20 }]}>
        <View style={styles.goalHeader}>
          <Text style={[styles.goalTitle, { color: getGoalTypeColor(goal.type) }]}>
            {getGoalTypeIcon(goal.type)} {goal.title}
          </Text>
          <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(goal.priority) }]}>
            <Text style={styles.priorityText}>{goal.priority}</Text>
          </View>
        </View>

        <View style={styles.goalProgress}>
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                { width: `${goal.progress_percentage * 100}%` }
              ]}
            />
          </View>
          <Text style={styles.progressPercent}>
            {Math.round(goal.progress_percentage * 100)}%
          </Text>
        </View>

        {goal.children && goal.children.length > 0 && (
          <View style={styles.goalChildren}>
            {renderGoalTree(goal.children, level + 1)}
          </View>
        )}
      </View>
    ))
  );

  // Loading state
  if (loading && projects.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading projects...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'projects' && styles.activeTab]}
          onPress={() => setActiveTab('projects')}
        >
          <Text style={[styles.tabText, activeTab === 'projects' && styles.activeTabText]}>
            📁 Projects
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'portfolio' && styles.activeTab]}
          onPress={() => setActiveTab('portfolio')}
        >
          <Text style={[styles.tabText, activeTab === 'portfolio' && styles.activeTabText]}>
            💼 Portfolio
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'daily' && styles.activeTab]}
          onPress={() => setActiveTab('daily')}
        >
          <Text style={[styles.tabText, activeTab === 'daily' && styles.activeTabText]}>
            ⏰ Daily
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'integrations' && styles.activeTab]}
          onPress={() => setActiveTab('integrations')}
        >
          <Text style={[styles.tabText, activeTab === 'integrations' && styles.activeTabText]}>
            🔌 Integrations
          </Text>
        </TouchableOpacity>
      </View>

      {/* Tab Content */}
      {activeTab === 'projects' && (
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>📁 Project Spaces</Text>
            <TouchableOpacity
              style={styles.createButton}
              onPress={() => setShowCreateModal(true)}
            >
              <Text style={styles.createButtonText}>+ New Project</Text>
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.content}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
          >
            {/* Projects List */}
            <View style={styles.projectsSection}>
              <Text style={styles.sectionTitle}>Your Projects</Text>
              {projects.length === 0 ? (
                <View style={styles.emptyState}>
                  <Text style={styles.emptyStateText}>No projects yet</Text>
                  <Text style={styles.emptyStateSubtext}>
                    Create your first project to get started with goal management
                  </Text>
                </View>
              ) : (
                projects.map(renderProjectCard)
              )}
            </View>

        {/* Selected Project Dashboard */}
        {selectedProject && projectDashboard && (
          <View style={styles.projectDashboard}>
            <View style={styles.dashboardHeader}>
              <Text style={styles.dashboardTitle}>{selectedProject.name}</Text>
              <TouchableOpacity
                style={styles.addGoalButton}
                onPress={() => {
                  Alert.prompt(
                    'New Goal',
                    'Enter goal title',
                    (title) => {
                      if (title) createGoal(selectedProject.id, title);
                    }
                  );
                }}
              >
                <Text style={styles.addGoalButtonText}>+ Add Goal</Text>
              </TouchableOpacity>
            </View>

            {/* Goal Tree */}
            {projectDashboard.goal_tree.roots && projectDashboard.goal_tree.roots.length > 0 && (
              <View style={styles.goalTreeSection}>
                <Text style={styles.sectionTitle}>🎯 Goal Tree</Text>
                {renderGoalTree(projectDashboard.goal_tree.roots)}
              </View>
            )}

            {/* Kanban Board Preview */}
            {projectDashboard.kanban_board && (
              <View style={styles.kanbanSection}>
                <Text style={styles.sectionTitle}>📋 Kanban Board</Text>
                <View style={styles.kanbanColumns}>
                  {projectDashboard.kanban_board.columns.map((column) => {
                    const columnCards = projectDashboard.kanban_cards.filter(
                      card => card.column === column
                    );
                    return (
                      <View key={column} style={styles.kanbanColumn}>
                        <Text style={styles.columnTitle}>
                          {column} ({columnCards.length})
                        </Text>
                        {columnCards.slice(0, 3).map((card) => (
                          <View key={card.id} style={styles.kanbanCard}>
                            <Text style={styles.cardText} numberOfLines={2}>
                              Card {card.id.slice(-4)}
                            </Text>
                          </View>
                        ))}
                        {columnCards.length > 3 && (
                          <Text style={styles.moreCardsText}>
                            +{columnCards.length - 3} more
                          </Text>
                        )}
                      </View>
                    );
                  })}
                </View>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    )}

    {activeTab === 'portfolio' && (
      <PortfolioViewComponent
        onProjectSelect={(projectId) => {
          // Find the project and set it as selected
          const project = projects.find(p => p.id === projectId);
          if (project) {
            setSelectedProject(project);
            loadProjectDashboard(project.id);
            setActiveTab('projects'); // Switch back to projects view to see details
          }
        }}
      />
    )}

    {activeTab === 'daily' && (
      <DailyCycleComponent date={new Date().toISOString().split('T')[0]} />
    )}

    {activeTab === 'integrations' && (
      <IntegrationCheckPanel
        projectId={selectedProject?.id || 'default'}
        onStatusChange={(status) => {
          console.log('Integration status changed:', status);
        }}
      />
    )}

      {/* Create Project Modal */}
      <Modal
        visible={showCreateModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowCreateModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Create New Project</Text>

            <TextInput
              style={styles.input}
              placeholder="Project name"
              value={newProjectName}
              onChangeText={setNewProjectName}
            />

            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Project description (optional)"
              value={newProjectDescription}
              onChangeText={setNewProjectDescription}
              multiline
              numberOfLines={3}
            />

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setShowCreateModal(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, styles.confirmButton]}
                onPress={createProject}
              >
                <Text style={styles.confirmButtonText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// Helper functions
function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'active': return '#4CAF50';
    case 'planning': return '#FF9800';
    case 'on_hold': return '#9E9E9E';
    case 'completed': return '#2196F3';
    case 'cancelled': return '#F44336';
    default: return '#9E9E9E';
  }
}

function getGoalTypeColor(type: string): string {
  switch (type.toLowerCase()) {
    case 'outcome': return '#2196F3';
    case 'milestone': return '#FF9800';
    case 'epic': return '#9C27B0';
    case 'task': return '#4CAF50';
    default: return '#666';
  }
}

function getGoalTypeIcon(type: string): string {
  switch (type.toLowerCase()) {
    case 'outcome': return '🎯';
    case 'milestone': return '🏁';
    case 'epic': return '📚';
    case 'task': return '✅';
    default: return '📝';
  }
}

function getPriorityColor(priority: number): string {
  if (priority >= 8) return '#F44336';
  if (priority >= 6) return '#FF9800';
  if (priority >= 4) return '#FFEB3B';
  return '#4CAF50';
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: '#007AFF',
  },
  tabText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  activeTabText: {
    color: '#007AFF',
    fontWeight: 'bold',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  createButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  createButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
  },
  projectsSection: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  emptyState: {
    alignItems: 'center',
    padding: 32,
  },
  emptyStateText: {
    fontSize: 18,
    color: '#666',
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
  projectCard: {
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  selectedProjectCard: {
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  projectHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  projectName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  projectDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  projectStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  progressText: {
    fontSize: 14,
    color: '#333',
  },
  teamText: {
    fontSize: 14,
    color: '#666',
  },
  projectDashboard: {
    backgroundColor: 'white',
    margin: 16,
    marginTop: 0,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  dashboardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  dashboardTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333',
  },
  addGoalButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  addGoalButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
  },
  goalTreeSection: {
    marginBottom: 24,
  },
  goalItem: {
    marginBottom: 12,
    padding: 12,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  goalTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    flex: 1,
  },
  priorityBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 8,
  },
  priorityText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  goalProgress: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginRight: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
  progressPercent: {
    fontSize: 12,
    color: '#666',
    minWidth: 35,
  },
  goalChildren: {
    marginTop: 8,
  },
  kanbanSection: {
    marginTop: 24,
  },
  kanbanColumns: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  kanbanColumn: {
    flex: 1,
    marginHorizontal: 4,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 8,
    minHeight: 120,
  },
  columnTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
    textAlign: 'center',
  },
  kanbanCard: {
    backgroundColor: 'white',
    padding: 8,
    borderRadius: 4,
    marginBottom: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  cardText: {
    fontSize: 12,
    color: '#333',
  },
  moreCardsText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '90%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginBottom: 16,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modalButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    marginHorizontal: 4,
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
  },
  cancelButtonText: {
    color: '#666',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  confirmButton: {
    backgroundColor: '#007AFF',
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});