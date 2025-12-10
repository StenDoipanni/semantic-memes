#!/bin/bash
#SBATCH --job-name=meme_pipeline
#SBATCH --output=logs/slurm/meme_pipeline_%j.out
#SBATCH --error=logs/slurm/meme_pipeline_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -e

echo "🚀 Starting Meme Pipeline Job"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "=================================="

# Load modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0

# Navigate to the pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Install dependencies if needed
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Start Ollama service with GPU support
echo "🤖 Starting Ollama with GPU support..."
export OLLAMA_HOST=0.0.0.0:11434
export CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
sleep 10

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Failed to start Ollama service"
    exit 1
fi

echo "✅ Ollama service started successfully"

# Pull the model if not already available
echo "📥 Checking for qwen3:8b model..."
if ! ollama list | grep -q "qwen3:8b"; then
    echo "📥 Pulling qwen3:8b model..."
    ollama pull qwen3:8b
fi

echo "✅ Model ready: qwen3:8b"

# Test the pipeline
echo "🧪 Testing pipeline components..."
python3 test_pipeline.py

# If we have a test image, run the full pipeline
if [ -f "test_image.jpg" ]; then
    echo "🖼️  Running pipeline on test image..."
    python3 scripts/py/run_pipeline.py test_image.jpg \
        --mode Core \
        --llm-provider ollama \
        --model qwen3:8b \
        --output-dir ./output
else
    echo "⚠️  No test image found. Creating a simple test..."
    # Create a simple test without image
    python3 -c "
import sys
sys.path.append('.')
from llm_integration import LLMManager
from config import LLMConfig

# Test LLM connection
llm_manager = LLMManager()
if llm_manager.is_available('ollama'):
    print('✅ LLM connection successful')
    # Test a simple prompt
    response = llm_manager.generate_response('Hello, how are you?', provider='ollama')
    print(f'✅ LLM response: {response[:100]}...')
else:
    print('❌ LLM connection failed')
"

echo "🎉 Pipeline setup completed successfully!"
echo "=================================="
echo "✅ Ollama service running on GPU"
echo "✅ Model qwen3:8b loaded"
echo "✅ Pipeline ready for processing"
echo ""
echo "To run the pipeline on an image:"
echo "python3 scripts/py/run_pipeline.py <image_path> --mode Core --llm-provider ollama --model qwen3:8b"
echo ""
echo "To stop the service:"
echo "pkill -f ollama"
