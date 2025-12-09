# AutoAdmin Maestro E2E Tests

This directory contains comprehensive end-to-end tests for the AutoAdmin application using Maestro. The tests validate the complete PRD functionality including agent interactions, business intelligence, task delegation, and real-time streaming.

## Test Structure

```
.maestro/
├── README.md                    # This file
├── config                       # Test configuration
│   └── test_config.yaml         # Test configuration
├── flows                        # Test flows
│   ├── agent-chat/              # Agent interaction tests
│   ├── business-intelligence/   # BI feature tests
│   ├── task-delegation/         # Task management tests
│   └── integration/             # End-to-end integration tests
└── utils                        # Utility functions
    └── helpers.yaml             # Common test helpers
```

## Test Categories

### 1. Agent Chat Tests
- **Real-time chat with CEO agent**
- **Strategy agent market analysis**
- **DevOps agent system health checks**
- **Agent switching functionality**
- **Quick action buttons**
- **Streaming responses**

### 2. Business Intelligence Tests
- **Morning briefing generation**
- **Revenue intelligence analysis**
- **KPI dashboard validation**
- **Competitive intelligence**
- **Strategic recommendations**

### 3. Task Delegation Tests
- **Task creation and assignment**
- **Task status tracking**
- **Multi-agent coordination**
- **Task completion validation**
- **Error handling**

### 4. Integration Tests
- **Complete workflow testing**
- **Cross-feature integration**
- **Performance validation**
- **Real-time streaming**
- **HTTP-only communication**

## Running Tests

### Individual Tests
```bash
maestro test agent-chat-ceo-chat.yaml
maestro test business-intelligence-morning-briefing.yaml
```

### All Tests in Category
```bash
maestro test agent-chat/
maestro test business-intelligence/
```

### All Tests
```bash
maestro test .
```

## Test Prerequisites

1. **Backend running** on port 8000
2. **Firebase authentication** configured
3. **Algion LLM API** accessible
4. **Android emulator** running (for React Native)

## Key Features Tested

### Agent Orchestration
- Swarm agent initialization
- Agent health monitoring
- Inter-agent communication
- Task delegation workflows

### Real-time Features
- HTTP streaming responses
- Server-Sent Events (SSE)
- Long polling mechanisms
- Status updates

### Business Intelligence
- Morning briefing generation
- Revenue analysis
- Market intelligence
- KPI calculations

### Task Management
- Task creation
- Progress tracking
- Multi-agent execution
- Result aggregation

## Test Data

Tests use realistic business scenarios:
- CEO status updates
- Marketing campaign analysis
- System health monitoring
- Strategic planning
- Performance optimization

## Troubleshooting

1. **Backend not responding**: Check if FastAPI server is running on port 8000
2. **Agent initialization fails**: Verify Algion API key configuration
3. **Firebase auth errors**: Ensure Firebase project is properly configured
4. **Streaming issues**: Check network connectivity and backend streaming endpoints