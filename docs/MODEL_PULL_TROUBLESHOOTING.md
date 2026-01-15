# Ollama Model Pull Troubleshooting

## 401 Unauthorized Error

If you're seeing `401: unauthorized` errors when pulling Ollama models, this is **NOT** an API key issue. Ollama public models don't require authentication.

### Common Causes

1. **Network/Firewall Issues**
   - Corporate firewall blocking access to `registry.ollama.ai`
   - VPN or proxy interfering with connections
   - Docker network configuration issues

2. **Ollama Registry Issues**
   - Temporary registry outage
   - Rate limiting (if pulling many models quickly)

3. **Docker Network Configuration**
   - Container doesn't have internet access
   - DNS resolution issues

### Solutions

#### Option 1: Manual Model Pull (Recommended)

After the container starts, manually pull models:

```bash
# Check if Ollama is running
docker exec -it ai-chatbot-allinone ollama list

# Pull the chat model
docker exec -it ai-chatbot-allinone ollama pull llama3.1:8b

# Pull the embedding model
docker exec -it ai-chatbot-allinone ollama pull nomic-embed-text
```

#### Option 2: Check Network Connectivity

```bash
# Test if container can reach Ollama registry
docker exec -it ai-chatbot-allinone curl -I https://registry.ollama.ai

# Test DNS resolution
docker exec -it ai-chatbot-allinone nslookup registry.ollama.ai
```

#### Option 3: Use Different Network Mode

If you're behind a corporate firewall, try:

```bash
# Run with host network (may have security implications)
docker run --network host ... ai-chatbot-allinone
```

#### Option 4: Pull Models on Host, Copy to Container

1. Install Ollama on your host machine
2. Pull models: `ollama pull llama3.1:8b`
3. Copy model files to container volume

### Verify Models Are Available

```bash
# List available models
docker exec -it ai-chatbot-allinone ollama list

# Test a model
docker exec -it ai-chatbot-allinone ollama run llama3.1:8b "Hello"
```

### Alternative Models

If specific models fail, try alternatives:

- **Chat models**: `llama3.1:8b`, `mistral:7b`, `phi3:3.8b`
- **Embedding models**: `nomic-embed-text`, `all-minilm`

### Still Having Issues?

1. Check Ollama logs: `docker logs ai-chatbot-allinone | grep -i ollama`
2. Verify Ollama is running: `docker exec -it ai-chatbot-allinone ps aux | grep ollama`
3. Check network: `docker exec -it ai-chatbot-allinone curl http://localhost:11434/api/tags`

The application will continue to work even if models aren't pulled during startup - you can pull them manually later.
