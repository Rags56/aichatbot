# AI Knowledge Base Chatbot - Standalone Solution

A standalone, enterprise-grade AI chatbot solution that provides natural language access to organizational knowledge assets using Retrieval-Augmented Generation (RAG) technology.

## Features

- **RAG-based Query Engine**: Retrieval-Augmented Generation ensures all answers are grounded in actual source documents
- **Hybrid Search**: Combines semantic (vector) search and keyword search for optimal retrieval
- **Multi-format Document Support**: PDF, Word, Excel, PowerPoint, Markdown, HTML
- **Conversation Management**: Maintains context across multiple turns
- **Source Citations**: All answers include verifiable source citations
- **Confidence Scoring**: Provides confidence scores with reasoning
- **Enterprise Features**: Plugins, tools, memory management, quality monitoring
- **Real-time Chat Interface**: Modern React-based UI with streaming support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                            │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │  Web Portal  │  │  Admin UI    │                         │
│  └──────┬───────┘  └──────┬───────┘                         │
└─────────┼─────────────────┼──────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼──────────────────────────────────┐
│                    Backend Services Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Document    │  │ Conversation │  │  Integration  │      │
│  │  Service     │  │  Service    │  │  Service     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
┌─────────▼─────────────────▼──────────────────▼──────────────┐
│                    AI Orchestration Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Query       │  │  RAG         │  │  LLM         │      │
│  │  Engine      │  │  Pipeline   │  │  Service     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
┌─────────▼─────────────────▼──────────────────▼──────────────┐
│                    Data & Search Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │ Meilisearch  │  │  Vector DB   │      │
│  │  (Metadata)  │  │ (Keyword)    │  │ (Embeddings) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- PostgreSQL 15+ (with pgvector extension)
- Meilisearch
- Ollama (local LLM server)
- Python 3.11+
- Node.js 18+ (for frontend)

## Quick Start

### 1. Clone and Setup

```bash
cd ai-chatbot-standalone
cp .env.example .env
# Edit .env with your configuration
```

### Single-Container Quick Start (All-in-One)

This builds a single Docker image that includes PostgreSQL, Meilisearch,
and the AI backend, then runs everything with one command.

```bash
docker build --no-cache -f docker/all-in-one.Dockerfile -t ai-chatbot-allinone .
docker run -d --gpus all -p 5000:5000 -p 7700:7700 -p 5432:5432 -p 11434:11434 -e OLLAMA_URL=http://localhost:11434 -e OLLAMA_MODEL=llama3.1:8b -e OLLAMA_EMBEDDING_MODEL=nomic-embed-text -e DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db -e MEILISEARCH_URL=http://localhost:7700 -e MEILISEARCH_KEY=masterKey123 -v ai-chatbot-postgres-data:/var/lib/postgresql/data -v ai-chatbot-meilisearch-data:/var/lib/meilisearch -v ai-chatbot-ollama-data:/root/.ollama --name ai-chatbot-allinone ai-chatbot-allinone

# Alternative (multi-line for Unix/Mac):
# docker run -d -p 5000:5000 -p 7700:7700 -p 5432:5432 -p 11434:11434 \
#   -e OLLAMA_URL=http://localhost:11434 \
#   -e OLLAMA_MODEL=llama3.1:8b \
#   -e OLLAMA_EMBEDDING_MODEL=nomic-embed-text \
#   -e DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db \
#   -e MEILISEARCH_URL=http://localhost:7700 \
#   -e MEILISEARCH_KEY=masterKey123 \
#   -v ai-chatbot-postgres-data:/var/lib/postgresql/data \
#   -v ai-chatbot-meilisearch-data:/var/lib/meilisearch \
#   -v ai-chatbot-ollama-data:/root/.ollama \
#   --name ai-chatbot-allinone ai-chatbot-allinone

# Note: On first startup, Ollama will download the models (this may take several minutes)
# Check logs: docker logs ai-chatbot-allinone
```

