#!/bin/bash
set -e

echo "🚀 Setting up AI Chatbot on RunPod Ubuntu Server"
echo ""

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get install -y curl wget gnupg2 software-properties-common

# Install PostgreSQL 15 with pgvector
echo "🐘 Installing PostgreSQL 15..."
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update
apt-get install -y postgresql-15 postgresql-contrib-15 postgresql-15-pgvector

# Install Python 3.11
echo "🐍 Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-dev python3-pip python3.11-venv

# Install Meilisearch
echo "🔍 Installing Meilisearch..."
MEILI_VERSION=1.5.0
wget -qO /usr/local/bin/meilisearch \
    https://github.com/meilisearch/meilisearch/releases/download/v${MEILI_VERSION}/meilisearch-linux-amd64
chmod +x /usr/local/bin/meilisearch

# Install Ollama
echo "🤖 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
echo "📚 Installing Python dependencies..."
cd /workspace/ai-chatbot-standalone/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Setup PostgreSQL
echo "🗄️  Setting up PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql <<EOF
CREATE USER ai_chatbot WITH PASSWORD 'ai_chatbot123';
CREATE DATABASE ai_chatbot_db OWNER ai_chatbot;
ALTER USER ai_chatbot CREATEDB;
\q
EOF

# Enable pgvector extension
sudo -u postgres psql -d ai_chatbot_db <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
\q
EOF

# Initialize database schema
echo "📋 Initializing database schema..."
cd /workspace/ai-chatbot-standalone
sudo -u postgres psql -d ai_chatbot_db -f database/schema.sql
sudo -u postgres psql -d ai_chatbot_db -f database/ai_enterprise_schema.sql

# Create systemd service files
echo "⚙️  Creating systemd services..."

# Meilisearch service
cat > /etc/systemd/system/meilisearch.service <<EOF
[Unit]
Description=Meilisearch
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/meilisearch --db-path /workspace/meilisearch-data --http-addr 0.0.0.0:7700 --master-key masterKey123
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Ollama service
cat > /etc/systemd/system/ollama.service <<EOF
[Unit]
Description=Ollama
After=network.target

[Service]
Type=simple
User=root
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_GPU=1"
ExecStart=/usr/local/bin/ollama serve
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Install Node.js for frontend
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Setup Frontend
echo "🎨 Setting up frontend..."
cd /workspace/ai-chatbot-standalone/frontend
npm install

# Backend service
cat > /etc/systemd/system/ai-chatbot-backend.service <<EOF
[Unit]
Description=AI Chatbot Backend
After=network.target postgresql.service meilisearch.service ollama.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/ai-chatbot-standalone/backend
Environment="PATH=/workspace/ai-chatbot-standalone/backend/venv/bin"
Environment="DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db"
Environment="MEILISEARCH_URL=http://localhost:7700"
Environment="MEILISEARCH_KEY=masterKey123"
Environment="OLLAMA_URL=http://localhost:11434"
Environment="LLM_MODEL=llama3.1:8b"
Environment="EMBEDDING_MODEL=llama3.1:8b"
Environment="PORT=5000"
ExecStart=/workspace/ai-chatbot-standalone/backend/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Frontend service
cat > /etc/systemd/system/ai-chatbot-frontend.service <<EOF
[Unit]
Description=AI Chatbot Frontend
After=network.target ai-chatbot-backend.service
Requires=ai-chatbot-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/ai-chatbot-standalone/frontend
Environment="NEXT_PUBLIC_API_URL=http://localhost:5000"
Environment="PORT=3000"
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create data directories
mkdir -p /workspace/meilisearch-data
chmod 777 /workspace/meilisearch-data

# Enable and start services
echo "🔄 Starting services..."
systemctl daemon-reload
systemctl enable postgresql meilisearch ollama ai-chatbot-backend
systemctl start meilisearch ollama

# Wait for Ollama to start
echo "⏳ Waiting for Ollama to start..."
sleep 5

# Pull Llama model
echo "📥 Pulling Llama model (this may take a few minutes)..."
ollama pull llama3.1:8b || echo "⚠️  Model pull failed, you can pull it manually later with: ollama pull llama3.1:8b"

# Start backend
systemctl start ai-chatbot-backend

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Services status:"
systemctl status postgresql --no-pager | head -3
systemctl status meilisearch --no-pager | head -3
systemctl status ollama --no-pager | head -3
systemctl status ai-chatbot-backend --no-pager | head -3
echo ""
echo "🌐 Backend API: http://localhost:5000"
echo "🔍 Health check: curl http://localhost:5000/health"
echo ""
echo "📝 Useful commands:"
echo "  - Check logs: journalctl -u ai-chatbot-backend -f"
echo "  - Restart backend: systemctl restart ai-chatbot-backend"
echo "  - Pull model: ollama pull llama3.1:8b"

