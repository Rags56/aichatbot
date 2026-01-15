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
- **Ollama** (for local LLM - included in Docker setup)
- Python 3.11+
- Node.js 18+ (for frontend)
- **Hardware**: 8GB+ RAM (16GB+ recommended), GPU optional but recommended

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

**Note**: This setup now uses local Llama models via Ollama. See [Local LLM Setup Guide](docs/LOCAL_LLM_SETUP.md) for details.

```bash
docker build -f docker/all-in-one.Dockerfile -t ai-chatbot-allinone .
docker run -d -p 5000:5000 -p 7700:7700 -p 5432:5432 \
  -e OLLAMA_URL=http://localhost:11434 \
  -e LLM_MODEL=llama3.1:8b \
  --name ai-chatbot-allinone ai-chatbot-allinone
```

Backend health check: `http://localhost:5000/health`

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```env
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/ai_chatbot_db

# Local LLM (Ollama)
OLLAMA_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=llama3.1:8b

# Meilisearch
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_KEY=masterKey123

# Backend
BACKEND_CORE_URL=http://localhost:3001
PORT=5000
```

**Note**: See [Local LLM Setup Guide](docs/LOCAL_LLM_SETUP.md) for model selection and setup.

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL with pgvector
- Meilisearch
- **Ollama** (local LLM server)
- AI Orchestrator Backend (Flask)
- Frontend (if configured)

### 4. Pull Llama Model

After services start, pull the Llama model:

```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b
```

For faster performance on CPU, use a quantized model:
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b-instruct-q4_0
```

### 5. Initialize Database

```bash
docker-compose exec postgres psql -U user -d ai_chatbot_db -f /docker-entrypoint-initdb.d/schema.sql
```

### 6. Access the Application

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

The system now uses **local Llama models via Ollama** by default. No API keys required!

**Setup Options:**

1. **Docker (Recommended)**
   - Ollama is included in `docker-compose.yml`
   - Pull models: `docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b`
   - Configure in `.env`: `LLM_MODEL=llama3.1:8b`

2. **Local Ollama Installation**
   - Install: `curl -fsSL https://ollama.com/install.sh | sh`
   - Start: `ollama serve`
   - Pull model: `ollama pull llama3.1:8b`
   - Configure: `OLLAMA_URL=http://localhost:11434`

**Available Models:**
- `llama3.1:8b` - Best quality (~4.7GB)
- `llama3.1:8b-instruct-q4_0` - Quantized, faster (~4.6GB)
- `llama3.2:3b` - Smaller, faster (~2GB)

See [Local LLM Setup Guide](docs/LOCAL_LLM_SETUP.md) for detailed instructions.

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