Backend health check: `http://localhost:5000/health`

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```env
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/ai_chatbot_db

# AI Service (Ollama)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_KEY=masterKey123

# Backend
BACKEND_CORE_URL=http://localhost:3001
PORT=5000
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL with pgvector
- Meilisearch
- AI Orchestrator Backend (Flask)
- Frontend (if configured)

### 4. Initialize Database

```bash
docker-compose exec postgres psql -U user -d ai_chatbot_db -f /docker-entrypoint-initdb.d/schema.sql
```

### 5. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- API Health Check: http://localhost:5000/health

## Project Structure

```
ai-chatbot-standalone/
├── backend/                 # Python Flask backend service
│   ├── app.py              # Main Flask application
│   ├── ai_service.py       # Core AI service with RAG
│   ├── ai_enterprise.py    # Enterprise features
│   ├── sync_automation.py  # Knowledge sync automation
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/               # React frontend
│   ├── components/         # React components
│   │   └── AIAssistant.tsx # Main chat component
│   ├── pages/              # Page components
│   └── lib/                # API client library
├── database/               # Database schemas
│   ├── schema.sql          # Core schema
│   └── ai_enterprise_schema.sql  # Enterprise features schema
├── docs/                   # Documentation
├── docker/                 # Docker configurations
├── docker-compose.yml      # Docker Compose setup
├── .env.example           # Environment variables template
└── README.md              # This file
```

## API Endpoints

### Chat Endpoints

- `POST /api/ai/chat` - Send a chat message
- `POST /api/ai/query` - Execute a RAG query
- `GET /api/conversations` - Get user conversations
- `GET /api/conversations/:id/messages` - Get conversation messages

### Document Management

- `POST /api/ai/ingest-webhook` - Webhook for document ingestion
- `POST /api/ai/reindex` - Reindex all documents

### Enterprise Features

- `GET /api/ai/plugins` - Get available plugins
- `GET /api/ai/tools` - Get available tools
- `POST /api/ai/tools/:id/execute` - Execute a tool
- `GET /api/ai/memory` - Get conversation memory
- `POST /api/ai/memory` - Save conversation memory

### Admin Endpoints

- `GET /api/ai/admin/datasets` - List datasets
- `POST /api/ai/admin/datasets` - Create dataset version
- `POST /api/ai/admin/documents/:id/validate` - Submit for validation
- `POST /api/ai/admin/documents/:id/approve` - Approve document
- `GET /api/ai/admin/quality` - Get quality metrics
- `POST /api/ai/admin/sync` - Create sync job

## Usage Examples

### Basic Chat Query

```bash
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is our company policy on remote work?",
    "userId": "1"
  }'
```

### RAG Query with Filters

```bash
curl -X POST http://localhost:5000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain the onboarding process",
    "userId": "1",
    "filters": {
      "department": "HR",
      "classification": "internal"
    },
    "topK": 5
  }'
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Configuration

### LLM Provider

The system uses **Ollama** for local LLM inference:

1. **Ollama** (default, local inference)
   - Set `OLLAMA_URL` in `.env` (default: `http://localhost:11434`)
   - Set `OLLAMA_MODEL` for chat (default: `llama3.1:8b`)
   - Set `OLLAMA_EMBEDDING_MODEL` for embeddings (default: `nomic-embed-text`)
   - Models are automatically pulled on first startup
   - For all-in-one Docker, Ollama runs inside the container

### Search Configuration

- **Vector Search Weight**: 60% (semantic)
- **Keyword Search Weight**: 40% (exact match)
- **Top-K Results**: Default 6, configurable per query
- **Chunk Size**: 800 tokens (configurable)
- **Chunk Overlap**: 50 tokens (configurable)

## Security

- **Authentication**: JWT tokens (configure as needed)
- **Access Control**: Document-level permissions
- **Data Encryption**: AES-256 at rest
- **TLS**: All communications encrypted in transit
- **Audit Logging**: All queries logged with metadata

## Monitoring

- Query logs stored in `ai_queries` table
- Quality metrics available via `/api/ai/admin/quality`
- Retrieval debugging via `/api/ai/admin/retrieval-debug/:query_id`

## Troubleshooting

### Backend not starting

- Check database connection in `.env`
- Verify Meilisearch is running
- Check logs: `docker-compose logs backend`

### No search results

- Ensure documents are ingested: `POST /api/ai/reindex`
- Check Meilisearch index: `GET http://localhost:7700/indexes`
- Verify embeddings are generated

### Frontend connection errors

- Verify `NEXT_PUBLIC_API_URL` or `REACT_APP_API_URL` points to backend
- Check CORS settings in `backend/app.py`

## License

[Specify your license here]

## Support

For issues and questions, please open an issue in the repository.
