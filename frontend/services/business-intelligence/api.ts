/**
 * Business Intelligence API Service
 * Provides comprehensive business intelligence functionality integration
 * with HTTP-only communication and Server-Sent Events for real-time updates
 */

import { FastAPIResponse, getFastAPIClient } from '../api/fastapi-client';

// Types based on business intelligence backend models
export interface MorningBriefingData {
  id: string;
  date: string;
  title: string;
  executive_summary: {
    overall_health_score: number;
    key_priorities: string[];
    critical_alerts: string[];
    opportunities: string[];
  };
  business_health: {
    revenue_trends: {
      current_mrr: number;
      growth_rate: number;
      forecast_mrr: number;
      variance: number;
    };
    operational_metrics: {
      active_users: number;
      conversion_rate: number;
      retention_rate: number;
      support_tickets: number;
    };
    team_productivity: {
      tasks_completed: number;
      avg_completion_time: number;
      team_utilization: number;
    };
  };
  strategic_priorities: Array<{
    priority: string;
    impact: 'high' | 'medium' | 'low';
    deadline: string;
    owner: string;
    status: 'on_track' | 'at_risk' | 'delayed';
  }>;
  competitive_insights: Array<{
    competitor: string;
    development: string;
    impact: string;
    recommended_response: string;
  }>;
  market_opportunities: Array<{
    opportunity: string;
    potential_value: number;
    confidence: number;
    timeframe: string;
  }>;
  generated_at: string;
}

export interface RevenueMetrics {
  current_mrr: number;
  arr: number;
  mrr_growth: {
    current_period: number;
    previous_period: number;
    rate: number;
  };
  arr_growth: {
    current_period: number;
    previous_period: number;
    rate: number;
  };
  revenue_forecast: Array<{
    period: string;
    forecasted: number;
    actual?: number;
    confidence: number;
  }>;
  churn_analysis: {
    monthly_rate: number;
    annual_rate: number;
    revenue_impact: number;
    risk_customers: number;
  };
  customer_metrics: {
    cac: number;
    ltv: number;
    ltv_cac_ratio: number;
    payback_period: number;
  };
  pricing_analysis: {
    optimal_arpu: number;
    price_sensitivity: number;
    recommended_changes: Array<{
      plan: string;
      current_price: number;
      recommended_price: number;
      expected_impact: number;
    }>;
  };
  revenue_breakdown: {
    by_plan: Array<{ plan: string; revenue: number; percentage: number }>;
    by_cohort: Array<{ cohort: string; revenue: number; retention: number }>;
    by_region: Array<{ region: string; revenue: number; growth: number }>;
  };
}

export interface TaskDelegationResult {
  original_task: {
    id: string;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
    required_capabilities: string[];
  };
  evaluation: {
    business_impact: 'low' | 'medium' | 'high' | 'critical';
    urgency_score: number;
    complexity_score: number;
    estimated_effort: number;
    business_value: number;
  };
  delegation_decision: {
    should_delegate: boolean;
    target_agent: string;
    confidence: number;
    reasoning: string;
  };
  context_analysis: {
    relevant_business_goals: string[];
    dependencies: string[];
    risk_factors: string[];
  };
}

export interface CompetitorAnalysis {
  competitor_profile: {
    name: string;
    industry: string;
    size: string;
    market_position: string;
    strengths: string[];
    weaknesses: string[];
  };
  product_comparison: {
    feature_gaps: Array<{
      competitor_feature: string;
      our_feature?: string;
      advantage: 'them' | 'us' | 'neutral';
      importance: 'high' | 'medium' | 'low';
    }>;
    pricing_comparison: Array<{
      plan: string;
      their_price: number;
      our_price: number;
      difference_percentage: number;
    }>;
    market_positioning: {
      their_positioning: string;
      our_positioning: string;
      differentiation_opportunities: string[];
    };
  };
  market_intelligence: {
    recent_developments: Array<{
      date: string;
      development: string;
      potential_impact: string;
    }>;
    strategic_moves: Array<{
      move_type: string;
      description: string;
      timeline: string;
      threat_level: 'low' | 'medium' | 'high';
    }>;
    customer_sentiment: {
      overall_score: number;
      key_themes: string[];
      common_complaints: string[];
    };
  };
  opportunities: Array<{
    opportunity: string;
    type: 'feature' | 'pricing' | 'marketing' | 'strategic';
    potential_impact: 'low' | 'medium' | 'high';
    effort_required: 'low' | 'medium' | 'high';
    timeline: string;
  }>;
  strategic_recommendations: Array<{
    recommendation: string;
    rationale: string;
    expected_outcome: string;
    priority: 'high' | 'medium' | 'low';
  }>;
}

