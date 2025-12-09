/**
 * PortfolioViewComponent
 * Shows all projects with their current MVP stage, progress bars, and momentum trends
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  FlatList,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface PortfolioProject {
  id: string;
  name: string;
  description?: string;
  stage: 'ideation' | 'mvp' | 'development' | 'testing' | 'launch' | 'maintenance';
  progressPercentage: number;
  tasksInReview: number;
  nextPriorityItem: string;
  momentumTrend: 'up' | 'down' | 'stable';
  momentumScore: number;
  lastActivity: string;
}

interface PortfolioViewProps {
  onProjectSelect?: (projectId: string) => void;
}

const PortfolioViewComponent: React.FC<PortfolioViewProps> = ({ onProjectSelect }) => {
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  // Simulate loading projects
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      
      // Mock data - in real app, this would come from API
      const mockProjects: PortfolioProject[] = [
        {
          id: 'project_1',
          name: 'E-commerce Platform',
          description: 'Full-featured online store with payment processing',
          stage: 'development',
          progressPercentage: 75,
          tasksInReview: 3,
          nextPriorityItem: 'Payment integration',
          momentumTrend: 'up',
          momentumScore: 82,
          lastActivity: '2 hours ago',
        },
        {
          id: 'project_2',
          name: 'Mobile Analytics Dashboard',
          description: 'Real-time analytics for mobile app usage',
          stage: 'mvp',
          progressPercentage: 45,
          tasksInReview: 2,
          nextPriorityItem: 'User authentication',
          momentumTrend: 'stable',
          momentumScore: 67,
          lastActivity: '1 day ago',
        },
        {
          id: 'project_3',
          name: 'AI Content Generator',
          description: 'Automated content creation using large language models',
          stage: 'ideation',
          progressPercentage: 15,
          tasksInReview: 0,
          nextPriorityItem: 'Market research',
          momentumTrend: 'up',
          momentumScore: 45,
          lastActivity: '3 days ago',
        },
        {
          id: 'project_4',
          name: 'Task Management App',
          description: 'Focus-first task management with WIP limits',
          stage: 'launch',
          progressPercentage: 95,
          tasksInReview: 1,
          nextPriorityItem: 'Bug fixes',
          momentumTrend: 'down',
          momentumScore: 88,
          lastActivity: 'Just now',
        },
      ];

      setProjects(mockProjects);
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'ideation': return '#9E9E9E';
      case 'mvp': return '#FF9800';
      case 'development': return '#2196F3';
      case 'testing': return '#9C27B0';
      case 'launch': return '#4CAF50';
      case 'maintenance': return '#607D8B';
      default: return '#9E9E9E';
    }
  };

  const getStageName = (stage: string) => {
    switch (stage) {
      case 'ideation': return 'Ideation';
      case 'mvp': return 'MVP';
      case 'development': return 'Development';
      case 'testing': return 'Testing';
      case 'launch': return 'Launch';
      case 'maintenance': return 'Maintenance';
      default: return stage;
    }
  };

  const getMomentumIcon = (trend: string) => {
    switch (trend) {
      case 'up': return 'trending-up';
      case 'down': return 'trending-down';
      case 'stable': return 'trending';
      default: return 'trending';
    }
  };

  const getMomentumColor = (trend: string) => {
    switch (trend) {
      case 'up': return '#4CAF50';
      case 'down': return '#F44336';
      case 'stable': return '#9E9E9E';
      default: return '#9E9E9E';
    }
  };

  const ProjectCard = ({ project }: { project: PortfolioProject }) => (
    <TouchableOpacity
      style={[
        styles.projectCard,
        selectedProject === project.id && styles.selectedProjectCard
      ]}
      onPress={() => {
        setSelectedProject(project.id);
        onProjectSelect?.(project.id);
      }}
    >
      <View style={styles.projectHeader}>
        <Text style={styles.projectName}>{project.name}</Text>
        <View style={[styles.stageBadge, { backgroundColor: getStageColor(project.stage) }]}>
          <Text style={styles.stageText}>{getStageName(project.stage)}</Text>
        </View>
      </View>

      {project.description && (
        <Text style={styles.projectDescription} numberOfLines={2}>
          {project.description}
        </Text>
      )}

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              { backgroundColor: getStageColor(project.stage) },
              { width: `${project.progressPercentage}%` }
            ]}
          />
        </View>
        <Text style={styles.progressText}>{project.progressPercentage}%</Text>
      </View>

      {/* Stats Row */}
      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{project.tasksInReview}</Text>
          <Text style={styles.statLabel}>In Review</Text>
        </View>
        <View style={styles.statItem}>
          <Text 
            style={[
              styles.statValue, 
              { color: getMomentumColor(project.momentumTrend) }
            ]}
          >
            {project.momentumScore}
          </Text>
          <View style={styles.momentumRow}>
            <Ionicons 
              name={getMomentumIcon(project.momentumTrend)} 
              size={12} 
              color={getMomentumColor(project.momentumTrend)} 
            />
            <Text style={styles.statLabel}>Momentum</Text>
          </View>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{project.lastActivity}</Text>
          <Text style={styles.statLabel}>Last Activity</Text>
        </View>
      </View>

      {/* Next Priority */}
      <View style={styles.nextPriorityContainer}>
        <Text style={styles.nextPriorityLabel}>Next Priority:</Text>
        <Text style={styles.nextPriorityItem}>{project.nextPriorityItem}</Text>
      </View>

      {/* Action Button */}
      <TouchableOpacity 
        style={styles.viewProjectButton}
        onPress={() => onProjectSelect?.(project.id)}
      >
        <Text style={styles.viewProjectButtonText}>View Project</Text>
        <Ionicons name="arrow-forward" size={16} color="white" />
      </TouchableOpacity>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading portfolio...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>💼 Portfolio View</Text>
        <Text style={styles.subtitle}>
          {projects.length} projects • {projects.filter(p => p.momentumTrend === 'up').length} trending up
        </Text>
      </View>

      {projects.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Ionicons name="folder-open" size={48} color="#9E9E9E" />
          <Text style={styles.emptyTitle}>No Projects</Text>
          <Text style={styles.emptySubtitle}>Create your first project to get started</Text>
        </View>
      ) : (
        <ScrollView style={styles.projectsList}>
          {projects.map(project => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </ScrollView>
      )}

      {/* Summary Stats */}
      <View style={styles.summaryContainer}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>{projects.length}</Text>
          <Text style={styles.summaryLabel}>Total Projects</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>
            {projects.filter(p => p.progressPercentage >= 80).length}
          </Text>
          <Text style={styles.summaryLabel}>Ready to Launch</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>
            {projects.filter(p => p.momentumTrend === 'up').length}
          </Text>
          <Text style={styles.summaryLabel}>Improving</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 4,
  },
  projectsList: {
    flex: 1,
  },
  projectCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
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
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  projectName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
    marginRight: 8,
  },
  stageBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  stageText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  projectDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    lineHeight: 18,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  progressBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
    marginRight: 8,
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  progressText: {
    fontSize: 12,
    color: '#666',
    fontWeight: 'bold',
    minWidth: 30,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
  },
  momentumRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextPriorityContainer: {
    marginBottom: 12,
    padding: 8,
    backgroundColor: '#f8f9fa',
    borderRadius: 6,
  },
  nextPriorityLabel: {
    fontSize: 12,
    color: '#666',
    fontWeight: 'bold',
    marginBottom: 2,
  },
  nextPriorityItem: {
    fontSize: 14,
    color: '#333',
  },
  viewProjectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#007AFF',
    paddingVertical: 10,
    borderRadius: 8,
  },
  viewProjectButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginRight: 8,
  },
  summaryContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 16,
  },
  summaryCard: {
    flex: 1,
    alignItems: 'center',
    padding: 12,
    backgroundColor: 'white',
    borderRadius: 8,
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  summaryValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textAlign: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#666',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
  },
});

export default PortfolioViewComponent;