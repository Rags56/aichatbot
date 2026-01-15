#!/usr/bin/env bash
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-ai_chatbot}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-ai_chatbot123}"
POSTGRES_DB="${POSTGRES_DB:-ai_chatbot_db}"
MEILISEARCH_KEY="${MEILISEARCH_KEY:-masterKey123}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
OLLAMA_EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"

export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB MEILISEARCH_KEY OLLAMA_MODEL OLLAMA_EMBEDDING_MODEL

DATA_DIR="/var/lib/postgresql/data"

# Find PostgreSQL binary directory
PG_BIN_DIR=$(find /usr/lib/postgresql -name "initdb" -type f 2>/dev/null | head -1 | xargs dirname)
if [ -z "$PG_BIN_DIR" ]; then
  # Fallback: try common locations in order
  for version in 16 15 14 13 12; do
    if [ -f "/usr/lib/postgresql/${version}/bin/initdb" ]; then
      PG_BIN_DIR="/usr/lib/postgresql/${version}/bin"
      break
    fi
  done
  
  if [ -z "$PG_BIN_DIR" ]; then
    echo "Error: Could not find PostgreSQL binaries. Please check PostgreSQL installation."
    exit 1
  fi
fi

echo "Using PostgreSQL binaries from: ${PG_BIN_DIR}"
export PATH="${PG_BIN_DIR}:${PATH}"

if [ ! -s "${DATA_DIR}/PG_VERSION" ]; then
  mkdir -p "${DATA_DIR}"
  chown -R postgres:postgres "${DATA_DIR}"

  su - postgres -c "${PG_BIN_DIR}/initdb -D ${DATA_DIR}"
  su - postgres -c "${PG_BIN_DIR}/pg_ctl -D ${DATA_DIR} -o \"-c listen_addresses='*'\" -w start"

  # Create user role if it doesn't exist
  # Use a SQL file to properly handle the DO block (use quoted heredoc to prevent $$ expansion)
  cat > /tmp/init_db.sql <<'INITSQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'POSTGRES_USER_PLACEHOLDER') THEN
    CREATE ROLE POSTGRES_USER_PLACEHOLDER LOGIN PASSWORD 'POSTGRES_PASSWORD_PLACEHOLDER';
  END IF;
END
$$;

SELECT 'CREATE DATABASE POSTGRES_DB_PLACEHOLDER OWNER POSTGRES_USER_PLACEHOLDER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'POSTGRES_DB_PLACEHOLDER')\gexec
INITSQL

  # Replace placeholders with actual values
  sed -i "s/POSTGRES_USER_PLACEHOLDER/${POSTGRES_USER}/g" /tmp/init_db.sql
  sed -i "s/POSTGRES_PASSWORD_PLACEHOLDER/${POSTGRES_PASSWORD}/g" /tmp/init_db.sql
  sed -i "s/POSTGRES_DB_PLACEHOLDER/${POSTGRES_DB}/g" /tmp/init_db.sql

  su postgres -c "${PG_BIN_DIR}/psql -v ON_ERROR_STOP=1 --username=postgres -f /tmp/init_db.sql"
  rm -f /tmp/init_db.sql

  su - postgres -c "${PG_BIN_DIR}/psql -v ON_ERROR_STOP=1 -d ${POSTGRES_DB} -f /app/database/schema.sql"
  su - postgres -c "${PG_BIN_DIR}/psql -v ON_ERROR_STOP=1 -d ${POSTGRES_DB} -f /app/database/ai_enterprise_schema.sql"

  su - postgres -c "${PG_BIN_DIR}/pg_ctl -D ${DATA_DIR} -m fast -w stop"
fi

# Create Meilisearch data directory
mkdir -p /var/lib/meilisearch

# Start supervisord in the background to start all services
echo "Starting services via supervisord..."
/usr/bin/supervisord -c /etc/supervisord.conf &
SUPERVISORD_PID=$!

# Wait for Ollama to be ready, then pull models
echo "Waiting for Ollama to start..."
sleep 20  # Give Ollama time to start via supervisor

# Wait for Ollama to actually be ready (check if it's responding)
OLLAMA_READY=false
for i in {1..90}; do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is ready!"
    OLLAMA_READY=true
    break
  fi
  sleep 1
done

if [ "$OLLAMA_READY" = false ]; then
  echo "Warning: Ollama did not become ready after 90 seconds"
  echo "Checking Ollama process..."
  ps aux | grep ollama || echo "Ollama process not found"
  echo "Continuing anyway - models can be pulled later..."
fi

# Pull Ollama models if Ollama is ready
if [ "$OLLAMA_READY" = true ]; then
  # Check Ollama version
  echo "Checking Ollama version..."
  /usr/local/bin/ollama --version || echo "Could not get Ollama version"
  
  pull_model() {
    local model=$1
    local max_attempts=2
    local attempt=1
    
    # Check if model already exists
    if /usr/local/bin/ollama list 2>/dev/null | grep -q "${model}"; then
      echo "Model ${model} already exists, skipping pull"
      return 0
    fi
    
    while [ $attempt -le $max_attempts ]; do
      echo "Attempting to pull ${model} (attempt $attempt/$max_attempts)..."
      
      # Try pulling with timeout
      if timeout 300 /usr/local/bin/ollama pull "${model}" 2>&1; then
        echo "Successfully pulled ${model}"
        return 0
      else
        local pull_exit_code=$?
        echo "Pull attempt $attempt failed for ${model} (exit code: ${pull_exit_code})"
        
        # If it's a 401 error, it's likely a network/registry issue
        if [ $attempt -eq 1 ]; then
          echo ""
          echo "⚠️  WARNING: Model pull failed with authentication error (401)"
          echo "   This usually means:"
          echo "   1. Network connectivity issue to Ollama registry"
          echo "   2. Firewall/proxy blocking access to registry.ollama.ai"
          echo "   3. Ollama registry temporary issue"
          echo ""
          echo "   Ollama public models do NOT require an API key."
          echo "   You can manually pull models after the container starts:"
          echo "   docker exec -it ai-chatbot-allinone ollama pull ${model}"
          echo ""
        fi
      fi
      attempt=$((attempt + 1))
      sleep 3
    done
    
    echo "⚠️  Failed to pull ${model} after ${max_attempts} attempts"
    echo "   The container will continue running. You can pull models manually:"
    echo "   docker exec -it ai-chatbot-allinone ollama pull ${model}"
    return 1
  }

  echo ""
  echo "=== Pulling Ollama Models ==="
  echo "Note: Model downloads can take several minutes depending on size and network speed"
  echo ""
  
  pull_model ${OLLAMA_MODEL} || echo "Continuing without ${OLLAMA_MODEL}..."
  pull_model ${OLLAMA_EMBEDDING_MODEL} || echo "Continuing without ${OLLAMA_EMBEDDING_MODEL}..."
  
  echo ""
  echo "=== Model Pull Complete ==="
  echo "Available models:"
  /usr/local/bin/ollama list || echo "Could not list models"
  echo ""
else
  echo "Skipping model pull - Ollama not ready. Models can be pulled manually later."
  echo "Once Ollama is running, use: docker exec -it ai-chatbot-allinone ollama pull <model-name>"
fi

# Keep supervisord running in foreground
wait $SUPERVISORD_PID
