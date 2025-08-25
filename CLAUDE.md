# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Document Testing System (AI资料自主测试系统) designed to evaluate documentation quality from a user's perspective, identify issues, and generate structured test reports.

## Architecture

### System Design Pattern
- **Frontend/Backend Separation**: React frontend + FastAPI backend
- **Monolithic Service with Modular Design**: Single deployable unit with clear module boundaries
- **External AI Service Integration**: AI models provided via external API gateway by specialized team
- **Layered Architecture**: Views → Services → Repositories → Models structure in backend

### Technology Stack
- **Frontend**: React 18 + TypeScript + Vite + Ant Design + Zustand + TanStack Query
- **Backend**: FastAPI + Python 3.11 + SQLite + Redis 7
- **Testing**: Vitest + Playwright (Frontend), pytest (Backend)
- **AI Integration**: External AI API Gateway (通用AI API + 结构化AI API)
- **File Processing**: PyPDF2, python-docx, chardet for document parsing
- **Authentication**: JWT + OAuth (Gitee provider)

### Backend Architecture
The backend follows a clean layered architecture:

```
app/
├── views/          # API endpoints (FastAPI routers)
├── services/       # Business logic and external integrations
├── repositories/   # Data access layer
├── models/         # SQLAlchemy ORM models
├── dto/           # Data transfer objects
└── core/          # Configuration and database setup
```

**Key Backend Services:**
- **AI Service Factory**: Manages different AI service providers (OpenAI, mock)
- **Task Processor**: Chain of responsibility pattern for document processing
- **Document Processor**: Handles file parsing and text extraction
- **Issue Detector**: AI-powered quality analysis
- **OAuth Service**: Third-party authentication (Gitee, extensible to others)
- **Analytics Service**: Usage metrics and reporting

### Frontend Architecture
React-based SPA with modular component structure:

```
src/
├── pages/          # Main application pages
├── components/     # Reusable UI components
├── services/       # API clients and business logic
├── hooks/          # Custom React hooks
├── types.ts        # TypeScript type definitions
└── config/         # Application configuration
```

**Key Frontend Features:**
- **TanStack Query**: Server state management
- **Ant Design**: UI component library
- **Playwright E2E**: End-to-end testing
- **Vitest**: Unit testing framework

### Key Modules
1. **User Authentication Module** (用户模块): JWT + OAuth integration for user authentication
2. **Task Management Module** (任务模块): Complete task lifecycle with real-time status updates
3. **File Processing Module** (文件模块): Multi-format document parsing (PDF, DOCX, Markdown)
4. **AI Analysis Module** (AI分析模块): Pluggable AI service providers with retry logic
5. **Report Generation Module** (报告模块): Excel report export with issue categorization
6. **System Management Module** (系统模块): Health checks, monitoring, and analytics

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 14+
- Docker and Docker Compose installed
- AI API credentials (obtained from AI team)

### Quick Start
```bash
# For Windows users
start.bat

# For Linux/Mac users
chmod +x start.sh
./start.sh
```

### Manual Setup
#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend service
python app/main.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start frontend service
npm run dev
```

## Common Commands

### Development Commands
```bash
# Start backend server
cd backend && python app/main.py

# Start frontend development server
cd frontend && npm run dev

# Run backend tests
cd backend && python -m pytest tests/

# Run specific backend test file
cd backend && python -m pytest tests/test_api.py

# Run backend tests with specific marker
cd backend && python -m pytest -m "unit" tests/

# Run frontend unit tests
cd frontend && npm run test:unit

# Run frontend tests with coverage
cd frontend && npm run test:coverage

# Run E2E tests
cd frontend && npm run test:e2e

# Run E2E tests with UI
cd frontend && npm run test:e2e:ui

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Build frontend for production
cd frontend && npm run build

# Preview frontend build
cd frontend && npm run preview
```

### Database Operations
```bash
# The system uses SQLite for development, no separate database setup required
# Database file is located at: ./data/app.db
```

### Testing
```bash
# Run all backend tests
cd backend && python -m pytest tests/

# Run specific test file
cd backend && python -m pytest tests/test_api.py

# Run tests by category
cd backend && python -m pytest -m "unit" tests/          # Unit tests only
cd backend && python -m pytest -m "integration" tests/   # Integration tests only
cd backend && python -m pytest -m "e2e" tests/          # E2E tests only

