-- ========== AI ENTERPRISE FEATURES SCHEMA ==========
-- Extensions for enterprise-ready AI Chatbot features

-- Dataset Versioning
CREATE TABLE IF NOT EXISTS kb_dataset_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id VARCHAR(100) NOT NULL, -- Identifier for the dataset (e.g., 'hr-policies', 'devops-sops')
  version_number INTEGER NOT NULL,
  description TEXT,
  document_count INTEGER DEFAULT 0,
  chunk_count INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'review', 'approved', 'published', 'archived'
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  metadata JSONB,
  UNIQUE(dataset_id, version_number)
);

-- Knowledge Validation Workflow
CREATE TABLE IF NOT EXISTS kb_validation_workflow (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE,
  workflow_stage VARCHAR(50) DEFAULT 'draft', -- 'draft', 'review', 'approved', 'published', 'rejected'
  submitted_by TEXT,
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  review_notes TEXT,
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  rejection_reason TEXT,
  metadata JSONB
);

-- Search Evaluations (Quality Metrics)
CREATE TABLE IF NOT EXISTS kb_search_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_name VARCHAR(255),
  query_text TEXT NOT NULL,
  expected_documents TEXT[], -- Array of document IDs that should be retrieved
  actual_documents TEXT[], -- Array of document IDs actually retrieved
  relevance_score NUMERIC(5,2), -- 0-100, how relevant the results were
  precision_score NUMERIC(5,2), -- Precision metric
  recall_score NUMERIC(5,2), -- Recall metric
  f1_score NUMERIC(5,2), -- F1 score
  evaluated_by TEXT,
  evaluated_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  metadata JSONB
);

-- Retrieval Debugger (Track which chunks matched and why)
CREATE TABLE IF NOT EXISTS kb_retrieval_debug (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id UUID REFERENCES ai_queries(id) ON DELETE CASCADE,
  chunk_id UUID REFERENCES kb_chunks(id) ON DELETE CASCADE,
  match_type VARCHAR(50), -- 'vector', 'keyword', 'hybrid'
  similarity_score NUMERIC(10,6), -- Vector similarity score
  keyword_score NUMERIC(10,6), -- Keyword match score
  combined_score NUMERIC(10,6), -- Final combined score
  rank_position INTEGER, -- Position in results (1 = top result)
  matched_terms TEXT[], -- Array of matched keywords
  debug_info JSONB, -- Additional debugging information
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversational Memory
CREATE TABLE IF NOT EXISTS ai_conversation_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id VARCHAR(100) NOT NULL,
  user_id TEXT NOT NULL,
  memory_type VARCHAR(50) NOT NULL, -- 'short_term', 'long_term', 'context'
  content TEXT NOT NULL,
  importance_score NUMERIC(5,2) DEFAULT 0.0, -- 0-100, how important this memory is
  expires_at TIMESTAMPTZ, -- For short-term memory
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- AI Tools & Actions
CREATE TABLE IF NOT EXISTS ai_tools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id VARCHAR(100) UNIQUE NOT NULL,
  tool_name VARCHAR(255) NOT NULL,
  description TEXT,
  tool_type VARCHAR(50) NOT NULL, -- 'system', 'api', 'script', 'workflow'
  endpoint_url TEXT, -- For API tools
  script_path TEXT, -- For script tools
  required_permissions TEXT[], -- Array of permission IDs required
  parameters JSONB, -- Schema for tool parameters
  status VARCHAR(20) DEFAULT 'active', -- 'active', 'disabled', 'deprecated'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Tool Executions (Audit trail for tool usage)
CREATE TABLE IF NOT EXISTS ai_tool_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id UUID REFERENCES ai_queries(id) ON DELETE SET NULL,
  tool_id UUID REFERENCES ai_tools(id) ON DELETE SET NULL,
  user_id TEXT NOT NULL,
  parameters JSONB, -- Parameters passed to the tool
  result JSONB, -- Tool execution result
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'executing', 'success', 'failed'
  error_message TEXT,
  execution_time_ms INTEGER,
  executed_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Knowledge Certification Process
CREATE TABLE IF NOT EXISTS kb_certifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE,
  dataset_id VARCHAR(100),
  certification_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_review', 'certified', 'rejected', 'expired'
  certified_by TEXT,
  certified_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  coverage_score NUMERIC(5,2), -- Coverage testing score
  consistency_score NUMERIC(5,2), -- Consistency check score
  validation_notes TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Quality Monitoring
CREATE TABLE IF NOT EXISTS ai_quality_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_date DATE NOT NULL,
  metric_type VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
  query_count INTEGER DEFAULT 0,
  success_count INTEGER DEFAULT 0,
  failure_count INTEGER DEFAULT 0,
  avg_response_time_ms INTEGER DEFAULT 0,
  avg_relevance_score NUMERIC(5,2) DEFAULT 0.0,
  harmful_response_count INTEGER DEFAULT 0,
  wrong_response_count INTEGER DEFAULT 0,
  dataset_drift_score NUMERIC(5,2) DEFAULT 0.0, -- How much the dataset has changed
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(metric_date, metric_type)
);

