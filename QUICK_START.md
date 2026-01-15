# Quick Start Guide - Local Llama Setup

This is a quick reference guide. For detailed instructions, see [Local LLM Setup Guide](docs/LOCAL_LLM_SETUP.md).

## 🚀 Fastest Setup (Docker)

### 1. Start Services
```bash
docker-compose up -d
```

### 2. Pull Model
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b
```

### 3. Test
```bash
curl http://localhost:5000/health
```

## 📋 Model Selection

**For CPU (8GB+ RAM):**
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.2:3b
```
Set in `.env`: `LLM_MODEL=llama3.2:3b`

**For GPU (8GB+ VRAM):**
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b
```
Set in `.env`: `LLM_MODEL=llama3.1:8b`

**For Speed (Quantized):**
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b-instruct-q4_0
```
Set in `.env`: `LLM_MODEL=llama3.1:8b-instruct-q4_0`

## ⚙️ Configuration

Create `.env` file:
```env
OLLAMA_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=llama3.1:8b
DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@postgres:5432/ai_chatbot_db
MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_KEY=masterKey123
```

## 🧪 Test Chat

```bash
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello!",
    "userId": "1"
  }'
```

## 🔧 Troubleshooting

**Ollama not responding:**
```bash
docker logs ai-chatbot-ollama
docker restart ai-chatbot-ollama
```

**Model not found:**
```bash
docker exec -it ai-chatbot-ollama ollama list
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b
```

**Check if Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

## 📚 More Information

- Full setup guide: [docs/LOCAL_LLM_SETUP.md](docs/LOCAL_LLM_SETUP.md)
- Ollama docs: https://ollama.com/docs
- Available models: https://ollama.com/library


