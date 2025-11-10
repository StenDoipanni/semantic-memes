"""
Server Configuration for Meme Analysis Pipeline

This configuration is optimized for server deployment with local LLMs.
"""

import os
from pathlib import Path

# Server-specific paths
SERVER_BASE_DIR = Path("/opt/meme-pipeline")
SERVER_OUTPUT_DIR = SERVER_BASE_DIR / "output"
SERVER_ONTOLOGY_PATH = SERVER_BASE_DIR / "memes-features" / "meme-dimensions.ttl"
SERVER_PROMPTS_DIR = SERVER_BASE_DIR / "memes-features" / "prompts" / "dimension-extraction-prompts"

# LLM Configuration for Server
class ServerLLMConfig:
    """Configuration for server-based LLM integrations."""
    
    # HuggingFace/Transformers settings (primary for server)
    HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen3-VL-8B-Instruct")  # Vision-language model
    HUGGINGFACE_DEVICE = os.getenv("HUGGINGFACE_DEVICE", "cuda")  # Use CUDA on server with A100 GPUs
    HUGGINGFACE_MAX_TOKENS = 4000
    HUGGINGFACE_TEMPERATURE = 0.1
    HUGGINGFACE_MAX_IMAGE_SIZE = (1024, 1024)
    
    # Claude API settings (fallback)
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
    CLAUDE_MAX_TOKENS = 4000
    CLAUDE_TEMPERATURE = 0.1
    CLAUDE_MAX_IMAGE_SIZE = (4096, 4096)
    
    # Processing settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    BATCH_SIZE = 5  # Process images in batches on server

# Server-specific environment variables
SERVER_ENV_VARS = {
    "ONTOLOGY_PATH": str(SERVER_ONTOLOGY_PATH),
    "PROMPTS_DIR": str(SERVER_PROMPTS_DIR),
    "OUTPUT_DIR": str(SERVER_OUTPUT_DIR),
    "LLM_PROVIDER": "huggingface",  # Default to HuggingFace/vLLM on server
    "SERVER_MODE": "true"
}

# Available models on server (update based on your server setup)
AVAILABLE_MODELS = [
    "Qwen/Qwen2-VL-7B-Instruct",  # Vision-language model
    "Qwen/Qwen2-VL-2B-Instruct",  # Smaller vision-language model
    "Qwen/Qwen2.5-7B-Instruct",  # Text-only model
    "Qwen/Qwen2.5-32B-Instruct",  # Larger text-only model
]

# Server deployment settings
DEPLOYMENT_SETTINGS = {
    "create_output_dirs": True,
    "setup_permissions": True,
    "install_dependencies": True,
    "configure_vllm": True
}

