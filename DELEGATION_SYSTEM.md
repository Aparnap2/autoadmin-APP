# AutoAdmin Task Delegation and Communication System

A comprehensive task delegation and communication system that bridges Expo frontend agents (LangGraph.js) with Python deep agents (GitHub Actions) for the AutoAdmin project.

## 🏗️ Architecture Overview

The system consists of several interconnected components:

### Frontend (Expo/LangGraph.js)
- **Task Delegation Service**: Intelligent task classification and routing
- **Communication Protocol Service**: Bidirectional messaging between systems
- **Task Status Tracker**: Real-time progress monitoring and analytics
- **Smart Routing Service**: Load balancing and optimal resource allocation

### Backend (Python/GitHub Actions)
- **Base Agent Framework**: Foundation for all Python deep agents
- **Specialized Agents**: Marketing, Finance, DevOps, and Strategy agents
- **Communication Layer**: Supabase integration for frontend-backend sync
- **Tool Integration**: Web search, social media analysis, competitor analysis

### Infrastructure
- **Supabase**: Real-time database for task coordination and knowledge graph
- **Firebase Firestore**: Message persistence and state synchronization
- **GitHub Actions**: Heavy task processing and computation
- **Webhooks**: Event-driven communication between systems

## 🚀 Quick Start

### Prerequisites

1. **Node.js 18+** and **Python 3.11+**
2. **Expo CLI** for frontend development
3. **GitHub repository** with Actions enabled
4. **Supabase project** for database and real-time features
5. **Firebase project** for Firestore (optional)

### Environment Variables

Create `.env` files in both frontend and backend directories:

#### Frontend (.env)
```bash
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
LLM_BASE_URL=https://api.openai.com/v1

# Supabase Configuration
EXPO_PUBLIC_SUPABASE_URL=your_supabase_url
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Firebase Configuration
EXPO_PUBLIC_FIREBASE_API_KEY=your_firebase_key
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
EXPO_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
```

#### Backend (.env)
```bash
# Core Service Configuration
OPENAI_API_KEY=your_openai_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
TAVILY_API_KEY=your_tavily_api_key

# GitHub Configuration (Optional)
GITHUB_TOKEN=ghp_your_github_token
GITHUB_REPO=your_username/your_repo

# System Configuration
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Installation

1. **Frontend Setup**:
```bash
cd frontend
npm install
# or
pnpm install
```

2. **Backend Setup**:
```bash
cd backend
pip install -e .
# or with uv
uv sync
```

3. **GitHub Secrets**:
Set up repository secrets in GitHub:
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `TAVILY_API_KEY`
- `GITHUB_TOKEN` (with repository access)

### Running the System

1. **Start Frontend**:
```bash
cd frontend
npx expo start
```

2. **Start Backend** (for development):
```bash
cd backend
uv run python main.py
```

3. **Deploy Backend to GitHub Actions**:
- Push to main branch
- GitHub Actions will automatically start the backend agent

## 📋 Usage Guide

### Basic Task Delegation

```typescript
import AutoAdminDelegationService from './services/delegation';

const delegationService = new AutoAdminDelegationService({
  userId: 'user-123',
  sessionId: 'session-456',
  delegation: {
    maxConcurrentTasks: 5,
    enableSmartRouting: true,
    enableLoadBalancing: true,
    // ... other config
  },
  communication: {
    enableRealtime: true,
    // ... other config
  },
  tracking: {
    enableRealtimeUpdates: true,
    // ... other config
  },
  routing: {
    enableLoadBalancing: true,
    enableCostOptimization: true,
    // ... other config
  }
});

// Initialize the service
await delegationService.initialize();

// Submit a task
const task = await delegationService.submitTask(
  'Market Research for AI Tools',
  'Research the current landscape of AI-powered SaaS tools, focusing on pricing models, key features, and market leaders.',
  {
    priority: 'high',
    autoClassify: true,
    metadata: {
      industry: 'Technology',
      geographic_focus: 'global'
    }
  }
);

// Monitor task progress
const status = await delegationService.getTaskStatus(task.id);
console.log('Task status:', status);
```

### Advanced Usage with Custom Routing

```typescript
// Submit with custom routing
const task = await delegationService.submitTask(
  'Complex Financial Analysis',
  'Analyze quarterly financial data and create forecasting models.',
  {
    priority: 'urgent',
    customRouting: {
      target: 'python_agent',
      bypassSmartRouting: true
    },
    deadline: new Date(Date.now() + 2 * 60 * 60 * 1000) // 2 hours
  }
);

// Add event listeners
delegationService.addEventListener('task:completed', (event) => {
  console.log('Task completed:', event.data);
});

delegationService.addEventListener('task:failed', (event) => {
  console.log('Task failed:', event.data);
});
```

### Direct Backend Task Processing

```python
from main import AutoAdminBackend

backend = AutoAdminBackend()
await backend.initialize()

