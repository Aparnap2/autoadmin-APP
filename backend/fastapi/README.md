# AutoAdmin FastAPI Backend

A production-ready, async-first FastAPI backend for AI agent orchestration and intelligent task automation. This backend replaces Netlify Functions with a robust Python architecture designed for scalability and performance.

## 🚀 Features

### Core Architecture
- **Async/First Design**: Built with FastAPI and async patterns for high concurrency
- **Modular Router Structure**: Organized by service domain (agents, AI, memory, webhooks, etc.)
- **Comprehensive Error Handling**: Global exception handlers with structured error responses
- **Rate Limiting**: Token bucket algorithm with Redis backend for distributed applications
- **Structured Logging**: JSON-formatted logs with correlation IDs and performance metrics

### AI/LLM Integration
- **OpenAI Integration**: Full OpenAI API support with chat, completions, and embeddings
- **Vector Search**: In-memory vector store with cosine similarity search
- **Model Management**: Multiple model support with configuration management
- **Streaming Support**: Real-time streaming chat completions

### Agent Orchestration
- **LangGraph Integration**: Agent task orchestration with LangGraph.js compatibility
- **Multi-Agent Support**: Marketing, Finance, DevOps, and Strategy agents
- **Task Management**: Background task processing with Celery and Redis
- **Real-time Monitoring**: Agent status, health checks, and performance metrics

### Memory & Knowledge Graph
- **Firebase Integration**: Firestore for persistent knowledge graph storage
- **Vector Embeddings**: Automatic embedding generation and similarity search
- **Graph Operations**: CRUD operations for nodes, edges, and subgraphs
- **Memory Queries**: Natural language and Cypher query support

### File Management
- **Secure Uploads**: File upload with validation, virus scanning, and encryption
- **Multiple Formats**: Support for documents, images, and data files
- **Metadata Extraction**: Automatic text extraction and metadata analysis
- **Access Control**: Public/private file access with expiring URLs

### Webhook Processing
- **Multi-Platform Support**: GitHub, HubSpot, and custom webhook handlers
- **Event Processing**: Asynchronous webhook processing with retry logic
- **Webhook Subscriptions**: Dynamic subscription management
- **Security**: Signature verification and IP filtering

## 📋 Prerequisites

- Python 3.11+
- Redis (for caching and Celery)
- PostgreSQL (optional, for persistent storage)
- Docker & Docker Compose (recommended for development)

## 🛠️ Installation

### Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd autoadmin-app/backend/fastapi
```

2. **Set up Python environment**
```bash
# Using uv (recommended)
pip install uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your actual values
```

4. **Start Redis and PostgreSQL**
```bash
docker-compose up -d db redis
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the development server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Setup

1. **Build and start all services**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f api
```

### Production Deployment

#### Render Deployment
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set build command: `pip install uv && uv pip install -e .`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`

#### Railway Deployment
1. Connect your GitHub repository to Railway
2. Railway will auto-detect the Python service
3. Configure environment variables
4. Deploy automatically

## 🔧 Configuration

### Required Environment Variables

```bash
# OpenAI API (Required)
OPENAI_API_KEY=sk-your-openai-api-key

# Firebase Configuration (Required)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Private-Key\n-----END PRIVATE KEY-----"
```

### Optional Configuration

See `.env.example` for all available configuration options including:
- Database configuration
- Redis settings
- External service API keys
- Feature flags
- Performance tuning

## 📚 API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Main API Endpoints

#### Agent Services
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}/status` - Get agent status
- `POST /api/v1/agents/{agent_id}/tasks` - Create agent task
- `POST /api/v1/agents/{agent_id}/actions` - Execute agent action

#### AI Services
- `POST /api/v1/ai/chat` - Chat completion
- `POST /api/v1/ai/completions` - Text completion
- `POST /api/v1/ai/embeddings` - Generate embeddings
- `POST /api/v1/ai/vector/search` - Vector similarity search

#### Memory Services
- `POST /api/v1/memory/query` - Query knowledge graph
- `POST /api/v1/memory/create` - Create memory nodes/edges
- `POST /api/v1/memory/export` - Export memory data

#### Webhook Services
- `POST /api/v1/webhooks/github` - GitHub webhook handler
- `POST /api/v1/webhooks/hubspot` - HubSpot webhook handler
- `GET /api/v1/webhooks/config` - List webhook configurations

#### File Management
- `POST /api/v1/files/upload` - Upload files
- `GET /api/v1/files/{file_id}/download` - Download files
- `GET /api/v1/files/` - List files

#### Health & Monitoring
- `GET /health` - System health check
- `GET /monitoring/metrics` - Application metrics
- `GET /monitoring/status/components` - Component status

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests only
pytest -m slow        # Slow tests only
```

### Test Coverage
- Unit tests for core business logic
- Integration tests for API endpoints
- Async test support with pytest-asyncio
- Mock external services for isolated testing

## 📊 Monitoring & Observability

### Health Checks
- `GET /health` - Comprehensive health check
- `GET /health/simple` - Basic health check for load balancers
- `GET /health/readiness` - Kubernetes readiness probe
- `GET /health/liveness` - Kubernetes liveness probe

### Metrics
- Built-in Prometheus metrics
- Custom business metrics
- Performance monitoring
- Resource usage tracking

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Log levels and filtering
- Integration with external log providers

## 🚀 Deployment

### Environment-Specific Configurations

#### Development
- Debug mode enabled
- Auto-reload for code changes
- Mock external services
- Local database and Redis

#### Production
- Optimized Docker images
- Security headers and middleware
- Rate limiting and throttling
- External service integrations

### Cloud Platform Guides

#### Render.com
1. Fork and connect repository
2. Create Web Service
3. Configure environment variables
4. Set health check path: `/health/simple`
5. Deploy automatically on push

#### Railway.app
1. Connect repository
2. Auto-detects Python service
3. Set environment variables
4. Deploy with automatic CI/CD

#### AWS ECS
1. Build and push Docker image
2. Create ECS task definition
3. Configure load balancer
4. Set up auto-scaling

## 🔒 Security

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- API key authentication
- Session management

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration

### Infrastructure Security
- Non-root Docker user
- Security scanning with Bandit
- Dependency vulnerability scanning
- Encrypted data storage

## 📈 Performance

### Optimization Features
- Async/await patterns throughout
- Connection pooling for databases
- Redis caching layer
- Efficient vector operations

### Scaling
- Horizontal scaling support
- Load balancer ready
- Database connection pooling
- Redis cluster support

### Monitoring
- Response time tracking
- Error rate monitoring
- Resource usage metrics
- Custom performance metrics

## 🛠️ Development

### Code Quality
- Black for code formatting
- Ruff for linting and formatting
- MyPy for type checking
- Pre-commit hooks

### Adding New Features
1. Create Pydantic models in `app/models/`
2. Implement business logic in `app/services/`
3. Add API routes in `app/routers/`
4. Write tests in `tests/`
5. Update documentation

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run test suite and ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: See this README and inline API docs
- **Issues**: Create an issue on GitHub
- **Community**: Join our Discord community
- **Support Email**: support@autoadmin.com

## 🔗 Related Projects

- **AutoAdmin Frontend**: React/Next.js frontend application
- **AutoAdmin CLI**: Command-line interface for local development
- **AutoAdmin SDK**: Python SDK for integrating with the backend

---

**Built with ❤️ by the AutoAdmin Team**