# AutoAdmin API Client Services

This directory contains the API client services for connecting the AutoAdmin frontend to the FastAPI backend, providing seamless integration between local agent orchestration and backend task management.

## Architecture Overview

The API system consists of three main layers:

1. **FastAPI Client** (`fastapi-client.ts`) - Low-level HTTP/WebSocket client
2. **Agent API Service** (`agent-api.ts`) - High-level task and agent operations
3. **Task Manager Hook** (`hooks/useTaskManager.ts`) - React hook integration

## Key Features

### 🔄 Dual-Mode Operation
- **Backend Mode**: Full integration with FastAPI backend for production
- **Local Mode**: Fallback to local agent system when backend is unavailable
- **Auto-failover**: Seamless switching between modes

### ⚡ Real-time Updates
- WebSocket connections for live task updates
- Automatic synchronization between local and backend state
- Optimistic updates with conflict resolution

### 🎯 Type Safety
- Full TypeScript support
- Generated types from backend Pydantic models
- Compile-time error checking

### 🚀 Performance
- Intelligent caching strategies
- Request batching and deduplication
- Background synchronization

## Getting Started

### Basic Usage

```typescript
import { getAgentAPIService } from '@/services/api/agent-api';
import { useTaskManager } from '@/hooks/useTaskManager';

// Initialize the task manager
const taskManager = useTaskManager({
  userId: 'user-123',
  syncWithBackend: true,
  autoSyncInterval: 30000,
});

// Create a task
const task = await taskManager.createBackendTask({
  type: 'market_research',
  description: 'Analyze Q4 market trends',
  priority: 'high'
});

// Execute with tracking
const response = await taskManager.executeTaskWithTracking(
  'Research competitor pricing strategies',
  'market_research'
);
```

### Configuration

```typescript
const client = new FastAPIClient({
  baseURL: 'http://localhost:8000', // Backend URL
  timeout: 30000,                  // Request timeout
  retryAttempts: 3,                // Retry failed requests
  enableWebSocket: true,           // Enable real-time updates
  apiKey: 'your-api-key'          // Authentication token
});
```

## API Services

### FastAPI Client

Low-level HTTP client with built-in retry logic and WebSocket support.

```typescript
import { getFastAPIClient } from '@/services/api/fastapi-client';

const client = getFastAPIClient({
  baseURL: 'https://api.autoadmin.com'
});

// Health check
const health = await client.healthCheck();

// Agent operations
const agents = await client.getAgents();
const agent = await client.getAgent('agent-123');

// Task operations
const tasks = await client.getTasks({ status: 'pending' });
const task = await client.createTask(taskData);
```

### Agent API Service

High-level service for agent and task management with caching.

```typescript
import { getAgentAPIService } from '@/services/api/agent-api';

const service = getAgentAPIService({
  syncWithBackend: true,
  enableRealTimeUpdates: true
});

// Task management
const tasks = await service.getTasks({
  status: ['pending', 'processing'],
  type: ['market_research', 'financial_analysis']
});

const task = await service.createTask({
  type: 'market_research',
  description: 'Research new markets',
  priority: 'high'
});

// Agent management
const agents = await service.getAgents();
const status = await service.getAgentStatus('agent-123');

// Analytics
const stats = await service.getTaskStats();
console.log(`Success rate: ${stats.successRate}%`);
```

## Task Manager Hook

React hook that integrates local agent system with backend API.

```typescript
import { useTaskManager } from '@/hooks/useTaskManager';

function TaskManagerComponent() {
  const taskManager = useTaskManager({
    userId: 'user-123',
    syncWithBackend: true,
    autoSyncInterval: 30000, // 30 seconds
    onError: (error) => console.error('Task manager error:', error)
  });

  const {
    // Local agent system
    agents,

    // Backend state
    backendTasks,
    backendStats,
    backendConnected,

    // Unified state
    allTasks,
    unifiedStats,

    // Operations
    createBackendTask,
    cancelBackendTask,
    executeTaskWithTracking,
    syncLocalToBackend
  } = taskManager;

  return (
    <div>
      <div>Status: {backendConnected ? 'Backend' : 'Local'}</div>
      <div>Total Tasks: {unifiedStats.totalTasks}</div>
      <div>Success Rate: {unifiedStats.successRate}%</div>
    </div>
  );
}
```

