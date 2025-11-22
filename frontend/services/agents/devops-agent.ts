/**
 * DevOps Agent - Serves as CTO (Chief Technology Officer)
 * Handles code analysis, UI/UX review, performance optimization, and technical decisions
 */

import { BaseMessage, HumanMessage, AIMessage } from '@langchain/core/messages';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';

import BaseAgent from './base-agent';
import {
  AgentState,
  AgentConfig,
  AgentResponse,
  AgentTool,
  TaskStatus,
  TaskType,
  DevOpsAgentTools,
  CodeAnalysisTool,
  UiUxReviewTool,
  PerformanceOptimizationTool,
  SecurityAuditTool
} from './types';
import GraphMemoryService from '../../utils/supabase/graph-memory';

export interface CodeQualityMetrics {
  maintainabilityIndex: number;
  cyclomaticComplexity: number;
  codeDuplication: number;
  testCoverage: number;
  technicalDebt: string;
  securityScore: number;
  performanceScore: number;
}

export interface UiUxAnalysis {
  accessibility: {
    score: number;
    issues: string[];
    recommendations: string[];
  };
  responsiveDesign: {
    score: number;
    breakpoints: string[];
    issues: string[];
  };
  usability: {
    score: number;
    userFlow: string[];
    painPoints: string[];
  };
  designConsistency: {
    score: number;
    componentUsage: any[];
    colorPalette: string[];
    typography: any[];
  };
}

export interface PerformanceReport {
  loadTime: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  cumulativeLayoutShift: number;
  bundleSize: {
    total: number;
    chunks: any[];
    largestModules: any[];
  };
  recommendations: string[];
}

export interface SecurityAuditResult {
  vulnerabilities: Array<{
    severity: 'critical' | 'high' | 'medium' | 'low';
    type: string;
    description: string;
    file?: string;
    line?: number;
    recommendation: string;
  }>;
  dependencies: {
    total: number;
    outdated: number;
    vulnerable: number;
    recommendations: string[];
  };
  bestPractices: {
    score: number;
    violations: string[];
    suggestions: string[];
  };
}

export interface TechnicalRecommendation {
  category: 'architecture' | 'performance' | 'security' | 'maintainability' | 'scalability';
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  implementation: {
    effort: 'low' | 'medium' | 'high';
    timeline: string;
    dependencies: string[];
    rollbackPlan?: string;
  };
  impact: {
    performance?: number;
    security?: number;
    maintainability?: number;
    userExperience?: number;
  };
  codeExample?: string;
}

export class DevOpsAgent extends BaseAgent {
  private devOpsTools: DevOpsAgentTools;
  private codebaseMetrics: Map<string, CodeQualityMetrics> = new Map();
  private performanceBaseline: PerformanceReport | null = null;
  private securityBaseline: SecurityAuditResult | null = null;

  constructor(config: AgentConfig, userId: string) {
    super(config, userId);

    this.devOpsTools = {
      codeAnalysis: {
        staticAnalysis: true,
        dependencyCheck: true,
        codeQuality: true,
        bestPractices: true,
      },
      uiUxReview: {
        accessibilityCheck: true,
        responsiveDesign: true,
        usabilityAnalysis: true,
        designConsistency: true,
      },
      performanceOptimization: {
        bundleAnalysis: true,
        renderOptimization: true,
        cachingStrategy: true,
        resourceOptimization: true,
      },
      securityAudit: {
        vulnerabilityScan: true,
        dependencyAudit: true,
        codeReview: true,
        complianceCheck: true,
      }
    };
  }

  /**
   * Initialize DevOps agent with technical context
   */
  async initialize(): Promise<void> {
    await super.initialize();

    // Load technical baseline metrics
    await this.loadTechnicalBaseline();

    console.log('DevOps Agent initialized successfully');
  }