export interface CRMAnalysisData {
  overall_health: {
    total_deals: number;
    total_pipeline_value: number;
    weighted_pipeline: number;
    conversion_rate: number;
    sales_cycle_length: number;
  };
  deal_health_scores: Array<{
    deal_id: string;
    deal_name: string;
    health_score: number;
    risk_factors: string[];
    recommendations: string[];
    days_in_stage: number;
  }>;
  pipeline_optimization: {
    bottleneck_stages: Array<{
      stage: string;
      conversion_rate: number;
      avg_days_in_stage: number;
      recommended_actions: string[];
    }>;
    win_rate_analysis: {
      overall: number;
      by_stage: Array<{ stage: string; rate: number }>;
      by_rep: Array<{ rep: string; rate: number }>;
      by_deal_size: Array<{ size: string; rate: number }>;
    };
    forecast_accuracy: {
      current_quarter: number;
      previous_quarters: Array<{ quarter: string; accuracy: number }>;
    };
  };
  customer_segments: Array<{
    segment: string;
    size: number;
    avg_deal_size: number;
    conversion_rate: number;
    ltv: number;
    characteristics: string[];
  }>;
  engagement_patterns: {
    communication_frequency: Array<{
      type: string;
      frequency: number;
      effectiveness: number;
    }>;
    best_practices: string[];
    risk_indicators: string[];
  };
  recommendations: Array<{
    category: 'pipeline' | 'forecasting' | 'engagement' | 'strategy';
    priority: 'high' | 'medium' | 'low';
    recommendation: string;
    expected_impact: string;
  }>;
}

export interface StrategicPlanData {
  current_status: {
    overall_progress: number;
    key_achievements: string[];
    current_challenges: string[];
    milestone_completion: number;
  };
  strategic_initiatives: Array<{
    id: string;
    title: string;
    description: string;
    category: 'growth' | 'efficiency' | 'innovation' | 'retention';
    priority: 'high' | 'medium' | 'low';
    current_progress: number;
    kpis: Array<{
      metric: string;
      current: number;
      target: number;
      trend: 'improving' | 'stable' | 'declining';
    }>;
    next_milestones: Array<{
      milestone: string;
      due_date: string;
      dependencies: string[];
    }>;
  }>;
  okrs: Array<{
    objective: string;
    key_results: Array<{
      key_result: string;
      current_value: number;
      target_value: number;
      progress_percentage: number;
      due_date: string;
    }>;
    progress_percentage: number;
    confidence_level: number;
  }>;
  scenario_analysis: Array<{
    scenario: 'best_case' | 'base_case' | 'worst_case';
    probability: number;
    projected_outcomes: {
      revenue: number;
      growth_rate: number;
      market_share: number;
    };
    key_assumptions: string[];
    risk_factors: string[];
    recommended_actions: string[];
  }>;
  recommendations: Array<{
    recommendation: string;
    rationale: string;
    expected_impact: string;
    implementation_timeline: string;
    required_resources: string[];
    success_metrics: string[];
  }>;
}

export interface KPIMetrics {
  overall_health: {
    total_kpis: number;
    healthy_kpis: number;
    at_risk_kpis: number;
    critical_kpis: number;
    overall_score: number;
  };
  kpi_categories: Array<{
    category: string;
    kpis: Array<{
      id: string;
      name: string;
      description: string;
      current_value: number;
      target_value: number;
      unit: string;
      status: 'healthy' | 'warning' | 'critical';
      trend: 'improving' | 'stable' | 'declining';
      last_updated: string;
    }>;
    category_health_score: number;
  }>;
  trend_analysis: Array<{
    kpi_id: string;
    kpi_name: string;
    trend_type: 'upward' | 'downward' | 'stable' | 'volatile';
    trend_strength: 'weak' | 'moderate' | 'strong';
    forecast: Array<{
      period: string;
      forecasted_value: number;
      confidence_interval: {
        lower: number;
        upper: number;
      };
    }>;
  }>;
  alert_thresholds: Array<{
    kpi_id: string;
    warning_threshold: number;
    critical_threshold: number;
    operator: 'greater_than' | 'less_than' | 'equals';
    current_status: 'normal' | 'warning' | 'critical';
  }>;
  real_time_updates: Array<{
    kpi_id: string;
    previous_value: number;
    current_value: number;
    change_percentage: number;
    timestamp: string;
  }>;
}