# Process manual task
task_data = {
    "title": "Competitor Analysis",
    "description": "Analyze top 5 competitors in the market",
    "category": "market_research",
    "type": "heavy_task",
    "priority": "high",
    "parameters": {
        "market": "AI SaaS",
        "competitors": ["OpenAI", "Anthropic", "Google", "Microsoft", "Amazon"]
    }
}

result = await backend.handle_manual_task(task_data)
print("Task result:", result)
```

### GitHub Actions Trigger

```bash
# Trigger via API
curl -X POST https://api.github.com/repos/your-username/your-repo/dispatches \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token your-github-token" \
  -d '{
    "event_type": "task_delegation",
    "client_payload": {
      "task_id": "task_123",
      "task_type": "market_research",
      "task_data": "{\"market\": \"AI SaaS\"}",
      "priority": "high"
    }
  }'
```

## 🔧 Configuration Options

### Task Classification

The system automatically classifies tasks into three categories:

#### Light Tasks (Handled by Expo Agents)
- Quick responses and local data analysis
- Simple decision making
- UI/UX reviews
- Basic strategic planning

#### Heavy Tasks (Delegated to Python Agents)
- Comprehensive market research
- Complex financial analysis
- Advanced code generation
- Data processing and computation

#### Hybrid Tasks (Split Between Systems)
- Market analysis with local insights
- Strategic planning with backend research
- Multi-stage workflows

### Routing Rules

Configure intelligent routing rules in the Smart Routing Service:

```typescript
await routingService.updateRoutingRule({
  id: 'complex-research-rule',
  name: 'Complex Research to Python',
  description: 'Route complex research tasks to Python backend',
  priority: 9,
  conditions: [
    { field: 'complexity', operator: 'greater_than', value: 7 },
    { field: 'category', operator: 'equals', value: 'market_research' }
  ],
  actions: [
    { type: 'assign_to', parameters: { agent: 'python_agent' } }
  ],
  enabled: true,
  createdAt: new Date(),
  updatedAt: new Date()
});
```

### Agent Capabilities

Configure agent capabilities for optimal routing:

```typescript
await delegationService.updateAgentCapabilities('marketing-agent-001', {
  agentType: 'marketing',
  capabilities: [
    'market_research',
    'competitor_analysis',
    'trend_identification',
    'social_media_analysis'
  ],
  maxConcurrentTasks: 5,
  currentLoad: 2,
  successRate: 0.92,
  specialties: ['competitive_intelligence', 'market_trends']
});
```

## 📊 Monitoring and Analytics

### System Status

```typescript
const status = await delegationService.getSystemStatus();
console.log('System status:', {
  activeTasks: status.activeTasks,
  successRate: status.successRate,
  agentHealth: status.systemHealth
});
```

### Task Analytics

```typescript
const analytics = await delegationService.getAnalytics({
  start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
  end: new Date()
});

console.log('Performance metrics:', analytics.performance);
console.log('Routing efficiency:', analytics.routing);
```

### Agent Performance

```python
# Backend agent monitoring
agent_status = backend.get_agent_status()
print("Agent performance:", agent_status)
```

## 🔗 API Reference

### Frontend Services

#### AutoAdminDelegationService

**Constructor**: `new AutoAdminDelegationService(config: AutoAdminDelegationConfig)`

**Methods**:
- `initialize()`: Initialize all delegation services
- `submitTask(title, description, options?)`: Submit a new task
- `getTaskStatus(taskId)`: Get comprehensive task status
- `cancelTask(taskId, reason?)`: Cancel a task
- `getSystemStatus()`: Get system health and status
- `getAnalytics(timeRange?)`: Get performance analytics
- `addEventListener(event, listener)`: Add event listener
- `cleanup()`: Clean up resources

#### TaskDelegationService

**Methods**:
- `classifyTask(description, context?)`: Classify task complexity
- `submitTask(title, description, options?)`: Submit task for delegation
- `getTaskStatus(taskId)`: Get task status
- `cancelTask(taskId, reason?)`: Cancel task
- `getActiveTasks()`: Get active tasks

#### CommunicationProtocolService

**Methods**:
- `sendMessage(type, payload, target, options?)`: Send message
- `sendTaskRequest(task, target)`: Send task request
- `sendHandoffRequest(handoff)`: Send handoff request
- `shareContext(context)`: Share context between agents
- `subscribe(eventType, callback, options?)`: Subscribe to events

#### TaskStatusTrackerService

**Methods**:
- `updateProgress(progress)`: Update task progress
- `updateStatus(taskId, status, message, agentId)`: Update status
- `recordResult(result)`: Record task result
- `getProgress(taskId)`: Get task progress
- `getStatusHistory(taskId)`: Get status history
- `getAnalytics(taskId)`: Get task analytics

### Backend Services

#### BaseAgent

**Abstract Methods**:
- `get_agent_capabilities()`: Return agent capabilities
- `get_supported_task_types()`: Return supported task types
- `get_agent_specialties()`: Return agent specialties
- `process_task(task)`: Process a task

**Methods**:
- `start()`: Start the agent
- `stop()`: Stop the agent
- `update_capabilities()`: Update agent capabilities

#### MarketingAgent

**Specialized Methods**:
- `handle_market_research(task)`: Handle market research
- `handle_competitor_analysis(task)`: Handle competitor analysis
- `handle_trend_analysis(task)`: Handle trend analysis
- `handle_customer_analysis(task)`: Handle customer analysis

## 🛠️ Development Guide

### Adding New Agents

1. **Create Agent Class**:
```python
from agents.base_agent import BaseAgent, AgentType, TaskType

