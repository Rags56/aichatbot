# Rebuild Instructions

When you make changes to the backend or frontend code, you need to rebuild/restart the services.

## Backend (Docker Container)

### Option 1: Restart Container (If code is mounted as volume)
If your code is mounted as a volume, just restart:
```bash
docker restart ai-chatbot-allinone
```

### Option 2: Rebuild Container (If code is baked into image)
Since the Dockerfile copies code into the image, you need to rebuild:

```bash
# Stop and remove the container
docker stop ai-chatbot-allinone
docker rm ai-chatbot-allinone

# Rebuild the image
docker build --no-cache -f docker/all-in-one.Dockerfile -t ai-chatbot-allinone .

# Start the container again
docker run -d --gpus all -p 5000:5000 -p 7700:7700 -p 5432:5432 -p 11434:11434 -e OLLAMA_URL=http://localhost:11434 -e OLLAMA_MODEL=llama3.1:8b -e OLLAMA_EMBEDDING_MODEL=nomic-embed-text -e DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db -e MEILISEARCH_URL=http://localhost:7700 -e MEILISEARCH_KEY=masterKey123 -v ai-chatbot-postgres-data:/var/lib/postgresql/data -v ai-chatbot-meilisearch-data:/var/lib/meilisearch -v ai-chatbot-ollama-data:/root/.ollama --name ai-chatbot-allinone ai-chatbot-allinone
```

### Option 3: Quick Restart (Preserves data)
```bash
# Just restart - this preserves all volumes
docker restart ai-chatbot-allinone

# If that doesn't work, rebuild:
docker stop ai-chatbot-allinone
docker rm ai-chatbot-allinone
docker build -f docker/all-in-one.Dockerfile -t ai-chatbot-allinone .
docker run -d --gpus all -p 5000:5000 -p 7700:7700 -p 5432:5432 -p 11434:11434 -e OLLAMA_URL=http://localhost:11434 -e OLLAMA_MODEL=llama3.1:8b -e OLLAMA_EMBEDDING_MODEL=nomic-embed-text -e DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db -e MEILISEARCH_URL=http://localhost:7700 -e MEILISEARCH_KEY=masterKey123 -v ai-chatbot-postgres-data:/var/lib/postgresql/data -v ai-chatbot-meilisearch-data:/var/lib/meilisearch -v ai-chatbot-ollama-data:/root/.ollama --name ai-chatbot-allinone ai-chatbot-allinone
```

## Frontend (Next.js)

### If running with `npm run dev`:
1. Stop the dev server (Ctrl+C)
2. Restart it:
   ```bash
   cd frontend
   npm run dev
   ```
3. Hard refresh the browser (Ctrl+Shift+R or Cmd+Shift+R)

### If running in production mode:
```bash
cd frontend
npm run build
npm start
```

## Verify Changes

### Check Backend is Running:
```bash
# Check container status
docker ps | grep ai-chatbot-allinone

# Check logs
docker logs --tail 50 ai-chatbot-allinone

# Test API
curl http://localhost:5000/health
```

### Check Frontend:
- Open browser console (F12)
- Check for any errors
- Verify the pipeline timing panel appears after sending a message

## Quick Debug Checklist

1. ✅ Backend container is running: `docker ps | grep ai-chatbot-allinone`
2. ✅ Backend logs show no errors: `docker logs --tail 100 ai-chatbot-allinone`
3. ✅ Frontend dev server is running: Check terminal where `npm run dev` is running
4. ✅ Browser console has no errors: Open F12 → Console tab
5. ✅ Send a test message and check if pipeline timing appears

## Common Issues

### Backend changes not showing:
- **Solution**: Rebuild the Docker image (Option 2 above)
- The code is copied into the image during build, so changes require rebuild

### Frontend changes not showing:
- **Solution**: Hard refresh browser (Ctrl+Shift+R)
- Or restart the dev server

### Pipeline timing still not showing:
1. Check browser console for errors
2. Check if `sessionStorage.getItem('lastPipelineTiming')` has data:
   - Open browser console (F12)
   - Type: `JSON.parse(sessionStorage.getItem('lastPipelineTiming'))`
   - Should show timing data
3. Check backend response includes `pipeline_timing`:
   - Send a message
   - Check Network tab in browser dev tools
   - Look at the `/api/ai/chat` response
   - Should have `meta.pipeline_timing` object
