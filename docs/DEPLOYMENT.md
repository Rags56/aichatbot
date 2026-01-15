# Deployment Guide

## Local Development

### Prerequisites

- Docker and Docker Compose
- Git

### Steps

1. **Clone and setup**:
   ```bash
   cd ai-chatbot-standalone
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**:
   ```bash
   docker-compose exec postgres psql -U ai_chatbot -d ai_chatbot_db -f /docker-entrypoint-initdb.d/01-schema.sql
   docker-compose exec postgres psql -U ai_chatbot -d ai_chatbot_db -f /docker-entrypoint-initdb.d/02-enterprise-schema.sql
   ```

4. **Verify services**:
   ```bash
   # Check backend health
   curl http://localhost:5000/health
   
   # Check Meilisearch
   curl http://localhost:7700/health
   ```

## Production Deployment

### Option 1: Docker Compose (Simple)

1. **Configure environment**:
   ```bash
   # Production .env
   POSTGRES_PASSWORD=<strong_password>
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   MEILISEARCH_KEY=<strong_key>
   ```

2. **Start with production config**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Setup SSL/TLS** (recommended):
   - Use reverse proxy (Nginx/Traefik)
   - Configure SSL certificates
   - Enable HTTPS

### Option 2: Kubernetes

1. **Create namespace**:
   ```bash
   kubectl create namespace ai-chatbot
   ```

2. **Deploy services**:
   ```bash
   kubectl apply -f k8s/
   ```

3. **Configure ingress**:
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

## Environment Variables

### Required

- `DATABASE_URL`: PostgreSQL connection string
- `OLLAMA_URL`: Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Ollama model for chat (default: `llama3.1:8b`)
- `OLLAMA_EMBEDDING_MODEL`: Ollama model for embeddings (default: `nomic-embed-text`)
- `MEILISEARCH_URL`: Meilisearch service URL
- `MEILISEARCH_KEY`: Meilisearch master key

### Optional

- `PORT`: Backend service port (default: 5000)
- `MAX_CHUNK_TOKENS`: Chunk size in tokens (default: 800)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 50)
- `BACKEND_CORE_URL`: External backend URL (if needed)

## Database Setup

### Initial Schema

```bash
# Run schema files in order
psql -U ai_chatbot -d ai_chatbot_db -f database/schema.sql
psql -U ai_chatbot -d ai_chatbot_db -f database/ai_enterprise_schema.sql
```

### Enable pgvector

```sql
CREATE EXTENSION IF NOT EXISTS "vector";
```

### Create Indexes

Indexes are created automatically by schema files, but you can verify:

```sql
\di
```

## Monitoring

### Health Checks

- Backend: `GET /health`
- Meilisearch: `GET http://localhost:7700/health`
- PostgreSQL: `pg_isready`

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
```

### Metrics

- Query count: Check `ai_queries` table
- Response times: Check `elapsed_ms` in `ai_queries`
- Quality metrics: `GET /api/ai/admin/quality`

## Backup and Recovery

### Database Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U ai_chatbot ai_chatbot_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U ai_chatbot ai_chatbot_db < backup.sql
```

### Meilisearch Backup

Meilisearch data is stored in Docker volume. Backup the volume:

```bash
docker run --rm -v ai-chatbot-standalone_meilisearch_data:/data -v $(pwd):/backup alpine tar czf /backup/meilisearch-backup.tar.gz /data
```

## Troubleshooting

### Backend won't start

1. Check database connection
2. Verify Ollama is running and accessible
3. Check logs: `docker-compose logs backend`
4. Verify Ollama models are pulled: `ollama list`

### No search results

1. Verify documents are ingested
2. Check Meilisearch index: `curl http://localhost:7700/indexes`
3. Reindex: `POST /api/ai/reindex`

### High memory usage

1. Reduce `MAX_CHUNK_TOKENS`
2. Limit concurrent queries
3. Scale backend horizontally

## Security Checklist

- [ ] Strong database passwords
- [ ] Secure API keys (use secrets management)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Enable authentication
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Audit logging enabled
- [ ] Backup strategy in place