# Run tests with verbose output
cd backend && python -m pytest tests/ -v

# Run tests with coverage report
cd backend && python -m pytest tests/ --tb=short --disable-warnings

# Frontend testing
cd frontend && npm run test                    # Run unit tests
cd frontend && npm run test:coverage          # Run with coverage
cd frontend && npm run test:e2e              # Run E2E tests
cd frontend && npm run test:e2e:debug        # Debug E2E tests
```

## API Integration

### External AI Service Configuration
The system integrates with external AI services via API Gateway. Configure in `backend/config.yaml`:
```
ai_models:
  default_index: 0
  models:
    - label: "GPT-4o Mini (快速)"
      provider: "openai"
      config:
        api_key: "${OPENAI_API_KEY}"
        base_url: "https://api.openai.com/v1"
        model: "gpt-4o-mini"
```

### Service Selection Strategy
- **Structured API**: Used for document analysis and quality checking tasks
- **General API**: Used for general text processing and long content (>8000 chars)

## Task Processing Workflow

### Static Analysis Workflow (静态检测)
1. **File Parsing**: Extract text from PDF/Word/Markdown files
2. **Text Structuring**: Split content into chunks (default 8000 chars) and extract structure
3. **Quality Analysis**: Analyze grammar, logic, completeness via AI models
4. **Result Validation**: Validate JSON output structure and retry if needed
5. **Report Generation**: Generate structured reports with identified issues

### Dynamic Analysis (动态检测)
Planned feature using MCP+Agent for operational validation (not yet implemented in MVP)

## Data Models

### Core Entities
- **Users**: User authentication and profile data
- **Tasks**: Document testing tasks with status tracking
- **Files**: Uploaded document metadata and storage paths
- **Analysis Results**: AI analysis outputs with confidence scores
- **Issues**: Identified documentation problems
- **User Feedback**: User responses to identified issues (accept/reject/comment)
- **Reports**: Generated test reports

## Important Notes

### AI Service Dependencies
- The system relies on external AI API services maintained by a specialized team
- No local AI model deployment required
- Ensure stable network connection to AI gateway
- Monitor API rate limits and quotas

### File Storage
- Files are stored locally in `./data/uploads/`
- Reports are generated in `./data/reports/`
- Ensure adequate disk space for file storage

### Database Operations
- SQLite stores all persistent data
- Redis handles caching, queues, and session management

### Security Considerations
- All API endpoints require authentication
- SSO integration for enterprise authentication
- File uploads limited to 10MB by default
- Supported formats: PDF, DOCX, Markdown, TXT only

## Code Style and Architecture Patterns

### Backend Patterns
- **Repository Pattern**: All data access goes through repository interfaces
- **Chain of Responsibility**: Task processing uses processor chain pattern
- **Factory Pattern**: AI service providers are created via factory
- **Dependency Injection**: Services injected via FastAPI dependency system
- **DTO Pattern**: Request/response models separate from domain models

### Frontend Patterns  
- **Custom Hooks**: Business logic extracted to reusable hooks
- **Service Layer**: API calls abstracted through service modules
- **Factory Pattern**: Test utilities created through factories
- **Component Composition**: Page components composed from smaller components

### Configuration Management
- **Environment Variables**: Use `${VAR_NAME:default_value}` syntax in config.yaml
- **Multi-environment**: Separate config files (config.yaml, config.blue.yaml, config.test.yaml)
- **Type Safety**: Configuration loaded through Pydantic models

## Development Workflow

### Git 操作
- 本项目每次提交请先创建分支，提交本次更新至远端仓库，合入到main分支
- 分支命名规范: `feature/`, `fix/`, `refactor/`, `test/`

### 任务处理
- 所有回答通过中文进行回复
- 任务创建的临时测试脚本统一放到tmp目录中，任务结束时请清理
- 使用pytest标记系统组织测试: `@pytest.mark.unit`, `@pytest.mark.integration`

### Testing Strategy
- **Backend**: pytest with fixtures, mock services, database isolation
- **Frontend**: Vitest for unit tests, Playwright for E2E tests
- **Test Categories**: unit, integration, e2e, security, performance markers
- **Coverage Thresholds**: Frontend 80% line coverage, Backend comprehensive test suite