-- Retrieval Plugins (Domain Knowledge Modules)
CREATE TABLE IF NOT EXISTS kb_plugins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plugin_id VARCHAR(100) UNIQUE NOT NULL,
  plugin_name VARCHAR(255) NOT NULL,
  plugin_type VARCHAR(50) NOT NULL, -- 'systems', 'devops', 'security', 'hr', 'finance', 'custom'
  description TEXT,
  dataset_id VARCHAR(100), -- Associated dataset
  embedding_model VARCHAR(100), -- Embedding model used for this plugin
  access_permissions TEXT[], -- Array of permission IDs required to query this plugin
  status VARCHAR(20) DEFAULT 'active', -- 'active', 'disabled', 'deprecated'
  config JSONB, -- Plugin-specific configuration
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Plugin-Document Mapping (which documents belong to which plugin)
CREATE TABLE IF NOT EXISTS kb_plugin_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plugin_id UUID REFERENCES kb_plugins(id) ON DELETE CASCADE,
  document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(plugin_id, document_id)
);

-- Continuous Knowledge Sync Jobs
CREATE TABLE IF NOT EXISTS kb_sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id VARCHAR(100) UNIQUE NOT NULL,
  job_type VARCHAR(50) NOT NULL, -- 'sop_upload', 'git_push', 'diagram_update', 'project_create', 'log_summary'
  source_type VARCHAR(50) NOT NULL, -- 'file_gateway', 'git', 'api', 'webhook', 'scheduled'
  source_config JSONB, -- Configuration for the source
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
  documents_processed INTEGER DEFAULT 0,
  chunks_created INTEGER DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Indexes for Enterprise Features
