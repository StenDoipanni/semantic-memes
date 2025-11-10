# vLLM Setup Guide

## Quick Fix for Missing Dependencies

If you get a `ModuleNotFoundError: No module named 'packaging'`, install it:

```bash
pip install packaging
```

## Full vLLM Installation

vLLM can be tricky to install. Here are the recommended approaches:

### Option 1: Install vLLM (Recommended for local inference)

```bash
# Install vLLM with CUDA support (if you have a GPU)
pip install vllm

# Or install specific dependencies
pip install packaging safetensors torch transformers
```

### Option 2: Use HuggingFace Transformers API (Alternative)

If vLLM installation is problematic, you can use HuggingFace Transformers directly.
This requires updating the `HuggingFaceProvider` to use Transformers API instead of vLLM.

### Option 3: Use vLLM via Docker (Easiest)

```bash
# Run vLLM in a Docker container
docker run --gpus all -p 8000:8000 \
  --shm-size=10g \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2-VL-7B-Instruct
```

## Start vLLM Server

Once installed, start the server:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2-VL-7B-Instruct \
  --port 8000
```

## Verify Installation

Test if vLLM is working:

```bash
curl http://localhost:8000/v1/models
```

You should see a JSON response with available models.

## Troubleshooting

1. **Missing CUDA**: vLLM requires CUDA for GPU acceleration. Check with:
   ```bash
   nvidia-smi
   ```

2. **Memory Issues**: Large models require significant GPU memory. Try a smaller model:
   ```bash
   python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2-VL-2B-Instruct --port 8000
   ```

3. **Port Conflicts**: If port 8000 is in use, use a different port:
   ```bash
   python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2-VL-7B-Instruct --port 8001
   ```
   Then update the base URL:
   ```bash
   export VLLM_BASE_URL="http://localhost:8001"
   ```

## Alternative: Direct HuggingFace Usage

If vLLM is too complex, you can modify the code to use HuggingFace Transformers directly
without needing a separate server. This would require updating `HuggingFaceProvider`
to use `transformers` library directly instead of vLLM's OpenAI-compatible API.