export interface AlertData {
  active_alerts: Array<{
    id: string;
    title: string;
    description: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    category: string;
    kpi_id?: string;
    source: string;
    timestamp: string;
    acknowledged: boolean;
    metadata: Record<string, any>;
  }>;
  alert_history: Array<{
    id: string;
    title: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    status: 'resolved' | 'acknowledged' | 'escalated';
    resolution_time?: number;
    created_at: string;
    resolved_at?: string;
  }>;
  alert_rules: Array<{
    id: string;
    name: string;
    description: string;
    condition: {
      kpi_id: string;
      operator: 'greater_than' | 'less_than' | 'equals';
      threshold: number;
      duration_minutes?: number;
    };
    actions: Array<{
      type: 'notification' | 'escalation' | 'automation';
      target: string;
      message: string;
    }>;
    is_active: boolean;
    last_triggered?: string;
  }>;
  escalation_policies: Array<{
    id: string;
    name: string;
    levels: Array<{
      level: number;
      delay_minutes: number;
      targets: string[];
      actions: string[];
    }>;
    is_active: boolean;
  }>;
}

class BusinessIntelligenceService {
  private apiClient = getFastAPIClient();
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Array<(data: any) => void>> = new Map();

  /**
   * Morning Briefing Operations
   */
  async getMorningBriefing(date?: string): Promise<FastAPIResponse<MorningBriefingData>> {
    const params = date ? `?date=${date}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/morning-briefing${params}`);
  }

  async generateMorningBriefing(): Promise<FastAPIResponse<MorningBriefingData>> {
    return this.apiClient.makeRequest('/business-intelligence/morning-briefing/generate', {
      method: 'POST'
    });
  }

  async subscribeToMorningBriefingUpdates(callback: (data: MorningBriefingData) => void): Promise<void> {
    this.addListener('morning_briefing_update', callback);
  }

  /**
   * Revenue Intelligence Operations
   */
  async getRevenueIntelligence(params?: {
    period?: string;
    forecast_periods?: number;
    include_churn_analysis?: boolean;
  }): Promise<FastAPIResponse<RevenueMetrics>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/revenue-intelligence${queryString}`);
  }

  async generateRevenueForecast(periods: number = 12): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/revenue-intelligence/forecast', {
      method: 'POST',
      body: JSON.stringify({ periods })
    });
  }

  async analyzeChurnRisk(customerIds?: string[]): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/revenue-intelligence/churn-analysis', {
      method: 'POST',
      body: JSON.stringify({ customer_ids: customerIds })
    });
  }

  async optimizePricing(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/revenue-intelligence/pricing-optimization', {
      method: 'POST'
    });
  }

  /**
   * Task Delegation Operations
   */
  async evaluateTaskForDelegation(task: {
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
    required_capabilities: string[];
  }): Promise<FastAPIResponse<TaskDelegationResult>> {
    return this.apiClient.makeRequest('/business-intelligence/task-delegation/evaluate', {
      method: 'POST',
      body: JSON.stringify(task)
    });
  }

  async delegateTask(taskId: string, targetAgent?: string): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/task-delegation/delegate/${taskId}`, {
      method: 'POST',
      body: JSON.stringify({ target_agent: targetAgent })
    });
  }

  async getDelegationHistory(params?: {
    limit?: number;
    agent_id?: string;
    status?: string;
  }): Promise<FastAPIResponse<any>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/task-delegation/history${queryString}`);
  }

  /**
   * Competitive Intelligence Operations
   */
  async analyzeCompetitor(competitorName: string): Promise<FastAPIResponse<CompetitorAnalysis>> {
    return this.apiClient.makeRequest('/business-intelligence/competitive-intelligence/analyze', {
      method: 'POST',
      body: JSON.stringify({ competitor_name: competitorName })
    });
  }

  async getCompetitorAnalysis(params?: {
    competitor?: string;
    include_market_intelligence?: boolean;
  }): Promise<FastAPIResponse<CompetitorAnalysis[]>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/competitive-intelligence${queryString}`);
  }

  async monitorCompetitors(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/competitive-intelligence/monitor', {
      method: 'POST'
    });
  }

  async getMarketPositioning(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/competitive-intelligence/market-positioning');
  }

  /**
   * CRM Intelligence Operations
   */
  async getCRMAnalysis(params?: {
    period?: string;
    include_forecasts?: boolean;
    deal_stage?: string;
  }): Promise<FastAPIResponse<CRMAnalysisData>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/crm-intelligence${queryString}`);
  }

  async analyzeDealHealth(dealIds?: string[]): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/crm-intelligence/deal-health', {
      method: 'POST',
      body: JSON.stringify({ deal_ids: dealIds })
    });
  }

  async optimizePipeline(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/crm-intelligence/optimize-pipeline', {
      method: 'POST'
    });
  }

  async analyzeCustomerSegments(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/crm-intelligence/customer-segments', {
      method: 'POST'
    });
  }

  /**
   * Strategic Planning Operations
   */
  async getStrategicPlan(params?: {
    initiative_id?: string;
    include_okrs?: boolean;
    include_scenarios?: boolean;
  }): Promise<FastAPIResponse<StrategicPlanData>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/strategic-planner${queryString}`);
  }

  async generateRecommendations(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/strategic-planner/recommendations', {
      method: 'POST'
    });
  }

  async updateProgress(initiativeId: string, progress: number): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/strategic-planner/progress/${initiativeId}`, {
      method: 'PATCH',
      body: JSON.stringify({ progress })
    });
  }

  async analyzeScenarios(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/strategic-planner/scenarios', {
      method: 'POST'
    });
  }

  /**
   * KPI Operations
   */
  async getKPIs(params?: {
    category?: string;
    status?: string;
    include_trends?: boolean;
  }): Promise<FastAPIResponse<KPIMetrics>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/kpis${queryString}`);
  }

  async calculateKPI(kpiId: string, params?: Record<string, any>): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/kpis/calculate/${kpiId}`, {
      method: 'POST',
      body: JSON.stringify(params || {})
    });
  }

  async updateKPI(kpiId: string, value: number): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/kpis/update/${kpiId}`, {
      method: 'POST',
      body: JSON.stringify({ value })
    });
  }

  async getKPIForecast(kpiId: string, periods: number = 12): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/kpis/forecast/${kpiId}?periods=${periods}`);
  }

  /**
   * Alert Operations
   */
  async getAlerts(params?: {
    severity?: string;
    category?: string;
    acknowledged?: boolean;
    limit?: number;
  }): Promise<FastAPIResponse<AlertData>> {
    const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : '';
    return this.apiClient.makeRequest(`/business-intelligence/alerts${queryString}`);
  }

  async acknowledgeAlert(alertId: string): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/alerts/${alertId}/acknowledge`, {
      method: 'POST'
    });
  }

  async createAlertRule(rule: {
    name: string;
    condition: any;
    actions: any[];
  }): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/alerts/rules', {
      method: 'POST',
      body: JSON.stringify(rule)
    });
  }

  async updateAlertRule(ruleId: string, updates: any): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/alerts/rules/${ruleId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates)
    });
  }

  async deleteAlertRule(ruleId: string): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest(`/business-intelligence/alerts/rules/${ruleId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Real-time Updates (Server-Sent Events)
   */
  async connectRealtimeUpdates(): Promise<void> {
    try {
      this.disconnectRealtimeUpdates();

      const baseURL = this.apiClient.getBaseURL();
      const eventURL = `${baseURL}/business-intelligence/stream/dashboard`;

      if (typeof EventSource !== 'undefined') {
        this.eventSource = new EventSource(eventURL);

        this.eventSource.onopen = () => {
          console.log('Business Intelligence SSE connected');
        };

        this.eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleRealtimeEvent(data);
          } catch (error) {
            console.error('Error parsing BI SSE message:', error);
          }
        };

        this.eventSource.onerror = (error) => {
          console.error('Business Intelligence SSE error:', error);
          // Implement reconnection logic if needed
        };
      }
    } catch (error) {
      console.error('Failed to connect BI real-time updates:', error);
    }
  }

  disconnectRealtimeUpdates(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  addListener(eventType: string, callback: (data: any) => void): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  removeListener(eventType: string, callback: (data: any) => void): void {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  private handleRealtimeEvent(event: { type: string; data: any; timestamp: string }): void {
    const callbacks = this.listeners.get(event.type);
    if (callbacks) {
      callbacks.forEach(callback => callback(event.data));
    }
  }

  /**
   * Executive Dashboard Operations
   */
  async getExecutiveDashboardData(): Promise<FastAPIResponse<{
    morning_briefing?: MorningBriefingData;
    revenue_metrics?: RevenueMetrics;
    kpi_summary?: KPIMetrics;
    active_alerts?: AlertData;
    recent_tasks?: any[];
    system_health?: any;
  }>> {
    return this.apiClient.makeRequest('/business-intelligence/executive-dashboard');
  }

  async refreshDashboardData(): Promise<FastAPIResponse<any>> {
    return this.apiClient.makeRequest('/business-intelligence/executive-dashboard/refresh', {
      method: 'POST'
    });
  }

  /**
   * Utility Methods
   */
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  getHealthCheck(): Promise<any> {
    return this.apiClient.healthCheck();
  }
}

// Singleton instance
let biService: BusinessIntelligenceService | null = null;

export function getBusinessIntelligenceService(): BusinessIntelligenceService {
  if (!biService) {
    biService = new BusinessIntelligenceService();
  }
  return biService;
}

export default BusinessIntelligenceService;