CREATE INDEX IF NOT EXISTS idx_kb_dataset_versions_dataset_id ON kb_dataset_versions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_kb_dataset_versions_status ON kb_dataset_versions(status);
CREATE INDEX IF NOT EXISTS idx_kb_validation_workflow_document_id ON kb_validation_workflow(document_id);
CREATE INDEX IF NOT EXISTS idx_kb_validation_workflow_stage ON kb_validation_workflow(workflow_stage);
CREATE INDEX IF NOT EXISTS idx_kb_search_evaluations_evaluated_at ON kb_search_evaluations(evaluated_at);
CREATE INDEX IF NOT EXISTS idx_kb_retrieval_debug_query_id ON kb_retrieval_debug(query_id);
CREATE INDEX IF NOT EXISTS idx_kb_retrieval_debug_chunk_id ON kb_retrieval_debug(chunk_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_memory_conversation_id ON ai_conversation_memory(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_memory_user_id ON ai_conversation_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_memory_type ON ai_conversation_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_ai_tools_tool_id ON ai_tools(tool_id);
CREATE INDEX IF NOT EXISTS idx_ai_tools_tool_type ON ai_tools(tool_type);
CREATE INDEX IF NOT EXISTS idx_ai_tool_executions_query_id ON ai_tool_executions(query_id);
CREATE INDEX IF NOT EXISTS idx_ai_tool_executions_tool_id ON ai_tool_executions(tool_id);
CREATE INDEX IF NOT EXISTS idx_ai_tool_executions_user_id ON ai_tool_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_kb_certifications_document_id ON kb_certifications(document_id);
CREATE INDEX IF NOT EXISTS idx_kb_certifications_status ON kb_certifications(certification_status);
CREATE INDEX IF NOT EXISTS idx_ai_quality_metrics_metric_date ON ai_quality_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_ai_quality_metrics_metric_type ON ai_quality_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_kb_plugins_plugin_id ON kb_plugins(plugin_id);
CREATE INDEX IF NOT EXISTS idx_kb_plugins_plugin_type ON kb_plugins(plugin_type);
CREATE INDEX IF NOT EXISTS idx_kb_plugin_documents_plugin_id ON kb_plugin_documents(plugin_id);
CREATE INDEX IF NOT EXISTS idx_kb_plugin_documents_document_id ON kb_plugin_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_kb_sync_jobs_job_id ON kb_sync_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_kb_sync_jobs_status ON kb_sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_kb_sync_jobs_job_type ON kb_sync_jobs(job_type);

-- Insert default plugins
INSERT INTO kb_plugins (plugin_id, plugin_name, plugin_type, description, status) VALUES
('plugin-systems', 'Systems Knowledge Plugin', 'systems', 'Server metrics, DR plans, architecture diagrams', 'active'),
('plugin-devops', 'DevOps Knowledge Plugin', 'devops', 'CI/CD runs, deployment history, compute usage', 'active'),
('plugin-security', 'Security Knowledge Plugin', 'security', 'ZTA policies, access logs, security playbooks', 'active'),
('plugin-hr', 'HR Knowledge Plugin', 'hr', 'Employee policies, reimbursement rules, onboarding flow', 'active'),
('plugin-finance', 'Finance Knowledge Plugin', 'finance', 'Invoice SOPs, payment flows, approval workflows', 'active')
ON CONFLICT (plugin_id) DO NOTHING;

-- Insert default tools
INSERT INTO ai_tools (tool_id, tool_name, description, tool_type, required_permissions, parameters, status) VALUES
('tool-restart-service', 'Restart Service', 'Restart a system service', 'system', ARRAY['PERM_SYSTEM_ADMIN'], '{"service_name": "string", "force": "boolean"}'::jsonb, 'active'),
('tool-fetch-logs', 'Fetch Logs', 'Retrieve last N lines of logs from a service', 'api', ARRAY['PERM_SYSTEM_READ'], '{"service": "string", "lines": "integer", "level": "string"}'::jsonb, 'active'),
('tool-server-status', 'Server Status', 'Get status of a server', 'api', ARRAY['PERM_SYSTEM_READ'], '{"server_id": "string"}'::jsonb, 'active'),
('tool-trigger-build', 'Trigger Build', 'Trigger a CI/CD build', 'api', ARRAY['PERM_DEVOPS_WRITE'], '{"pipeline": "string", "branch": "string"}'::jsonb, 'active'),
('tool-create-ticket', 'Create Ticket', 'Create an internal ticket', 'api', ARRAY['PERM_TICKETS_WRITE'], '{"title": "string", "description": "string", "priority": "string"}'::jsonb, 'active'),
('tool-update-kb', 'Update KB Article', 'Update a knowledge base article through approval workflow', 'workflow', ARRAY['PERM_KB_WRITE'], '{"article_id": "string", "content": "string"}'::jsonb, 'active')
ON CONFLICT (tool_id) DO NOTHING;

