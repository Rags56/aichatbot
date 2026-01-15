# RunPod Ubuntu Server Setup Instructions

## Step 1: Upload Project to RunPod

1. **Start RunPod Server** (Ubuntu 22.04)
2. **Connect via SSH** or use RunPod's web terminal
3. **Upload your project**:

```bash
# Option A: Using git (if you have a repo)
cd /workspace
git clone <your-repo-url> ai-chatbot-standalone

# Option B: Using RunPod's file upload
# Upload the entire project folder to /workspace/ai-chatbot-standalone
```

## Step 2: Run Setup Script

```bash
cd /workspace/ai-chatbot-standalone
chmod +x setup-runpod.sh
sudo ./setup-runpod.sh
```

This will:
- ✅ Install PostgreSQL 15 with pgvector
- ✅ Install Python 3.11
- ✅ Install Meilisearch
- ✅ Install Ollama
- ✅ Install Python dependencies
- ✅ Setup database
- ✅ Create systemd services
- ✅ Start all services
- ✅ Pull Llama model

## Step 3: Verify Everything Works

```bash
# Check services
systemctl status ai-chatbot-backend
systemctl status ollama
systemctl status meilisearch
systemctl status postgresql

# Test API
curl http://localhost:5000/health

# Test chat
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "userId": "1"}'
```

## Step 4: Expose Ports (Optional)

If you want to access from outside RunPod:

1. **RunPod Dashboard** → Your Pod → **Connect** → **HTTP Service**
2. Set port: `5000`
3. Access via RunPod's public URL

## Manual Setup (if script fails)

### Install Dependencies

```bash
# PostgreSQL
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update
apt-get install -y postgresql-15 postgresql-contrib-15 postgresql-15-pgvector

# Python 3.11
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-dev python3-pip python3.11-venv

# Meilisearch
wget -qO /usr/local/bin/meilisearch \
    https://github.com/meilisearch/meilisearch/releases/download/v1.5.0/meilisearch-linux-amd64
chmod +x /usr/local/bin/meilisearch

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Setup Python Environment

```bash
cd /workspace/ai-chatbot-standalone/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Setup Database

```bash
systemctl start postgresql
sudo -u postgres psql <<EOF
CREATE USER ai_chatbot WITH PASSWORD 'ai_chatbot123';
CREATE DATABASE ai_chatbot_db OWNER ai_chatbot;
\c ai_chatbot_db
CREATE EXTENSION vector;
\q
EOF

cd /workspace/ai-chatbot-standalone
sudo -u postgres psql -d ai_chatbot_db -f database/schema.sql
sudo -u postgres psql -d ai_chatbot_db -f database/ai_enterprise_schema.sql
```

### Start Services Manually

```bash
# Terminal 1: Meilisearch
meilisearch --db-path /workspace/meilisearch-data --http-addr 0.0.0.0:7700 --master-key masterKey123

# Terminal 2: Ollama
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_NUM_GPU=1 ollama serve

# Terminal 3: Pull model
ollama pull llama3.1:8b

# Terminal 4: Backend
cd /workspace/ai-chatbot-standalone/backend
source venv/bin/activate
export DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db
export MEILISEARCH_URL=http://localhost:7700
export OLLAMA_URL=http://localhost:11434
export LLM_MODEL=llama3.1:8b
python app.py
```

## Useful Commands

```bash
# View backend logs
journalctl -u ai-chatbot-backend -f

# Restart services
systemctl restart ai-chatbot-backend
systemctl restart ollama
systemctl restart meilisearch

# Check if model is downloaded
ollama list

# Pull different model
ollama pull llama3.2:3b  # Smaller, faster
ollama pull llama3.1:8b-instruct-q4_0  # Quantized

# Update environment variables
sudo systemctl edit ai-chatbot-backend
# Add:
# [Service]
# Environment="LLM_MODEL=llama3.2:3b"
```

## Troubleshooting

**Services not starting:**
```bash
systemctl status ai-chatbot-backend
journalctl -u ai-chatbot-backend -n 50
```

**Ollama not working:**
```bash
systemctl status ollama
curl http://localhost:11434/api/tags
```

**Database issues:**
```bash
sudo -u postgres psql -d ai_chatbot_db -c "SELECT 1;"
```

**Port already in use:**
```bash
lsof -i :5000
# Kill process or change PORT in environment
```

## That's It!

Your AI Chatbot should now be running on:
- **Backend API**: `http://localhost:5000`
- **Ollama**: `http://localhost:11434`
- **Meilisearch**: `http://localhost:7700`


