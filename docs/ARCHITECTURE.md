# AI Chatbot Architecture

## Overview

The AI Knowledge Base Chatbot is built using a microservices architecture with the following key components:

## Components

### 1. Backend Service (`backend/`)

**Technology**: Python 3.11+, Flask, FastAPI (optional)

**Key Files**:
- `app.py`: Main Flask application with API endpoints
- `ai_service.py`: Core AI service implementing RAG pipeline
- `ai_enterprise.py`: Enterprise features (plugins, tools, memory)
- `sync_automation.py`: Knowledge synchronization automation

**Responsibilities**:
- Handle HTTP requests
- Process queries through RAG pipeline
- Manage document ingestion and indexing
- Integrate with local LLM via Ollama (Llama models)
- Maintain conversation context
- Enforce access controls

### 2. Frontend (`frontend/`)

**Technology**: React 18, TypeScript, Next.js (optional)

**Key Files**:
- `components/AIAssistant.tsx`: Main chat interface component
- `pages/AIAssistantPage.tsx`: Page wrapper
- `lib/api.ts`: API client library

**Responsibilities**:
- Provide user interface for chat
- Display messages, sources, and confidence scores
- Handle real-time updates
- Manage conversation state

### 3. Database Layer (`database/`)

**Technology**: PostgreSQL 15+ with pgvector extension

**Key Tables**:
- `kb_documents`: Document metadata
- `kb_chunks`: Text chunks from documents
- `kb_embeddings`: Vector embeddings (pgvector)
- `ai_queries`: Query audit log
- `ai_conversations`: Conversation management
- `ai_messages`: Message history

**Responsibilities**:
- Store document metadata
- Store vector embeddings
- Maintain conversation history
- Audit logging

### 4. Search Layer

**Meilisearch**: Fast keyword search with typo tolerance

**Responsibilities**:
- Keyword-based document retrieval
- Fast full-text search
- Typo-tolerant matching

## Data Flow

### Query Processing Flow

1. **User submits query** → Frontend sends to `/api/ai/chat`
2. **Backend receives query** → Validates user, evaluates risk
3. **Query processing**:
   - Query expansion and intent detection
   - Hybrid search (vector + keyword)
   - Re-ranking results
   - Context assembly
4. **LLM generation**:
   - Send query + context to LLM
   - Generate response with citations
   - Calculate confidence score
5. **Response** → Return to frontend with sources and metadata

### Document Ingestion Flow

1. **Document uploaded** → Webhook or API call
2. **Document processing**:
   - Extract text (PDF, Word, etc.)
   - Chunk document (800 tokens with 50 overlap)
   - Generate embeddings
3. **Indexing**:
   - Store metadata in PostgreSQL
   - Store chunks in PostgreSQL
   - Store embeddings in pgvector
   - Index text in Meilisearch
4. **Ready for querying**

## RAG Pipeline

### Retrieval Phase

1. **Query Embedding**: Convert user query to vector
2. **Vector Search**: Find similar chunks using cosine similarity
3. **Keyword Search**: Find chunks with matching keywords
4. **Hybrid Fusion**: Combine results (60% vector, 40% keyword)
5. **Re-ranking**: Score and rank final results

### Generation Phase

1. **Context Assembly**: Combine top-K chunks
2. **Prompt Construction**: Build RAG prompt with context
3. **LLM Generation**: Send to local Ollama (Llama model)
4. **Post-processing**: Extract citations, calculate confidence
5. **Response Formatting**: Structure response with metadata

## Security Architecture

- **Authentication**: JWT tokens (configurable)
- **Authorization**: Document-level access control
- **Risk Evaluation**: Query risk scoring
- **Policy Enforcement**: Block/allow based on risk
- **Audit Logging**: All queries logged

## Scalability

- **Horizontal Scaling**: Backend services can scale independently
- **Caching**: Redis for conversation caching (optional)
- **Load Balancing**: API Gateway (optional)
- **Database**: Read replicas for scaling queries

## Deployment

- **Docker**: Containerized services
- **Docker Compose**: Local development
- **Kubernetes**: Production deployment (optional)
- **CI/CD**: Automated testing and deployment (optional)
