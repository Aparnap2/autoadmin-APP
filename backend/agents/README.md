# AutoAdmin Deep Agents System

A comprehensive hierarchical agent system built with LangGraph for automating business operations, research, and development tasks.

## 🚀 Features

### **Hierarchical Agent Architecture**
- **CEO Agent**: Central orchestrator for strategic decision-making and task delegation
- **Strategy Agent (CMO/CFO)**: Market research, financial analysis, and strategic planning
- **DevOps Agent (CTO)**: Code management, GitHub operations, and technical architecture

### **Core Capabilities**
- **Shared Graph Memory**: Knowledge graph storage using Supabase with vector search
- **Virtual File System**: Persistent file storage across agent runs
- **External Integrations**: Tavily search, GitHub operations, and more
- **TDD-Powered**: Comprehensive pytest test suite with 90%+ coverage

### **Execution Environments**
- **GitHub Actions**: Autonomous execution in CI/CD pipelines
- **Docker**: Containerized deployment for any environment
- **Local Development**: Easy setup with Docker Compose

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CEO Agent     │───▶│ Strategy Agent   │───▶│   DevOps Agent  │
│ (Orchestrator)  │    │  (CMO/CFO)       │    │    (CTO)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │            Shared Memory Systems                 │
         │  ┌─────────────┐    ┌─────────────────────┐     │
         │  │Graph Memory │    │ Virtual File System │     │
         │  │(Supabase)   │    │   (Supabase)        │     │
         │  └─────────────┘    └─────────────────────┘     │
         └─────────────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Supabase account & project
- OpenAI API key
- (Optional) GitHub personal access token
- (Optional) Tavily search API key

### Quick Start

1. **Clone and Setup**
```bash
git clone <repository-url>
cd autoadmin-app/backend
cp .env.example .env
# Edit .env with your API keys
```

2. **Install Dependencies**
```bash
# Using uv (recommended)
pip install uv
uv sync

# Or using pip
pip install -r requirements.txt
```

3. **Run Agents**
```bash
# Proactive analysis mode
python agents/main.py --mode proactive

# Interactive mode
python agents/main.py --mode interactive --message "Research AI automation trends"

# Task mode
python agents/main.py --mode task --task-type strategy --task-description "Analyze market opportunities"
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or use Docker directly
docker build -t autoadmin-agents .
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY -e SUPABASE_URL=$SUPABASE_URL -e SUPABASE_KEY=$SUPABASE_KEY autoadmin-agents
```

## 🔧 Configuration

### Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key for LLM operations
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anonymous key

Optional:
- `GITHUB_TOKEN`: GitHub personal access token for DevOps operations
- `TAVILY_API_KEY`: Tavily search API key for market research
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT`: Environment (development, staging, production)

### Supabase Setup

Create the following tables in your Supabase project:

```sql
-- Graph Memory Tables
CREATE TABLE nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type text NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz
);

CREATE TABLE edges (
  source_id uuid REFERENCES nodes(id),
  target_id uuid REFERENCES nodes(id),
  relation text NOT NULL,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (source_id, target_id)
);

-- Virtual File System
CREATE TABLE agent_files (
  path text PRIMARY KEY,
  content text NOT NULL,
  content_type text DEFAULT 'text/plain',
  last_modified timestamptz DEFAULT now()
);

-- Task Management
CREATE TABLE tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_type text NOT NULL,
  description text NOT NULL,
  parameters jsonb,
  status text DEFAULT 'pending',
  result text,
  error text,
  created_at timestamptz DEFAULT now()
);
```

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Slow tests only
```

### Test Coverage

- **Unit Tests**: 95%+ coverage of core functionality
- **Integration Tests**: End-to-end agent workflows
- **Performance Tests**: Agent response time and resource usage
- **Security Tests**: Vulnerability scanning and security validation

## 📊 Usage Examples

### Market Research

```python
from agents import AutoAdminAgents

# Initialize the system
agents = AutoAdminAgents()
await agents.initialize()

# Research AI automation trends
result = await agents.create_task(
    task_type="strategy",
    description="Research AI automation market trends for Q4 planning",
    parameters={"industry": "technology", "depth": "comprehensive"}
)
```

### Code Generation

```python
# Generate API endpoint code
result = await agents.create_task(
    task_type="devops",
    description="Create a RESTful API for user management",
    parameters={
        "requirements": "CRUD operations for users",
        "file_type": "python",
        "repo": "myproject/backend"
    }
)
```

### Daily Proactive Analysis

```python
# Run morning briefing
result = await agents.run_proactive_analysis()
print(result["response"])
```

## 🔄 GitHub Actions Integration

The system is designed to run autonomously in GitHub Actions:

### Automatic Triggers
- **Daily**: Runs at 9 AM UTC for proactive analysis
- **Manual**: Trigger via workflow dispatch
- **API**: Trigger via repository dispatch

### Example Workflow Trigger

```bash
# Trigger from external system
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/dispatches \
  -d '{"event_type":"start_task","client_payload":{"mode":"proactive"}}'
```

## 📈 Monitoring & Observability

### Health Checks
- Container health monitoring
- Agent response time tracking
- Error rate monitoring
- Resource usage metrics

### Logging
- Structured JSON logging
- Configurable log levels
- Integration with external logging services

### Performance Metrics
- Agent execution time
- Memory usage patterns
- API response times
- Task completion rates

## 🔒 Security

### Best Practices
- Non-root Docker containers
- Environment variable encryption
- API key rotation
- Input validation and sanitization
- Rate limiting and DDoS protection

### Compliance
- GDPR-compliant data handling
- SOC 2-ready controls
- Security scanning in CI/CD
- Vulnerability management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Install development dependencies
uv sync --group dev

# Run pre-commit hooks
pre-commit run --all-files

# Run type checking
mypy agents/

# Run code formatting
black agents/
ruff check agents/
```

## 📚 Documentation

- [API Reference](./docs/api.md)
- [Agent Architecture](./docs/architecture.md)
- [Deployment Guide](./docs/deployment.md)
- [Troubleshooting](./docs/troubleshooting.md)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed with `uv sync`
2. **API Key Errors**: Verify environment variables are set correctly
3. **Database Connection**: Check Supabase URL and credentials
4. **Memory Issues**: Increase container memory limits for large operations

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python agents/main.py --mode proactive
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the agent framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) for hierarchical orchestration
- [Supabase](https://supabase.com/) for database and storage
- [Tavily](https://tavily.com/) for search capabilities
- [OpenAI](https://openai.com/) for LLM services

## 📞 Support

- 📧 Email: team@autoadmin.com
- 💬 Discord: [Join our community](https://discord.gg/autoadmin)
- 🐛 Issues: [GitHub Issues](https://github.com/autoadmin/agents/issues)
- 📖 Documentation: [AutoAdmin Docs](https://docs.autoadmin.com)