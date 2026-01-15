# Local LLM Setup Guide

This guide explains how to set up and use a local Llama model instead of external AI APIs (Groq/OpenAI).

## Overview

The system now uses **Ollama** to run Llama models locally. Ollama is a lightweight, easy-to-use tool for running LLMs on your machine.

## Prerequisites

- **Docker and Docker Compose** (for containerized setup)
- **OR** Ollama installed locally (for non-Docker setup)
- **Hardware Requirements**:
  - **CPU-only**: Works but slower (8GB+ RAM recommended)
  - **GPU (NVIDIA)**: Much faster (8GB+ VRAM recommended for 8B models)

## Option 1: Docker Setup (Recommended)

### Step 1: Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL with pgvector
- Meilisearch
- **Ollama** (local LLM server)
- Backend API

### Step 2: Pull Llama Model

Once Ollama is running, pull the model:

```bash
# Enter the Ollama container
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b

# Or pull a smaller/faster model
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b-instruct-q4_0
```

**Available Models:**
- `llama3.1:8b` - Full 8B model (best quality, ~4.7GB)
- `llama3.1:8b-instruct-q4_0` - Quantized 4-bit (faster, ~4.6GB)
- `llama3.1:70b` - Larger model (requires 40GB+ RAM/VRAM)
- `llama3.2:3b` - Smaller, faster model (~2GB)

### Step 3: Configure Model (Optional)

Edit `.env` file to specify which model to use:

```env
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=llama3.1:8b
```

### Step 4: Verify Setup

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test the backend
curl http://localhost:5000/health
```

## Option 2: Local Ollama Installation

### Step 1: Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### Step 2: Start Ollama

```bash
ollama serve
```

This starts Ollama on `http://localhost:11434`

### Step 3: Pull Model

In a new terminal:
```bash
ollama pull llama3.1:8b
```

### Step 4: Configure Backend

Update `.env` file:
```env
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=llama3.1:8b
```

### Step 5: Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Model Selection Guide

### For CPU-only Systems:
- **Recommended**: `llama3.2:3b` (fastest, ~2GB)
- **Alternative**: `llama3.1:8b-instruct-q4_0` (quantized, ~4.6GB)

### For GPU Systems (8GB+ VRAM):
- **Recommended**: `llama3.1:8b` (best quality)
- **For speed**: `llama3.1:8b-instruct-q4_0` (quantized)

### For GPU Systems (16GB+ VRAM):
- **Best quality**: `llama3.1:70b` (if you have enough VRAM)

## Using Different Models for Text vs Embeddings

You can use different models for text generation and embeddings:

```env
LLM_MODEL=llama3.1:8b              # For text generation
EMBEDDING_MODEL=nomic-embed-text  # For embeddings (smaller, faster)
```

To use nomic-embed-text for embeddings:
```bash
docker exec -it ai-chatbot-ollama ollama pull nomic-embed-text
```

## Performance Optimization

### 1. Use Quantized Models
Quantized models (q4_0, q5_0) are smaller and faster:
```bash
ollama pull llama3.1:8b-instruct-q4_0
```

### 2. GPU Acceleration (Docker)

Uncomment GPU support in `docker-compose.yml`:
```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Requires: `nvidia-docker2` installed

### 3. Adjust Context Window

For longer documents, increase context:
```env
MAX_CHUNK_TOKENS=1200  # Default: 800
```

## Troubleshooting

### Ollama Not Responding

**Check if Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

**Restart Ollama:**
```bash
# Docker
docker restart ai-chatbot-ollama

# Local
pkill ollama
ollama serve
```

### Model Not Found

**List available models:**
```bash
docker exec -it ai-chatbot-ollama ollama list
# or locally
ollama list
```

**Pull the model:**
```bash
docker exec -it ai-chatbot-ollama ollama pull llama3.1:8b
```

### Slow Performance

1. **Use a smaller/quantized model**
2. **Enable GPU** (if available)
3. **Reduce MAX_CHUNK_TOKENS** in `.env`
4. **Use nomic-embed-text** for embeddings

### Out of Memory

1. **Use a smaller model** (llama3.2:3b)
2. **Use quantized version** (q4_0)
3. **Reduce MAX_CHUNK_TOKENS**
4. **Close other applications**

### Embeddings Not Working

Some models don't support embeddings well. Use:
- `llama3.1:8b` (supports embeddings)
- `nomic-embed-text` (dedicated embedding model)

## Testing the Setup

### Test Text Generation

```bash
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "userId": "1"
  }'
```

### Test Embeddings

The embeddings are automatically tested when you ingest documents. Check logs:
```bash
docker logs ai-chatbot-backend
```

## Migration from Groq/OpenAI

If you were previously using Groq/OpenAI:

1. **Remove API keys** from `.env`:
   ```env
   # Remove these:
   # GROQ_API_KEY=...
   # OPENAI_API_KEY=...
   ```

2. **Add Ollama configuration**:
   ```env
   OLLAMA_URL=http://ollama:11434  # or http://localhost:11434 for local
   LLM_MODEL=llama3.1:8b
   EMBEDDING_MODEL=llama3.1:8b
   ```

3. **Restart services**:
   ```bash
   docker-compose restart backend
   ```

## Advanced Configuration

### Custom Ollama URL

If Ollama is running on a different machine:
```env
OLLAMA_URL=http://192.168.1.100:11434
```

### Model Parameters

You can customize model behavior in `ai_service.py`:
- `temperature`: Controls randomness (0.0-1.0)
- `num_predict`: Max tokens to generate
- `top_p`: Nucleus sampling
- `top_k`: Top-k sampling

## Resources

- **Ollama Documentation**: https://ollama.com/docs
- **Available Models**: https://ollama.com/library
- **Performance Benchmarks**: Check Ollama GitHub

## Next Steps

1. Pull your preferred model
2. Test with a simple query
3. Ingest some documents
4. Monitor performance and adjust model if needed


