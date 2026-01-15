# How to Run on RunPod

## Step 1: Build Docker Image

```bash
docker build -t your-username/ai-chatbot:latest .
docker push your-username/ai-chatbot:latest
```

## Step 2: Deploy on RunPod

1. Go to RunPod → **Pods** → **Deploy**
2. **Image**: `your-username/ai-chatbot:latest`
3. **GPU**: RTX 3090 / A4000 (24GB) or better
4. **Ports**: `5000`, `11434`
5. **Environment Variables** (optional):
   ```
   LLM_MODEL=llama3.1:8b
   EMBEDDING_MODEL=llama3.1:8b
   ```
6. **Volumes** (recommended):
   - `/root/.ollama` → Persistent storage for models

## Step 3: Pull Model

After pod starts, SSH in and run:
```bash
ollama pull llama3.1:8b
```

## Step 4: Test

```bash
curl http://localhost:5000/health
```

That's it!