class CustomAgent(BaseAgent):
    def __init__(self, supabase_url: str, supabase_key: str, openai_api_key: str):
        super().__init__(
            agent_id="custom-agent-001",
            agent_type=AgentType.STRATEGY,  # Or create new type
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key
        )

    def get_agent_capabilities(self) -> List[str]:
        return ["custom_capability_1", "custom_capability_2"]

    def get_supported_task_types(self) -> List[TaskType]:
        return [TaskType.STRATEGIC_PLANNING]

    def get_agent_specialties(self) -> List[str]:
        return ["custom_specialty"]

    async def process_task(self, task: TaskDelegation) -> TaskResult:
        # Implement custom task processing
        pass
```

2. **Register Agent**:
```python
# In main.py
from agents.custom_agent import CustomAgent

async def initialize_agents(self):
    custom_agent = CustomAgent(
        supabase_url=os.getenv('SUPABASE_URL'),
        supabase_key=os.getenv('SUPABASE_KEY'),
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    self.agents['custom'] = custom_agent
```

### Adding New Tools

1. **Create Tool Class**:
```python
# tools/custom_tool.py
from typing import List, Dict, Any

class CustomTool:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def analyze(self, query: str) -> List[Dict[str, Any]]:
        # Implement tool functionality
        pass
```

2. **Integrate with Agent**:
```python
# In agent class
from tools.custom_tool import CustomTool

def __init__(self, ...):
    # ... existing init code
    self.custom_tool = CustomTool(api_key=os.getenv('CUSTOM_API_KEY'))
```

### Custom Routing Rules

```typescript
await routingService.updateRoutingRule({
  id: 'custom-rule',
  name: 'Custom Routing Rule',
  description: 'Route based on custom criteria',
  priority: 8,
  conditions: [
    { field: 'metadata.department', operator: 'equals', value: 'engineering' },
    { field: 'complexity', operator: 'greater_than', value: 6 }
  ],
  actions: [
    { type: 'assign_to', parameters: { agent: 'devops_agent' } },
    { type: 'set_priority', parameters: { priority: 'high' } }
  ],
  enabled: true,
  createdAt: new Date(),
  updatedAt: new Date()
});
```

## 🔍 Testing

### Frontend Testing

```typescript
// Run tests
cd frontend
npm test

# Run specific test
npm test -- --testNamePattern="TaskDelegationService"
```

### Backend Testing

```bash
# Run tests
cd backend
uv run pytest

# Run specific test
uv run pytest tests/test_agents.py::test_marketing_agent

# Test with coverage
uv run pytest --cov=agents --cov-report=html
```

### Integration Testing

```python
# Test task delegation
python main.py --test-task '{"title": "Test Task", "description": "Test description"}'
```

## 📝 Troubleshooting

### Common Issues

1. **Task Not Processing**:
   - Check agent status: `await delegationService.getSystemStatus()`
   - Verify environment variables
   - Check Supabase connection

2. **Communication Failures**:
   - Verify Firebase configuration
   - Check network connectivity
   - Review message logs

3. **GitHub Actions Issues**:
   - Check workflow logs
   - Verify repository secrets
   - Ensure runner permissions

### Debug Mode

Enable detailed logging:

```typescript
// Frontend
const config = {
  communication: {
    enableRealtime: true
  },
  tracking: {
    enableRealtimeUpdates: true
  }
};
```

```python
# Backend
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deployment

### Frontend Deployment

```bash
# Build for production
cd frontend
expo export --platform web

# Deploy to your preferred hosting
```

### Backend Deployment

The backend automatically deploys via GitHub Actions when pushed to the main branch.

### Environment-Specific Configurations

Create different environment files:
- `.env.development`
- `.env.staging`
- `.env.production`

## 📚 Additional Resources

- [LangGraph.js Documentation](https://langchain-ai.github.io/langgraphjs/)
- [LangGraph.py Documentation](https://langchain-ai.github.io/langgraph/)
- [Supabase Documentation](https://supabase.com/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Expo Documentation](https://docs.expo.dev/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**AutoAdmin** - Intelligent task delegation and communication for modern applications.