## WebSocket Events

The system supports real-time updates through WebSocket connections:

```typescript
// Connect to WebSocket
await client.connectWebSocket();

// Listen for task updates
client.addWebSocketListener('task_update', (data) => {
  console.log('Task updated:', data);
});

// Listen for agent status updates
client.addWebSocketListener('agent_status', (data) => {
  console.log('Agent status:', data);
});

// Listen for system notifications
client.addWebSocketListener('system_notification', (data) => {
  console.log('System notification:', data);
});
```

## Error Handling

The API services include comprehensive error handling:

```typescript
try {
  const task = await service.createTask(taskData);
} catch (error) {
  if (error.message.includes('ECONNREFUSED')) {
    console.log('Backend unavailable, using local agents');
    // Fallback to local processing
  } else if (error.message.includes('401')) {
    console.log('Authentication required');
    // Handle auth error
  } else {
    console.error('Unexpected error:', error);
    // Handle other errors
  }
}
```

## Caching Strategy

The system implements intelligent caching:

1. **Memory Cache**: Tasks and agents are cached in memory for fast access
2. **Real-time Updates**: WebSocket connections keep cache up-to-date
3. **Background Sync**: Periodic synchronization ensures data consistency
4. **Cache Invalidation**: Automatic invalidation when data changes

## Performance Optimization

### Request Deduplication

```typescript
// Multiple identical requests are deduplicated
const task1 = await service.getTask('task-123');
const task2 = await service.getTask('task-123'); // Returns cached result
```

### Batch Operations

```typescript
// Batch multiple operations
const tasks = await Promise.all([
  service.getTask('task-1'),
  service.getTask('task-2'),
  service.getTask('task-3')
]);
```

### Background Processing

```typescript
// Configure background sync
const service = getAgentAPIService({
  enableRealTimeUpdates: true,
  autoSyncInterval: 30000 // Sync every 30 seconds
});
```

## Security

### Authentication

```typescript
const client = new FastAPIClient({
  apiKey: 'your-jwt-token'
});

// Token is automatically included in all requests
```

### CORS Configuration

```typescript
// Backend CORS is configured for your frontend domain
app.add_middleware(
  CORSMiddleware,
  allow_origins=['https://your-frontend.com'],
  allow_credentials=True
);
```

## Development

### Running Tests

```bash
# Run API client tests
npm test services/api/

# Run with coverage
npm run test:coverage
```

### Mock Backend

For development without a running backend:

```typescript
import { MockFastAPIClient } from '@/services/api/mock-client';

const mockClient = new MockFastAPIClient();
// Use mockClient instead of real client for testing
```

### Type Generation

Types are generated from backend Pydantic models:

```bash
# Generate TypeScript types from backend
npm run generate-types
```

## Production Deployment

### Environment Variables

```env
REACT_APP_API_BASE_URL=https://api.autoadmin.com
REACT_APP_WS_URL=wss://api.autoadmin.com/ws
REACT_APP_API_KEY=your-production-api-key
```

### Monitoring

```typescript
// Enable performance monitoring
const service = getAgentAPIService({
  enableMetrics: true,
  onMetric: (metric) => {
    // Send to your monitoring service
    analytics.track('api_metric', metric);
  }
});
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check backend URL and network connectivity
2. **Authentication Error**: Verify API key and user permissions
3. **Sync Issues**: Check WebSocket connection status
4. **Performance**: Reduce auto-sync interval or disable real-time updates

### Debug Mode

```typescript
// Enable debug logging
const client = new FastAPIClient({
  debug: true
});

console.log('Debug info:', client.getDebugInfo());
```

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure backward compatibility

## License

This API client system is part of the AutoAdmin project and follows the same licensing terms.