# GPU Setup for Ollama

This guide explains how to enable GPU acceleration for Ollama in the Docker container.

## Prerequisites

1. **NVIDIA GPU** with CUDA support
2. **NVIDIA drivers** installed on your host system
3. **NVIDIA Container Toolkit** installed on your host

## Step 1: Install NVIDIA Container Toolkit

### On Linux (Ubuntu/Debian):

```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker daemon
sudo systemctl restart docker
```

### On Windows:

1. Install **Docker Desktop** with WSL 2 backend
2. Install **NVIDIA drivers** for Windows
3. Install **NVIDIA Container Toolkit** for WSL 2:
   ```powershell
   # In WSL 2 terminal
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

## Step 2: Verify GPU Access

Test that Docker can see your GPU:

```bash
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

You should see your GPU information. If not, check your NVIDIA Container Toolkit installation.

## Step 3: Run Container with GPU Support

The Docker run command includes `--gpus all` flag:

```bash
docker run -d --gpus all -p 5000:5000 -p 7700:7700 -p 5432:5432 -p 11434:11434 \
  -e OLLAMA_URL=http://localhost:11434 \
  -e OLLAMA_MODEL=llama3.1:8b \
  -e OLLAMA_EMBEDDING_MODEL=nomic-embed-text \
  -e DATABASE_URL=postgresql://ai_chatbot:ai_chatbot123@localhost:5432/ai_chatbot_db \
  -e MEILISEARCH_URL=http://localhost:7700 \
  -e MEILISEARCH_KEY=masterKey123 \
  -v ai-chatbot-postgres-data:/var/lib/postgresql/data \
  -v ai-chatbot-meilisearch-data:/var/lib/meilisearch \
  -v ai-chatbot-ollama-data:/root/.ollama \
  --name ai-chatbot-allinone ai-chatbot-allinone
```

## Step 4: Verify GPU Usage

Check if Ollama is using the GPU:

```bash
# Check GPU usage from host
nvidia-smi

# Check from inside container
docker exec -it ai-chatbot-allinone nvidia-smi

# Check Ollama is using GPU
docker exec -it ai-chatbot-allinone ollama run llama3.1:8b "Hello, test GPU"
```

## Troubleshooting

### GPU not detected in container

1. **Verify NVIDIA Container Toolkit is installed:**
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
   ```

2. **Check Docker daemon configuration:**
   ```bash
   # On Linux, ensure /etc/docker/daemon.json includes:
   {
     "runtimes": {
       "nvidia": {
         "path": "nvidia-container-runtime",
         "runtimeArgs": []
       }
     }
   }
   ```

3. **Restart Docker:**
   ```bash
   sudo systemctl restart docker
   ```

### Ollama still using CPU

1. **Check Ollama logs:**
   ```bash
   docker logs ai-chatbot-allinone | grep -i ollama
   ```

2. **Verify CUDA is available:**
   ```bash
   docker exec -it ai-chatbot-allinone ollama ps
   ```

3. **Force GPU usage:**
   Ollama should automatically detect and use GPU if available. If not, check:
   - GPU drivers are up to date
   - CUDA version compatibility
   - Container has GPU access (`--gpus all` flag)

### Performance Issues

- **Model size**: Larger models (8B+) require more VRAM
- **VRAM check**: Ensure you have enough GPU memory:
  ```bash
  nvidia-smi
  ```
- **Batch size**: Ollama automatically adjusts based on available VRAM

## Expected Performance

With GPU acceleration:
- **8B model**: ~20-50 tokens/second (depending on GPU)
- **CPU only**: ~2-5 tokens/second

The debug panel in the frontend will show "GPU" status when GPU is being used.
