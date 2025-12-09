/**
 * AutoAdmin Dashboard Components
 * A sophisticated UI for the AutoAdmin agent system
 */

export { AutoAdminDashboard } from './AutoAdminDashboard';
export { AgentStatusCard } from './AgentStatusCard';
export { QuickActions } from './QuickActions';
export { ConversationPreview } from './ConversationPreview';
export { SystemMetrics } from './SystemMetrics';
export { TaskProgress } from './TaskProgress';

// Types for dashboard components
export interface DashboardAgent {
  id: string;
  name: string;
  type: 'ceo' | 'strategy' | 'devops';
  status: 'active' | 'idle' | 'processing' | 'error';
  lastActive?: string;
  tasksCompleted?: number;
  avatar?: string;
}

export interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  agentType?: 'ceo' | 'strategy' | 'devops';
  requiresConfirmation?: boolean;
}

export interface ConversationItem {
  id: string;
  type: 'human' | 'ai' | 'system';
  content: string;
  agent?: string;
  timestamp: Date;
  isPartial?: boolean;
}

export interface MetricCard {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
  icon?: string;
}

export interface TaskProgress {
  id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'delegated';
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
  assignedTo?: string;
  delegatedTo?: string;
  metadata?: Record<string, any>;
}