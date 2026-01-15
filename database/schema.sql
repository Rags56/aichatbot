-- ========== AI CHATBOT STANDALONE DATABASE SCHEMA ==========
-- Core tables for AI Knowledge Base Chatbot

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Knowledge Base Documents
CREATE TABLE IF NOT EXISTS kb_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  source TEXT NOT NULL, -- 'google_drive', 'nas', 'local', 'erp', 'crm', 'upload'
  path TEXT NOT NULL, -- S3/minio path or original URL
  uploaded_by TEXT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB,
  department TEXT,
  classification TEXT DEFAULT 'internal', -- 'public', 'internal', 'confidential', 'restricted'
  tags TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Knowledge Base Chunks (text chunks with metadata)
CREATE TABLE IF NOT EXISTS kb_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- AI Knowledge Base Embeddings (using pgvector)
CREATE TABLE IF NOT EXISTS kb_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID REFERENCES kb_chunks(id) ON DELETE CASCADE,
  vector vector(1536), -- Ollama embedding dimension (nomic-embed-text)
  model TEXT DEFAULT 'ollama-embedding',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Query Logs (audit trail)
CREATE TABLE IF NOT EXISTS ai_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  query_text TEXT NOT NULL,
  response_text TEXT,
  sources JSONB, -- Array of document/chunk references
  risk_score NUMERIC(5,2),
  policy_decision TEXT, -- 'allowed', 'blocked', 'conditional'
  mfa_required BOOLEAN DEFAULT FALSE,
  elapsed_ms INTEGER,
  confidence_score NUMERIC(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Conversations Table
CREATE TABLE IF NOT EXISTS ai_conversations (
  id SERIAL PRIMARY KEY,
  conversation_id VARCHAR(50) UNIQUE NOT NULL,
  user_id TEXT NOT NULL,
  title VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Messages Table
CREATE TABLE IF NOT EXISTS ai_messages (
  id SERIAL PRIMARY KEY,
  conversation_id INTEGER REFERENCES ai_conversations(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for AI Knowledge Base
CREATE INDEX IF NOT EXISTS idx_kb_documents_source ON kb_documents(source);
CREATE INDEX IF NOT EXISTS idx_kb_documents_department ON kb_documents(department);
CREATE INDEX IF NOT EXISTS idx_kb_documents_classification ON kb_documents(classification);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_document_id ON kb_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_chunk_id ON kb_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_vector ON kb_embeddings USING ivfflat (vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_ai_queries_user_id ON ai_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_queries_created_at ON ai_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_id ON ai_messages(conversation_id);
