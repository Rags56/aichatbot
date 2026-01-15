# Ollama Timeout Troubleshooting

## Error: `HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120)`

This error means the backend is trying to communicate with Ollama, but Ollama is not responding within the timeout period (120 seconds).

## Quick Diagnosis

### 1. Check if Ollama is Running

```bash
# Check if Ollama process is running
docker exec ai-chatbot-allinone supervisorctl status ollama

# Should show: `ollama RUNNING pid X, uptime X:XX:XX`
# If it shows FATAL or STOPPED, Ollama crashed
```

### 2. Check Ollama Logs

```bash
# View Ollama logs
docker exec ai-chatbot-allinone supervisorctl tail -100 ollama

# Or view all container logs filtered for Ollama
docker logs ai-chatbot-allinone 2>&1 | grep -i ollama
```

### 3. Test Ollama Directly

```bash
# Test if Ollama API is responding
docker exec ai-chatbot-allinone curl http://localhost:11434/api/tags

# Test if Ollama can list models
docker exec ai-chatbot-allinone ollama list

# Test if Ollama can run a simple query
docker exec ai-chatbot-allinone ollama run llama3.1:8b "Hello"
```

## Common Causes and Fixes

### Cause 1: Ollama Service Crashed

**Symptoms:**
- `supervisorctl status ollama` shows `FATAL` or `STOPPED`
- No response from Ollama API

**Fix:**
```bash
# Restart Ollama service
docker exec ai-chatbot-allinone supervisorctl restart ollama

# Check status again
docker exec ai-chatbot-allinone supervisorctl status ollama
```

### Cause 2: Model Not Loaded / Loading Slowly

**Symptoms:**
- First request after container start times out
- Ollama is running but slow to respond

**Fix:**
```bash
# Pre-load the model
docker exec ai-chatbot-allinone ollama run llama3.1:8b "test"

# Check if model is loaded
docker exec ai-chatbot-allinone ollama ps
```

### Cause 3: GPU Out of Memory

**Symptoms:**
- Ollama starts but hangs when processing
- GPU memory is full

**Fix:**
```bash
# Check GPU memory usage
docker exec ai-chatbot-allinone nvidia-smi

# If GPU memory is full, try a smaller model or reduce context size
# Or restart the container to free GPU memory
docker restart ai-chatbot-allinone
```

### Cause 4: Ollama Port Not Accessible

**Symptoms:**
- Connection refused errors
- Timeout errors

**Fix:**
```bash
# Check if port 11434 is listening
docker exec ai-chatbot-allinone netstat -tlnp | grep 11434

# Check Ollama configuration
docker exec ai-chatbot-allinone env | grep OLLAMA
```

### Cause 5: Model File Corrupted

**Symptoms:**
- Ollama starts but fails when loading model
- Errors in Ollama logs about model files

**Fix:**
```bash
# Remove and re-pull the model
docker exec ai-chatbot-allinone ollama rm llama3.1:8b
docker exec ai-chatbot-allinone ollama pull llama3.1:8b
```

## Prevention

### 1. Increase Timeout (Already Done)

The timeout has been increased from 120 to 180 seconds for large models.

### 2. Add Health Checks

The code now checks if Ollama is responsive before making requests.

### 3. Pre-load Models on Startup

Ensure models are pulled and loaded during container startup (already in `start.sh`).

## Full Container Restart

If nothing else works:

```bash
# Stop container
docker stop ai-chatbot-allinone

# Start container (data is preserved in volumes)
docker start ai-chatbot-allinone

# Check logs
docker logs -f ai-chatbot-allinone
```

## Check System Resources

```bash
# Check CPU usage
docker stats ai-chatbot-allinone

# Check memory usage
docker exec ai-chatbot-allinone free -h

# Check GPU usage
docker exec ai-chatbot-allinone nvidia-smi
```

## Expected Behavior

After a successful startup:
- Ollama should be running: `supervisorctl status ollama` shows `RUNNING`
- Models should be available: `ollama list` shows your models
- API should respond: `curl http://localhost:11434/api/tags` returns JSON
- Simple query should work: `ollama run llama3.1:8b "test"` returns a response

If any of these fail, Ollama is not working correctly.
