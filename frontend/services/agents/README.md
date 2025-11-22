# AutoAdmin Agent System

A comprehensive client-side LangGraph.js 3-agent swarm hierarchy built for the AutoAdmin app. This system provides intelligent automation with fast, responsive client-side processing and strategic delegation to backend services.

## Architecture Overview

```
┌─────────────────┐
│   CEO Agent     │ ◄─── Main Orchestrator
│   (Supervisor)  │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
┌───▼───┐   ┌───▼───┐
│Strategy│   │DevOps │
│Agent  │   │Agent  │
│(CMO/  │   │(CTO)  │
│CFO)   │   │       │
└───────┘   └───────┘
```

## Features

### 🚀 **3-Agent Hierarchy**
- **CEO Agent**: Main orchestrator and decision maker
- **Strategy Agent (CMO/CFO)**: Market research, financial analysis, business strategy
- **DevOps Agent (CTO)**: Code analysis, UI/UX review, technical decisions

### ⚡ **Performance Optimized**
- Client-side processing for immediate responses
- React Native Worklets for heavy computations
- Intelligent task delegation to GitHub Actions when needed
- Streaming responses for large operations

### 🧠 **Smart Memory**
- Supabase Graph Memory for shared knowledge
- Semantic search and relationship tracking
- Learning patterns and business context retention
- Real-time knowledge sharing between agents

### 📁 **Virtual File System**
- Sandbox environment for agents
- Persistent file storage with Supabase
- Real-time file operations and watching
- Code, data, and document management

### 🔄 **Real-time Sync**
- Firebase real-time integration
- Live agent status updates
- Collaborative session management
- Push notifications for task completion

## Quick Start

### Basic Usage

```typescript
import { useAutoAdminAgents } from '../hooks/useAutoAdminAgents';

function MyComponent() {
  const {
    sendMessage,
    isInitialized,
    isLoading,
    conversationHistory,
    metrics
  } = useAutoAdminAgents({
    userId: 'user-123',
    enableStreaming: true,
    enableRealtimeSync: true
  });

  const handleUserMessage = async (message: string) => {
    const response = await sendMessage(message);
    console.log('Agent response:', response);
  };

  return (
    <div>
      <button onClick={() => handleUserMessage('Analyze our SaaS market position')}>
        Get Market Analysis
      </button>
    </div>
  );
}
```

### Advanced Setup

```typescript
import { createAgentSystem } from '../services/agents';

const orchestrator = createAgentSystem('user-123', {
  sessionConfig: {
    maxSessionDuration: 120,
    enableRealtimeSync: true
  },
  agentConfigs: {
    ceo: {
      model: 'gpt-4o-mini',
      temperature: 0.3,
      delegationRules: [
        {
          condition: 'market research OR financial analysis',
          targetAgent: 'strategy',
          threshold: { complexity: 6 }
        }
      ]
    }
  }
});

await orchestrator.initialize();

const response = await orchestrator.processUserMessage(
  'Research our competitive landscape'
);
```

## Agent Capabilities

### CEO Agent (Main Orchestrator)
- **Task Delegation**: Routes requests to appropriate agents
- **Decision Making**: Handles vs delegates complex tasks
- **Virtual FileSystem Management**: Coordinates file operations
- **Session Management**: Maintains conversation state
- **Performance Monitoring**: Tracks agent metrics and performance

### Strategy Agent (CMO/CFO)
- **Market Research**: Trend analysis, competitive intelligence
- **Financial Analysis**: Budget optimization, revenue projections
- **Strategic Planning**: Business growth strategies, market positioning
- **Risk Assessment**: Market risks, financial implications
- **Business Intelligence**: Data-driven insights and recommendations

### DevOps Agent (CTO)
- **Code Analysis**: Quality metrics, best practices review
- **UI/UX Review**: Accessibility, responsive design, consistency
- **Performance Optimization**: Bundle analysis, rendering optimization
- **Security Audit**: Vulnerability scanning, dependency analysis
- **Technical Architecture**: System design recommendations

## File Structure

