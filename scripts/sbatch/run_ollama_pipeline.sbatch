#!/bin/bash
#SBATCH --job-name=ollama_meme_pipeline
#SBATCH --output=logs/slurm/ollama_meme_pipeline_%j.out
#SBATCH --error=logs/slurm/ollama_meme_pipeline_%j.err
#SBATCH --partition=gpu_a100
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -e

echo "🚀 Starting Ollama-powered Meme Pipeline"
echo "========================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo ""

# Load necessary modules
module load 2023
module load Python/3.11.3-GCCcore-12.3.0
module load CUDA/12.1.1

# Set GPU environment variables
export CUDA_VISIBLE_DEVICES=0
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_ORIGINS=*

# GPU-optimized Ollama settings
export OLLAMA_GPU_LAYERS=32
export OLLAMA_GPU_MEMORY_FRACTION=0.8
export OLLAMA_BATCH_SIZE=512
export OLLAMA_CONTEXT_LENGTH=4096
export OLLAMA_NUM_THREAD=8
export OLLAMA_KEEP_ALIVE=5m
export OLLAMA_TIMEOUT=300

# Activate conda environment
source /home/sdegiorgis/miniconda3/bin/activate meme-qa-pipeline-env

# Set pipeline environment variables
# API key should be set via environment variable or .env file
# Do not hardcode API keys in version control
# export CLAUDE_API_KEY="${CLAUDE_API_KEY:-}"
export ONTOLOGY_PATH="/home/sdegiorgis/memes/meme-pipeline-server/memes-features/meme-dimensions.ttl"
export PROMPTS_DIR="/home/sdegiorgis/memes/meme-pipeline-server/prompts/dimension-extraction-prompts"

# Navigate to pipeline directory
cd /home/sdegiorgis/memes/meme-pipeline-server

# Start Ollama service with GPU optimization
echo "🤖 Starting Ollama with GPU optimization..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service to start..."
sleep 10

# Check if Ollama is responding
until curl -s http://localhost:11434/api/tags > /dev/null; do
    echo "⏳ Waiting for Ollama service..."
    sleep 5
done
echo "✅ Ollama service started successfully"

# Check if llama3.2-vision:11b model is available
echo "🔍 Checking for llama3.2-vision:11b model..."
if ! ollama list | grep -q "llama3.2-vision:11b"; then
    echo "📥 Pulling llama3.2-vision:11b model..."
    ollama pull llama3.2-vision:11b
fi
echo "✅ Model ready: llama3.2-vision:11b"

# Test Ollama with a simple prompt
echo "🧪 Testing Ollama connection..."
python3 -c "
from llm_integration import LLMManager
import logging
logging.basicConfig(level=logging.INFO)

llm_manager = LLMManager()
providers = llm_manager.get_available_providers()
print(f'Available providers: {providers}')

if 'ollama' in providers:
    print('Testing Ollama with llama3.2-vision:11b...')
    try:
        response = llm_manager.generate_response(
            'Hello! Please respond with just \"Ollama vision test successful!\"',
            provider='ollama'
        )
        print(f'✅ Ollama response: {response}')
    except Exception as e:
        print(f'❌ Ollama test failed: {e}')
        exit(1)
else:
    print('❌ Ollama provider not available')
    exit(1)
"

# Run the meme pipeline with Ollama
echo "🚀 Running meme pipeline with Ollama..."
echo "======================================"

# Parse command line arguments for the pipeline
IMAGE_PATH="${1:-9_image_batch_2.png}"
MODE="${2:-Core}"

# Resolve bare filenames to ./img directory (keep explicit paths working)
if [[ ! -f "$IMAGE_PATH" ]]; then
    BASENAME_ONLY=$(basename -- "$IMAGE_PATH")
    CANDIDATE_PATH="./img/$BASENAME_ONLY"
    if [[ -f "$CANDIDATE_PATH" ]]; then
        IMAGE_PATH="$CANDIDATE_PATH"
    else
        echo "❌ Error: Image file not found: $IMAGE_PATH"
        echo "Tried also: $CANDIDATE_PATH"
        exit 1
    fi
fi

echo "📊 Configuration:"
echo "  Image: $IMAGE_PATH"
echo "  Mode: $MODE"
echo "  LLM Provider: ollama (llama3.2-vision:11b)"
echo "  GPU: $CUDA_VISIBLE_DEVICES"
echo ""

# Run the pipeline
python scripts/py/run_pipeline.py "$IMAGE_PATH" \
    --mode dimension_extraction \
    --dimensions $([ "$MODE" = "All" ] && echo "TextualMaterial VisualMaterial EmotionExpression ColorComposition SceneUnderstanding BackgroundKnowledge Metadata MetaphoricalAndAnalogicalMapping OverallIntent SemioticInterpretation TargetCommunity TemplateStructure ToxicityAssessment" || echo "TextualMaterial VisualMaterial SceneUnderstanding BackgroundKnowledge") \
    --llm-provider ollama \
    --output-dir ./output

echo ""
echo "🎉 Ollama pipeline completed successfully!"
echo "📁 Check output files in: ./output"

# Clean up
echo "🛑 Stopping Ollama service..."
kill $OLLAMA_PID
echo "✅ Pipeline job completed"
