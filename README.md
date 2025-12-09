# AutoAdmin App

A comprehensive administrative automation platform built with modern technologies.

## Overview

AutoAdmin is a full-stack application designed to streamline administrative tasks through intelligent automation, multi-agent orchestration, and real-time collaboration features.

## Tech Stack

### Backend
- **Python 3.12+** with FastAPI
- **LangGraph** for multi-agent orchestration
- **PostgreSQL** for relational data
- **Redis** for caching and session management
- **Docker** for containerization

### Frontend
- **React + TypeScript** with Vite
- **TanStack Query** for data fetching
- **TanStack Router** for routing
- **Tailwind CSS** for styling
- **Expo** for mobile deployment

### Key Features
- 🤖 Multi-agent AI orchestration
- 📊 Real-time business intelligence dashboard
- 🔄 HTTP streaming and polling systems
- 📱 Cross-platform mobile support
- 🔐 Secure authentication and authorization
- 📈 Performance monitoring and analytics

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker and Docker Compose
- pnpm (for frontend)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Aparnap2/autoadmin-APP.git
cd autoadmin-APP
```

2. Backend setup:
```bash
cd backend
uv sync
```

3. Frontend setup:
```bash
cd frontend
pnpm install
```

### Environment Configuration

Create environment files based on the examples:
- `backend/.env`
- `frontend/.env`

### Running the Application

1. Start backend services:
```bash
cd backend
uv run python main.py
```

2. Start frontend:
```bash
cd frontend
pnpm start
```

## Architecture

The application follows a microservices architecture with:
- **Agent System**: LangGraph-based multi-agent coordination
- **API Layer**: FastAPI with async support
- **Frontend**: React with real-time updates
- **Database**: PostgreSQL with Redis caching
- **Monitoring**: Comprehensive logging and metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please use the GitHub issue tracker.