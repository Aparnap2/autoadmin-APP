/**
 * Test Data Generators for E2E Testing
 * Creates realistic test data for comprehensive testing scenarios
 */

import { faker } from '@faker-js/faker';

// Initialize faker with consistent seed for reproducible tests
faker.seed(12345);

export interface TestUser {
  id: string;
  email: string;
  password: string;
  name: string;
  company: string;
  role: string;
  created_at: string;
  metadata: Record<string, any>;
}

export interface TestAgent {
  agent_id: string;
  agent_type: string;
  name: string;
  description: string;
  capabilities: string[];
  max_capacity: number;
  user_id: string;
  status: string;
  metadata: Record<string, any>;
  track_performance?: boolean;
}

export interface TestTask {
  task_id: string;
  title: string;
  description: string;
  task_type: string;
  priority: string;
  assigned_to?: string;
  user_id: string;
  status: string;
  metadata: Record<string, any>;
  estimated_duration?: number;
  deadline?: string;
  requires_collaboration?: boolean;
  collaborators?: string[];
}

export interface TestDataSet {
  user: TestUser;
  agents: TestAgent[];
  tasks: TestTask[];
  campaigns: any[];
  analytics: any[];
}

export class TestDataGenerator {
  private generatedIds = new Set<string>();

  /**
   * Generate unique ID
   */
  private generateId(prefix: string): string {
    let id: string;
    do {
      id = `${prefix}_${faker.string.alphanumeric({ length: 8 })}`;
    } while (this.generatedIds.has(id));

    this.generatedIds.add(id);
    return id;
  }