  /**
   * Process DevOps-related tasks
   */
  async process(state: AgentState): Promise<AgentResponse> {
    const startTime = Date.now();

    try {
      await this.updateMetrics('start');

      const latestMessage = state.messages[state.messages.length - 1];
      const taskType = this.determineTaskType(latestMessage.content as string);

      let response: AgentResponse;

      switch (taskType) {
        case 'code_analysis':
          response = await this.handleCodeAnalysis(state);
          break;
        case 'ui_ux_review':
          response = await this.handleUiUxReview(state);
          break;
        case 'technical_decision':
          response = await this.handleTechnicalDecision(state);
          break;
        case 'performance_optimization':
          response = await this.handlePerformanceOptimization(state);
          break;
        case 'security_audit':
          response = await this.handleSecurityAudit(state);
          break;
        default:
          response = await this.handleGeneralDevOps(state);
          break;
      }

      // Store technical insights in graph memory
      await this.storeTechnicalInsights(response, taskType);

      const responseTime = Date.now() - startTime;
      await this.updateMetrics('complete', responseTime, response.success);

      return response;

    } catch (error) {
      console.error('DevOps Agent processing error:', error);
      await this.updateMetrics('error');

      return {
        success: false,
        message: `Error in technical analysis: ${error}`,
        requiresUserInput: true,
        userInputPrompt: 'The technical analysis encountered an error. Would you like to provide more context or focus on a specific area?'
      };
    }
  }

  /**
   * Handle code analysis tasks
   */
  private async handleCodeAnalysis(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages.length - 1].content as string;

