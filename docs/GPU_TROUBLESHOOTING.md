# GPU Troubleshooting Guide

If you're seeing the same token/s performance on GPU and CPU (e.g., ~0.82 tokens/s), Ollama is likely not using your GPU.

## Quick Diagnosis

### 1. Verify GPU is accessible in container

```bash
# Check if nvidia-smi works in container
docker exec -it ai-chatbot-allinone nvidia-smi
```

**Expected output:** GPU information (name, memory, utilization)
**If it fails:** GPU passthrough is not working - see "GPU Not Accessible" below

### 2. Check Ollama GPU detection

```bash
# Check what Ollama sees
docker exec -it ai-chatbot-allinone ollama ps

# Check Ollama logs for GPU detection
docker logs ai-chatbot-allinone | grep -i gpu
docker logs ai-chatbot-allinone | grep -i cuda
```

### 3. Test GPU inference directly

```bash
# Run a test query and watch GPU usage
docker exec -it ai-chatbot-allinone ollama run llama3.1:8b "Hello, this is a test"
```

While running, check GPU utilization:
```bash
# In another terminal
nvidia-smi -l 1  # Updates every second
```

**Expected:** GPU utilization should spike to 80-100% during inference
**If it stays at 0%:** GPU is not being used

## Common Issues and Fixes

### Issue 1: GPU Not Accessible in Container

**Symptoms:**
- `nvidia-smi` fails in container
- Error: "nvidia-smi: command not found" or "NVIDIA-SMI has failed"

**Solutions:**

1. **Verify NVIDIA Container Toolkit is installed:**
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
   ```

2. **Check Docker daemon configuration** (Linux):
   ```bash
   cat /etc/docker/daemon.json
   ```
   
   Should include:
   ```json
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

4. **On Windows/WSL2:**
   - Ensure you're using WSL 2 (not WSL 1)
   - Install NVIDIA drivers for WSL 2
   - Install NVIDIA Container Toolkit in WSL 2

### Issue 2: Ollama Not Detecting GPU

**Symptoms:**
- `nvidia-smi` works in container
- But Ollama still uses CPU
- Same performance on GPU and CPU

**Solutions:**

1. **Check Ollama version:**
   ```bash
   docker exec -it ai-chatbot-allinone ollama --version
   ```
   Ensure you have a recent version (0.1.20+)

2. **Verify CUDA libraries:**
   ```bash
   docker exec -it ai-chatbot-allinone ldconfig -p | grep cuda
   ```

3. **Check environment variables:**
   Ollama should auto-detect GPU, but you can try:
   ```bash
   # Restart container with explicit CUDA paths
   docker stop ai-chatbot-allinone
   docker run -d --gpus all \
     -e CUDA_VISIBLE_DEVICES=0 \
     ... (rest of your command)
   ```

4. **Force GPU layers:**
   When pulling/running models, Ollama should automatically use GPU. If not:
   ```bash
   # Check model info
   docker exec -it ai-chatbot-allinone ollama show llama3.1:8b
   ```

### Issue 3: Low Performance Even with GPU

**Symptoms:**
- GPU is detected and being used
- But performance is still low (< 5 tokens/s)

**Possible causes:**

1. **Model too large for VRAM:**
   - 8B model needs ~8-10GB VRAM
   - Check available VRAM: `nvidia-smi`
   - Consider using quantized model: `llama3.1:8b-instruct-q4_0`

2. **GPU is old/slow:**
   - Older GPUs (GTX 10xx, etc.) are slower
   - Check GPU compute capability

3. **CPU bottleneck:**
   - Some operations still run on CPU
   - Check CPU usage during inference

4. **Thermal throttling:**
   - GPU overheating
   - Check GPU temperature: `nvidia-smi`

### Issue 4: Performance Calculation Issues

The tokens/s calculation uses `eval_duration` from Ollama's response. If this is incorrect:

1. **Check actual response times:**
   - Look at frontend debug panel
   - Compare with `nvidia-smi` GPU utilization

2. **Verify calculation:**
   - Tokens/s = `eval_count / eval_duration`
   - `eval_duration` is in nanoseconds, converted to seconds

## Expected Performance

With proper GPU acceleration:
- **llama3.1:8b on RTX 3080/4080**: 20-40 tokens/s
- **llama3.1:8b on RTX 3090/4090**: 30-50 tokens/s
- **llama3.1:8b on RTX 3060/4060**: 10-20 tokens/s
- **CPU only**: 1-5 tokens/s

If you're getting ~0.82 tokens/s, that's CPU performance - GPU is not being used.

## Debug Commands

```bash
# Full diagnostic
docker exec -it ai-chatbot-allinone bash -c "
  echo '=== GPU Check ===' && 
  nvidia-smi || echo 'nvidia-smi failed' && 
  echo '' && 
  echo '=== Ollama Check ===' && 
  ollama ps && 
  echo '' && 
  echo '=== CUDA Check ===' && 
  ldconfig -p | grep cuda | head -5
"

# Test inference with timing
time docker exec -it ai-chatbot-allinone ollama run llama3.1:8b "Test"
```

## Still Not Working?

1. Check the debug panel in the frontend - it shows GPU status
2. Check container logs: `docker logs ai-chatbot-allinone`
3. Verify your GPU is CUDA-compatible
4. Try a smaller model first: `llama3.1:3b` to test GPU detection