```
services/agents/
├── types.ts                    # Core type definitions
├── base-agent.ts              # Base agent class
├── ceo-agent.ts              # CEO agent implementation
├── strategy-agent.ts         # Strategy agent implementation
├── devops-agent.ts           # DevOps agent implementation
├── agent-orchestrator.ts     # Main orchestrator
├── virtual-filesystem.ts     # Virtual file system
├── graph-memory-integration.ts # Supabase memory integration
├── firebase-realtime-integration.ts # Firebase real-time sync
├── worklets-optimized.ts     # Performance optimization
├── index.ts                  # Main exports
└── __tests__/
    ├── basic-validation.test.js
    ├── agent-system.test.ts
    └── integration.test.js
```

## Performance Features

### Worklets Integration
- Heavy computations moved to background threads
- UI remains responsive during agent processing
- Chunked processing for large operations
- Streaming responses for real-time feedback

### Smart Delegation
- Automatic backend delegation for complex tasks
- Complexity-based routing decisions
- Resource usage optimization
- Timeout and retry mechanisms

### Memory Optimization
- Efficient caching strategies
- Lazy loading of agent capabilities
- Resource cleanup and garbage collection
- Memory usage monitoring

## Configuration Options

### Agent Configuration
```typescript
interface AgentConfig {
  id: string;
  name: string;
  type: 'ceo' | 'strategy' | 'devops';
  model: string;
  temperature: number;
  maxTokens?: number;
  tools: AgentTool[];
  systemPrompt: string;
  delegationRules: DelegationRule[];
}
```

### Performance Settings
```typescript
interface WorkletAgentConfig {
  useWorklets: boolean;
  maxWorkletConcurrency: number;
  enableStreaming: boolean;
  chunkSize: number;
}
```

### Real-time Configuration
```typescript
interface RealtimeConfig {
  enabled: boolean;
  channels: string[];
  syncStrategy: 'optimistic' | 'pessimistic';
  conflictResolution: 'last_write_wins' | 'merge';
}
```

## Testing

Run the test suite:
```bash
npm test
```

Run specific tests:
```bash
npm test basic-validation.test.js
npm test agent-system.test.ts
```

## Examples

### Market Research Request
```typescript
const response = await sendMessage(
  'Research the SaaS market for small businesses in 2024'
);
// Routes to Strategy Agent
// Returns: Market trends, competitive analysis, recommendations
```

### Code Analysis Request
```typescript
const response = await sendMessage(
  'Review this React component for performance and accessibility'
);
// Routes to DevOps Agent
// Returns: Code metrics, optimization suggestions, best practices
```

### Financial Analysis Request
```typescript
const response = await sendMessage(
  'Analyze our burn rate and suggest optimization strategies'
);
// Routes to Strategy Agent
// Returns: Financial insights, cost-saving opportunities, projections
```

## Integration Points

### Supabase Integration
- Graph memory for knowledge sharing
- Vector similarity search
- File persistence
- Real-time collaboration

### Firebase Integration
- Real-time session sync
- Push notifications
- Authentication and user management
- Analytics and monitoring

### GitHub Actions Integration
- Heavy computational tasks
- Long-running processes
- Batch data processing
- External API integrations

## Monitoring and Analytics

### Agent Metrics
- Total tasks processed
- Success rate and error tracking
- Average response time
- Delegation rate
- Resource usage

### Performance Metrics
- CPU and memory usage
- Worklet concurrency
- Queue length and throughput
- File system operations

### Business Metrics
- Task completion rate
- User satisfaction
- Feature usage patterns
- ROI calculations

## Best Practices

### Performance
- Enable worklets for heavy computations
- Use streaming for large responses
- Monitor memory usage in long sessions
- Clean up resources properly

### Security
- Validate all user inputs
- Sanitize file system operations
- Use proper authentication
- Monitor for abuse patterns

### Reliability
- Implement proper error handling
- Use retry mechanisms
- Monitor system health
- Provide fallback options

## Troubleshooting

### Common Issues
1. **Agent not responding**: Check initialization and API keys
2. **Slow performance**: Enable worklets and check resource usage
3. **Memory issues**: Clear conversation history periodically
4. **Sync problems**: Verify Firebase/Supabase configuration

### Debug Mode
```typescript
const orchestrator = createAgentSystem('user-123', {
  performanceConfig: {
    enableWorklets: false, // Disable for debugging
    enableStreaming: false
  }
});
```

## Contributing

1. Follow the existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Use TypeScript strictly
5. Consider performance implications

## License

This project is part of the AutoAdmin ecosystem and follows the same licensing terms.