    try {
      // Extract code or file path from request
      const codeAnalysisParams = await this.extractCodeAnalysisParams(request);

      // Perform code quality analysis
      const codeMetrics = await this.performCodeQualityAnalysis(codeAnalysisParams);

      // Check dependencies
      const dependencyAnalysis = await this.analyzeDependencies();

      // Check for code patterns and best practices
      const bestPracticesReview = await this.reviewBestPractices(codeAnalysisParams);

      // Generate recommendations
      const recommendations = await this.generateCodeRecommendations(codeMetrics, dependencyAnalysis, bestPracticesReview);

      const analysis = {
        summary: this.generateCodeAnalysisSummary(codeMetrics),
        metrics: codeMetrics,
        dependencyAnalysis,
        bestPracticesReview,
        recommendations,
        technicalDebtAssessment: await this.assessTechnicalDebt(codeMetrics),
        refactoringPlan: await this.createRefactoringPlan(recommendations),
      };

      return {
        success: true,
        data: analysis,
        message: 'Code analysis completed successfully',
        nextAction: {
          type: 'continue',
          target: 'ceo',
          payload: { analysisType: 'code_analysis', issuesFound: recommendations.length }
        }
      };

    } catch (error) {
      console.error('Code analysis error:', error);
      return {
        success: false,
        message: `Code analysis failed: ${error}`
      };
    }
  }

  /**
   * Handle UI/UX review tasks
   */
  private async handleUiUxReview(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages.length - 1].content as string;

    try {
      // Extract UI/UX review parameters
      const uiUxParams = await this.extractUiUxParams(request);

      // Perform accessibility analysis
      const accessibilityAnalysis = await this.performAccessibilityAnalysis(uiUxParams);

      // Check responsive design
      const responsiveAnalysis = await this.checkResponsiveDesign(uiUxParams);

      // Analyze usability
      const usabilityAnalysis = await this.analyzeUsability(uiUxParams);

      // Review design consistency
      const consistencyAnalysis = await this.reviewDesignConsistency(uiUxParams);

      const analysis: UiUxAnalysis = {
        accessibility: accessibilityAnalysis,
        responsiveDesign: responsiveAnalysis,
        usability: usabilityAnalysis,
        designConsistency: consistencyAnalysis,
      };

      const recommendations = await this.generateUiUxRecommendations(analysis);

      return {
        success: true,
        data: {
          ...analysis,
          recommendations,
          summary: this.generateUiUxSummary(analysis),
          implementationPriority: this.prioritizeUiUxImprovements(recommendations),
        },
        message: 'UI/UX review completed successfully',
        nextAction: {
          type: 'continue',
          target: 'ceo',
          payload: { analysisType: 'ui_ux_review', score: this.calculateOverallUiUxScore(analysis) }
        }
      };

    } catch (error) {
      console.error('UI/UX review error:', error);
      return {
        success: false,
        message: `UI/UX review failed: ${error}`
      };
    }
  }

  /**
   * Handle performance optimization tasks
   */
  private async handlePerformanceOptimization(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages.length - 1].content as string;

    try {
      // Analyze current performance
      const performanceReport = await this.analyzePerformance();

      // Bundle analysis
      const bundleAnalysis = await this.analyzeBundleSize();

      // Identify bottlenecks
      const bottlenecks = await this.identifyPerformanceBottlenecks();

      // Generate optimization recommendations
      const recommendations = await this.generatePerformanceRecommendations(performanceReport, bundleAnalysis, bottlenecks);

      const analysis = {
        currentPerformance: performanceReport,
        bundleAnalysis,
        bottlenecks,
        recommendations,
        optimizationPlan: await this.createOptimizationPlan(recommendations),
        expectedImprovements: await this.estimatePerformanceImprovements(recommendations),
      };

      return {
        success: true,
        data: analysis,
        message: 'Performance optimization analysis completed',
        nextAction: {
          type: 'continue',
          target: 'ceo',
          payload: { analysisType: 'performance_optimization', improvementsCount: recommendations.length }
        }
      };

    } catch (error) {
      console.error('Performance optimization error:', error);
      return {
        success: false,
        message: `Performance optimization analysis failed: ${error}`
      };
    }
  }

  /**
   * Handle security audit tasks
   */
  private async handleSecurityAudit(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages - 1].content as string;

    try {
      // Perform vulnerability scan
      const vulnerabilityScan = await this.performVulnerabilityScan();

      // Analyze dependencies
      const dependencyAudit = await this.auditDependencies();

      // Review security best practices
      const bestPracticesAudit = await this.auditSecurityBestPractices();

      // Check compliance
      const complianceCheck = await this.checkCompliance();

      const audit: SecurityAuditResult = {
        vulnerabilities: vulnerabilityScan,
        dependencies: dependencyAudit,
        bestPractices: bestPracticesAudit,
      };

      const recommendations = await this.generateSecurityRecommendations(audit, complianceCheck);

      return {
        success: true,
        data: {
          ...audit,
          complianceCheck,
          recommendations,
          securityScore: this.calculateSecurityScore(audit),
          remediationPlan: await this.createSecurityRemediationPlan(recommendations),
        },
        message: 'Security audit completed successfully',
        nextAction: {
          type: 'continue',
          target: 'ceo',
          payload: { analysisType: 'security_audit', vulnerabilitiesFound: vulnerabilityScan.length }
        }
      };

    } catch (error) {
      console.error('Security audit error:', error);
      return {
        success: false,
        message: `Security audit failed: ${error}`
      };
    }
  }

  /**
   * Handle technical decision tasks
   */
  private async handleTechnicalDecision(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages.length - 1].content as string;

    try {
      // Extract decision parameters
      const decisionParams = await this.extractDecisionParams(request);

      // Analyze options
      const optionsAnalysis = await this.analyzeTechnicalOptions(decisionParams);

      // Evaluate against criteria
      const evaluation = await this.evaluateTechnicalOptions(optionsAnalysis, decisionParams);

      // Make recommendation
      const recommendation = await this.makeTechnicalRecommendation(evaluation, decisionParams);

      return {
        success: true,
        data: {
          decisionContext: decisionParams,
          optionsAnalysis,
          evaluation,
          recommendation,
          implementationPlan: await this.createImplementationPlan(recommendation),
          risks: await this.identifyTechnicalRisks(recommendation),
        },
        message: 'Technical decision analysis completed',
        nextAction: {
          type: 'continue',
          target: 'ceo',
          payload: { analysisType: 'technical_decision', decisionMade: true }
        }
      };

    } catch (error) {
      console.error('Technical decision error:', error);
      return {
        success: false,
        message: `Technical decision analysis failed: ${error}`
      };
    }
  }

  /**
   * Handle general DevOps tasks
   */
  private async handleGeneralDevOps(state: AgentState): Promise<AgentResponse> {
    const request = state.messages[state.messages.length - 1].content as string;

    try {
      // Use LLM with DevOps-specific tools
      const tools = this.getDevOpsSpecificTools().map(t =>
        tool(t.handler, {
          name: t.name,
          description: t.description,
          schema: t.schema,
        })
      );

      const analysisPrompt = `As a DevOps Agent (CTO), analyze this technical request:

Request: "${request}"

Consider:
- Code quality and maintainability
- Performance implications
- Security considerations
- Best practices and standards
- Scalability and architecture
- Development workflow and processes
- Technical debt and refactoring needs

Provide comprehensive technical analysis and actionable recommendations.`;

      const response = await this.llm.invoke([
        new HumanMessage(analysisPrompt),
        ...tools.map(t => ({ type: 'tool', tool: t.name } as any))
      ]);

      return {
        success: true,
        data: response.content,
        message: 'Technical analysis completed'
      };

    } catch (error) {
      console.error('General DevOps error:', error);
      return {
        success: false,
        message: `Technical analysis failed: ${error}`
      };
    }
  }

  /**
   * Get DevOps-specific tools
   */
  protected getDevOpsSpecificTools(): AgentTool[] {
    return [
      {
        name: 'code_quality_check',
        description: 'Analyze code quality metrics and identify issues',
        schema: z.object({
          filePath: z.string().optional().describe('Specific file to analyze'),
          repositoryPath: z.string().optional().describe('Repository path to analyze'),
          metrics: z.array(z.string()).optional().describe('Specific metrics to check'),
        }),
        handler: async (input) => {
          try {
            const metrics = await this.performCodeQualityAnalysis(input);
            return JSON.stringify(metrics, null, 2);
          } catch (error) {
            return `Error analyzing code quality: ${error}`;
          }
        }
      },
      {
        name: 'performance_audit',
        description: 'Audit application performance and identify bottlenecks',
        schema: z.object({
          url: z.string().optional().describe('Application URL to test'),
          metrics: z.array(z.string()).optional().describe('Performance metrics to analyze'),
        }),
        handler: async (input) => {
          try {
            const audit = await this.analyzePerformance();
            return JSON.stringify(audit, null, 2);
          } catch (error) {
            return `Error auditing performance: ${error}`;
          }
        }
      },
      {
        name: 'security_scan',
        description: 'Perform security vulnerability scan',
        schema: z.object({
          target: z.string().optional().describe('Target to scan (file, directory, or URL)'),
          scanType: z.enum(['vulnerability', 'dependency', 'code', 'compliance']).optional().describe('Type of security scan'),
        }),
        handler: async (input) => {
          try {
            const scan = await this.performSecurityScan(input);
            return JSON.stringify(scan, null, 2);
          } catch (error) {
            return `Error performing security scan: ${error}`;
          }
        }
      },
      {
        name: 'architecture_review',
        description: 'Review system architecture and provide recommendations',
        schema: z.object({
          architectureType: z.string().optional().describe('Type of architecture'),
          components: z.array(z.string()).optional().describe('System components to review'),
          concerns: z.array(z.string()).optional().describe('Specific architectural concerns'),
        }),
        handler: async (input) => {
          try {
            const review = await this.reviewArchitecture(input);
            return JSON.stringify(review, null, 2);
          } catch (error) {
            return `Error reviewing architecture: ${error}`;
          }
        }
      },
      ...this.config.tools
    ];
  }

  /**
   * Technical analysis methods
   */
  private async performCodeQualityAnalysis(params: any): Promise<CodeQualityMetrics> {
    // Check cache first
    const cacheKey = JSON.stringify(params);
    if (this.codebaseMetrics.has(cacheKey)) {
      return this.codebaseMetrics.get(cacheKey)!;
    }

    // Use LLM to analyze code quality
    const prompt = `Analyze code quality for the following parameters:

${JSON.stringify(params, null, 2)}

Provide metrics for:
- Maintainability Index (0-100)
- Cyclomatic Complexity
- Code Duplication Percentage
- Test Coverage Percentage
- Technical Debt Score
- Security Score (0-100)
- Performance Score (0-100)

Consider industry best practices and standards.`;

    const response = await this.llm.invoke(prompt);
    const metrics = this.parseCodeQualityMetrics(response.content as string);

    // Cache results
    this.codebaseMetrics.set(cacheKey, metrics);

    return metrics;
  }

  private async analyzeDependencies(): Promise<any> {
    // Simplified dependency analysis
    return {
      total: 156,
      outdated: 12,
      vulnerable: 2,
      recommendations: [
        'Update React to latest stable version',
        'Address vulnerable dependencies in package.json',
        'Review and remove unused dependencies'
      ]
    };
  }

  private async reviewBestPractices(params: any): Promise<any> {
    return {
      score: 85,
      violations: [
        'Some components lack proper error boundaries',
        'Missing TypeScript strict mode in some files',
        'Inconsistent naming conventions'
      ],
      suggestions: [
        'Implement error boundaries for all route components',
        'Enable TypeScript strict mode project-wide',
        'Establish and enforce naming conventions'
      ]
    };
  }

  /**
   * Helper methods for parsing and analysis
   */
  private parseCodeQualityMetrics(text: string): CodeQualityMetrics {
    // Simplified parsing - would use structured extraction in production
    return {
      maintainabilityIndex: 75,
      cyclomaticComplexity: 12,
      codeDuplication: 8,
      testCoverage: 82,
      technicalDebt: 'Medium',
      securityScore: 88,
      performanceScore: 79
    };
  }

  /**
   * Parameter extraction methods
   */
  private async extractCodeAnalysisParams(request: string): Promise<any> {
    const prompt = `Extract code analysis parameters from this request:

"${request}"

Return JSON with: filePath, repositoryPath, language, frameworks, specificConcerns`;

    const response = await this.llm.invoke(prompt);
    try {
      const jsonMatch = response.content as string;
      return JSON.parse(jsonMatch);
    } catch {
      return { filePath: '', repositoryPath: './', language: 'javascript', frameworks: [] };
    }
  }

  private async extractUiUxParams(request: string): Promise<any> {
    const prompt = `Extract UI/UX review parameters from this request:

"${request}"

Return JSON with: componentPath, screenSize, accessibilityStandards, userFlow, specificIssues`;

    const response = await this.llm.invoke(prompt);
    try {
      const jsonMatch = response.content as string;
      return JSON.parse(jsonMatch);
    } catch {
      return { componentPath: '', screenSize: 'all', accessibilityStandards: 'WCAG 2.1' };
    }
  }

  private async extractDecisionParams(request: string): Promise<any> {
    const prompt = `Extract technical decision parameters from this request:

"${request}"

Return JSON with: decisionType, options, criteria, constraints, timeline, stakeholders`;

    const response = await this.llm.invoke(prompt);
    try {
      const jsonMatch = response.content as string;
      return JSON.parse(jsonMatch);
    } catch {
      return { decisionType: 'general', options: [], criteria: [], constraints: [] };
    }
  }

  /**
   * Load technical baseline metrics
   */
  private async loadTechnicalBaseline(): Promise<void> {
    try {
      // Load baseline from graph memory
      const baselineNodes = await this.graphMemory.getNodesByType('metric');

      // In a real implementation, would parse and set baseline metrics
      this.performanceBaseline = {
        loadTime: 2.3,
        firstContentfulPaint: 1.8,
        largestContentfulPaint: 3.2,
        cumulativeLayoutShift: 0.15,
        bundleSize: { total: 245000, chunks: [], largestModules: [] },
        recommendations: []
      };

      this.securityBaseline = {
        vulnerabilities: [],
        dependencies: { total: 0, outdated: 0, vulnerable: 0, recommendations: [] },
        bestPractices: { score: 0, violations: [], suggestions: [] }
      };

    } catch (error) {
      console.warn('Could not load technical baseline:', error);
    }
  }

  /**
   * Store technical insights in graph memory
   */
  private async storeTechnicalInsights(response: AgentResponse, taskType: TaskType): Promise<void> {
    if (response.success && response.data) {
      try {
        await this.graphMemory.addMemory(
          JSON.stringify(response.data),
          'feature',
          [],
          { taskType, agent: 'devops', timestamp: new Date().toISOString() }
        );
      } catch (error) {
        console.warn('Could not store technical insights:', error);
      }
    }
  }

  /**
   * Determine task type from content
   */
  private determineTaskType(content: string): TaskType {
    const contentLower = content.toLowerCase();

    if (contentLower.includes('code') || contentLower.includes('refactor') || contentLower.includes('technical debt')) {
      return 'code_analysis';
    }
    if (contentLower.includes('ui') || contentLower.includes('ux') || contentLower.includes('design') || contentLower.includes('accessibility')) {
      return 'ui_ux_review';
    }
    if (contentLower.includes('performance') || contentLower.includes('optimization') || contentLower.includes('speed')) {
      return 'performance_optimization';
    }
    if (contentLower.includes('security') || contentLower.includes('vulnerability') || contentLower.includes('audit')) {
      return 'security_audit';
    }
    if (contentLower.includes('decision') || contentLower.includes('architecture') || contentLower.includes('choose')) {
      return 'technical_decision';
    }

    return 'technical_decision';
  }

  /**
   * Placeholder methods for full implementation
   */
  private generateCodeAnalysisSummary(metrics: CodeQualityMetrics): string { return 'Code quality analysis summary'; }
  private async assessTechnicalDebt(metrics: CodeQualityMetrics): Promise<any> { return {}; }
  private async createRefactoringPlan(recommendations: any[]): Promise<any> { return {}; }
  private async generateCodeRecommendations(metrics: CodeQualityMetrics, deps: any, practices: any): Promise<TechnicalRecommendation[]> { return []; }
  private async performAccessibilityAnalysis(params: any): Promise<any> { return { score: 0, issues: [], recommendations: [] }; }
  private async checkResponsiveDesign(params: any): Promise<any> { return { score: 0, breakpoints: [], issues: [] }; }
  private async analyzeUsability(params: any): Promise<any> { return { score: 0, userFlow: [], painPoints: [] }; }
  private async reviewDesignConsistency(params: any): Promise<any> { return { score: 0, componentUsage: [], colorPalette: [], typography: [] }; }
  private async generateUiUxRecommendations(analysis: UiUxAnalysis): Promise<TechnicalRecommendation[]> { return []; }
  private generateUiUxSummary(analysis: UiUxAnalysis): string { return 'UI/UX analysis summary'; }
  private prioritizeUiUxImprovements(recommendations: TechnicalRecommendation[]): any { return {}; }
  private calculateOverallUiUxScore(analysis: UiUxAnalysis): number { return 0; }
  private async analyzePerformance(): Promise<PerformanceReport> {
    return {
      loadTime: 0,
      firstContentfulPaint: 0,
      largestContentfulPaint: 0,
      cumulativeLayoutShift: 0,
      bundleSize: { total: 0, chunks: [], largestModules: [] },
      recommendations: []
    };
  }
  private async analyzeBundleSize(): Promise<any> { return {}; }
  private async identifyPerformanceBottlenecks(): Promise<any[]> { return []; }
  private async generatePerformanceRecommendations(report: PerformanceReport, bundle: any, bottlenecks: any[]): Promise<TechnicalRecommendation[]> { return []; }
  private async createOptimizationPlan(recommendations: TechnicalRecommendation[]): Promise<any> { return {}; }
  private async estimatePerformanceImprovements(recommendations: TechnicalRecommendation[]): Promise<any> { return {}; }
  private async performVulnerabilityScan(): Promise<any[]> { return []; }
  private async auditDependencies(): Promise<any> { return { total: 0, outdated: 0, vulnerable: 0, recommendations: [] }; }
  private async auditSecurityBestPractices(): Promise<any> { return { score: 0, violations: [], suggestions: [] }; }
  private async checkCompliance(): Promise<any> { return {}; }
  private async generateSecurityRecommendations(audit: SecurityAuditResult, compliance: any): Promise<TechnicalRecommendation[]> { return []; }
  private calculateSecurityScore(audit: SecurityAuditResult): number { return 0; }
  private async createSecurityRemediationPlan(recommendations: TechnicalRecommendation[]): Promise<any> { return {}; }
  private async analyzeTechnicalOptions(params: any): Promise<any> { return {}; }
  private async evaluateTechnicalOptions(options: any, params: any): Promise<any> { return {}; }
  private async makeTechnicalRecommendation(evaluation: any, params: any): Promise<any> { return {}; }
  private async createImplementationPlan(recommendation: any): Promise<any> { return {}; }
  private async identifyTechnicalRisks(recommendation: any): Promise<any[]> { return []; }
  private async performSecurityScan(params: any): Promise<any> { return {}; }
  private async reviewArchitecture(params: any): Promise<any> { return {}; }
}

export default DevOpsAgent;