  /**
   * Generate test user
   */
  generateTestUser(overrides: Partial<TestUser> = {}): TestUser {
    const firstName = faker.person.firstName();
    const lastName = faker.person.lastName();
    const company = faker.company.name();

    return {
      id: this.generateId('user'),
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}@${faker.internet.domainName()}`,
      password: 'Test123456!',
      name: `${firstName} ${lastName}`,
      company: company,
      role: faker.helpers.arrayElement(['admin', 'manager', 'user']),
      created_at: faker.date.past().toISOString(),
      metadata: {
        department: faker.helpers.arrayElement(['marketing', 'sales', 'engineering', 'operations']),
        location: faker.location.city(),
        timezone: faker.location.timeZone(),
        preferences: {
          theme: faker.helpers.arrayElement(['light', 'dark']),
          notifications: faker.datatype.boolean(),
          language: 'en-US'
        }
      },
      ...overrides
    };
  }

  /**
   * Generate test agent
   */
  generateTestAgent(overrides: Partial<TestAgent> = {}): TestAgent {
    const agentTypes = ['marketing', 'sales', 'customer_support', 'analytics', 'content', 'social_media'];
    const capabilities = {
      marketing: ['content_creation', 'campaign_management', 'analytics', 'email_marketing'],
      sales: ['lead_generation', 'customer_communication', 'deal_management', 'forecasting'],
      customer_support: ['ticket_management', 'customer_communication', 'knowledge_base', 'escalation'],
      analytics: ['data_analysis', 'reporting', 'insights', 'visualization'],
      content: ['content_creation', 'seo_optimization', 'publishing', 'editing'],
      social_media: ['content_creation', 'posting', 'engagement', 'monitoring']
    };

    const agentType = overrides.agent_type || faker.helpers.arrayElement(agentTypes);
    const agentCapabilities = capabilities[agentType as keyof typeof capabilities] || [];

    return {
      agent_id: this.generateId('agent'),
      agent_type: agentType,
      name: faker.helpers.arrayElement([
        'AI Assistant',
        'Marketing Bot',
        'Analytics Engine',
        'Content Creator',
        'Social Media Manager',
        'Customer Service Agent',
        'Sales Assistant'
      ]) + ' ' + faker.number.int({ min: 1, max: 999 }),
      description: faker.helpers.arrayElement([
        'Advanced AI agent for automated marketing tasks',
        'Intelligent assistant for customer engagement',
        'Automated content generation and optimization',
        'Real-time analytics and insights generation',
        'Comprehensive social media management',
        'Efficient customer support automation'
      ]),
      capabilities: faker.helpers.arrayElements(agentCapabilities, { min: 2, max: agentCapabilities.length }),
      max_capacity: faker.number.int({ min: 5, max: 20 }),
      user_id: overrides.user_id || this.generateId('user'),
      status: 'inactive',
      metadata: {
        version: faker.system.semver(),
        model: faker.helpers.arrayElement(['gpt-4', 'claude-3', 'gemini-pro']),
        training_data: faker.date.past().toISOString(),
        last_updated: faker.date.recent().toISOString(),
        performance_history: [],
        configuration: {
          response_time_target: faker.number.int({ min: 1000, max: 5000 }),
          accuracy_threshold: faker.number.float({ min: 0.8, max: 0.99 }),
          auto_scaling: faker.datatype.boolean()
        }
      },
      ...overrides
    };
  }

  /**
   * Generate test task
   */
  generateTestTask(overrides: Partial<TestTask> = {}): TestTask {
    const taskTypes = [
      'content_creation',
      'campaign_management',
      'data_analysis',
      'customer_communication',
      'social_media_posting',
      'report_generation',
      'lead_generation',
      'email_marketing',
      'research_task',
      'optimization_task'
    ];

    const taskType = overrides.task_type || faker.helpers.arrayElement(taskTypes);

    const taskTitles = {
      content_creation: [
        'Create blog post about industry trends',
        'Write email newsletter for subscribers',
        'Generate social media content campaign',
        'Create product description copy'
      ],
      campaign_management: [
        'Setup and configure marketing campaign',
        'Monitor and optimize campaign performance',
        'Analyze campaign results and generate report',
        'Update campaign targeting parameters'
      ],
      data_analysis: [
        'Analyze customer behavior data',
        'Generate monthly performance report',
        'Extract insights from sales data',
        'Create competitive analysis report'
      ],
      social_media_posting: [
        'Post daily social media updates',
        'Schedule weekly content calendar',
        'Engage with social media followers',
        'Monitor social media metrics'
      ]
    };

    const titles = taskTitles[taskType as keyof typeof taskTitles] || ['Complete automated task'];

    return {
      task_id: this.generateId('task'),
      title: overrides.title || faker.helpers.arrayElement(titles),
      description: faker.lorem.paragraph({ min: 2, max: 5 }),
      task_type: taskType,
      priority: faker.helpers.arrayElement(['LOW', 'NORMAL', 'HIGH', 'CRITICAL']),
      assigned_to: overrides.assigned_to,
      user_id: overrides.user_id || this.generateId('user'),
      status: 'pending',
      metadata: {
        created_at: faker.date.recent().toISOString(),
        estimated_effort: faker.number.int({ min: 1, max: 8 }),
        required_skills: faker.helpers.arrayElements(['writing', 'analysis', 'communication', 'technical']),
        dependencies: faker.helpers.arrayElements([this.generateId('task')], { min: 0, max: 2 }),
        tags: faker.helpers.arrayElements(['urgent', 'recurring', 'high-impact', 'client-facing']),
        performance_metrics: {
          accuracy_target: faker.number.float({ min: 0.85, max: 0.99 }),
          timeliness_target: faker.number.float({ min: 0.9, max: 1.0 }),
          quality_score_target: faker.number.float({ min: 0.8, max: 0.95 })
        }
      },
      estimated_duration: faker.number.int({ min: 1800, max: 14400 }), // 30 mins to 4 hours
      deadline: faker.date.future().toISOString(),
      requires_collaboration: faker.datatype.boolean(),
      collaborators: faker.helpers.arrayElements([this.generateId('agent')], { min: 0, max: 3 }),
      ...overrides
    };
  }

  /**
   * Generate marketing campaign data
   */
  generateMarketingCampaign(overrides: any = {}): any {
    return {
      campaign_id: this.generateId('campaign'),
      name: faker.company.catchPhrase(),
      type: faker.helpers.arrayElement(['email', 'social', 'display', 'search', 'content']),
      status: faker.helpers.arrayElement(['draft', 'active', 'paused', 'completed']),
      budget: faker.number.float({ min: 1000, max: 50000, fractionDigits: 2 }),
      target_audience: {
        demographics: {
          age_range: `${faker.number.int({ min: 18, max: 65 })}-${faker.number.int({ min: 18, max: 65 })}`,
          locations: faker.helpers.arrayElements([faker.location.city(), faker.location.city(), faker.location.city()]),
          interests: faker.helpers.arrayElements(['technology', 'business', 'lifestyle', 'health', 'finance'])
        },
        size: faker.number.int({ min: 1000, max: 100000 })
      },
      performance: {
        impressions: faker.number.int({ min: 10000, max: 1000000 }),
        clicks: faker.number.int({ min: 100, max: 10000 }),
        conversions: faker.number.int({ min: 10, max: 1000 }),
        cost_per_conversion: faker.number.float({ min: 5, max: 200, fractionDigits: 2 }),
        roi: faker.number.float({ min: 0.5, max: 5.0, fractionDigits: 2 })
      },
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
      ...overrides
    };
  }

  /**
   * Generate analytics data
   */
  generateAnalyticsData(overrides: any = {}): any {
    const date = faker.date.recent({ days: 30 });

    return {
      metric_id: this.generateId('metric'),
      date: date.toISOString().split('T')[0],
      metrics: {
        website_visitors: faker.number.int({ min: 100, max: 10000 }),
        new_users: faker.number.int({ min: 10, max: 1000 }),
        conversion_rate: faker.number.float({ min: 0.01, max: 0.10, fractionDigits: 4 }),
        bounce_rate: faker.number.float({ min: 0.2, max: 0.8, fractionDigits: 3 }),
        avg_session_duration: faker.number.int({ min: 30, max: 600 }),
        revenue: faker.number.float({ min: 100, max: 10000, fractionDigits: 2 })
      },
      sources: {
        organic: faker.number.float({ min: 0.2, max: 0.6 }),
        paid: faker.number.float({ min: 0.1, max: 0.4 }),
        social: faker.number.float({ min: 0.1, max: 0.3 }),
        referral: faker.number.float({ min: 0.05, max: 0.2 }),
        direct: faker.number.float({ min: 0.05, max: 0.3 })
      },
      campaigns: faker.helpers.arrayElements([
        this.generateMarketingCampaign({ campaign_id: this.generateId('campaign') })
      ], { min: 1, max: 5 }),
      ...overrides
    };
  }

  /**
   * Generate comprehensive test dataset
   */
  generateComprehensiveTestData(overrides: Partial<TestDataSet> = {}): TestDataSet {
    const user = this.generateTestUser(overrides.user);

    // Generate multiple agents
    const agents = Array.from({ length: faker.number.int({ min: 3, max: 8 }) }, () =>
      this.generateTestAgent({ user_id: user.id })
    );

    // Generate tasks for different agents
    const tasks = [];
    for (const agent of agents) {
      const taskCount = faker.number.int({ min: 2, max: 5 });
      for (let i = 0; i < taskCount; i++) {
        tasks.push(this.generateTestTask({
          assigned_to: agent.agent_id,
          user_id: user.id,
          status: faker.helpers.arrayElement(['pending', 'in_progress', 'completed'])
        }));
      }
    }

    // Generate some unassigned tasks
    const unassignedTaskCount = faker.number.int({ min: 1, max: 3 });
    for (let i = 0; i < unassignedTaskCount; i++) {
      tasks.push(this.generateTestTask({
        user_id: user.id,
        status: 'pending'
      }));
    }

    // Generate marketing campaigns
    const campaigns = Array.from({ length: faker.number.int({ min: 2, max: 5 }) }, () =>
      this.generateMarketingCampaign({ user_id: user.id })
    );

    // Generate analytics data
    const analytics = Array.from({ length: 30 }, (_, index) =>
      this.generateAnalyticsData({
        date: new Date(Date.now() - (29 - index) * 24 * 60 * 60 * 1000).toISOString()
      })
    );

    return {
      user,
      agents,
      tasks,
      campaigns,
      analytics,
      ...overrides
    };
  }

  /**
   * Generate performance test data
   */
  generatePerformanceTestData(scale: 'small' | 'medium' | 'large' = 'medium'): {
    users: TestUser[];
    agents: TestAgent[];
    tasks: TestTask[];
    events: any[];
  } {
    const scaleConfig = {
      small: { users: 5, agents: 10, tasks: 50, events: 200 },
      medium: { users: 20, agents: 50, tasks: 200, events: 1000 },
      large: { users: 100, agents: 200, tasks: 1000, events: 5000 }
    };

    const config = scaleConfig[scale];

    const users = Array.from({ length: config.users }, () => this.generateTestUser());

    const agents = users.flatMap(user =>
      Array.from({ length: Math.floor(config.agents / config.users) }, () =>
        this.generateTestAgent({ user_id: user.id })
      )
    );

    const tasks = agents.flatMap(agent =>
      Array.from({ length: Math.floor(config.tasks / agents.length) }, () =>
        this.generateTestTask({
          assigned_to: agent.agent_id,
          user_id: agent.user_id
        })
      )
    );

    const events = Array.from({ length: config.events }, () => ({
      event_id: this.generateId('event'),
      event_type: faker.helpers.arrayElement([
        'agent_status_update',
        'task_created',
        'task_progress',
        'task_completed',
        'system_notification',
        'user_action',
        'metric_update'
      ]),
      data: {
        message: faker.lorem.sentence(),
        value: faker.number.float({ min: 0, max: 100 }),
        metadata: faker.helpers.arrayElements(['priority', 'urgent', 'batch'])
      },
      timestamp: faker.date.recent().toISOString(),
      user_id: faker.helpers.arrayElement(users).id,
      agent_id: faker.helpers.maybe(() => faker.helpers.arrayElement(agents).agent_id),
      task_id: faker.helpers.maybe(() => faker.helpers.arrayElement(tasks).task_id)
    }));

    return { users, agents, tasks, events };
  }
}

// Export singleton instance
export const dataGenerator = new TestDataGenerator();

// Export convenience functions
export const generateTestUser = (overrides?: Partial<TestUser>) => dataGenerator.generateTestUser(overrides);
export const generateTestAgent = (overrides?: Partial<TestAgent>) => dataGenerator.generateTestAgent(overrides);
export const generateTestTask = (overrides?: Partial<TestTask>) => dataGenerator.generateTestTask(overrides);
export const generateComplexTestData = (overrides?: Partial<TestDataSet>) => dataGenerator.generateComprehensiveTestData(overrides);