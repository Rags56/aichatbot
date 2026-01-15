# Docker Debugging Guide

This guide shows you how to check exact errors and debug issues in the Docker container.

## View Container Logs

### 1. View All Logs (Most Recent First)

```bash
docker logs ai-chatbot-allinone
```

### 2. Follow Logs in Real-Time (Like `tail -f`)

```bash
docker logs -f ai-chatbot-allinone
```

### 3. View Last N Lines

```bash
# Last 100 lines
docker logs --tail 100 ai-chatbot-allinone

# Last 500 lines
docker logs --tail 500 ai-chatbot-allinone
```

### 4. View Logs with Timestamps

```bash
docker logs -t ai-chatbot-allinone
```

### 5. View Logs Since Specific Time

```bash
# Last 10 minutes
docker logs --since 10m ai-chatbot-allinone

# Last hour
docker logs --since 1h ai-chatbot-allinone

# Since specific time
docker logs --since "2024-01-15T10:00:00" ai-chatbot-allinone
```

## Filter Logs by Service

### View Only Python Backend Logs

```bash
docker logs ai-chatbot-allinone 2>&1 | grep -i "backend\|python\|Error\|Traceback"
```

### View Only Ollama Logs

```bash
docker logs ai-chatbot-allinone 2>&1 | grep -i "ollama"
```

### View Only PostgreSQL Logs

```bash
docker logs ai-chatbot-allinone 2>&1 | grep -i "postgres\|database"
```

### View Only Errors

```bash
docker logs ai-chatbot-allinone 2>&1 | grep -i "error\|exception\|traceback\|failed"
```

## Execute Commands Inside Container

### 1. Open Interactive Shell

```bash
docker exec -it ai-chatbot-allinone /bin/bash
```

Once inside, you can:
- Check Python errors: `python -c "import sys; print(sys.path)"`
- Test Ollama: `ollama ps`
- Test PostgreSQL: `psql -U ai_chatbot -d ai_chatbot_db`
- Check processes: `ps aux`
- View environment variables: `env | grep -i ollama`

### 2. Run Single Commands

```bash
# Check if Ollama is running
docker exec ai-chatbot-allinone ollama ps

# Check Python version
docker exec ai-chatbot-allinone python --version

# Test database connection
docker exec ai-chatbot-allinone psql -U ai_chatbot -d ai_chatbot_db -c "SELECT 1"

# Check if services are running
docker exec ai-chatbot-allinone supervisorctl status
```

## Check Supervisor Status

Supervisor manages all services in the container:

```bash
# Check status of all services
docker exec ai-chatbot-allinone supervisorctl status

# View supervisor logs
docker exec ai-chatbot-allinone supervisorctl tail -f backend
docker exec ai-chatbot-allinone supervisorctl tail -f ollama
docker exec ai-chatbot-allinone supervisorctl tail -f postgres
docker exec ai-chatbot-allinone supervisorctl tail -f meilisearch
```

## View Real-Time Python Errors

### Follow Backend Logs Only

```bash
docker logs -f ai-chatbot-allinone 2>&1 | grep --line-buffered -i "error\|exception\|traceback"
```

### View Full Python Traceback

```bash
docker logs ai-chatbot-allinone 2>&1 | grep -A 20 "Traceback"
```

## Check Container Health

### 1. Check Container Status

```bash
docker ps -a | grep ai-chatbot-allinone
```

### 2. Check Resource Usage

```bash
docker stats ai-chatbot-allinone
```

### 3. Inspect Container Configuration

```bash
docker inspect ai-chatbot-allinone
```

## Test API Endpoints

### From Host Machine

```bash
# Health check
curl http://localhost:5000/health

# Debug endpoint
curl http://localhost:5000/api/ai/debug

# Test chat (replace with your query)
curl -X POST http://localhost:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"userId": "1", "message": "test"}'
```

### From Inside Container

```bash
docker exec ai-chatbot-allinone curl http://localhost:5000/health
docker exec ai-chatbot-allinone curl http://localhost:5000/api/ai/debug
```

## Common Debugging Scenarios

### Scenario 1: Python Error with Full Traceback

```bash
# Get last 200 lines and search for errors
docker logs --tail 200 ai-chatbot-allinone 2>&1 | grep -B 5 -A 20 "Error\|Traceback"
```

### Scenario 2: Service Not Starting

```bash
# Check supervisor status
docker exec ai-chatbot-allinone supervisorctl status

# View service-specific logs
docker exec ai-chatbot-allinone supervisorctl tail -100 backend
docker exec ai-chatbot-allinone supervisorctl tail -100 ollama
```

### Scenario 3: Database Connection Issues

```bash
# Test PostgreSQL connection
docker exec ai-chatbot-allinone psql -U ai_chatbot -d ai_chatbot_db -c "SELECT version();"

# Check PostgreSQL logs
docker logs ai-chatbot-allinone 2>&1 | grep -i postgres
```

### Scenario 4: Ollama Not Working

```bash
# Check if Ollama is running
docker exec ai-chatbot-allinone ollama ps

# Test Ollama API
docker exec ai-chatbot-allinone curl http://localhost:11434/api/tags

# Check Ollama logs
docker logs ai-chatbot-allinone 2>&1 | grep -i ollama
```

### Scenario 5: GPU Not Detected

```bash
# Check if GPU is accessible
docker exec ai-chatbot-allinone nvidia-smi

# Check CUDA libraries
docker exec ai-chatbot-allinone ldconfig -p | grep cuda
```

## Save Logs to File

```bash
# Save all logs
docker logs ai-chatbot-allinone > docker_logs.txt 2>&1

# Save only errors
docker logs ai-chatbot-allinone 2>&1 | grep -i "error\|exception\|traceback" > errors.txt

# Save with timestamps
docker logs -t ai-chatbot-allinone > logs_with_timestamps.txt 2>&1
```

## Restart Container for Fresh Logs

```bash
# Restart container
docker restart ai-chatbot-allinone

# Follow logs immediately after restart
docker logs -f ai-chatbot-allinone
```

## Quick Debug Checklist

When debugging an error:

1. **Get the exact error:**
   ```bash
   docker logs --tail 100 ai-chatbot-allinone 2>&1 | grep -B 10 -A 20 "Error"
   ```

2. **Check which service failed:**
   ```bash
   docker exec ai-chatbot-allinone supervisorctl status
   ```

3. **View service-specific logs:**
   ```bash
   docker exec ai-chatbot-allinone supervisorctl tail -f backend
   ```

4. **Test the failing component directly:**
   ```bash
   docker exec -it ai-chatbot-allinone /bin/bash
   # Then test the component manually
   ```

5. **Check environment variables:**
   ```bash
   docker exec ai-chatbot-allinone env | grep -E "OLLAMA|DATABASE|MEILI"
   ```

## Tips

- Use `-f` flag to follow logs in real-time while testing
- Use `--tail` to limit output to recent logs
- Combine with `grep` to filter for specific errors
- Use `supervisorctl` to check individual service status
- Save logs to file for detailed analysis
